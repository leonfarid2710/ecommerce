-- ============================================
-- STAR UP E-COMMERCE - DATABASE SCHEMA
-- Compatible with MySQL 8.0+ / PostgreSQL 13+
-- ============================================

-- Drop tables if exist (order matters due to FK)
DROP TABLE IF EXISTS items_carrito;
DROP TABLE IF EXISTS carrito;
DROP TABLE IF EXISTS detalle_venta;
DROP TABLE IF EXISTS ventas;
DROP TABLE IF EXISTS productos;
DROP TABLE IF EXISTS proveedores;
DROP TABLE IF EXISTS clientes;

-- ============================================
-- TABLA: clientes (Users/Customers)
-- ============================================
CREATE TABLE clientes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre      TEXT NOT NULL,
    email       TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    telefono    TEXT,
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- TABLA: proveedores (Suppliers)
-- ============================================
CREATE TABLE proveedores (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre      TEXT NOT NULL,
    contacto    TEXT,
    email       TEXT,
    telefono    TEXT
);

-- ============================================
-- TABLA: productos (Products + Inventory)
-- ============================================
CREATE TABLE productos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre          TEXT NOT NULL,
    descripcion     TEXT,
    precio          REAL NOT NULL CHECK (precio >= 0),
    existencias     INTEGER NOT NULL DEFAULT 0 CHECK (existencias >= 0),
    proveedor_id    INTEGER REFERENCES proveedores(id) ON DELETE SET NULL,
    categoria       TEXT DEFAULT 'General',
    imagen_url      TEXT,
    activo          INTEGER DEFAULT 1  -- 1=activo, 0=inactivo
);

-- ============================================
-- TABLA: ventas (Sales header)
-- ============================================
CREATE TABLE ventas (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id      INTEGER NOT NULL REFERENCES clientes(id),
    fecha           DATETIME DEFAULT CURRENT_TIMESTAMP,
    total           REAL NOT NULL DEFAULT 0,
    estado          TEXT DEFAULT 'pendiente',  -- pendiente|pagado|cancelado
    metodo_pago     TEXT DEFAULT 'tarjeta'
);

-- ============================================
-- TABLA: detalle_venta (Sale line items)
-- ============================================
CREATE TABLE detalle_venta (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    venta_id        INTEGER NOT NULL REFERENCES ventas(id) ON DELETE CASCADE,
    producto_id     INTEGER NOT NULL REFERENCES productos(id),
    cantidad        INTEGER NOT NULL CHECK (cantidad > 0),
    precio_unitario REAL NOT NULL
);

-- ============================================
-- TABLA: carrito (Shopping cart session)
-- ============================================
CREATE TABLE carrito (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id  INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    creado      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- TABLA: items_carrito (Cart line items)
-- ============================================
CREATE TABLE items_carrito (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    carrito_id  INTEGER NOT NULL REFERENCES carrito(id) ON DELETE CASCADE,
    producto_id INTEGER NOT NULL REFERENCES productos(id),
    cantidad    INTEGER NOT NULL DEFAULT 1 CHECK (cantidad > 0)
);

-- ============================================
-- SEED DATA - Proveedores
-- ============================================
INSERT INTO proveedores (nombre, contacto, email, telefono) VALUES
('TechSupply MX', 'Laura Gómez', 'laura@techsupply.mx', '9811234567'),
('Moda Campeche', 'Pedro Dzul', 'pedro@modacampeche.mx', '9819876543'),
('Artesanías del Sureste', 'Ana Canul', 'ana@artesaniassureste.mx', '9817654321');

-- ============================================
-- SEED DATA - Productos
-- ============================================
INSERT INTO productos (nombre, descripcion, precio, existencias, proveedor_id, categoria, imagen_url) VALUES
('Laptop Ultrabook Pro',    'Procesador i7, 16GB RAM, 512GB SSD, pantalla 14" FHD',             18500.00,  12, 1, 'Electrónica',    'https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=400'),
('Smartphone Nova X',       'Pantalla AMOLED 6.5", cámara 108MP, batería 5000mAh',              8900.00,   25, 1, 'Electrónica',    'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=400'),
('Audífonos Bluetooth Pro', 'Cancelación de ruido activa, 30h de batería, plegables',           1250.00,   40, 1, 'Electrónica',    'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400'),
('Teclado Mecánico RGB',    'Switches Cherry MX Red, retroiluminación RGB, TKL',                950.00,    18, 1, 'Electrónica',    'https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=400'),
('Playera Lino Premium',    'Tela de lino 100%, corte slim, colores variados',                   350.00,    60, 2, 'Ropa',           'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=400'),
('Mochila Ejecutiva',       'Material impermeable, compartimento laptop 15", USB port',          780.00,    30, 2, 'Accesorios',     'https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400'),
('Artesanía Jícara Maya',   'Jícara tallada a mano, diseños tradicionales mayas, 20cm',         420.00,    15, 3, 'Artesanías',     'https://images.unsplash.com/photo-1606722590583-6951b5ea92ad?w=400'),
('Hamaca Yucateca',         'Algodón 100%, tejido artesanal, tamaño matrimonial',               1100.00,   8,  3, 'Artesanías',     'https://images.unsplash.com/photo-1560448205-4d9b3e6bb6db?w=400'),
('Mouse Ergonómico',        'Diseño vertical, 6 botones programables, inalámbrico',             680.00,    22, 1, 'Electrónica',    'https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=400'),
('Agenda Ejecutiva 2025',   'Pasta dura, papel 90g, marcapáginas, formato A5',                  195.00,    50, 2, 'Papelería',      'https://images.unsplash.com/photo-1517842645767-c639042777db?w=400'),
('Cámara Mirrorless',       'Sensor APS-C 24MP, vídeo 4K, Wi-Fi, kit 18-55mm',                 15000.00,  5,  1, 'Electrónica',    'https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=400'),
('Huaraches Artesanales',   'Cuero genuino, suela resistente, hecho a mano en Campeche',        550.00,    20, 3, 'Calzado',        'https://images.unsplash.com/photo-1603808033192-082d6919d3e1?w=400');
