# TuxAudifonos

Tienda en línea académica con Python (FastAPI), SQL Server y un frontend HTML/CSS/JavaScript.
Mantiene la arquitectura MVC:

- `app/controlador/`: rutas HTTP (`routes.py` para clientes, `admin_routes.py` para administración, `sesion.py` para permisos).
- `app/vista/`: esquemas de validación (Pydantic).
- `app/models/`: acceso a datos por entidad (`catalogo.py`, `cuentas.py`, `ventas.py`) y seguridad (`seguridad.py`).
- `app/db/`: conexión y transacciones.
- `frontt/`: vistas HTML con JavaScript común (`common.js`) y estilos (`tux.css`).

## Funciones

- Catálogo con categorías, búsqueda, orden por precio/novedades, filtro de disponibles y precios anteriores.
- Página de producto con existencias, especificaciones y opiniones (solo de quien compró).
- Carrito con validación de existencias al pagar.
- Compra en pasos: dirección (guardada o nueva) → método de pago → revisión → confirmación.
- Direcciones guardadas en la cuenta, con dirección predeterminada.
- Pedidos con historial de estados, seguimiento y cancelación (mientras esté en "Comprada"; devuelve existencias).
- Envío gratis en compras de $1,500 o más; de lo contrario, $99.
- Panel de administración (`/admin`) para productos, existencias y estados de pedidos.
- Roles `cliente` y `admin`; los productos nunca se borran físicamente, solo se desactivan.
- Límite de intentos de inicio de sesión (5 fallos en 15 minutos).

## 1. SQL Server y creación automática

Al arrancar la aplicación, Python crea la base `tuxaudifonos_db` si no existe y aplica el esquema de `app/db/schema.sql`. También carga el catálogo de muestra. La conexión y la inicialización están en `app/db/database.py`; no necesitas ejecutar `tuxaudifonos_db.sql` manualmente. La inicialización puede repetirse y no borra datos existentes.

Copia `.env.example` como `.env` antes de ajustar la conexión. Para autenticación de Windows deja vacíos `DB_USER` y `DB_PASSWORD`; ajusta `DB_SERVER` al nombre de tu instancia (por ejemplo `localhost\SQLEXPRESS`). También puedes configurar credenciales de autenticación SQL. La cuenta configurada necesita permisos para crear la base de datos y sus tablas, y debe estar instalado el controlador ODBC de Microsoft para SQL Server.

Para habilitar el panel `/admin`, configura `INITIAL_ADMIN_EMAIL` y una contraseña propia en `INITIAL_ADMIN_PASSWORD`. La aplicación crea esa cuenta con la contraseña protegida si todavía no existe. No hay claves de administrador predeterminadas.

Comprueba la conexión en `http://127.0.0.1:8000/health/database`.

## 2. Ejecutar

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

Abre `http://127.0.0.1:8000`. La documentación de la API está en `/docs`.

## Notas importantes

- El carrito se guarda en el navegador (`localStorage`); el precio y las existencias se validan en el servidor al confirmar.
- Los pagos son solo de demostración. No hay pasarela ni cobros reales.
- Si `SESSION_SECRET` no está definida, se genera una temporal y las sesiones se pierden al reiniciar.
- Para producción: define `SESSION_SECRET`, activa `HTTPS_ONLY=1`, sirve con HTTPS y cambia las contraseñas de prueba.
- Las imágenes de muestra son de [Unsplash](https://unsplash.com) (licencia libre). Si no hay imagen, se muestra la inicial del producto.

## Cambios respecto a la versión anterior

- Los endpoints de creación, edición y borrado de productos ahora exigen rol de administrador (`/api/admin/...`).
- Se corrigió el script SQL (faltaba una comilla en la restricción de método de pago).
- El método de pago por defecto ya coincide con los valores permitidos por la base de datos.
- El carrito usa el `id` del producto, no su nombre; se eliminaron los productos de muestra del frontend.
- Se quitó CORS: frontend y API comparten origen.


