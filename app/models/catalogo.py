import pyodbc
from app.db.database import conexion, filas_a_dicts

ORDENES = {
    "destacados": "a.destacado DESC, a.id_audifono",
    "precio_asc": "a.precio ASC, a.id_audifono",
    "precio_desc": "a.precio DESC, a.id_audifono",
    "nuevos": "a.fecha_creacion DESC, a.id_audifono DESC",
}

SELECT_BASE = """
SELECT a.id_audifono, a.nombre, a.id_marca, m.nombre AS marca,
       a.id_categoria, c.nombre AS categoria, c.slug AS categoria_slug,
       a.precio, a.precio_anterior, a.existencias, a.imagen, a.descripcion,
       a.bateria_horas, a.cancelacion_ruido, a.destacado, a.activo,
       (SELECT AVG(CAST(r.calificacion AS DECIMAL(4,2))) FROM dbo.resenas r WHERE r.id_audifono=a.id_audifono) AS calificacion,
       (SELECT COUNT(*) FROM dbo.resenas r WHERE r.id_audifono=a.id_audifono) AS num_resenas
FROM dbo.audifonos a
JOIN dbo.marcas m ON m.id_marca=a.id_marca
JOIN dbo.categorias c ON c.id_categoria=a.id_categoria
"""


def _normalizar(fila: dict) -> dict:
    for k in ("precio", "precio_anterior", "calificacion"):
        if fila.get(k) is not None:
            fila[k] = float(fila[k])
    for k in ("cancelacion_ruido", "destacado", "activo"):
        fila[k] = bool(fila[k])
    return fila


def listar(categoria=None, buscar=None, orden="destacados", solo_disponibles=False, incluir_inactivos=False):
    condiciones, params = [], []
    if not incluir_inactivos:
        condiciones.append("a.activo=1")
    if categoria:
        condiciones.append("c.slug=?")
        params.append(categoria)
    if buscar:
        condiciones.append("(a.nombre LIKE ? OR m.nombre LIKE ? OR a.descripcion LIKE ?)")
        params += [f"%{buscar}%"] * 3
    if solo_disponibles:
        condiciones.append("a.existencias>0")
    where = (" WHERE " + " AND ".join(condiciones)) if condiciones else ""
    sql = SELECT_BASE + where + " ORDER BY " + ORDENES.get(orden, ORDENES["destacados"])
    with conexion() as cn:
        cur = cn.cursor()
        cur.execute(sql, *params)
        return [_normalizar(f) for f in filas_a_dicts(cur)]


def obtener(id_audifono: int, incluir_inactivos=False):
    sql = SELECT_BASE + " WHERE a.id_audifono=?" + ("" if incluir_inactivos else " AND a.activo=1")
    with conexion() as cn:
        cur = cn.cursor()
        cur.execute(sql, id_audifono)
        filas = filas_a_dicts(cur)
        return _normalizar(filas[0]) if filas else None


def catalogos():
    with conexion() as cn:
        cur = cn.cursor()
        cur.execute("SELECT id_categoria, nombre, slug FROM dbo.categorias WHERE activo=1 ORDER BY nombre")
        categorias = filas_a_dicts(cur)
        cur.execute("SELECT id_marca, nombre FROM dbo.marcas ORDER BY nombre")
        marcas = filas_a_dicts(cur)
    return {"categorias": categorias, "marcas": marcas}


CAMPOS = ["nombre", "id_marca", "id_categoria", "precio", "precio_anterior", "existencias",
          "imagen", "descripcion", "bateria_horas", "cancelacion_ruido", "destacado"]


def crear(datos: dict) -> int:
    valores = [datos.get(c) for c in CAMPOS]
    sql = (f"INSERT dbo.audifonos({','.join(CAMPOS)}) OUTPUT INSERTED.id_audifono "
           f"VALUES({','.join('?' * len(CAMPOS))})")
    with conexion() as cn:
        cur = cn.cursor()
        cur.execute(sql, *valores)
        return cur.fetchone()[0]


def actualizar(id_audifono: int, datos: dict) -> bool:
    cambios = {k: v for k, v in datos.items() if k in CAMPOS}
    with conexion() as cn:
        cur = cn.cursor()
        cur.execute("SELECT 1 FROM dbo.audifonos WHERE id_audifono=?", id_audifono)
        if not cur.fetchone():
            return False
        if cambios:
            sets = ", ".join(f"{k}=?" for k in cambios)
            cur.execute(f"UPDATE dbo.audifonos SET {sets} WHERE id_audifono=?", *cambios.values(), id_audifono)
        return True


def desactivar(id_audifono: int) -> bool:
    with conexion() as cn:
        cur = cn.cursor()
        cur.execute("UPDATE dbo.audifonos SET activo=0 WHERE id_audifono=? AND activo=1", id_audifono)
        return cur.rowcount > 0


def resenas_de(id_audifono: int):
    with conexion() as cn:
        cur = cn.cursor()
        cur.execute("""SELECT r.calificacion, r.comentario, r.fecha, c.nombre + N' ' + LEFT(c.apellidos,1) + N'.' AS autor
                       FROM dbo.resenas r JOIN dbo.clientes c ON c.id_cliente=r.id_cliente
                       WHERE r.id_audifono=? ORDER BY r.fecha DESC""", id_audifono)
        return filas_a_dicts(cur)


def agregar_resena(id_audifono: int, cliente_id: int, calificacion: int, comentario: str):
    with conexion() as cn:
        cur = cn.cursor()
        cur.execute("""SELECT 1 FROM dbo.ventas v JOIN dbo.detalle_venta d ON d.id_venta=v.id_venta
                       WHERE v.id_cliente=? AND d.id_audifono=? AND v.estado<>N'Cancelada'""",
                    cliente_id, id_audifono)
        if not cur.fetchone():
            raise ValueError("Solo puedes calificar productos que hayas comprado.")
        try:
            cur.execute("INSERT dbo.resenas(id_audifono,id_cliente,calificacion,comentario) VALUES(?,?,?,?)",
                        id_audifono, cliente_id, calificacion, comentario or None)
        except pyodbc.IntegrityError as exc:
            raise ValueError("Ya calificaste este producto.") from exc
