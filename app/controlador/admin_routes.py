from fastapi import APIRouter, HTTPException, Query, Request
from app.controlador.sesion import require_admin
from app.controlador.routes import _error_bd
from app.models import catalogo, ventas
from app.vista.audifonos import AudifonoIn, AudifonoUpdate, EstadoIn

router = APIRouter(prefix="/admin")


@router.get("/resumen")
def resumen(request: Request):
    require_admin(request)
    try:
        return ventas.resumen()
    except Exception as e:
        raise _error_bd("resumen", e)


@router.get("/audifonos")
def listar(request: Request):
    require_admin(request)
    try:
        return catalogo.listar(incluir_inactivos=True)
    except Exception as e:
        raise _error_bd("admin_listar", e)


@router.post("/audifonos")
def crear(data: AudifonoIn, request: Request):
    require_admin(request)
    try:
        return {"id_audifono": catalogo.crear(data.a_dict()), "message": "Producto creado"}
    except Exception as e:
        raise _error_bd("admin_crear", e)


@router.put("/audifonos/{id_audifono}")
def actualizar(id_audifono: int, data: AudifonoUpdate, request: Request):
    require_admin(request)
    try:
        if not catalogo.actualizar(id_audifono, data.a_dict()):
            raise HTTPException(404, "Producto no encontrado.")
        return {"message": "Producto actualizado"}
    except HTTPException:
        raise
    except Exception as e:
        raise _error_bd("admin_actualizar", e)


@router.delete("/audifonos/{id_audifono}")
def desactivar(id_audifono: int, request: Request):
    require_admin(request)
    try:
        if not catalogo.desactivar(id_audifono):
            raise HTTPException(404, "Producto no encontrado o ya inactivo.")
        return {"message": "Producto desactivado (el historial de pedidos se conserva)"}
    except HTTPException:
        raise
    except Exception as e:
        raise _error_bd("admin_desactivar", e)


@router.get("/pedidos")
def pedidos(request: Request, estado: str | None = Query(default=None, max_length=20)):
    require_admin(request)
    try:
        return ventas.listar(estado=estado)
    except Exception as e:
        raise _error_bd("admin_pedidos", e)


@router.put("/pedidos/{id_venta}/estado")
def cambiar_estado(id_venta: int, data: EstadoIn, request: Request):
    require_admin(request)
    try:
        if not ventas.cambiar_estado(id_venta, data.estado, data.nota, data.codigo_seguimiento):
            raise HTTPException(404, "Pedido no encontrado.")
        return {"message": f"Pedido actualizado a '{data.estado}'"}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise _error_bd("admin_estado", e)
