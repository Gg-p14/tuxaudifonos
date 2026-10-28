from decimal import Decimal
from app.db.database import conexion, filas_a_dicts

ENVIO_GRATIS_DESDE = Decimal("1500.00")
COSTO_ENVIO = Decimal("99.00")
CANTIDAD_MAX_POR_PRODUCTO = 20
TRANSICIONES = {
    "Comprada": {"En preparación", "Cancelada"},
    "En preparación": {"Enviado", "Cancelada"},
    "Enviado": {"Entregado"},
    "Entregado": set(),
    "Cancelada": set(),
}


def calcular_envio(subtotal: Decimal) -> Decimal:
    return Decimal("0.00") if subtotal >= ENVIO_GRATIS_DESDE else COSTO_ENVIO


def crear_pedido(cliente_id: int, items: list[dict], envio: dict, id_direccion, metodo_pago: str) -> dict:
    """Valida existencias, descuenta inventario y registra el pedido en una sola transacción."""
    # Une productos repetidos en el carrito para validar el total por producto.
    pedido: dict[int, int] = {}
    for it in items:
        pedido[it["id_audifono"]] = pedido.get(it["id_audifono"], 0) + it["cantidad"]
    if not pedido:
        raise ValueError("El carrito está vacío.")

    with conexion() as cn:
        cur = cn.cursor()
        subtotal = Decimal("0.00")
        lineas = []
        for id_aud, cantidad in pedido.items():
            if cantidad > CANTIDAD_MAX_POR_PRODUCTO:
                raise ValueError(f"Máximo {CANTIDAD_MAX_POR_PRODUCTO} piezas por producto.")
            cur.execute("SELECT nombre, precio, existencias FROM dbo.audifonos WITH (UPDLOCK, HOLDLOCK) "
                        "WHERE id_audifono=? AND activo=1", id_aud)
            fila = cur.fetchone()
            if not fila:
                raise ValueError("Uno de los productos ya no está disponible.")
            nombre, precio, stock = fila[0], Decimal(str(fila[1])), fila[2]
            if stock < cantidad:
                raise ValueError(f"Existencias insuficientes para {nombre}. Disponibles: {stock}.")
            subtotal += precio * cantidad
            lineas.append((id_aud, cantidad, precio))

        costo_envio = calcular_envio(subtotal)
        total = subtotal + costo_envio
        cur.execute(
            "INSERT dbo.ventas(id_cliente,id_direccion,estado,subtotal,costo_envio,total,metodo_pago,"
            "nombre_recibe,telefono_envio,direccion_envio,ciudad_envio,estado_envio,cp_envio,referencia_envio) "
            "OUTPUT INSERTED.id_venta VALUES(?,?,N'Comprada',?,?,?,?,?,?,?,?,?,?,?)",
            cliente_id, id_direccion, float(subtotal), float(costo_envio), float(total), metodo_pago,
            envio["nombre_recibe"], envio["telefono"], envio["direccion"], envio["ciudad"],
            envio["estado"], envio["codigo_postal"], envio.get("referencia") or None)
        venta_id = cur.fetchone()[0]

        for id_aud, cantidad, precio in lineas:
            cur.execute("INSERT dbo.detalle_venta(id_venta,id_audifono,cantidad,precio_unitario) VALUES(?,?,?,?)",
                        venta_id, id_aud, cantidad, float(precio))
            cur.execute("UPDATE dbo.audifonos SET existencias=existencias-? WHERE id_audifono=?", cantidad, id_aud)

        cur.execute("INSERT dbo.historial_estado_venta(id_venta,estado,nota) VALUES(?,N'Comprada',N'Pedido registrado')",
                    venta_id)
    return {"id_venta": venta_id, "subtotal": float(subtotal), "costo_envio": float(costo_envio),
            "total": float(total), "estado": "Comprada"}


def _cargar(cur, venta: dict) -> dict:
    venta["subtotal"] = float(venta["subtotal"])
    venta["costo_envio"] = float(venta["costo_envio"])
    venta["total"] = float(venta["total"])
    cur.execute("""SELECT d.cantidad, d.precio_unitario, a.nombre, a.id_audifono, a.imagen
                   FROM dbo.detalle_venta d JOIN dbo.audifonos a ON a.id_audifono=d.id_audifono
                   WHERE d.id_venta=?""", venta["id_venta"])
    venta["productos"] = [{"cantidad": f["cantidad"], "precio": float(f["precio_unitario"]),
                           "nombre": f["nombre"], "id_audifono": f["id_audifono"], "imagen": f["imagen"]}
                          for f in filas_a_dicts(cur)]
    cur.execute("SELECT estado, nota, fecha FROM dbo.historial_estado_venta WHERE id_venta=? ORDER BY fecha, id_historial",
                venta["id_venta"])
    venta["historial"] = filas_a_dicts(cur)
    return venta


_SQL_VENTA = ("SELECT id_venta, id_cliente, fecha_venta, fecha_actualizacion, estado, subtotal, costo_envio, total, "
              "metodo_pago, nombre_recibe, telefono_envio, direccion_envio, ciudad_envio, estado_envio, "
              "cp_envio, referencia_envio, codigo_seguimiento FROM dbo.ventas")


def listar(cliente_id=None, estado=None):
    condiciones, params = [], []
    if cliente_id is not None:
        condiciones.append("id_cliente=?")
        params.append(cliente_id)
    if estado:
        condiciones.append("estado=?")
        params.append(estado)
    where = (" WHERE " + " AND ".join(condiciones)) if condiciones else ""
    with conexion() as cn:
        cur = cn.cursor()
        cur.execute(_SQL_VENTA + where + " ORDER BY fecha_venta DESC, id_venta DESC", *params)
        ventas = filas_a_dicts(cur)
        return [_cargar(cur, v) for v in ventas]


def obtener(id_venta: int, cliente_id=None):
    sql = _SQL_VENTA + " WHERE id_venta=?"
    params = [id_venta]
    if cliente_id is not None:
        sql += " AND id_cliente=?"
        params.append(cliente_id)
    with conexion() as cn:
        cur = cn.cursor()
        cur.execute(sql, *params)
        ventas = filas_a_dicts(cur)
        return _cargar(cur, ventas[0]) if ventas else None


def cambiar_estado(id_venta: int, nuevo: str, nota: str = "", codigo_seguimiento=None, cliente_id=None) -> bool:
    """Cambia el estado respetando el flujo. Si se cancela, devuelve existencias.
    Un cliente solo puede cancelar sus pedidos que aún estén en 'Comprada'."""
    with conexion() as cn:
        cur = cn.cursor()
        sql = "SELECT estado FROM dbo.ventas WITH (UPDLOCK, HOLDLOCK) WHERE id_venta=?"
        params = [id_venta]
        if cliente_id is not None:
            sql += " AND id_cliente=?"
            params.append(cliente_id)
        cur.execute(sql, *params)
        fila = cur.fetchone()
        if not fila:
            return False
        actual = fila[0]
        if nuevo not in TRANSICIONES.get(actual, set()):
            raise ValueError(f"No se puede cambiar un pedido de '{actual}' a '{nuevo}'.")
        if cliente_id is not None and actual != "Comprada":
            raise ValueError("Solo puedes cancelar pedidos que aún no se preparan.")

        if nuevo == "Cancelada":
            cur.execute("SELECT id_audifono, cantidad FROM dbo.detalle_venta WHERE id_venta=?", id_venta)
            for id_aud, cantidad in cur.fetchall():
                cur.execute("UPDATE dbo.audifonos SET existencias=existencias+? WHERE id_audifono=?", cantidad, id_aud)

        cur.execute("UPDATE dbo.ventas SET estado=?, fecha_actualizacion=SYSDATETIME(), "
                    "codigo_seguimiento=COALESCE(?, codigo_seguimiento) WHERE id_venta=?",
                    nuevo, codigo_seguimiento, id_venta)
        cur.execute("INSERT dbo.historial_estado_venta(id_venta,estado,nota) VALUES(?,?,?)",
                    id_venta, nuevo, nota or None)
        return True


def resumen():
    with conexion() as cn:
        cur = cn.cursor()
        cur.execute("""SELECT
            (SELECT COUNT(*) FROM dbo.audifonos WHERE activo=1) AS productos,
            (SELECT COUNT(*) FROM dbo.ventas) AS pedidos,
            (SELECT COUNT(*) FROM dbo.ventas WHERE estado IN (N'Comprada',N'En preparación')) AS pendientes,
            (SELECT ISNULL(SUM(total),0) FROM dbo.ventas WHERE estado<>N'Cancelada') AS ventas_totales""")
        f = filas_a_dicts(cur)[0]
        f["ventas_totales"] = float(f["ventas_totales"])
        return f
