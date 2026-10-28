/* Esquema de TuxAudifonos. Se ejecuta desde app/db/database.py al iniciar. */
IF OBJECT_ID(N'dbo.categorias',N'U') IS NULL
CREATE TABLE dbo.categorias(
    id_categoria INT IDENTITY(1,1) PRIMARY KEY,
    nombre NVARCHAR(60) NOT NULL UNIQUE,
    slug NVARCHAR(60) NOT NULL UNIQUE,
    activo BIT NOT NULL DEFAULT 1);
IF OBJECT_ID(N'dbo.marcas',N'U') IS NULL
CREATE TABLE dbo.marcas(
    id_marca INT IDENTITY(1,1) PRIMARY KEY,
    nombre NVARCHAR(60) NOT NULL UNIQUE);
IF OBJECT_ID(N'dbo.audifonos',N'U') IS NULL
CREATE TABLE dbo.audifonos(
    id_audifono INT IDENTITY(1,1) PRIMARY KEY,
    nombre NVARCHAR(100) NOT NULL,
    id_marca INT NOT NULL CONSTRAINT FK_audifonos_marca REFERENCES dbo.marcas(id_marca),
    id_categoria INT NOT NULL CONSTRAINT FK_audifonos_categoria REFERENCES dbo.categorias(id_categoria),
    precio DECIMAL(10,2) NOT NULL CONSTRAINT CK_audifonos_precio CHECK(precio>0),
    precio_anterior DECIMAL(10,2) NULL,
    existencias INT NOT NULL DEFAULT 0 CONSTRAINT CK_audifonos_stock CHECK(existencias>=0),
    imagen NVARCHAR(500) NULL,
    descripcion NVARCHAR(1000) NULL,
    bateria_horas INT NULL CONSTRAINT CK_audifonos_bateria CHECK(bateria_horas IS NULL OR bateria_horas>0),
    cancelacion_ruido BIT NOT NULL DEFAULT 0,
    destacado BIT NOT NULL DEFAULT 0,
    activo BIT NOT NULL DEFAULT 1,
    fecha_creacion DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT CK_audifonos_precio_ant CHECK(precio_anterior IS NULL OR precio_anterior>precio));
IF OBJECT_ID(N'dbo.clientes',N'U') IS NULL
CREATE TABLE dbo.clientes(
    id_cliente INT IDENTITY(1,1) PRIMARY KEY,
    nombre NVARCHAR(100) NOT NULL,
    apellidos NVARCHAR(120) NOT NULL,
    correo NVARCHAR(150) NOT NULL UNIQUE,
    telefono NVARCHAR(20) NOT NULL,
    password_hash NVARCHAR(300) NOT NULL,
    rol NVARCHAR(20) NOT NULL DEFAULT N'cliente' CONSTRAINT CK_clientes_rol CHECK(rol IN(N'cliente',N'admin')),
    activo BIT NOT NULL DEFAULT 1,
    fecha_registro DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT CK_clientes_correo CHECK(correo LIKE N'%_@_%._%'));
IF OBJECT_ID(N'dbo.direcciones',N'U') IS NULL
CREATE TABLE dbo.direcciones(
    id_direccion INT IDENTITY(1,1) PRIMARY KEY,
    id_cliente INT NOT NULL CONSTRAINT FK_direcciones_cliente REFERENCES dbo.clientes(id_cliente),
    alias NVARCHAR(50) NOT NULL,
    nombre_recibe NVARCHAR(150) NOT NULL,
    telefono NVARCHAR(20) NOT NULL,
    direccion NVARCHAR(250) NOT NULL,
    ciudad NVARCHAR(100) NOT NULL,
    estado NVARCHAR(100) NOT NULL,
    codigo_postal NVARCHAR(10) NOT NULL,
    referencia NVARCHAR(250) NULL,
    predeterminada BIT NOT NULL DEFAULT 0,
    activo BIT NOT NULL DEFAULT 1);
IF OBJECT_ID(N'dbo.ventas',N'U') IS NULL
CREATE TABLE dbo.ventas(
    id_venta INT IDENTITY(1,1) PRIMARY KEY,
    id_cliente INT NOT NULL CONSTRAINT FK_ventas_cliente REFERENCES dbo.clientes(id_cliente),
    id_direccion INT NULL CONSTRAINT FK_ventas_direccion REFERENCES dbo.direcciones(id_direccion),
    fecha_venta DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    fecha_actualizacion DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    estado NVARCHAR(20) NOT NULL DEFAULT N'Comprada' CONSTRAINT CK_ventas_estado CHECK(estado IN(N'Comprada',N'En preparación',N'Enviado',N'Entregado',N'Cancelada')),
    subtotal DECIMAL(12,2) NOT NULL CONSTRAINT CK_ventas_subtotal CHECK(subtotal>=0),
    costo_envio DECIMAL(10,2) NOT NULL DEFAULT 0 CONSTRAINT CK_ventas_envio CHECK(costo_envio>=0),
    total DECIMAL(12,2) NOT NULL CONSTRAINT CK_ventas_total CHECK(total>=0),
    metodo_pago NVARCHAR(30) NOT NULL CONSTRAINT CK_ventas_pago CHECK(metodo_pago IN(N'Efectivo',N'Transferencia',N'Tarjeta')),
    nombre_recibe NVARCHAR(150) NOT NULL,
    telefono_envio NVARCHAR(20) NOT NULL,
    direccion_envio NVARCHAR(250) NOT NULL,
    ciudad_envio NVARCHAR(100) NOT NULL,
    estado_envio NVARCHAR(100) NOT NULL,
    cp_envio NVARCHAR(10) NOT NULL,
    referencia_envio NVARCHAR(250) NULL,
    codigo_seguimiento NVARCHAR(30) NULL);
IF OBJECT_ID(N'dbo.detalle_venta',N'U') IS NULL
CREATE TABLE dbo.detalle_venta(
    id_detalle INT IDENTITY(1,1) PRIMARY KEY,
    id_venta INT NOT NULL CONSTRAINT FK_detalle_venta REFERENCES dbo.ventas(id_venta),
    id_audifono INT NOT NULL CONSTRAINT FK_detalle_audifono REFERENCES dbo.audifonos(id_audifono),
    cantidad INT NOT NULL CONSTRAINT CK_detalle_cantidad CHECK(cantidad>0),
    precio_unitario DECIMAL(10,2) NOT NULL CONSTRAINT CK_detalle_precio CHECK(precio_unitario>0),
    subtotal AS CONVERT(DECIMAL(12,2),cantidad*precio_unitario) PERSISTED);
IF OBJECT_ID(N'dbo.historial_estado_venta',N'U') IS NULL
CREATE TABLE dbo.historial_estado_venta(
    id_historial INT IDENTITY(1,1) PRIMARY KEY,
    id_venta INT NOT NULL CONSTRAINT FK_historial_venta REFERENCES dbo.ventas(id_venta),
    estado NVARCHAR(20) NOT NULL,
    nota NVARCHAR(250) NULL,
    fecha DATETIME2 NOT NULL DEFAULT SYSDATETIME());
IF OBJECT_ID(N'dbo.resenas',N'U') IS NULL
CREATE TABLE dbo.resenas(
    id_resena INT IDENTITY(1,1) PRIMARY KEY,
    id_audifono INT NOT NULL CONSTRAINT FK_resenas_audifono REFERENCES dbo.audifonos(id_audifono),
    id_cliente INT NOT NULL CONSTRAINT FK_resenas_cliente REFERENCES dbo.clientes(id_cliente),
    calificacion TINYINT NOT NULL CONSTRAINT CK_resenas_cal CHECK(calificacion BETWEEN 1 AND 5),
    comentario NVARCHAR(500) NULL,
    fecha DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT UQ_resenas_cliente_producto UNIQUE(id_audifono,id_cliente));
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name=N'IX_audifonos_categoria' AND object_id=OBJECT_ID(N'dbo.audifonos'))
    CREATE INDEX IX_audifonos_categoria ON dbo.audifonos(id_categoria) INCLUDE(precio,activo);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name=N'IX_ventas_cliente_fecha' AND object_id=OBJECT_ID(N'dbo.ventas'))
    CREATE INDEX IX_ventas_cliente_fecha ON dbo.ventas(id_cliente,fecha_venta DESC);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name=N'IX_ventas_estado' AND object_id=OBJECT_ID(N'dbo.ventas'))
    CREATE INDEX IX_ventas_estado ON dbo.ventas(estado);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name=N'IX_detalle_venta' AND object_id=OBJECT_ID(N'dbo.detalle_venta'))
    CREATE INDEX IX_detalle_venta ON dbo.detalle_venta(id_venta);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name=N'IX_direcciones_cliente' AND object_id=OBJECT_ID(N'dbo.direcciones'))
    CREATE INDEX IX_direcciones_cliente ON dbo.direcciones(id_cliente) WHERE activo=1;
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name=N'IX_historial_venta' AND object_id=OBJECT_ID(N'dbo.historial_estado_venta'))
    CREATE INDEX IX_historial_venta ON dbo.historial_estado_venta(id_venta,fecha);
/* ---------- Datos de muestra ---------- */
IF NOT EXISTS (SELECT 1 FROM dbo.categorias)
    INSERT dbo.categorias(nombre,slug) VALUES(N'Diadema',N'diadema'),(N'In-ear',N'in-ear'),(N'Deportivos',N'deportivos');
IF NOT EXISTS (SELECT 1 FROM dbo.marcas)
    INSERT dbo.marcas(nombre) VALUES(N'Tux Sound'),(N'Nimbus'),(N'Aurora');
IF NOT EXISTS (SELECT 1 FROM dbo.audifonos)
    INSERT dbo.audifonos(nombre,id_marca,id_categoria,precio,precio_anterior,existencias,imagen,descripcion,bateria_horas,cancelacion_ruido,destacado) VALUES
(N'Studio One',(SELECT id_marca FROM dbo.marcas WHERE nombre=N'Tux Sound'),(SELECT id_categoria FROM dbo.categorias WHERE slug=N'diadema'),1899,2199,12,N'https://images.unsplash.com/photo-1546435770-a3e426bf472b?auto=format&fit=crop&w=800&q=85',N'Inmersión total, comodidad sin esfuerzo.',30,1,1),
(N'Air Beat',(SELECT id_marca FROM dbo.marcas WHERE nombre=N'Tux Sound'),(SELECT id_categoria FROM dbo.categorias WHERE slug=N'in-ear'),999,NULL,20,N'https://images.unsplash.com/photo-1606220945770-b5b6c2c55bf1?auto=format&fit=crop&w=800&q=85',N'Pequeños en tamaño. Grandes en sonido.',8,0,1),
(N'Pulse Max',(SELECT id_marca FROM dbo.marcas WHERE nombre=N'Tux Sound'),(SELECT id_categoria FROM dbo.categorias WHERE slug=N'diadema'),2499,NULL,8,N'https://images.unsplash.com/photo-1484704849700-f032a568e944?auto=format&fit=crop&w=800&q=85',N'Detalles precisos. Presencia extraordinaria.',40,1,1),
(N'Nimbus Flow',(SELECT id_marca FROM dbo.marcas WHERE nombre=N'Nimbus'),(SELECT id_categoria FROM dbo.categorias WHERE slug=N'in-ear'),1699,1999,15,NULL,N'Cancelación activa de ruido en un formato compacto.',24,1,0),
(N'Nimbus Run',(SELECT id_marca FROM dbo.marcas WHERE nombre=N'Nimbus'),(SELECT id_categoria FROM dbo.categorias WHERE slug=N'deportivos'),1299,NULL,15,NULL,N'Ajuste firme y resistencia al sudor para entrenar.',10,0,0),
(N'Aurora Lite',(SELECT id_marca FROM dbo.marcas WHERE nombre=N'Aurora'),(SELECT id_categoria FROM dbo.categorias WHERE slug=N'in-ear'),599,NULL,30,NULL,N'Sonido equilibrado para el día a día.',6,0,0),
(N'Aurora Sprint',(SELECT id_marca FROM dbo.marcas WHERE nombre=N'Aurora'),(SELECT id_categoria FROM dbo.categorias WHERE slug=N'deportivos'),849,NULL,0,NULL,N'Ligeros y con ganchos para correr.',7,0,0);
/* ---------- Imágenes (Unsplash, licencia libre) ---------- */


