import pyodbc
from app.db.database import conexion, filas_a_dicts

PUBLICO = "id_cliente, nombre, apellidos, correo, telefono, rol"


def buscar_por_correo(correo: str):
    with conexion() as cn:
        cur = cn.cursor()
        cur.execute(f"SELECT {PUBLICO}, password_hash, activo FROM dbo.clientes WHERE correo=?", correo)
        filas = filas_a_dicts(cur)
        return filas[0] if filas else None


def obtener(cliente_id: int):
    with conexion() as cn:
        cur = cn.cursor()
        cur.execute(f"SELECT {PUBLICO}, activo FROM dbo.clientes WHERE id_cliente=?", cliente_id)
        filas = filas_a_dicts(cur)
        return filas[0] if filas else None


def crear(datos: dict, password_hash: str) -> int:
    try:
        with conexion() as cn:
            cur = cn.cursor()
            cur.execute("INSERT dbo.clientes(nombre,apellidos,correo,telefono,password_hash) "
                        "OUTPUT INSERTED.id_cliente VALUES(?,?,?,?,?)",
                        datos["nombre"], datos["apellidos"], datos["correo"].lower(),
                        datos["telefono"], password_hash)
            return cur.fetchone()[0]
    except pyodbc.IntegrityError as exc:
        raise ValueError("Ese correo ya tiene una cuenta.") from exc


def actualizar_perfil(cliente_id: int, datos: dict):
    with conexion() as cn:
        cn.cursor().execute("UPDATE dbo.clientes SET nombre=?, apellidos=?, telefono=? WHERE id_cliente=?",
                            datos["nombre"], datos["apellidos"], datos["telefono"], cliente_id)


# ---------- Direcciones guardadas ----------
CAMPOS_DIR = ["alias", "nombre_recibe", "telefono", "direccion", "ciudad", "estado",
              "codigo_postal", "referencia", "predeterminada"]


def listar_direcciones(cliente_id: int):
    with conexion() as cn:
        cur = cn.cursor()
        cur.execute("SELECT id_direccion, alias, nombre_recibe, telefono, direccion, ciudad, estado, "
                    "codigo_postal, referencia, predeterminada FROM dbo.direcciones "
                    "WHERE id_cliente=? AND activo=1 ORDER BY predeterminada DESC, id_direccion", cliente_id)
        filas = filas_a_dicts(cur)
        for f in filas:
            f["predeterminada"] = bool(f["predeterminada"])
        return filas


def obtener_direccion(cliente_id: int, id_direccion: int):
    with conexion() as cn:
        cur = cn.cursor()
        cur.execute("SELECT * FROM dbo.direcciones WHERE id_direccion=? AND id_cliente=? AND activo=1",
                    id_direccion, cliente_id)
        filas = filas_a_dicts(cur)
        return filas[0] if filas else None


def _quitar_predeterminada(cur, cliente_id):
    cur.execute("UPDATE dbo.direcciones SET predeterminada=0 WHERE id_cliente=? AND activo=1", cliente_id)


def crear_direccion(cliente_id: int, datos: dict) -> int:
    with conexion() as cn:
        cur = cn.cursor()
        cur.execute("SELECT COUNT(*) FROM dbo.direcciones WHERE id_cliente=? AND activo=1", cliente_id)
        es_primera = cur.fetchone()[0] == 0
        predeterminada = bool(datos.get("predeterminada")) or es_primera
        if predeterminada:
            _quitar_predeterminada(cur, cliente_id)
        cur.execute("INSERT dbo.direcciones(id_cliente,alias,nombre_recibe,telefono,direccion,ciudad,estado,"
                    "codigo_postal,referencia,predeterminada) OUTPUT INSERTED.id_direccion "
                    "VALUES(?,?,?,?,?,?,?,?,?,?)",
                    cliente_id, datos["alias"], datos["nombre_recibe"], datos["telefono"], datos["direccion"],
                    datos["ciudad"], datos["estado"], datos["codigo_postal"], datos.get("referencia") or None,
                    1 if predeterminada else 0)
        return cur.fetchone()[0]


def actualizar_direccion(cliente_id: int, id_direccion: int, datos: dict) -> bool:
    if not obtener_direccion(cliente_id, id_direccion):
        return False
    cambios = {k: v for k, v in datos.items() if k in CAMPOS_DIR and v is not None}
    with conexion() as cn:
        cur = cn.cursor()
        if cambios.get("predeterminada"):
            _quitar_predeterminada(cur, cliente_id)
        if cambios:
            sets = ", ".join(f"{k}=?" for k in cambios)
            cur.execute(f"UPDATE dbo.direcciones SET {sets} WHERE id_direccion=? AND id_cliente=?",
                        *cambios.values(), id_direccion, cliente_id)
    return True


def eliminar_direccion(cliente_id: int, id_direccion: int) -> bool:
    with conexion() as cn:
        cur = cn.cursor()
        cur.execute("UPDATE dbo.direcciones SET activo=0, predeterminada=0 WHERE id_direccion=? "
                    "AND id_cliente=? AND activo=1", id_direccion, cliente_id)
        return cur.rowcount > 0
