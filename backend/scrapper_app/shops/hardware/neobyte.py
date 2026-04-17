import random
import logging
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


class NeoByteScraper(BaseScraper):

    def extraer_productos_de_pagina(self, page):
        """Extrae productos de la vista actual adaptado a NeoByte"""
        ultimo_conteo = 0
        intentos_sin_crecer = 0
        
        for _ in range(10):
            scroll_humano_avanzado(page, repeticiones=1, max_y=1800)

            conteo_actual = page.locator('article.product-miniature').count()
            if conteo_actual > ultimo_conteo:
                ultimo_conteo = conteo_actual
                intentos_sin_crecer = 0
            else:
                intentos_sin_crecer += 1
                
            if intentos_sin_crecer >= 2:
                break

        datos = page.evaluate(r'''() => {
            let resultados = [];
            let tarjetas = document.querySelectorAll('article.product-miniature');
            
            tarjetas.forEach(tarjeta => {
                try {
                    let tituloEl = tarjeta.querySelector('.product-title a');
                    
                    if (tituloEl) {
                        let nombre = tituloEl.innerText;
                        let link = tituloEl.href;
                        
                        let precioStr = "0";
                        let precioEl = tarjeta.querySelector('.product-price');
                        if (precioEl) {
                            // NeoByte suele poner el precio en el atributo 'content' o como texto
                            precioStr = precioEl.getAttribute('content') || precioEl.innerText;
                        }
                        
                        let imgEl = tarjeta.querySelector('.product-thumbnail img');
                        // NeoByte usa lazy loading y puede guardar la url real en data-src
                        let imgUrl = null;
                        if (imgEl) {
                            imgUrl = imgEl.getAttribute('data-src') || imgEl.src;
                        }

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

    def escanear_catalogo(self, url_catalogo_base, categoria_db, tipo_db, excluir_palabras=None):
        print(f"\n🕷️ [NEOBYTE] -> Escaneando: {url_catalogo_base}")
        
        todos_los_productos_extraidos = []
        pagina_actual = 1
        hay_mas_paginas = True

        with sync_playwright() as p:
            browser = p.chromium.launch(
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

            context = browser.new_context(
                viewport={'width': ancho_viewport, 'height': alto_viewport},
                user_agent=perfil["user_agent"],
                locale='es-ES',
                timezone_id='Europe/Madrid',
                proxy=obtener_configuracion_proxy(),
                extra_http_headers=headers_completos
            )
            
            page = context.new_page()
            page.route("**/*", bloquear_recursos_innecesarios)
            
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.chrome = { runtime: {} };
            """)
            
            try:
                while hay_mas_paginas:
                    url_con_paginacion = f"{url_catalogo_base}?page={pagina_actual}"
                    print(f"  📄 Entrando a la página {pagina_actual}... ({url_con_paginacion})")
                    
                    exito_carga = False
                    for intento in range(3):
                        try:
                            page.goto(url_con_paginacion, timeout=40000, wait_until="domcontentloaded")
                            resolver_captcha_cloudflare(page)
                            exito_carga = True
                            break
                        except Exception as e:
                            print(f"    ⚠️ Fallo de conexión en página {pagina_actual}. Intento {intento+1} de 3...")
                            page.wait_for_timeout(3000)

                    if not exito_carga:
                        print(f"    ❌ Imposible cargar la página {pagina_actual} tras 3 intentos. Cancelando catálogo.")
                        hay_mas_paginas = False
                        break

                    try:
                        page.wait_for_selector('article.product-miniature', state='attached', timeout=5000)
                    except:
                        pass

                    # Cookies en la primera página
                    if pagina_actual == 1:
                        try:
                            btn_cookies = page.locator('.cookiesplus-reject').first
                            if btn_cookies.is_visible(timeout=3000):
                                btn_cookies.click()
                                print("    🍪 Cookies rechazadas en NeoByte.")
                                page.wait_for_timeout(1000)
                        except:
                            pass 

                    # Extraer de la página
                    datos_pagina = self.extraer_productos_de_pagina(page)
                    
                    if not datos_pagina:
                        print(f"  ⚠️ No se encontraron productos. Fin del catálogo.")
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
                        print(f"  ✂️ Filtrados artículos no deseados. Quedan {len(datos_pagina)} en esta página.")
                    
                    todos_los_productos_extraidos.extend(datos_pagina)
                    
                    # Comprobar si hay botón "Siguiente" activo en la paginación
                    siguiente_deshabilitado = page.evaluate(r'''() => {
                        let nextBtn = document.querySelector('a[rel="next"], a.next');
                        if (!nextBtn) return true; // Si no existe, no hay más
                        return false; // Si existe, hay más páginas
                    }''')

                    if siguiente_deshabilitado:
                        hay_mas_paginas = False
                    else:
                        pagina_actual += 1

            except Exception as e:
                print(f"❌ Error en Playwright escaneando NeoByte: {e}")
                logging.error(f"[SCRAPER {url_catalogo_base}] Fallo crítico: {str(e)}")
            finally:
                context.close()
                browser.close()

        # Llamamos a la función universal para guardar en la BD
        return guardar_productos_en_db(
            productos_extraidos=todos_los_productos_extraidos,
            nombre_tienda="NeoByte",
            url_base_tienda="https://www.neobyte.es",
            categoria_db=categoria_db,
            tipo_db=tipo_db
        )

# Registrar scraper en la fábrica
ScraperFactory.registrar_scraper("neobyte", NeoByteScraper)