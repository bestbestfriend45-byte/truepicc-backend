import os
import time
import hmac
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests
import qrcode
from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.status import HTTP_302_FOUND
from nanoid import generate
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from .database import ENGINE, Base, Photo, PhotoAudit
from .utils import make_web_copy

# ----- Конфигурация -----
API_KEY = os.environ.get("TRUEPICC_API_KEY", "demo-dev-key")
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
HMAC_SECRET = os.environ.get("TRUEPICC_HMAC_SECRET", "dev-hmac-secret").encode("utf-8")
MAX_SKEW_SEC = 300  # ±5 минут

ADMIN_USER = os.environ.get("TRUEPICC_ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("TRUEPICC_ADMIN_PASS", "admin123")
SESSION_SECRET = os.environ.get("TRUEPICC_ADMIN_SESSION_SECRET", "change-this-session-secret")
GMAPS_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")

# ----- Приложение / ресурсы -----
Base.metadata.create_all(ENGINE)

app = FastAPI(title="Truepicc API")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, max_age=24*3600)

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
STORAGE_DIR = BASE_DIR / "storage"
STORAGE_ORIG = STORAGE_DIR / "original"
STORAGE_WEB  = STORAGE_DIR / "web"
STORAGE_QR   = STORAGE_DIR / "qr"

for d in (STORAGE_DIR, STORAGE_ORIG, STORAGE_WEB, STORAGE_QR):
    d.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/storage", StaticFiles(directory=str(STORAGE_DIR)), name="storage")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# ----- Утилиты -----
def auth_check(authorization: Optional[str], x_api_key: Optional[str]):
    key = None
    if authorization and authorization.startswith("ApiKey "):
        key = authorization.split(" ", 1)[1].strip()
    elif x_api_key:
        key = x_api_key.strip()
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def reverse_geocode(lat: float, lon: float) -> Optional[str]:
    """Адрес: Google (если есть ключ) -> OSM fallback."""
    try:
        if GMAPS_KEY:
            r = requests.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params={"latlng": f"{lat:.6f},{lon:.6f}", "key": GMAPS_KEY, "language": "ru"},
                timeout=5,
            )
            if r.ok:
                data = r.json()
                results = data.get("results", [])
                if results:
                    return results[0].get("formatted_address")
        r = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"format": "jsonv2", "lat": f"{lat:.6f}", "lon": f"{lon:.6f}", "accept-language": "ru"},
            headers={"User-Agent": "Truepicc/1.0"},
            timeout=5,
        )
        if r.ok:
            data = r.json()
            return data.get("display_name")
    except Exception:
        pass
    return None

def build_static_map_url(lat: float, lon: float) -> Optional[str]:
    """Google Static Maps (уменьшенная карта ~213x120)."""
    if not GMAPS_KEY:
        return None
    return (
        "https://maps.googleapis.com/maps/api/staticmap"
        f"?center={lat:.6f},{lon:.6f}"
        "&zoom=16&size=213x120&maptype=roadmap"
        f"&markers=color:red%7C{lat:.6f},{lon:.6f}"
        f"&key={GMAPS_KEY}"
    )

def ensure_qr(photo_id: str, verify_url: str) -> Path:
    qr_path = STORAGE_QR / f"{photo_id}.png"
    if not qr_path.exists():
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=6, border=2)
        qr.add_data(verify_url); qr.make(fit=True)
        qr.make_image(fill_color="black", back_color="white").save(qr_path)
    return qr_path

# ----- Публичные страницы / API -----
@app.get("/", response_class=HTMLResponse)
def root():
    return "<h3>Truepicc backend is running</h3><p>POST /api/v1/upload</p>"

@app.post("/api/v1/upload")
async def upload(
    request: Request,
    image: UploadFile = File(...),
    device_time_utc: str = Form(...),
    tz_offset_min: int = Form(...),
    lat: float = Form(...),
    lon: float = Form(...),
    accuracy_m: Optional[float] = Form(None),
    altitude_m: Optional[float] = Form(None),
    provider: Optional[str] = Form(None),
    is_mock: bool = Form(...),
    device_model: str = Form(...),
    android_api: int = Form(...),
    app_version: str = Form(...),
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None),
    x_timestamp: Optional[str] = Header(None),
    x_nonce: Optional[str] = Header(None),
    x_sign: Optional[str] = Header(None),
    x_client: Optional[str] = Header(None),
):
    auth_check(authorization, x_api_key)

    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise HTTPException(400, "Invalid coordinates")

    if not (x_timestamp and x_nonce and x_sign):
        raise HTTPException(401, "Missing signature headers")
    try:
        ts = int(x_timestamp)
    except Exception:
        raise HTTPException(401, "Bad x-timestamp")
    now = int(time.time())
    if abs(now - ts) > MAX_SKEW_SEC:
        raise HTTPException(401, f"Clock skew too large ({abs(now - ts)}s)")

    content = await image.read()
    file_hash = sha256_bytes(content)

    lat_str = f"{lat:.6f}"
    lon_str = f"{lon:.6f}"
    string_to_sign = (
        f"device_time_utc={device_time_utc}\n"
        f"lat={lat_str}\n"
        f"lon={lon_str}\n"
        f"file_sha256={file_hash}\n"
        f"nonce={x_nonce}\n"
        f"ts={x_timestamp}"
    )
    expected = hmac.new(HMAC_SECRET, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, (x_sign or "").lower()):
        raise HTTPException(401, "Bad signature")

    now_utc = now_utc_iso()
    photo_id = generate("0123456789abcdefghijklmnopqrstuvwxyz", 10)

    orig_path = STORAGE_ORIG / f"{photo_id}.jpg"
    with open(orig_path, "wb") as f:
        f.write(content)

    web_path = STORAGE_WEB / f"{photo_id}.jpg"
    make_web_copy(orig_path, web_path, max_side=1600, quality=85)

    with Session(ENGINE) as s:
        p = Photo(
            id=photo_id,
            created_server_utc=now_utc,
            device_time_utc=device_time_utc,
            tz_offset_min=int(tz_offset_min),
            lat=float(lat), lon=float(lon),
            accuracy_m=float(accuracy_m) if accuracy_m is not None else None,
            altitude_m=float(altitude_m) if altitude_m is not None else None,
            provider=provider,
            is_mock=bool(is_mock),
            device_model=device_model,
            android_api=int(android_api),
            app_version=app_version,
            image_key_original=f"storage/original/{photo_id}.jpg",
            image_key_web=f"storage/web/{photo_id}.jpg",
            hash_sha256=file_hash,
        )
        s.add(p)
        s.commit()

    verify_url = f"{PUBLIC_BASE_URL}/verify/{photo_id}"
    ensure_qr(photo_id, verify_url)

    return JSONResponse({"id": photo_id, "verify_url": verify_url})

@app.get("/verify/{photo_id}", response_class=HTMLResponse)
def verify_page(request: Request, photo_id: str):
    with Session(ENGINE) as s:
        p = s.get(Photo, photo_id)
        if not p:
            return HTMLResponse("<h3>Not found</h3>", status_code=404)

        verify_url = f"{PUBLIC_BASE_URL}/verify/{p.id}"
        qr_path = ensure_qr(p.id, verify_url)
        place = reverse_geocode(p.lat, p.lon)
        static_map_url = build_static_map_url(p.lat, p.lon)
        embed_map_url = f"https://www.google.com/maps?q={p.lat:.6f},{p.lon:.6f}&z=16&output=embed"

        # ВАЖНО: передаём device_time_utc — это "время снимка"
        return templates.TemplateResponse("verify.html", {
            "request": request,
            "img_web": f"/{p.image_key_web}",
            "qr_png": f"/storage/qr/{p.id}.png",
            "has_qr": qr_path.exists(),
            "place_name": place,
            "lat": p.lat, "lon": p.lon,
            "device_time_utc": p.device_time_utc,
            "verify_url": verify_url,
            "static_map_url": static_map_url,
            "embed_map_url": embed_map_url,
        })

# ----- Админка (логин, список, правка) -----
@app.get("/admin/login", response_class=HTMLResponse)
def admin_login_page(request: Request):
    return templates.TemplateResponse("admin_login.html", {"request": request, "error": None})

@app.post("/admin/login")
async def admin_login(request: Request):
    form = await request.form()
    user = form.get("username", "")
    pwd = form.get("password", "")
    if user == ADMIN_USER and pwd == ADMIN_PASS:
        request.session["is_admin"] = True
        request.session["admin_user"] = user
        return RedirectResponse(url="/admin/photos", status_code=HTTP_302_FOUND)
    return templates.TemplateResponse("admin_login.html", {"request": request, "error": "Неверные данные"}, status_code=401)

@app.get("/admin/logout")
def admin_logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/admin/login", status_code=HTTP_302_FOUND)

@app.get("/admin")
def admin_root():
    return RedirectResponse(url="/admin/photos", status_code=HTTP_302_FOUND)

@app.get("/admin/photos", response_class=HTMLResponse)
def admin_photos(request: Request, q: Optional[str] = None, page: int = 1, page_size: int = 50):
    def require_admin(req: Request):
        return req.session.get("is_admin") is True
    if not require_admin(request):
        return RedirectResponse(url="/admin/login", status_code=HTTP_302_FOUND)

    page = max(1, page)
    page_size = max(1, min(page_size, 200))

    with Session(ENGINE) as s:
        stmt = select(Photo)
        if q:
            stmt = stmt.filter(Photo.id.contains(q))
        stmt = stmt.order_by(desc(Photo.created_server_utc)).limit(page_size).offset((page-1)*page_size)
        rows = s.execute(stmt).scalars().all()

    return templates.TemplateResponse("admin_list.html", {
        "request": request, "rows": rows, "q": q or "", "page": page, "page_size": page_size
    })
