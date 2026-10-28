import os
from contextlib import contextmanager
from pathlib import Path
import pyodbc


def get_db_connection():
    """Abre una conexión a SQL Server según las variables de entorno DB_*."""
    servidor = os.getenv("DB_SERVER", "localhost")
    base_datos = os.getenv("DB_NAME", "tuxaudifonos_db")
    usuario = os.getenv("DB_USER", "")
    contrasena = os.getenv("DB_PASSWORD", "")
    controlador = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")
    confiar = os.getenv("DB_TRUST_CERTIFICATE", "yes")

    base = f"DRIVER={{{controlador}}};SERVER={servidor};DATABASE={base_datos};TrustServerCertificate={confiar};"
    if usuario:
        cadena = base + f"UID={usuario};PWD={contrasena};"
    else:
        cadena = base + "Trusted_Connection=yes;"
    return pyodbc.connect(cadena)


def initialize_database():
    """Crea la base de datos si hace falta y aplica su esquema desde el proyecto."""
    servidor = os.getenv("DB_SERVER", "localhost")
    base_datos = os.getenv("DB_NAME", "tuxaudifonos_db")
    usuario = os.getenv("DB_USER", "")
    contrasena = os.getenv("DB_PASSWORD", "")
    controlador = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")
    confiar = os.getenv("DB_TRUST_CERTIFICATE", "yes")

    # El nombre de la base se escapa como identificador porque SQL Server no lo parametriza.
    identificador = f"[{base_datos.replace(']', ']]')}]"
    cadena_master = (
        f"DRIVER={{{controlador}}};SERVER={servidor};DATABASE=master;"
        f"TrustServerCertificate={confiar};"
    )
    if usuario:
        cadena_master += f"UID={usuario};PWD={contrasena};"
    else:
        cadena_master += "Trusted_Connection=yes;"

    with pyodbc.connect(cadena_master, autocommit=True) as cn:
        cursor = cn.cursor()
        if not cursor.execute("SELECT DB_ID(?)", base_datos).fetchone()[0]:
            cursor.execute(f"CREATE DATABASE {identificador}")

    esquema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8-sig")
    with get_db_connection() as cn:
        cursor = cn.cursor()
        for instruccion in (parte.strip() for parte in esquema.split(";")):
            if instruccion:
                cursor.execute(instruccion)
        cn.commit()

    correo_admin = os.getenv("INITIAL_ADMIN_EMAIL", "").strip().lower()
    password_admin = os.getenv("INITIAL_ADMIN_PASSWORD", "")
    if correo_admin and password_admin:
        from app.models.seguridad import hash_password

        with get_db_connection() as cn:
            cursor = cn.cursor()
            cursor.execute("SELECT 1 FROM dbo.clientes WHERE correo=?", correo_admin)
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT dbo.clientes(nombre,apellidos,correo,telefono,password_hash,rol) "
                    "VALUES(?,?,?,?,?,N'admin')",
                    "Administrador", "TuxAudifonos", correo_admin, "0000000000", hash_password(password_admin),
                )
            cn.commit()


@contextmanager
def conexion():
    """Transacción: confirma si todo sale bien, revierte si hay error, y siempre cierra."""
    cn = get_db_connection()
    try:
        yield cn
        cn.commit()
    except Exception:
        cn.rollback()
        raise
    finally:
        cn.close()


def filas_a_dicts(cursor):
    cols = [c[0] for c in cursor.description]
    return [dict(zip(cols, fila)) for fila in cursor.fetchall()]


def check_db_connection():
    with conexion() as cn:
        row = cn.cursor().execute(
            "SELECT CAST(SERVERPROPERTY('ServerName') AS NVARCHAR(128)), DB_NAME()"
        ).fetchone()
        return {"servidor": row[0], "base_datos": row[1]}
