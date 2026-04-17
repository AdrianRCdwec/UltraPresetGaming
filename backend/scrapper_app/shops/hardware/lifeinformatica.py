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


class LifeInformaticaScraper(BaseScraper):

    def extraer_productos_de_pagina(self, page):
        """Extrae productos de la vista actual adaptado a Life Informatica (WooCommerce)"""
        ultimo_conteo = 0
        intentos_sin_crecer = 0
        
        for _ in range(10):
            scroll_humano_avanzado(page, repeticiones=1, max_y=1800)

            conteo_actual = page.locator('li.product.type-product').count()
            if conteo_actual > ultimo_conteo:
                ultimo_conteo = conteo_actual
                intentos_sin_crecer = 0
            else:
                intentos_sin_crecer += 1
                
            if intentos_sin_crecer >= 2:
                break

        datos = page.evaluate(r'''() => {
            let resultados = [];
            let tarjetas = document.querySelectorAll('li.product.type-product');
            
            tarjetas.forEach(tarjeta => {
                try {
                    let enlaceEl = tarjeta.querySelector('a.woocommerce-LoopProduct-link');
                    let tituloEl = tarjeta.querySelector('h2.woocommerce-loop-product__title');
                    
                    if (enlaceEl && tituloEl) {
                        let nombre = tituloEl.innerText;
                        let link = enlaceEl.href;
                        
                        let imgEl = tarjeta.querySelector('img.attachment-woocommerce_thumbnail');
                        let imgUrl = imgEl ? imgEl.src : null;

                        // Lógica para precios de Life Informática (WooCommerce)
                        let precioStr = "0";
                        let precioIns = tarjeta.querySelector('.price ins .woocommerce-Price-amount bdi');
                        
                        if (precioIns) {
                            precioStr = precioIns.innerText; // Precio rebajado
                        } else {
                            let precioNormal = tarjeta.querySelector('.price .woocommerce-Price-amount bdi');
                            if (precioNormal) {
                                precioStr = precioNormal.innerText; // Precio normal
                            }
                        }
                        
                        // Limpiamos el texto del precio (ej: "649,88 €" -> "649.88")
                        precioStr = precioStr.replace('€', '').replace(/\u00a0/g, '').replace(/\s/g, '').replace('.', '').replace(',', '.');

                        if (nombre && nombre.trim() !== '') {
                            resultados.push({
                                nombre: nombre.trim(),
                                link: link,
                                precio: precioStr, 
                                imagen: imgUrl
                            });
                        }
                    }
                } catch(e) {
                    // Silenciamos el error individual para que siga iterando
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
        logger.info(f"\n🕷️ [LIFE INFO] -> Escaneando: {url_catalogo_base}")
        
        todos_los_productos_extraidos = []

        with sync_playwright() as p:
            # Usamos self.debug
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

            exito_carga = False
            for intento in range(3):
                try:
                    page.goto(url_catalogo_base, timeout=40000, wait_until="domcontentloaded")
                    resolver_captcha_cloudflare(page)
                    exito_carga = True
                    break 
                except Exception as e:
                    logger.warning(f"    ⚠️ Fallo de conexión en LifeInformatica. Intento {intento+1} de 3...")
                    page.wait_for_timeout(3000)

            if not exito_carga:
                logger.error(f"    ❌ Imposible cargar el catálogo {url_catalogo_base} tras 3 intentos. Abortando esta categoría.")
                context.close()
                browser.close()
                return 0

            # Todo el bloque siguiente solo se ejecuta si la página cargó con éxito
            try:
                # Espera máximo 5 segundos a que aparezca al menos un producto en el DOM
                try:
                    page.wait_for_selector('li.product.type-product', state='attached', timeout=5000)
                except:
                    pass

                # Rechazar cookies (vital para que no tape el botón Cargar Más)
                try:
                    btn_cookies = page.locator('#cf_consent-buttons__reject-all').first
                    if btn_cookies.is_visible(timeout=3000):
                        btn_cookies.click()
                        page.wait_for_timeout(2000)
                except:
                    pass  

                intentos_fallidos = 0
                MAX_REINTENTOS = 3

                # Bucle para pulsar "Cargar Más" hasta que desaparezca
                while True:
                    try:
                        boton_cargar_mas = page.locator('#yith-infs-button')

                        if boton_cargar_mas.is_visible(timeout=2000):
                            boton_cargar_mas.scroll_into_view_if_needed()
                            box = boton_cargar_mas.bounding_box()
                            
                            if box:
                                # Movemos el ratón hacia el botón en pasos (curva)
                                centro_x = box['x'] + box['width'] / 2
                                centro_y = box['y'] + box['height'] / 2
                                page.mouse.move(centro_x, centro_y, steps=random.randint(8, 15))
                                
                                # Pausa de duda antes de hacer clic
                                page.wait_for_timeout(random.uniform(100, 350))
                                page.mouse.click(centro_x, centro_y)
                            else:
                                boton_cargar_mas.click()
                            
                            logger.info("    ⏳ Cargando más productos...")
                            page.wait_for_timeout(2500)
                            intentos_fallidos = 0
                        else:
                            logger.info("    ✅ Catálogo completo desplegado.")
                            break
                    except Exception as e:
                        intentos_fallidos += 1
                        if intentos_fallidos <= MAX_REINTENTOS:
                            logger.warning(f"    ⚠️ Interferencia al pulsar 'Cargar Más' (Intento {intentos_fallidos}/{MAX_REINTENTOS}). Reintentando...")
                            page.wait_for_timeout(250)
                        else:
                            logger.error(f"    ❌ Imposible pulsar el botón tras {MAX_REINTENTOS} reintentos. Asumiendo fin del catálogo.")
                            break

                # Extraer TODOS los productos de golpe ahora que la página está entera
                datos_pagina = self.extraer_productos_de_pagina(page)
                
                if not datos_pagina:
                    logger.warning(f"  ⚠️ No se encontraron productos.")
                    return 0

                # Aplicar filtro de palabras excluidas
                if excluir_palabras:
                    datos_filtrados = []
                    for prod in datos_pagina:
                        nombre_lower = prod['nombre'].lower()
                        if not any(palabra in nombre_lower for palabra in excluir_palabras):
                            datos_filtrados.append(prod)
                    
                    datos_pagina = datos_filtrados
                    logger.info(f"  ✂️ Filtrados artículos no deseados. Quedan {len(datos_pagina)}.")
                    
                todos_los_productos_extraidos.extend(datos_pagina)
                
            except Exception as e:
                logger.error(f"❌ Error crítico en Playwright [{url_catalogo_base}]: {e}")
            finally:
                context.close()
                browser.close()
                
        return guardar_productos_en_db(
            productos_extraidos=todos_los_productos_extraidos,
            nombre_tienda="Life Informatica",
            url_base_tienda="https://lifeinformatica.com",
            categoria_db=categoria_db,
            tipo_db=tipo_db
        )

# Registrar scraper en la fábrica
ScraperFactory.registrar_scraper("lifeinformatica", LifeInformaticaScraper)