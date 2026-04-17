import random
from playwright.sync_api import sync_playwright

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


class CoolmodScraper(BaseScraper):

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
        logger.info(f"\n🕷️ [COOLMOD] -> Escaneando: {url_catalogo_base}")
        
        todos_los_productos_extraidos = []
        pagina_actual = 1
        hay_mas_paginas = True

        try:
            while hay_mas_paginas:
                separador = "&" if "?" in url_catalogo_base else "?"
                url_con_paginacion = f"{url_catalogo_base}{separador}pagina={pagina_actual}"
                
                logger.info(f"  📄 Entrando a la página {pagina_actual}...")
                
                exito_carga = False
                for intento in range(3):
                    try:
                        self.page.goto(url_con_paginacion, timeout=40000, wait_until="domcontentloaded")
                        resolver_captcha_cloudflare(self.page)
                        exito_carga = True
                        break
                    except Exception as e:
                        logger.warning(f"    ⚠️ Fallo de conexión (Intento {intento+1}/3)...")
                        self.page.wait_for_timeout(3000)

                if not exito_carga:
                    logger.error(f"    ❌ Imposible cargar la página {pagina_actual}. Cancelando catálogo.")
                    break

                try:
                    self.page.wait_for_selector('article.product-card', state='attached', timeout=5000)
                except:
                    pass

                # Aceptamos cookies solo en la primera página
                if pagina_actual == 1:
                    try:
                        btn_cookies = self.page.locator('#CybotCookiebotDialogBodyButtonDecline').first
                        if btn_cookies.is_visible(timeout=3000):
                            btn_cookies.click()
                            self.page.wait_for_timeout(1000)
                    except:
                        pass 

                datos_pagina = self.extraer_productos_de_pagina(self.page)
                
                if not datos_pagina:
                    logger.warning(f"  ⚠️ No se encontraron productos. Fin del catálogo.")
                    break

                # Aplicar lógica de exclusión de palabras de tu código original
                if excluir_palabras:
                    datos_filtrados = []
                    for prod in datos_pagina:
                        nombre_lower = prod['nombre'].lower()
                        if not any(palabra in nombre_lower for palabra in excluir_palabras):
                            datos_filtrados.append(prod)
                    
                    datos_pagina = datos_filtrados
                    logger.info(f"  ✂️ Filtrados artículos no deseados. Quedan {len(datos_pagina)} en esta página.")
                    
                todos_los_productos_extraidos.extend(datos_pagina)
                
                # Lógica de paginación adaptada a Coolmod
                siguiente_deshabilitado = self.page.evaluate(r'''() => {
                    let nextBtn = document.querySelector('.paginate-buttons.next-button');
                    if (!nextBtn) return true; 
                    return nextBtn.disabled || nextBtn.hasAttribute('disabled') || nextBtn.classList.contains('disabled');
                }''')

                if siguiente_deshabilitado:
                    hay_mas_paginas = False
                else:
                    pagina_actual += 1

        except Exception as e:
            logger.error(f"❌ Error crítico en Playwright [{url_catalogo_base}]: {e}")

        return guardar_productos_en_db(
            productos_extraidos=todos_los_productos_extraidos,
            nombre_tienda="Coolmod",
            url_base_tienda="https://www.coolmod.com",
            categoria_db=categoria_db,
            tipo_db=tipo_db
        )

    def extraer_productos_de_pagina(self, page):
        """Extrae productos de la vista actual adaptado a Coolmod"""
        ultimo_conteo = 0
        intentos_sin_crecer = 0
        
        for _ in range(10):
            scroll_humano_avanzado(page, repeticiones=1, max_y=1800)

            conteo_actual = page.locator('article.product-card').count()
            if conteo_actual > ultimo_conteo:
                ultimo_conteo = conteo_actual
                intentos_sin_crecer = 0
            else:
                intentos_sin_crecer += 1
                
            if intentos_sin_crecer >= 2:
                break

        datos = page.evaluate(r'''() => {
            let resultados = [];
            let tarjetas = document.querySelectorAll('article.product-card');
            
            tarjetas.forEach(tarjeta => {
                try {
                    let datosProducto = tarjeta.querySelector('figure a[data-itemname]');
                    
                    if (datosProducto) {
                        let nombre = datosProducto.getAttribute('data-itemname');
                        let precioStr = datosProducto.getAttribute('data-itemprice');
                        let link = datosProducto.href;
                        
                        let imgEl = datosProducto.querySelector('img');
                        let imgUrl = imgEl ? imgEl.src : null;

                        if (nombre && precioStr && nombre.trim() !== '') {
                            resultados.push({
                                nombre: nombre.trim(),
                                link: link,
                                precio: precioStr.toString(), 
                                imagen: imgUrl
                            });
                        }
                    }
                } catch(e) {
                    // Silenciamos el error individual para que siga iterando
                }
            });
            
            // Filtramos duplicados por si Coolmod renderiza algún elemento de más
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
ScraperFactory.registrar_scraper("coolmod", CoolmodScraper)