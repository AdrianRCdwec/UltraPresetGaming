import random
from playwright.sync_api import sync_playwright
from scrapper_app.utils.events import shutdown_event
from .base_scraper import BaseScraper
from .factory import ScraperFactory
from scrapper_app.utils.stealth import (
    obtener_perfil_navegador, 
    bloquear_recursos_innecesarios, 
    resolver_captcha_cloudflare, 
    scroll_humano_avanzado,
    obtener_configuracion_proxy
)
from scrapper_app.utils.db_manager import guardar_productos_en_db
from scrapper_app.utils.logger import logger


class AlternateScraper(BaseScraper):

    def iniciar_navegador(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=not self.debug, 
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu"
            ]
        )

        ancho_viewport = random.randint(1366, 1920)
        alto_viewport = random.randint(768, 1080)
        perfil = obtener_perfil_navegador()

        headers_base = {
            'Accept-Language': 'es-ES,es;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1'
        }

        headers_completos = {**headers_base, **perfil["headers"]}

        self.context = self.browser.new_context(
            viewport={'width': ancho_viewport, 'height': alto_viewport},
            user_agent=perfil["user_agent"],
            locale='es-ES',
            timezone_id='Europe/Madrid',
            proxy=obtener_configuracion_proxy(),
            extra_http_headers=headers_completos
        )
        self.page = self.context.new_page()
        
        self.page.route("**/*", bloquear_recursos_innecesarios)
        self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = { runtime: {} };
        """)

    def escanear_catalogo(self, url_catalogo_base, categoria_db, tipo_db, excluir_palabras=None):
        logger.info(f"\n🕷️ [ALTERNATE] -> Escaneando: {url_catalogo_base}")
        
        todos_los_productos_extraidos = []
        pagina_actual = 1
        hay_mas_paginas = True

        try:
            while hay_mas_paginas:
                if shutdown_event.is_set():
                    logger.warning(f"  🛑 Apagado seguro detectado. Saliendo de {url_catalogo_base}...")
                    break
                url_con_paginacion = f"{url_catalogo_base}?page={pagina_actual}"
                logger.info(f"  📄 Entrando a la página {pagina_actual}...")

                exito_carga = False
                for intento in range(3):
                    try:
                        self.page.goto(url_con_paginacion, timeout=40000, wait_until="domcontentloaded")
                        resolver_captcha_cloudflare(self.page)
                        exito_carga = True
                        break
                    except Exception as e:
                        logger.warning(f"    ⚠️ Fallo de conexión en página {pagina_actual}. Intento {intento+1} de 3...")
                        self.page.wait_for_timeout(3000)

                if not exito_carga:
                    logger.error(f"    ❌ Imposible cargar la página {pagina_actual} tras 3 intentos. Cancelando catálogo.")
                    hay_mas_paginas = False
                    break

                try:
                    # Espera máximo 5 segundos a que aparezca al menos un producto en el DOM
                    self.page.wait_for_selector('a.productBox', state='attached', timeout=5000)
                except:
                    pass

                # Cookies (Solo en la primera página)
                if pagina_actual == 1:
                    try:
                        btn_cookies = self.page.locator('#deny').first
                        if btn_cookies.is_visible(timeout=3000):
                            btn_cookies.click()
                            self.page.wait_for_timeout(1000)
                    except:
                        pass 

                # Extraer de la página
                datos_pagina = self.extraer_productos_de_pagina(self.page)
                
                if not datos_pagina:
                    logger.warning(f"  ⚠️ No se encontraron productos. Fin del catálogo.")
                    hay_mas_paginas = False
                    break

                # Aplicar filtro de palabras excluidas
                if excluir_palabras:
                    datos_filtrados = []
                    for prod in datos_pagina:
                        nombre_lower = prod['nombre'].lower()
                        if not any(palabra in nombre_lower for palabra in excluir_palabras):
                            datos_filtrados.append(prod)
                    
                    datos_pagina = datos_filtrados
                    logger.info(f"  ✂️ Filtrados artículos no deseados. Quedan {len(datos_pagina)} en esta página.")
                
                todos_los_productos_extraidos.extend(datos_pagina)
                
                # Comprobar botón "Página Siguiente"
                siguiente_deshabilitado = self.page.evaluate(r'''() => {
                    let nextBtn = document.querySelector('a[aria-label="Página siguiente"]');
                    if (!nextBtn) return true;
                    // En Alternate, cuando no hay más páginas, el botón suele tener la clase "disabled"
                    return nextBtn.classList.contains('disabled');
                }''')

                if siguiente_deshabilitado:
                    hay_mas_paginas = False
                else:
                    pagina_actual += 1

        except Exception as e:
            logger.error(f"❌ Error crítico en Playwright [{url_catalogo_base}]: {e}")

        # Llamamos a la función universal para guardar en la BD
        return guardar_productos_en_db(
            productos_extraidos=todos_los_productos_extraidos,
            nombre_tienda="Alternate",
            url_base_tienda="https://www.alternate.es",
            categoria_db=categoria_db,
            tipo_db=tipo_db
        )

    def extraer_productos_de_pagina(self, page):
        """Extrae productos de la vista actual adaptado a Alternate"""
        ultimo_conteo = 0
        intentos_sin_crecer = 0
        
        for _ in range(10):
            scroll_humano_avanzado(page, repeticiones=1, max_y=1800)

            conteo_actual = page.locator('a.productBox').count()
            if conteo_actual > ultimo_conteo:
                ultimo_conteo = conteo_actual
                intentos_sin_crecer = 0
            else:
                intentos_sin_crecer += 1
                
            if intentos_sin_crecer >= 2:
                break

        datos = page.evaluate(r'''() => {
            let resultados = [];
            // Alternate utiliza estos elementos 'a' como tarjetas de producto
            let tarjetas = document.querySelectorAll('a.productBox');
            
            tarjetas.forEach(tarjeta => {
                try {
                    let link = tarjeta.href;
                    
                    // El nombre está dentro de un div con clase 'product-name'
                    let nombreEl = tarjeta.querySelector('.product-name');
                    let subtituloEl = tarjeta.querySelector('.product-name-sub');
                    let nombre = "";
                    
                    if (nombreEl) {
                        nombre = nombreEl.innerText.trim();
                        // A veces añaden el tipo de caja en el subtitulo, lo juntamos si quieres o lo dejamos así
                        if (subtituloEl && subtituloEl.innerText.trim() !== '') {
                            nombre += " " + subtituloEl.innerText.trim();
                        }
                    }
                    
                    // El precio está en un span con clase 'price'
                    let precioStr = "0";
                    let precioEl = tarjeta.querySelector('.price');
                    if (precioEl) {
                        precioStr = precioEl.innerText;
                    }
                    
                    let imgEl = tarjeta.querySelector('.productPicture');
                    let imgUrl = imgEl ? imgEl.src : null;

                    if (nombre !== '' && precioStr !== "0") {
                        resultados.push({
                            nombre: nombre,
                            link: link,
                            precio: precioStr, 
                            imagen: imgUrl
                        });
                    }
                } catch(e) {
                    // Silenciamos error individual
                }
            });
            
            // Filtramos duplicados
            let unicos = [];
            let linksVistos = new Set();
            resultados.forEach(r => {
                if(!linksVistos.has(r.link)) {
                    linksVistos.add(r.link);
                    unicos.push(r);
                }
            });
            
            return unicos;
        }''')
        
        return datos

# Registrar scraper en la fábrica
ScraperFactory.registrar_scraper("alternate", AlternateScraper)