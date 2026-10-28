import logging
from fastapi import APIRouter, HTTPException, Query, Request
from app.controlador.sesion import current_user
from app.models import catalogo, cuentas, ventas
from app.models.seguridad import (hash_password, verify_password, login_bloqueado,
                                  registrar_fallo, reiniciar_intentos)
from app.vista.audifonos import (AudifonoIn, RegistroSchema, LoginSchema, PerfilSchema,
                                 DireccionIn, DireccionUpdate, CompraIn, ResenaIn)

log = logging.getLogger("tuxaudifonos")
router = APIRouter()


def _error_bd(mensaje: str, exc: Exception):
    log.exception(mensaje)
    return HTTPException(503, "No se pudo completar la operación. Intenta de nuevo más tarde.")


def _publico(c: dict) -> dict:
    return {k: c[k] for k in ("id_cliente", "nombre", "apellidos", "correo", "telefono", "rol")}


# ---------- Catálogo (público) ----------
@router.get("/categorias")
def categorias():
    try:
        return catalogo.catalogos()
    except Exception as e:
        raise _error_bd("categorias", e)


@router.get("/audifonos/")
def listar_audifonos(categoria: str | None = None, q: str | None = Query(default=None, max_length=80),
                     orden: str = Query(default="destacados", pattern="^(destacados|precio_asc|precio_desc|nuevos)$"),
                     disponibles: bool = False):
    try:
        return catalogo.listar(categoria=categoria, buscar=q, orden=orden, solo_disponibles=disponibles)
    except Exception as e:
        raise _error_bd("listar", e)


@router.get("/audifonos/{id_audifono}")
def detalle_audifono(id_audifono: int):
    try:
        producto = catalogo.obtener(id_audifono)
        if not producto:
            raise HTTPException(404, "Producto no encontrado.")
        producto["resenas"] = catalogo.resenas_de(id_audifono)
        return producto
    except HTTPException:
        raise
    except Exception as e:
        raise _error_bd("detalle", e)


@router.post("/audifonos/{id_audifono}/resenas")
def resenar(id_audifono: int, data: ResenaIn, request: Request):
    cid = current_user(request)
    try:
        catalogo.agregar_resena(id_audifono, cid, data.calificacion, data.comentario.strip())
        return {"message": "Gracias por tu calificación."}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise _error_bd("resena", e)


# ---------- Autenticación ----------
@router.post("/auth/registro")
def registro(data: RegistroSchema, request: Request):
    try:
        cid = cuentas.crear(data.model_dump(), hash_password(data.password))
    except ValueError as e:
        raise HTTPException(409, str(e))
    except Exception as e:
        raise _error_bd("registro", e)
    request.session.clear()
    request.session["cliente_id"] = cid
    return {"message": "Cuenta creada correctamente",
            "usuario": _publico({**data.model_dump(exclude={"password"}), "id_cliente": cid,
                                 "correo": data.correo.lower(), "rol": "cliente"})}


@router.post("/auth/login")
def login(data: LoginSchema, request: Request):
    clave = data.correo.lower()
    if login_bloqueado(clave):
        raise HTTPException(429, "Demasiados intentos fallidos. Espera 15 minutos e intenta de nuevo.")
    try:
        u = cuentas.buscar_por_correo(clave)
    except Exception as e:
        raise _error_bd("login", e)
    if not u or not u["activo"] or not verify_password(data.password, u["password_hash"]):
        registrar_fallo(clave)
        raise HTTPException(401, "Correo o contraseña incorrectos.")
    reiniciar_intentos(clave)
    request.session.clear()
    request.session["cliente_id"] = u["id_cliente"]
    return {"message": "Sesión iniciada", "usuario": _publico(u)}


@router.post("/auth/logout")
def logout(request: Request):
    request.session.clear()
    return {"message": "Sesión cerrada"}


@router.get("/auth/me")
def me(request: Request):
    cid = current_user(request)
    try:
        return {"usuario": _publico(cuentas.obtener(cid))}
    except Exception as e:
        raise _error_bd("me", e)


@router.put("/auth/perfil")
def perfil(data: PerfilSchema, request: Request):
    cid = current_user(request)
    try:
        cuentas.actualizar_perfil(cid, data.model_dump())
        return {"message": "Perfil actualizado"}
    except Exception as e:
        raise _error_bd("perfil", e)


# ---------- Direcciones guardadas ----------
@router.get("/cuenta/direcciones")
def mis_direcciones(request: Request):
    cid = current_user(request)
    try:
        return cuentas.listar_direcciones(cid)
    except Exception as e:
        raise _error_bd("direcciones", e)


@router.post("/cuenta/direcciones")
def nueva_direccion(data: DireccionIn, request: Request):
    cid = current_user(request)
    try:
        return {"id_direccion": cuentas.crear_direccion(cid, data.model_dump()), "message": "Dirección guardada"}
    except Exception as e:
        raise _error_bd("crear_direccion", e)


@router.put("/cuenta/direcciones/{id_direccion}")
def editar_direccion(id_direccion: int, data: DireccionUpdate, request: Request):
    cid = current_user(request)
    try:
        if not cuentas.actualizar_direccion(cid, id_direccion, data.model_dump(exclude_unset=True)):
            raise HTTPException(404, "Dirección no encontrada.")
        return {"message": "Dirección actualizada"}
    except HTTPException:
        raise
    except Exception as e:
        raise _error_bd("editar_direccion", e)


@router.delete("/cuenta/direcciones/{id_direccion}")
def borrar_direccion(id_direccion: int, request: Request):
    cid = current_user(request)
    try:
        if not cuentas.eliminar_direccion(cid, id_direccion):
            raise HTTPException(404, "Dirección no encontrada.")
        return {"message": "Dirección eliminada"}
    except HTTPException:
        raise
    except Exception as e:
        raise _error_bd("borrar_direccion", e)


# ---------- Compras ----------
@router.post("/compras")
def comprar(data: CompraIn, request: Request):
    cid = current_user(request)
    try:
        if data.id_direccion:
            d = cuentas.obtener_direccion(cid, data.id_direccion)
            if not d:
                raise HTTPException(400, "La dirección seleccionada no es válida.")
            envio = {k: d[k] for k in ("nombre_recibe", "telefono", "direccion", "ciudad", "estado",
                                       "codigo_postal", "referencia")}
            id_direccion = data.id_direccion
        elif data.nueva_direccion:
            envio = data.nueva_direccion.model_dump()
            id_direccion = None
            if data.guardar_direccion:
                id_direccion = cuentas.crear_direccion(cid, {**envio, "alias": envio.get("alias") or "Guardada"})
        else:
            raise HTTPException(400, "Indica una dirección de envío.")

        items = [i.model_dump() for i in data.items]
        resultado = ventas.crear_pedido(cid, items, envio, id_direccion, data.metodo_pago)
        return {**resultado, "message": "Compra registrada"}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise _error_bd("compra", e)


@router.get("/compras")
def mis_compras(request: Request):
    cid = current_user(request)
    try:
        return ventas.listar(cliente_id=cid)
    except Exception as e:
        raise _error_bd("compras", e)


@router.get("/compras/{id_venta}")
def detalle_compra(id_venta: int, request: Request):
    cid = current_user(request)
    try:
        venta = ventas.obtener(id_venta, cliente_id=cid)
        if not venta:
            raise HTTPException(404, "Pedido no encontrado.")
        return venta
    except HTTPException:
        raise
    except Exception as e:
        raise _error_bd("detalle_compra", e)


@router.post("/compras/{id_venta}/cancelar")
def cancelar_compra(id_venta: int, request: Request):
    cid = current_user(request)
    try:
        if not ventas.cambiar_estado(id_venta, "Cancelada", "Cancelado por el cliente", cliente_id=cid):
            raise HTTPException(404, "Pedido no encontrado.")
        return {"message": "Pedido cancelado y existencias restauradas"}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise _error_bd("cancelar", e)
