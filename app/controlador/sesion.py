from fastapi import HTTPException, Request
from app.models import cuentas


def current_user(request: Request) -> int:
    cid = request.session.get("cliente_id")
    if not cid:
        raise HTTPException(401, "Inicia sesión para continuar.")
    cuenta = cuentas.obtener(int(cid))
    if not cuenta or not cuenta["activo"]:
        request.session.clear()
        raise HTTPException(401, "La cuenta ya no está disponible.")
    return int(cid)


def require_admin(request: Request) -> int:
    cid = current_user(request)
    cuenta = cuentas.obtener(cid)
    if cuenta["rol"] != "admin":
        raise HTTPException(403, "Solo administradores pueden realizar esta acción.")
    return cid
