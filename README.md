# UltraPresetGaming 🎮🖥️

Aplicación web de comparación de precios de hardware y videojuegos que consume una API REST propia desarrollada con Django y Django REST Framework. El sistema integra un motor de scraping basado en Playwright y técnicas de IA (modelos locales vía Ollama y TF‑IDF) para mantener actualizado un catálogo de productos, tiendas y ofertas de forma automática.

Este proyecto es el **Trabajo Intermodular de 2.º DAW (Tipo 2: HTML + CSS + JavaScript consumiendo API REST propia)**.

---

## 🧩 Objetivos del proyecto

- Permitir al usuario comparar rápidamente precios de **hardware** (GPU, CPU, etc.) y **videojuegos** entre distintas tiendas especializadas.
- Mostrar siempre un **precio de referencia u “oficial”** frente a las ofertas encontradas en las tiendas.
- Ofrecer una experiencia de usuario cuidada, responsive y accesible, con **múltiples pantallas** (inicio, listados, detalle, comparador, carrito/checkout, perfil, etc.).
- Automatizar la obtención de precios mediante **scraping concurrente** y un sistema de **matching inteligente de productos** con IA local y TF‑IDF.
- Cumplir los requisitos del proyecto intermodular: API REST propia con múltiples endpoints, relación ternaria en la base de datos, documentación y memoria técnica.

---

## 🏗️ Tipo de proyecto y alcance académico

- **Tipo de proyecto:** Tipo 2 (HTML + JS + CSS consumiendo un API REST de elaboración propia desde JavaScript).
- **Backend:** Django + Django REST Framework.
- **Frontend:** HTML5, CSS3, JavaScript vanilla.
- **Scraper + IA:** Playwright, TF‑IDF (scikit‑learn), modelos locales vía Ollama.
- **Base de datos:** SQLite en desarrollo (adaptable a otros motores en despliegue).

El proyecto está pensado como **prototipo funcional** y base de un posible producto futuro, ampliable a nuevas tiendas, nuevas categorías y nuevas funcionalidades (alertas avanzadas, recomendaciones, etc.).

---

## ✨ Funcionalidades principales

### Frontend (HTML/CSS/JS)

- Página de **inicio** con acceso rápido a hardware, videojuegos y noticias.
- Listados dinámicos de **productos** (hardware y videojuegos) obtenidos desde la API REST.
- **Detalle y comparador de precios** por producto:
  - Visualización del precio oficial.
  - Ofertas activas en distintas tiendas, indicando ahorro y coste final.
- **Carrito / checkout**:
  - Selección de ofertas por producto.
  - Cálculo de totales, ahorro total y coste con envío.
  - Persistencia de carrito para usuarios invitados usando `localStorage`.
- Navegación coherente entre pantallas (inicio, listados, perfil, login/registro…).
- Diseño responsive (móvil, tablet, escritorio) mediante media queries.

### Backend (Django + DRF)

- Modelado de entidades principales:
  - **Producto**, **Tienda**, **Oferta** (relación 1:N y N:M).
  - **AlertaPrecio** como **relación ternaria** entre usuario, producto y tienda.
  - **DecisionIA** como caché de decisiones del motor de IA para evitar recomputar comparaciones.
- API REST con múltiples endpoints para:
  - Listar y gestionar productos, tiendas y ofertas.
  - Gestionar elementos del carrito/configuración personalizada.
  - Crear y administrar alertas de precio por usuario autenticado.
- Soporte de métodos HTTP: GET, POST, PUT, PATCH y DELETE.
- Soft-delete de ofertas mediante flag `disponible` para preservar histórico de precios.

### Scraper + IA

- Orquestador principal multihilo con **ThreadPoolExecutor**.
- **BaseScraper** abstracto y factoría de scrapers por tienda (PcComponentes, Coolmod, Life Informática, Alternate, NeoByte, etc.).
- Uso de **Playwright** con:
  - Rotación dinámica de User‑Agents y Client‑Hints.
  - Simulación de comportamiento humano (scroll, movimientos de ratón, tiempos de espera).
  - Resolución de captchas y pantallas tipo “Just a moment…” (Cloudflare).
- Descarga y guardado local de imágenes de productos en `media/`.
- Motor de matching de productos con:
  - Limpieza avanzada de nombres mediante expresiones regulares precompiladas.
  - Vectorización TF‑IDF + similitud del coseno para emparejar productos en milisegundos.
  - IA local via Ollama:
    - Modelo ligero (ej. Phi‑3) para filtrar decisiones triviales.
    - Modelo más pesado sólo para casos dudosos.
    - Caché en BD (`DecisionIA`) para no repetir comparaciones.

---

## 🛠️ Stack tecnológico

**Frontend**

- HTML5, CSS3, JavaScript vanilla.
- Diseño responsive con media queries.
- Organización modular de CSS (estilos compartidos, variables, componentes comunes).

**Backend**

- Python 3.x
- Django
- Django REST Framework
- SQLite (desarrollo)

**Scraping + IA**

- Playwright para Python
- scikit‑learn (TF‑IDF)
- Ollama (modelos locales)
- requests
- logging centralizado
- concurrent.futures / threading

---

## 🔗 Repositorio y control de versiones

El código fuente se aloja en GitHub y se ha desarrollado usando **control de versiones con commits frecuentes y detallados**, que reflejan la evolución del proyecto:

- Refactors del scraper (modularización, patrón Factory, BaseScraper, factoría de tiendas).
- Incorporación progresiva de TF‑IDF, caché de IA, batching, async, logging, graceful shutdown.
- Mejoras en el frontend, corrección de rutas de imágenes, reestructuración de carpetas y CSS compartido.
- Documentación adicional (comandos, mejoras futuras, etc.).

---

## 📁 Estructura del proyecto

```text
.
|-- backend
|   |-- api
|   |   |-- migrations
|   |   |   |-- __init__.py
|   |   |   |   0001_initial.py
|   |   |   |   0002_producto_categoria.py
|   |   |   |   0003_producto_imagen_alter_producto_categoria.py
|   |   |   |   0004_alter_producto_categoria.py
|   |   |   |   0005_oferta_disponible.py
|   |   |   |   0006_perfil_itemguardado.py
|   |   |   |   0007_alertaprecio.py
|   |   |   |   0008_decisionia.py
|   |   |   |   0009_alter_producto_categoria_alter_producto_nombre.py
|   |   |   |   0010_tienda_logo.py
|   |   |-- __init__.py
|   |   |-- admin.py
|   |   |-- apps.py
|   |   |-- backends.py
|   |   |-- models.py
|   |   |-- serializers.py
|   |   |-- tests.py
|   |   |-- urls.py
|   |   `-- views.py
|   |-- comparador
|   |   |-- __init__.py
|   |   |-- asgi.py
|   |   |-- settings.py
|   |   |-- urls.py
|   |   `-- wsgi.py
|   |-- media
|   |   |-- perfiles
|   |   |   `-- Spotify.jpeg
|   |   |-- productos
|   |   `-- profiles
|   |-- scrapper_app
|   |   |-- shops
|   |   |   |-- hardware
|   |   |   |   |-- __init__.py
|   |   |   |   |-- alternate.py
|   |   |   |   |-- base_scraper.py
|   |   |   |   |-- coolmod.py
|   |   |   |   |-- factory.py
|   |   |   |   |-- lifeinformatica.py
|   |   |   |   |-- neobyte.py
|   |   |   |   `-- pccomponentes.py
|   |   |   `-- videogames
|   |   |       `-- __init__.py
|   |   |-- utils
|   |   |   |-- __init__.py
|   |   |   |-- db_manager.py
|   |   |   |-- events.py
|   |   |   |-- ia_matcher.py
|   |   |   |-- interactive_prompt.py
|   |   |   |-- logger.py
|   |   |   `-- stealth.py
|   |   |-- __init__.py
|   |   |-- main_crawler.py
|   |   `-- scraper.log
|   |-- db.sqlite3
|   `-- manage.py
|-- docs
|   |-- extras
|   |   |-- archivos
|   |   |   |-- RESUMEN.md
|   |   |   `-- RESUMEN.txt
|   |   |-- PDFs
|   |   |   |-- Explicación Proyecto Intermodular.pdf
|   |   |   `-- Requisitos Proyecto.pdf
|   |   `-- structure.txt
|   `-- important
|       |-- comandsList.txt
|       |-- dependencies.txt
|       |-- requirementsToExecuteScripts.txt
|       `-- webUpgrades.md
|-- frontend
|   |-- assets
|   |   |-- images
|   |   |   |-- games
|   |   |   |-- hardware
|   |   |   |-- icons
|   |   |   |   |-- instagram.svg
|   |   |   |   |-- menu.svg
|   |   |   |   |-- tiktok.svg
|   |   |   |   |-- x.svg
|   |   |   |   `-- youtube.svg
|   |   |   |-- misc
|   |   |   |-- news
|   |   |   |   |-- gtaVI.jpeg
|   |   |   |   |-- nvidia.jpeg
|   |   |   |   `-- snapdragon.jpeg
|   |   |   `-- shops
|   |   `-- favicon.ico
|   |-- pages
|   |   |-- hardware
|   |   |   |-- hardware.css
|   |   |   |-- hardware.html
|   |   |   `-- hardware.js
|   |   |-- home
|   |   |   |-- home.css
|   |   |   `-- index.html
|   |   |-- login
|   |   |   |-- login.css
|   |   |   |-- login.html
|   |   |   `-- login.js
|   |   |-- mods
|   |   |   |-- mods.css
|   |   |   `-- mods.html
|   |   |-- news
|   |   |   |-- news.css
|   |   |   `-- news.html
|   |   |-- prices
|   |   |   |-- prices.css
|   |   |   |-- prices.html
|   |   |   `-- prices.js
|   |   |-- profile
|   |   |   |-- profile.html
|   |   |   |-- profile.js
|   |   |   `-- profile-main.css
|   |   |-- register
|   |   |   |-- register.css
|   |   |   |-- register.html
|   |   |   `-- register.js
|   |   `-- videogames
|   |       |-- videogames.css
|   |       |-- videogames.html
|   |       `-- videogames.js
|   |-- shared
|   |   |-- css
|   |   |   |-- button.css
|   |   |   |-- footer.css
|   |   |   |-- header.css
|   |   |   |-- profile.css
|   |   |   `-- reset.css
|   |   `-- js
|   |       `-- auth-header.js
|   `-- index.html
|-- scripts
|   |-- run-crawler.ps1
|   `-- tr.ps1
|-- .gitignore
|-- LICENSE
`-- README.md
```

---

## 💻 Requisitos previos

### Hardware (desarrollo local)

- CPU multi‑núcleo (4–8 núcleos recomendados).
- 16 GB de RAM recomendados si se usan modelos locales de IA con Ollama.
- Al menos 50 GB de espacio libre si se almacenan varios modelos y datos del proyecto.

### Software

- Sistema operativo: Windows 10/11, macOS o Linux.
- Python 3.10+.
- pip para instalación de dependencias.
- Node/PowerShell (opcional) para ejecutar ciertos scripts auxiliares.
- Git para clonar el repositorio.
- Navegador moderno (Chrome, Edge, Firefox).

---

## 🚀 Puesta en marcha (desarrollo local)

### 1. Clonar el repositorio

```bash
git clone https://github.com/AdrianRCdwec/UltraPresetGaming.git
cd UltraPresetGaming
```

### 2. Crear y activar entorno virtual

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Aplicar migraciones y crear superusuario

```bash
cd backend
python manage.py migrate
python manage.py createsuperuser
```

### 5. Ejecutar el servidor Django

```bash
python manage.py runserver
```

El backend quedará accesible en `http://127.0.0.1:8000/`.

### 6. Ejecutar el frontend

Abre el archivo principal del frontend (por ejemplo `frontend/index.html`) en el navegador, idealmente sirviéndolo con un servidor estático simple (VS Code Live Server o similar) para evitar problemas con rutas relativas.

---

## 🧪 Ejecución del scraper

El proyecto incluye scripts para lanzar el motor de scraping de forma cómoda.

Ejemplo en PowerShell (Windows):

```powershell
# Desde la raíz del proyecto
scripts\run-crawler.ps1
```

El script se encarga de:

- Activar el entorno virtual.
- Colocarse en el directorio backend correspondiente.
- Ejecutar `main_crawler.py` con los parámetros adecuados (modo normal, secuencial o debug).

Durante la ejecución, el scraper:

- Abre Playwright con perfiles “stealth”.
- Recorre las tiendas configuradas.
- Descarga/actualiza productos, ofertas e imágenes en la base de datos.

---

## 🌐 API REST (resumen)

La API REST está construida con Django REST Framework y expone, entre otros, recursos como:

- **Productos**: listado, detalle, filtrado por categoría, etc.
- **Tiendas**: listado de tiendas disponibles y sus logos.
- **Ofertas**: ofertas activas asociadas a productos y tiendas.
- **Alertas de precio**: creación y gestión de alertas por usuario logueado.
- **Configuración / carrito**: endpoints para sincronizar selección de productos.

La configuración usa `ViewSet`s y routers de DRF, proporcionando endpoints estándar para operaciones CRUD (GET, POST, PUT, PATCH, DELETE) sobre los recursos anteriores.

Además, se incluye una **especificación OpenAPI** (Swagger/Redoc) accesible desde el backend, que documenta los endpoints, parámetros y respuestas.

---

## 🔐 Autenticación y seguridad

- Autenticación basada en Django (y/o JWT si se configura).
- Los endpoints sensibles (por ejemplo, gestión de alertas de precio) requieren usuario autenticado.
- El frontend gestiona el estado de sesión (token, cabeceras de autorización, etc.) y ajusta la UI según si el usuario está logueado o no.

---

## 🧱 Requisitos del proyecto intermodular cubiertos

- **Tipo 2:** HTML + CSS + JS consumiendo API REST propia.
- **UI:** Mínimo 4 pantallas, uso de etiquetas semánticas, diseño responsive.
- **Django (backend):**
  - Al menos 3 modelos usados en la fachada REST.
  - Relación **N:N / ternaria** mediante `AlertaPrecio`.
  - Endpoints con GET, POST, PUT, PATCH y DELETE.
  - Uso de parámetros en ruta, query y cuerpo.
  - Intercambio de datos en formato JSON.
- **Documentación:** README, memoria en PDF, diagramas y especificación OpenAPI.

---

## 📌 Roadmap y mejoras futuras

- Soporte para más tiendas y plataformas digitales.
- Historial de evolución de precios con visualizaciones gráficas.
- Sistema de notificaciones por email para alertas de precio.
- Despliegue en servidor remoto (Docker, VPS, etc.).
- Optimización de modelos de IA y selección automática de modelo según recursos disponibles.

---

## 📄 Licencia

Proyecto académico desarrollado como Trabajo Intermodular de 2.º de Desarrollo de Aplicaciones Web.  
Puede reutilizarse y ampliarse con fines educativos, citando al autor original.