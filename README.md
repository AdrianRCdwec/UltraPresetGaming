# UltraPresetGaming — Comparador de precios (Tipo 2)

Aplicación web que compara precios finales de hardware y videojuegos entre distintas tiendas/plataformas, teniendo en cuenta descuentos y costes extra (p. ej. envío, comisiones), y muestra novedades/actualidad tecnológica y de gaming.

> Proyecto académico (Frontend: HTML/CSS/JS) consumiendo una API REST propia (Backend: Django + Django REST Framework).

---

## Índice
- [Objetivo](#objetivo)
- [Funcionalidades](#funcionalidades)
- [Páginas (UI)](#páginas-ui)
- [Backend (API REST)](#backend-api-rest)
- [Modelo de datos](#modelo-de-datos)
- [Estructura del repositorio](#estructura-del-repositorio)
- [Instalación y ejecución](#instalación-y-ejecución)
- [Uso rápido](#uso-rápido)
- [Buenas prácticas y seguridad](#buenas-prácticas-y-seguridad)
- [Roadmap](#roadmap)

---

## Objetivo
Construir una web responsive y accesible que permita:
- Buscar un producto (juego o componente).
- Consultar precios por tienda/plataforma.
- Calcular el **precio final** (precio base - descuento + extras).
- Determinar automáticamente la opción más barata.
- Consultar novedades (tecnología y videojuegos) desde la propia aplicación.

---

## Funcionalidades
- Comparación multi-tienda de precios por producto.
- Cálculo de precio final: incluye descuentos y extras configurables.
- Filtros y búsqueda (por nombre, categoría, tienda, rango de precio).
- Página de detalle de producto con historial/variación de precios (si se implementa).
- Sección de novedades (listado y detalle).

---

## Páginas (UI)
La aplicación incluye al menos 4 páginas (HTML) usando etiquetas semánticas:
- **Home / Novedades**: listado de noticias/actualizaciones.
- **Comparador / Buscador**: búsqueda de productos y comparación de precios.
- **Detalle de producto**: desglose de tiendas, descuentos, extras y precio final.
- **Favoritos / Seguimiento** (o **Acerca de / Contacto**, según la implementación final).

### Accesibilidad y responsive
- Uso de `<header>`, `<nav>`, `<main>`, `<aside>`, `<footer>`.
- Diseño responsive con *media queries* (móvil, tablet, escritorio).
- CSS modular: variables, clases reutilizables y estructura mantenible.

---

## Backend (API REST)
Backend implementado con Django + Django REST Framework.
- Formato de intercambio: **JSON** (request/response).

### Endpoints (mínimos obligatorios)
> Nota: los nombres finales pueden variar, pero deben existir los verbos y mecanismos.

Ejemplo de endpoints:
- `GET /api/productos/`  
  - Soporta filtros mediante **query params** (p. ej. `?search=ryzen&categoria=cpu&tienda=pccomponentes`)
- `POST /api/productos/`  
  - Crea producto (parámetros en **cuerpo JSON**)
- `PUT /api/productos/<id>/`  
  - Actualización completa (**path param** `id` + cuerpo JSON)
- `PATCH /api/productos/<id>/`  
  - Actualización parcial (**path param** `id` + cuerpo JSON)
- `DELETE /api/productos/<id>/`  
  - Eliminación (**path param** `id`)

*(Además se pueden añadir endpoints para tiendas, precios, noticias, favoritos, etc.)*

### Parámetros requeridos (al menos una vez en toda la API)
- **Path params**: `/api/productos/<id>/`
- **Query params**: `/api/productos/?search=...`
- **Body params (JSON)**: `POST/PUT/PATCH` con payload JSON

---

## Modelo de datos
Mínimo 3 modelos con relación N:N (o ternaria).

Diseño recomendado (ejemplo):
- `Producto` (hardware o videojuego)
- `Tienda` (PcComponentes, Amazon, Steam, etc.)
- `Oferta` (o `Precio`) como entidad intermedia N:N:
  - `producto` (FK a Producto)
  - `tienda` (FK a Tienda)
  - `precio_base`
  - `descuento` (porcentaje o cantidad)
  - `extras` (envío/comisión) o campos separados
  - `updated_at` (fecha/hora de actualización)

Relaciones:
- `Producto` N:N `Tienda` a través de `Oferta/Precio`.

---

## Estructura del repositorio

[...]

---

## Instalación y ejecución

### Requisitos
- Python 3.10+ (recomendado 3.11)
- pip
- (Opcional) Node.js si se usan herramientas de build, si no, no hace falta.

### 1) Backend (Django)
Desde la carpeta `backend/`:

1. Crear y activar entorno virtual:
   - Windows (PowerShell):
     ```bash
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   - Windows (CMD):
     ```bash
     python -m venv venv
     .\venv\Scripts\activate.bat
     ```

2. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   python manage.py makemigrations
   python manage.py migrate
