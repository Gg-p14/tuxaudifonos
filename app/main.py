import logging
import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from app.controlador.routes import router
from app.controlador.admin_routes import router as admin_router
from app.db.database import check_db_connection, initialize_database

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("tuxaudifonos")

BASE_DIR = Path(__file__).resolve().parent.parent
FRONT_DIR = BASE_DIR / "frontt"

try:
    from dotenv import load_dotenv
    load_dotenv()  # Lee el archivo .env de la carpeta del proyecto
except ImportError:
    pass
SECRETO = os.getenv("SESSION_SECRET")
if not SECRETO:
    SECRETO = secrets.token_urlsafe(32)
    log.warning("SESSION_SECRET no definido: se usa una clave temporal. Las sesiones se pierden al reiniciar.")

@asynccontextmanager
async def ciclo_vida(_app: FastAPI):
    initialize_database()
    log.info("Base de datos SQL Server lista.")
    yield


app = FastAPI(title="TuxAudifonos", version="3.0.0", lifespan=ciclo_vida)
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRETO,
    same_site="lax",
    https_only=os.getenv("HTTPS_ONLY", "0") == "1",
    max_age=60 * 60 * 12,
)
app.mount("/static", StaticFiles(directory=FRONT_DIR), name="static")
app.include_router(router, prefix="/api")
app.include_router(admin_router, prefix="/api")

PAGINAS = {
    "/": "index.html",
    "/producto": "producto.html",
    "/carrito": "carrito.html",
    "/checkout": "checkout.html",
    "/pedidos": "pedidos.html",
    "/pedido": "pedido.html",
    "/perfil": "perfil.html",
    "/iniciar-sesion": "login.html",
    "/registro": "registro.html",
    "/admin": "admin.html",
}


def _vista(archivo: str):
    def responder():
        return FileResponse(FRONT_DIR / archivo)
    return responder


for ruta, archivo in PAGINAS.items():
    app.add_api_route(ruta, _vista(archivo), methods=["GET"], include_in_schema=False)


@app.get("/health", include_in_schema=False)
def health():
    return {"status": "TuxAudifonos funcionando"}


@app.get("/health/database", tags=["salud"])
def health_database():
    try:
        return {"status": "conectada", **check_db_connection()}
    except Exception as exc:
        log.exception("Fallo de conexión con SQL Server")
        raise HTTPException(503, "No se pudo conectar con SQL Server. Revisa DB_SERVER, DB_NAME y el controlador ODBC.") from exc
