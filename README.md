# UltraPresetGaming 🎮🖥️

Aplicación web comparadora de precios de **hardware** (GPU, CPU, placas base, RAM, SSD, fuentes, refrigeración…) y **videojuegos** entre distintas tiendas especializadas. Consume una **API REST propia** desarrollada con Django y Django REST Framework, e integra un motor de scraping basado en Playwright con técnicas de IA (modelos locales vía Ollama y TF‑IDF con scikit‑learn) para mantener actualizado el catálogo de forma automática.

> **Trabajo Intermodular de 2.º DAW · Tipo 2: HTML + CSS + JavaScript consumiendo API REST propia.**

***

## 🧩 Objetivos del proyecto

- Comparar rápidamente precios de hardware y videojuegos entre tiendas especializadas (PcComponentes, Coolmod, Life Informática, Alternate, NeoByte, etc.).
- Mostrar siempre el **precio más barato disponible** junto a las ofertas activas en cada tienda.
- Ofrecer una experiencia responsive y accesible en múltiples pantallas: inicio, listados, detalle de producto, comparador, carrito/configurador, perfil, login/registro y mods.
- Automatizar la obtención de precios mediante **scraping concurrente** y un **motor de matching inteligente** con IA local y TF‑IDF.
- Cumplir los requisitos del proyecto intermodular: API REST propia con ≥5 endpoints, relación ternaria en BD, documentación y memoria técnica completa.

***

## 🏗️ Tipo de proyecto y alcance académico

| Capa | Tecnología |
|---|---|
| Frontend | HTML5, CSS3, JavaScript vanilla |
| Backend | Python 3.12 · Django 6.0.5 · Django REST Framework 3.17.1 |
| Autenticación | djangorestframework-simplejwt 5.5.1 |
| Documentación API | drf-spectacular 0.29.0 (OpenAPI / Swagger / Redoc) |
| Scraping | Playwright 1.60.0 |
| Matching IA | scikit-learn 1.8.0 (TF‑IDF) · Ollama (modelos locales) |
| Imágenes | Pillow 12.2.0 |
| Base de datos | SQLite (desarrollo) |

El proyecto está concebido como **prototipo funcional** y base de un producto ampliable a nuevas tiendas, nuevas categorías, alertas avanzadas, historial de precios y despliegue en producción.

***

## ✨ Funcionalidades principales

### Frontend (HTML / CSS / JS)

- **Inicio** (`frontend/pages/home/`) — acceso rápido a hardware, videojuegos y noticias.
- **Listados** (`frontend/pages/hardware/` y `frontend/pages/videogames/`) — productos obtenidos dinámicamente desde la API REST.
- **Comparador de precios** (`frontend/pages/prices/`) — visualización de precio base y ofertas activas por tienda, con ahorro calculado.
- **Carrito / Configurador** — selección de componentes (ranuras hardware) y videojuegos; persistencia con `localStorage` para invitados y sincronización con el backend para usuarios autenticados.
- **Perfil** (`frontend/pages/profile/`) — datos del usuario, foto de perfil, gestión de alertas y configuraciones guardadas.
- **Login / Registro** (`frontend/pages/login/` y `frontend/pages/register/`) — autenticación JWT, gestión de sesión en `sessionStorage` / `localStorage`.
- **Mods** (`frontend/pages/mods/`) — sección de mods de videojuegos.
- **Noticias** (`frontend/pages/news/`) — noticias del sector tecnológico y gaming.
- CSS compartido y modular (`frontend/shared/css/`) con variables CSS, `reset.css`, `header.css`, `footer.css`, `button.css`, `profile.css`.
- Diseño **responsive** con media queries (breakpoints móvil, tablet y escritorio).

### Backend (Django + DRF)

- **Modelos principales:** `Producto`, `Tienda`, `Oferta`, `Perfil`, `ItemGuardado`, `AlertaPrecio` (relación **ternaria** usuario–producto–tienda), `DecisionIA`.
- **API REST** con ViewSets y routers de DRF. Métodos soportados: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`.
- Uso de los tres mecanismos de parámetros: **path params**, **query params** y **cuerpo JSON**.
- Autenticación JWT (`djangorestframework_simplejwt`) con endpoints `/api/token/`, `/api/token/refresh/` y `/api/token/verify/`.
- Soft-delete de ofertas mediante flag `disponible` para preservar histórico de precios.
- **Documentación OpenAPI automática** vía `drf-spectacular`:
  - Swagger UI: `http://127.0.0.1:8000/api/docs/`
  - Redoc:       `http://127.0.0.1:8000/api/redoc/`
  - Schema raw:  `http://127.0.0.1:8000/api/schema/`

### Scraper + IA

- **Orquestador multihilo** (`main_crawler.py`) con `ThreadPoolExecutor` y cálculo dinámico de hilos óptimos según RAM y núcleos disponibles.
- **Patrón BaseScraper + Factory** — cada tienda implementa su propio scraper registrado en `ScraperFactory`.
- **Playwright** con rotación de User-Agents y Client-Hints, simulación de comportamiento humano (scroll, esperas) y resolución de Cloudflare.
- **Motor de matching en cascada:**
  1. Limpieza avanzada de nombres con regex precompiladas (procesadores Intel/AMD/Xeon, GPUs NVIDIA/AMD/Intel, RAM, SSD, PSU, monitores, AIO...).
  2. Vectorización TF‑IDF + similitud del coseno (scikit-learn).
  3. IA local vía Ollama para casos dudosos.
  4. Validación manual interactiva como último recurso.
  5. Caché de decisiones en `DecisionIA` para no repetir comparaciones.
- Descarga y guardado local de imágenes de productos en `backend/media/productos/`.
- **Graceful shutdown** mediante `shutdown_event` (signal handler para SIGINT/SIGTERM).

***

## 📁 Estructura del proyecto

```text
.
├── backend
│   ├── api
│   │   ├── migrations/
│   │   ├── admin.py
│   │   ├── backends.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   └── views.py
│   ├── comparador
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py / asgi.py
│   ├── scrapper_app
│   │   ├── shops
│   │   │   ├── hardware
│   │   │   │   ├── base_scraper.py
│   │   │   │   ├── factory.py
│   │   │   │   ├── pccomponentes.py
│   │   │   │   ├── coolmod.py
│   │   │   │   ├── lifeinformatica.py
│   │   │   │   ├── alternate.py
│   │   │   │   └── neobyte.py
│   │   │   └── videogames/
│   │   ├── utils
│   │   │   ├── db_manager.py
│   │   │   ├── ia_matcher.py
│   │   │   ├── interactive_prompt.py
│   │   │   ├── stealth.py
│   │   │   ├── events.py
│   │   │   └── logger.py
│   │   └── main_crawler.py
│   ├── media/
│   ├── db.sqlite3
│   └── manage.py
├── frontend
│   ├── pages
│   │   ├── home/          ← index.html + home.css
│   │   ├── hardware/      ← hardware.html + .css + .js
│   │   ├── videogames/    ← videogames.html + .css + .js
│   │   ├── prices/        ← prices.html + .css + .js
│   │   ├── login/         ← login.html + .css + .js
│   │   ├── register/      ← register.html + .css + .js
│   │   ├── profile/       ← profile.html + .css + .js
│   │   ├── mods/          ← mods.html + .css
│   │   └── news/          ← news.html + .css
│   ├── shared
│   │   ├── css/           ← reset, header, footer, button, profile
│   │   └── js/            ← auth-header.js, api-config.js, carrito.js
│   ├── assets/
│   └── index.html
├── docs
│   ├── extras/PDFs/       ← Explicación Proyecto Intermodular.pdf, Requisitos Proyecto.pdf
│   └── important/         ← comandsList.txt, dependencies.txt, executeScripts.txt
├── scripts
│   ├── run-crawler.ps1
│   └── tr.ps1
├── .gitignore
├── LICENSE
└── README.md
```

***

## 💻 Requisitos previos

### Hardware

#### Entorno completo (API + frontend + scraping + IA local)

| Componente | Mínimo | Recomendado |
|---|---|---|
| CPU | 4 núcleos (i5 / Ryzen 5) | 6–8 núcleos (i7 / Ryzen 7) |
| RAM | 16 GB | 24–32 GB |
| Almacenamiento | 50 GB SSD libres | 100 GB SSD |
| Conectividad | 10 Mbps | 50 Mbps o superior |
| GPU | Opcional (CPU-only funciona) | NVIDIA/AMD compatible con Ollama |

#### Entorno ligero (solo API + frontend, sin IA local)

| Componente | Mínimo | Recomendado |
|---|---|---|
| CPU | 2 núcleos | 4 núcleos |
| RAM | 2 GB | 4 GB |
| Almacenamiento | 10–20 GB libres | — |
| Conectividad | Cualquier conexión básica | — |

### Software

| Herramienta | Versión mínima | Notas |
|---|---|---|
| Python | 3.10 | 3.12 recomendado |
| pip | Última disponible | Incluido con Python |
| Git | 2.x | Para clonar y versionar |
| Visual Studio Code | 1.85+ | Extensiones: Python, Pylance, Live Server |
| Google Chrome / Edge / Firefox | Versión actual | Para el frontend y Playwright |
| Ollama | Última disponible | Solo si se usa IA local |
| Windows PowerShell | 5.1+ / PS Core 7+ | Para los scripts auxiliares |

> **Sistema operativo compatible:** Windows 10/11, macOS 14+, Ubuntu 22.04+, Debian 12+.

***

## 🚀 Puesta en marcha (desarrollo local)

### 1. Clonar el repositorio

```bash
git clone https://github.com/AdrianRCdwec/UltraPresetGaming.git
cd UltraPresetGaming
```

### 2. Crear y activar el entorno virtual

```bash
# Desde la raíz del proyecto
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r ../docs/important/dependencies.txt
playwright install chromium
```

### 4. Aplicar migraciones y crear superusuario

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 5. Arrancar el servidor Django

```bash
python manage.py runserver
```

El backend queda accesible en `http://127.0.0.1:8000/`.

### 6. Servir el frontend

Abre `frontend/index.html` con VS Code **Live Server** (botón "Go Live") o cualquier servidor estático. Esto evita errores de CORS con rutas relativas y peticiones a la API.

***

## 🔄 Actualizar el proyecto (en un dispositivo ya configurado)

```bash
git pull
cd backend
.venv\Scripts\activate
pip install -r ../docs/important/dependencies.txt
```

***

## 🔁 Reset de la base de datos

```bash
# Desde backend/ con el entorno activo
del db.sqlite3        # Windows
rm db.sqlite3         # Linux/macOS
python manage.py migrate
python manage.py createsuperuser
```

Para vaciar datos sin borrar estructura:

```bash
python manage.py flush
```

***

## 🧪 Ejecución del scraper

El proyecto incluye scripts PowerShell para lanzar el crawler cómodamente desde cualquier carpeta del repositorio.

### Configuración inicial (una sola vez)

Para habilitar los comandos `crawler` y `tr` globalmente en PowerShell, sigue las instrucciones de `docs/important/requirementsToExecuteScripts.txt`. En resumen, hay que añadir las funciones auxiliares al perfil de PowerShell (`$PROFILE`).

### Modos de ejecución

| Comando | Modo | Descripción |
|---|---|---|
| `crawler` | Normal | Multihilo + headless. Producción. |
| `crawler -s` | Secuencial | Monohilo + headless. Para depuración ligera. |
| `crawler -d` | Debug | Monohilo + ventana visible. Para ver el navegador en acción. |

### Árbol de ficheros personalizado

```powershell
tr       # Muestra árbol incluyendo archivos
tr -f    # Muestra árbol solo de carpetas
```

Durante la ejecución del scraper, el sistema:

1. Calcula el número óptimo de hilos según RAM y núcleos disponibles.
2. Abre Playwright con perfiles stealth (User-Agent rotado, viewport aleatorio, locale `es-ES`).
3. Recorre el catálogo de cada tienda página a página con reintentos automáticos.
4. Ejecuta el motor de matching (TF‑IDF → IA → validación manual) para cada producto.
5. Guarda o actualiza productos, ofertas e imágenes en la base de datos mediante `bulk_create` / `bulk_update`.
6. Marca como no disponibles las ofertas con más de 24 h sin actualizar.

***

## 🌐 API REST — Endpoints principales

La API está construida con Django REST Framework y documentada con drf-spectacular (OpenAPI 3.0).

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/productos/` | Lista productos (filtros: `search`, `categoria`, `tipo`) |
| `GET` | `/api/productos/{id}/` | Detalle de producto con ofertas activas |
| `GET` | `/api/tiendas/` | Lista de tiendas |
| `GET` | `/api/ofertas/` | Lista de ofertas disponibles |
| `GET/POST` | `/api/alertas/` | Gestión de alertas de precio del usuario |
| `PUT/PATCH/DELETE` | `/api/alertas/{id}/` | Modificar o eliminar una alerta |
| `GET/POST` | `/api/configuracion/` | Carrito/configuración guardada del usuario |
| `DELETE` | `/api/configuracion/{id}/` | Eliminar ítem del carrito |
| `POST` | `/api/auth/register/` | Registro de usuario |
| `POST` | `/api/token/` | Login (JWT access + refresh) |
| `POST` | `/api/token/refresh/` | Renovar access token |
| `GET` | `/api/docs/` | Swagger UI |
| `GET` | `/api/redoc/` | Redoc |
| `GET` | `/api/schema/` | Schema OpenAPI en YAML/JSON |

> Todos los endpoints de usuario autenticado requieren cabecera `Authorization: Bearer <token>`.

***

## 🔐 Autenticación y seguridad

- Autenticación basada en **JWT** (`djangorestframework_simplejwt`).
- Login personalizado con soporte de **username o email** como identificador (backend custom en `api/backends.py`).
- Los endpoints sensibles (alertas, carrito, perfil) requieren usuario autenticado.
- El frontend gestiona los tokens en `sessionStorage` / `localStorage`, añade la cabecera `Authorization` en cada petición y redirige al login si el token ha expirado.
- CORS configurado con `django-cors-headers` para permitir las peticiones del frontend local.

***

## 🧱 Requisitos del proyecto intermodular cubiertos

| Requisito | ¿Cubierto? |
|---|---|
| Tipo 2: HTML + CSS + JS consumiendo API REST propia | ✅ |
| Mínimo 4 pantallas | ✅ (9 pantallas: home, hardware, videogames, prices, login, register, profile, mods, news) |
| Etiquetas semánticas (header, nav, main, footer…) | ✅ |
| CSS modular con variables y clases reutilizables | ✅ (`shared/css/`) |
| Media queries / diseño responsive | ✅ |
| Al menos 3 modelos en la fachada REST | ✅ (Producto, Tienda, Oferta, AlertaPrecio, Perfil, ItemGuardado) |
| Relación N:N / ternaria | ✅ (`AlertaPrecio`: usuario + producto + tienda) |
| Mínimo 5 endpoints (GET, POST, PUT, PATCH, DELETE) | ✅ |
| Path params, query params y cuerpo JSON | ✅ |
| Intercambio de datos en JSON | ✅ |
| Especificación OpenAPI (Swagger/Redoc) | ✅ (`drf-spectacular`) |
| Control de versiones con commits frecuentes | ✅ |
| README.md | ✅ |

***

## 🔧 Comandos útiles de referencia

```bash
# Guardar dependencias actuales
cd backend
pip freeze > ../docs/important/dependencies.txt

# Actualizar todas las dependencias
pip-review --auto
pip freeze > ../docs/important/dependencies.txt

# Actualizar dependencias de forma interactiva
pip-review --interactive

# Deshacer último commit pusheado
git reset HEAD~1

# Deshacer último commit sin push
git reset --soft HEAD~1
```

***

## 📌 Roadmap y mejoras futuras

- Soporte para más tiendas y plataformas digitales (Steam, Instant Gaming, Amazon...).
- Historial de evolución de precios con visualizaciones gráficas.
- Sistema de notificaciones por email cuando se activa una alerta de precio.
- Despliegue en servidor remoto (Docker, VPS, PostgreSQL en producción).
- Optimización del selector de modelo IA según recursos disponibles del sistema.
- Ampliación del apartado de videojuegos con scrapers propios (ya integrado Steam e Instant Gaming en rama en desarrollo).

***

## 📄 Licencia

Proyecto académico desarrollado como Trabajo Intermodular de 2.º de Desarrollo de Aplicaciones Web (DAW).  
Puede reutilizarse y ampliarse con fines educativos citando al autor original.

***

## 👤 Autor

**Adrián RC** — [@AdrianRCdwec](https://github.com/AdrianRCdwec)  
2.º DAW · 2025–2026