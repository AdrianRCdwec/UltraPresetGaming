 # UltraPresetGaming
 
 ## Descripción
 UltraPresetGaming es una aplicación web comparadora de precios de hardware y videojuegos entre distintas tiendas y plataformas. Permite a los usuarios buscar y comparar precios, recibir alertas y visualizar tendencias de precios.
 
 ## Tecnologías
 - **Frontend:** HTML5, CSS3 (Bootstrap 5), JavaScript (Vanilla)
 - **Backend:** Python 3.11, Django 6.0, Django REST Framework
 - **Base de datos:** SQLite (desarrollo) / PostgreSQL (producción)
 - **Scraping:** Playwright, I/O asíncrono, Celery (para descargas de imágenes)
 - **IA:** Ollama (LLM) para matching de productos
 - **Otros:** Redis (caché), Docker (despliegue opcional)
 
 ## Estructura del proyecto
 ```
 UltraPresetGaming/
 ├── backend/                  # Proyecto Django
 │   ├── api/
 │   ├── comparador/
 │   ├── scrapper_app/
 │   └── manage.py
 ├── docs/
 │   ├── dependencies.txt
 │   ├── RESUMEN.txt
 │   └── webUpgrades.md
 ├── frontend/                 # Sitio web
 │   ├── assets/
 │   ├── pages/
 │   └── index.html
 └── README.md
 ```
 
 ## Instalación
 ```bash
 # Clonar el repositorio
 git clone https://github.com/AdrianRCdwec/UltraPresetGaming.git
 cd UltraPresetGaming
 
 # Crear entorno virtual (recomendado)
 python -m venv venv
 venv\Scripts\activate   # Windows
 # source venv/bin/activate   # Linux/macOS
 
 # Instalar dependencias
 pip install -r backend/requirements.txt
 
 # Migrar base de datos
 python backend/manage.py migrate
 
 # Crear superusuario (opcional)
 python backend/manage.py createsuperuser
 ```
 
 ## Uso
 ```bash
 # Ejecutar servidor de desarrollo
 python backend/manage.py runserver 0.0.0.0:8000
 # Acceder a http://127.0.0.1:8000/ en el navegador
 ```
 
 ## Características principales
 - Comparación de precios entre múltiples tiendas.
 - Búsqueda avanzada por palabras clave.
 - Alertas de precios y notificaciones.
 - Gráficos de tendencias con Chart.js.
 - Historial de precios y disponibilidad de stock.
 - Integración con IA para matching de productos.
 - Scraping asíncrono y rotación de proxies/User‑Agents.
 - Sistema de logging profesional.
 
 ## Mejoras planificadas (extraídas de `Mejoras página WEB.md`)
 ### Rendimiento y Scraping (Playwright)
 - Reutilizar contextos de Playwright.
 - Deshabilitar la carga de JavaScript donde no sea necesario.
 - Implementar rotación de proxies por petición.
 
 ### Base de Datos y Caché (Django/SQLite)
 - Evitar bloqueos de SQLite con semáforo (`threading.Lock()`).
 - Implementar caché en Redis.
 
 ### Inteligencia Artificial y Matching (LLM / NLP)
 - Reintentos en llamadas a la IA (Retry & Timeout).
 
 ### Scrapers y Web
 - Descarga asíncrona de imágenes (I/O Non‑Blocking) con Celery.
 - Extraer el stock real (En stock / Sin stock / Recíbelo mañana).
 
 ### Calidad de Código y Arquitectura (QA / Dev)
 - Refactorizar `main_crawler.py` siguiendo el principio DRY.
 - Securizar variables de entorno (proxies) usando `.env`.
 - Añadir pruebas unitarias con Pytest.
 
 ### Manejo de Errores y Robustez
 - Notificaciones por Telegram/Discord en caso de fallos críticos.
 
 ## Contribuir
 1. Haz fork del repositorio.
 2. Crea una rama `feature/nueva-funcionalidad`.
 3. Realiza los cambios y pruebas.
 4. Abre un Pull Request describiendo la mejora.
 
 ## Licencia
 Este proyecto está bajo la licencia MIT. Ver el archivo `LICENSE` para más detalles.
 ```
