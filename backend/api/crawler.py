import sys
import os
import django
import re
from playwright.sync_api import sync_playwright

# --- CONFIGURACIÓN DE DJANGO ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comparador.settings') 
django.setup()

from api.models import Producto, Tienda, Oferta

def limpiar_precio(texto):
    if not texto: return 0.0
    texto = str(texto).strip()
    
    if re.match(r'^\d+\.\d+$', texto):
        return float(texto)
    
    numeros = re.findall(r'\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?', texto)
    if not numeros: return 0.0
    
    num_str = numeros[0]
    if '.' in num_str and ',' in num_str:
        num_str = num_str.replace('.', '').replace(',', '.')
    elif ',' in num_str:
        num_str = num_str.replace(',', '.')
    elif '.' in num_str:
        if len(num_str.split('.')[-1]) == 2:
            pass 
        else:
            num_str = num_str.replace('.', '')
            
    return float(num_str)


# =================================================================
# NUEVA FUNCIÓN UNIVERSAL PARA GUARDAR EN LA BD (Sirve para TODAS las tiendas)
# =================================================================
def guardar_productos_en_db(productos_extraidos, nombre_tienda, url_base_tienda, categoria_db, tipo_db):
    if not productos_extraidos:
        return 0

    print(f"\n💾 Guardando {len(productos_extraidos)} productos en la BD para la tienda {nombre_tienda}...")
    
    # Nos aseguramos de que la tienda existe (ya sea Amazon, PcComponentes, etc)
    tienda_db, _ = Tienda.objects.get_or_create(
        nombre=nombre_tienda,
        defaults={"url_base": url_base_tienda}
    )
    
    productos_guardados_exitosamente = 0
    
    for item in productos_extraidos:
        try:
            nombre_limpio = item['nombre'].strip()
            precio_float = limpiar_precio(item['precio'])
            
            if precio_float <= 0:
                continue

            # 1. Producto
            producto, creado_prod = Producto.objects.get_or_create(
                nombre=nombre_limpio,
                defaults={'tipo': tipo_db, 'categoria': categoria_db}
            )
            
            # 2. Oferta
            oferta, creado_oferta = Oferta.objects.update_or_create(
                producto=producto,
                tienda=tienda_db,
                defaults={
                    'precio_base': precio_float,
                    'enlace_compra': item['link'],
                    'gastos_envio': 0.00,
                    'descuento_porcentaje': 0.00
                }
            )
            productos_guardados_exitosamente += 1
            print(f"{'➕ NUEVO' if creado_prod else '🔄 ACTUALIZADO'}: {nombre_limpio} -> {precio_float}€")
            
        except Exception as db_error:
            print(f"❌ Error guardando '{item.get('nombre', 'Desconocido')}': {db_error}")

    return productos_guardados_exitosamente


# =================================================================
# LÓGICA EXCLUSIVA DE PC COMPONENTES
# =================================================================
def extraer_productos_de_pagina_pcc(page):
    """Extrae productos de la vista actual adaptado a PcComponentes"""
    for _ in range(8):
        page.mouse.wheel(0, 1000)
        page.wait_for_timeout(800)

    datos = page.evaluate('''() => {
        let resultados = [];
        let tarjetas = document.querySelectorAll('a[data-product-id], a[data-testid="normal-link"]');
        
        tarjetas.forEach(tarjeta => {
            try {
                let link = tarjeta.href;
                if(!link || link.includes('#')) return;

                let titulo = tarjeta.getAttribute('data-product-name');
                let precioStr = tarjeta.getAttribute('data-product-price');
                
                if (!titulo) {
                    let tituloEl = tarjeta.querySelector('h3, [data-e2e="title-card"]');
                    titulo = tituloEl ? tituloEl.innerText : null;
                }
                
                if (!precioStr) {
                    let precioEl = tarjeta.querySelector('[data-e2e="price-card"], .priceBase-av5at');
                    precioStr = precioEl ? precioEl.innerText : null;
                }

                let imgEl = tarjeta.querySelector('img');
                let imgUrl = imgEl ? imgEl.src : null;

                if (titulo && precioStr && titulo.trim() !== '') {
                    resultados.push({
                        nombre: titulo,
                        link: link,
                        precio: precioStr.toString(), 
                        imagen: imgUrl
                    });
                }
            } catch(e) {}
        });
        
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


def escanear_catalogo_pcc(url_catalogo_base, categoria_db, tipo_db):
    print(f"\n🕷️ [PCC] -> Escaneando: {url_catalogo_base}")
    
    todos_los_productos_extraidos = []
    pagina_actual = 1
    hay_mas_paginas = True

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--start-maximized", "--disable-blink-features=AutomationControlled"])
        context = browser.new_context(no_viewport=True, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/123.0.0.0 Safari/537.36", locale="es-ES")
        page = context.new_page()
        
        try:
            while hay_mas_paginas:
                url_con_paginacion = f"{url_catalogo_base}?page={pagina_actual}"
                print(f"\n📄 Entrando a la página {pagina_actual}... ({url_con_paginacion})")
                
                page.goto(url_con_paginacion, timeout=40000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)

                # Cookies en la primera página
                if pagina_actual == 1:
                    try:
                        btn_cookies = page.locator('#cookiesAcceptAll').first
                        if btn_cookies.is_visible(timeout=3000):
                            btn_cookies.click()
                            page.wait_for_timeout(1000)
                    except:
                        pass 

                # Extraer de la página
                datos_pagina = extraer_productos_de_pagina_pcc(page)
                
                if not datos_pagina:
                    print(f"⚠️ No se encontraron productos. Fin del catálogo.")
                    hay_mas_paginas = False
                    break
                    
                todos_los_productos_extraidos.extend(datos_pagina)
                
                # Comprobar botón "Siguiente" de PC Componentes
                siguiente_deshabilitado = page.evaluate('''() => {
                    let nextBtn = document.querySelector('button[aria-label="Página siguiente"], a[aria-label="Página siguiente"]');
                    if (!nextBtn) return true;
                    return nextBtn.disabled || nextBtn.classList.contains('disabled');
                }''')

                if siguiente_deshabilitado:
                    hay_mas_paginas = False
                else:
                    pagina_actual += 1

        except Exception as e:
            print(f"❌ Error en Playwright: {e}")
        finally:
            context.close()
            browser.close()

    # Llamamos a la función universal para guardar, indicando que es PcComponentes
    return guardar_productos_en_db(
        productos_extraidos=todos_los_productos_extraidos,
        nombre_tienda="PcComponentes",
        url_base_tienda="https://www.pccomponentes.com",
        categoria_db=categoria_db,
        tipo_db=tipo_db
    )

# =================================================================
# LÓGICA EXCLUSIVA DE COOLMOD
# =================================================================
def extraer_productos_de_pagina_coolmod(page):
    """Extrae productos de la vista actual adaptado a Coolmod"""
    # Hacemos algo de scroll para asegurar que carguen las imágenes (Lazy Load)
    for _ in range(8):
        page.mouse.wheel(0, 1000)
        page.wait_for_timeout(800)

    datos = page.evaluate('''() => {
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


def escanear_catalogo_coolmod(url_catalogo_base, categoria_db, tipo_db, excluir_palabras=None):
    print(f"\n🕷️ [COOLMOD] -> Escaneando: {url_catalogo_base}")
    
    todos_los_productos_extraidos = []
    pagina_actual = 1
    hay_mas_paginas = True

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--start-maximized", "--disable-blink-features=AutomationControlled"])
        context = browser.new_context(no_viewport=True, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/123.0.0.0 Safari/537.36", locale="es-ES")
        page = context.new_page()
        
        try:
            while hay_mas_paginas:
                # Coolmod utiliza el parámetro '?pagina=X' o '&pagina=X'
                separador = "&" if "?" in url_catalogo_base else "?"
                url_con_paginacion = f"{url_catalogo_base}{separador}pagina={pagina_actual}"
                
                print(f"\n📄 Entrando a la página {pagina_actual}... ({url_con_paginacion})")
                
                page.goto(url_con_paginacion, timeout=40000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)

                # Aceptamos cookies solo en la primera página
                if pagina_actual == 1:
                    try:
                        # Botón estándar de cookies (ajusta si Coolmod cambia el selector)
                        btn_cookies = page.locator('button.accept-cookies, #acceptAllCookies').first
                        if btn_cookies.is_visible(timeout=3000):
                            btn_cookies.click()
                            page.wait_for_timeout(1000)
                    except:
                        pass 

                # Extraer de la página
                datos_pagina = extraer_productos_de_pagina_coolmod(page)
                
                if not datos_pagina:
                    print(f"⚠️ No se encontraron productos. Fin del catálogo.")
                    hay_mas_paginas = False
                    break

                if excluir_palabras:
                    datos_filtrados = []
                    for prod in datos_pagina:
                        nombre_lower = prod['nombre'].lower()
                        # Verificamos si alguna de las palabras excluidas está en el nombre
                        if not any(palabra in nombre_lower for palabra in excluir_palabras):
                            datos_filtrados.append(prod)
                    
                    datos_pagina = datos_filtrados
                    print(f"✂️ Filtrados artículos no deseados. Quedan {len(datos_pagina)} en esta página.")
                    
                todos_los_productos_extraidos.extend(datos_pagina)
                
                # Comprobar si hay botón "Siguiente" activo en la paginación
                siguiente_deshabilitado = page.evaluate('''() => {
                    let nextBtn = document.querySelector('.paginate-buttons.next-button');
                    
                    // Si no existe el botón de siguiente, o tiene un atributo 'disabled', o está 'disable', paramos.
                    if (!nextBtn) return true; 
                    
                    return nextBtn.disabled || nextBtn.hasAttribute('disabled') || nextBtn.classList.contains('disabled');
                }''')

                if siguiente_deshabilitado:
                    hay_mas_paginas = False
                else:
                    pagina_actual += 1

        except Exception as e:
            print(f"❌ Error en Playwright: {e}")
        finally:
            context.close()
            browser.close()

    # Llamamos a la función universal para guardar en la BD
    return guardar_productos_en_db(
        productos_extraidos=todos_los_productos_extraidos,
        nombre_tienda="Coolmod",
        url_base_tienda="https://www.coolmod.com",
        categoria_db=categoria_db,
        tipo_db=tipo_db
    )
    
# =================================================================
# LÓGICA EXCLUSIVA DE LIFE INFORMÁTICA
# =================================================================
def escanear_catalogo_lifeinformatica(url_catalogo_base, categoria_db, tipo_db, excluir_palabras=None):
    print(f"\n🕷️ [LIFE INFO] -> Escaneando: {url_catalogo_base}")
    
    todos_los_productos_extraidos = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--start-maximized", "--disable-blink-features=AutomationControlled"])
        context = browser.new_context(no_viewport=True, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/123.0.0.0 Safari/537.36", locale="es-ES")
        page = context.new_page()
        
        try:
            page.goto(url_catalogo_base, timeout=40000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            # Aceptar cookies (vital para que no tape el botón Cargar Más)
            try:
                # Usamos el ID y las clases que has proporcionado
                btn_cookies = page.locator('#cf_consent-buttons__accept-all, button.cf_button--accept').first
                if btn_cookies.is_visible(timeout=3000):
                    btn_cookies.click()
                    page.wait_for_timeout(1000)
            except:
                pass  

            # Bucle para pulsar "Cargar Más" hasta que desaparezca
            while True:
                try:
                    boton_cargar_mas = page.locator('#yith-infs-button')
                    if boton_cargar_mas.is_visible(timeout=2000):
                        boton_cargar_mas.scroll_into_view_if_needed()
                        boton_cargar_mas.click()
                        print("⏳ Cargando más productos...")
                        page.wait_for_timeout(2500) # Esperamos a que el DOM se actualice con los nuevos productos
                    else:
                        print("✅ Catálogo completo desplegado.")
                        break
                except Exception:
                    break

            # Extraer TODOS los productos de golpe ahora que la página está entera
            datos_pagina = extraer_productos_de_pagina_lifeinformatica(page)
            
            if not datos_pagina:
                print(f"⚠️ No se encontraron productos.")
                return 0

            # Aplicar filtro de palabras excluidas
            if excluir_palabras:
                datos_filtrados = []
                for prod in datos_pagina:
                    nombre_lower = prod['nombre'].lower()
                    if not any(palabra in nombre_lower for palabra in excluir_palabras):
                        datos_filtrados.append(prod)
                
                datos_pagina = datos_filtrados
                print(f"✂️ Filtrados artículos no deseados. Quedan {len(datos_pagina)}.")
                
            todos_los_productos_extraidos.extend(datos_pagina)
            
        except Exception as e:
            print(f"❌ Error escaneando {url_catalogo_base}: {e}")
        finally:
            browser.close()
            
    # Llamamos a la función universal para guardar en la BD
    return guardar_productos_en_db(
        productos_extraidos=todos_los_productos_extraidos,
        nombre_tienda="Life Informatica",
        url_base_tienda="https://lifeinformatica.com",
        categoria_db=categoria_db,
        tipo_db=tipo_db
    )

def extraer_productos_de_pagina_lifeinformatica(page):
    """Extrae productos de la vista actual adaptado a Life Informatica"""
    
    # Scroll suave para lazy loading de imágenes
    for _ in range(5):
        page.mouse.wheel(0, 1500)
        page.wait_for_timeout(500)

    datos = page.evaluate('''() => {
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

                    // Logica para precios de Life Informática (WooCommerce)
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

# =================================================================
# LÓGICA EXCLUSIVA DE ALTERNATE
# =================================================================
def extraer_productos_de_pagina_alternate(page):
    """Extrae productos de la vista actual adaptado a Alternate"""
    # Scroll suave para que carguen las imágenes
    for _ in range(6):
        page.mouse.wheel(0, 1000)
        page.wait_for_timeout(800)

    datos = page.evaluate('''() => {
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

def escanear_catalogo_alternate(url_catalogo_base, categoria_db, tipo_db, excluir_palabras=None):
    print(f"\n🕷️ [ALTERNATE] -> Escaneando: {url_catalogo_base}")
    
    todos_los_productos_extraidos = []
    pagina_actual = 1
    hay_mas_paginas = True

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--start-maximized", "--disable-blink-features=AutomationControlled"])
        context = browser.new_context(no_viewport=True, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36", locale="es-ES")
        page = context.new_page()
        
        try:
            while hay_mas_paginas:
                url_con_paginacion = f"{url_catalogo_base}?page={pagina_actual}"
                print(f"\n📄 Entrando a la página {pagina_actual}... ({url_con_paginacion})")
                
                page.goto(url_con_paginacion, timeout=40000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)

                # Cookies (Solo en la primera página)
                if pagina_actual == 1:
                    try:
                        btn_cookies = page.locator('#cookie-notice-button-agree').first
                        if btn_cookies.is_visible(timeout=3000):
                            btn_cookies.click()
                            print("🍪 Cookies aceptadas en Alternate.")
                            page.wait_for_timeout(1000)
                    except:
                        pass 

                # Extraer de la página
                datos_pagina = extraer_productos_de_pagina_alternate(page)
                
                if not datos_pagina:
                    print(f"⚠️ No se encontraron productos. Fin del catálogo.")
                    hay_mas_paginas = False
                    break

                if excluir_palabras:
                    datos_filtrados = []
                    for prod in datos_pagina:
                        nombre_lower = prod['nombre'].lower()
                        if not any(palabra in nombre_lower for palabra in excluir_palabras):
                            datos_filtrados.append(prod)
                    
                    datos_pagina = datos_filtrados
                    print(f"✂️ Filtrados artículos no deseados. Quedan {len(datos_pagina)} en esta página.")
                
                todos_los_productos_extraidos.extend(datos_pagina)
                
                # Comprobar botón "Página Siguiente"
                siguiente_deshabilitado = page.evaluate('''() => {
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
            print(f"❌ Error en Playwright escaneando Alternate: {e}")
        finally:
            context.close()
            browser.close()

    # Llamamos a la función universal para guardar en la BD
    return guardar_productos_en_db(
        productos_extraidos=todos_los_productos_extraidos,
        nombre_tienda="Alternate",
        url_base_tienda="https://www.alternate.es",
        categoria_db=categoria_db,
        tipo_db=tipo_db
    )
    
# =================================================================
# LÓGICA EXCLUSIVA DE NEOBYTE
# =================================================================
def extraer_productos_de_pagina_neobyte(page):
    """Extrae productos de la vista actual adaptado a NeoByte"""
    # Hacemos scroll para asegurar que las imágenes y elementos carguen (Lazy Load)
    for _ in range(6):
        page.mouse.wheel(0, 1000)
        page.wait_for_timeout(800)

    datos = page.evaluate('''() => {
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

def escanear_catalogo_neobyte(url_catalogo_base, categoria_db, tipo_db, excluir_palabras=None):
    print(f"\n🕷️ [NEOBYTE] -> Escaneando: {url_catalogo_base}")
    
    todos_los_productos_extraidos = []
    pagina_actual = 1
    hay_mas_paginas = True

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--start-maximized", "--disable-blink-features=AutomationControlled"])
        context = browser.new_context(no_viewport=True, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/123.0.0.0 Safari/537.36", locale="es-ES")
        page = context.new_page()
        
        try:
            while hay_mas_paginas:
                url_con_paginacion = f"{url_catalogo_base}?page={pagina_actual}"
                print(f"\n📄 Entrando a la página {pagina_actual}... ({url_con_paginacion})")
                
                page.goto(url_con_paginacion, timeout=40000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)

                # Cookies en la primera página
                if pagina_actual == 1:
                    try:
                        # Botón estándar de cookies de su módulo, o el genérico de PrestaShop
                        btn_cookies = page.locator('#btn-cookie-accept, .cb-accept').first
                        if btn_cookies.is_visible(timeout=3000):
                            btn_cookies.click()
                            print("🍪 Cookies aceptadas en NeoByte.")
                            page.wait_for_timeout(1000)
                    except:
                        pass 

                # Extraer de la página
                datos_pagina = extraer_productos_de_pagina_neobyte(page)
                
                if not datos_pagina:
                    print(f"⚠️ No se encontraron productos. Fin del catálogo.")
                    hay_mas_paginas = False
                    break

                if excluir_palabras:
                    datos_filtrados = []
                    for prod in datos_pagina:
                        nombre_lower = prod['nombre'].lower()
                        if not any(palabra in nombre_lower for palabra in excluir_palabras):
                            datos_filtrados.append(prod)
                    
                    datos_pagina = datos_filtrados
                    print(f"✂️ Filtrados artículos no deseados. Quedan {len(datos_pagina)} en esta página.")
                
                todos_los_productos_extraidos.extend(datos_pagina)
                
                # Comprobar si hay botón "Siguiente" activo en la paginación
                # NeoByte usa un enlace con id "infinity-url" y rel="next"
                siguiente_deshabilitado = page.evaluate('''() => {
                    let nextBtn = document.querySelector('a[rel="next"], a.next');
                    if (!nextBtn) return true; // Si no existe, no hay más
                    return false; // Si existe, hay más páginas
                }''')

                if siguiente_deshabilitado:
                    hay_mas_paginas = False
                else:
                    pagina_actual += 1

        except Exception as e:
            print(f"❌ Error en Playwright: {e}")
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

# =================================================================
# LÓGICA EXCLUSIVA DE AMAZON
# =================================================================
def extraer_productos_de_pagina_amazon(page, precio_min=0.0):
    """Extrae productos de la vista actual adaptado a Amazon"""
    for _ in range(8):
        page.mouse.wheel(0, 1000)
        page.wait_for_timeout(600)

    datos = page.evaluate(r'''() => {
        let resultados = [];
        let tarjetas = document.querySelectorAll('div[data-asin]');
        
        tarjetas.forEach(tarjeta => {
            try {
                let asin = tarjeta.getAttribute('data-asin');
                if (!asin || asin.trim() === '') return;

                // Localizamos el H2 (el contenedor del título)
                let h2El = tarjeta.querySelector('h2');
                if (!h2El) return;
                
                // Amazon a veces pone el <a> dentro del <h2>, y a veces el <a> envuelve al <h2>
                let linkEl = h2El.querySelector('a') || h2El.closest('a');
                let tituloEl = h2El.querySelector('span');
                
                if (tituloEl && linkEl) {
                    let nombre = tituloEl.innerText;
                    let link = linkEl.href;
                    
                    let precioStr = "0";
                    let precioEl = tarjeta.querySelector('.a-price .a-offscreen');
                    
                    if (!precioEl) {
                        let entero = tarjeta.querySelector('.a-price-whole');
                        let decimal = tarjeta.querySelector('.a-price-fraction');
                        if (entero) {
                            let enteroLimpio = entero.innerText.replace(',', '').replace('.', '').trim();
                            let decimalLimpio = decimal ? decimal.innerText.trim() : '00';
                            precioStr = enteroLimpio + '.' + decimalLimpio;
                        }
                    } else {
                        precioStr = precioEl.innerText;
                    }
                    
                    let imgEl = tarjeta.querySelector('.s-image');
                    let imgUrl = imgEl ? imgEl.src : null;

                    if (nombre && nombre.trim() !== '') {
                        resultados.push({
                            nombre: nombre.trim(),
                            link: link,
                            precio: precioStr, 
                            imagen: imgUrl
                        });
                    }
                }
            } catch(e) {}
        });
        return resultados;
    }''')
    
    unicos = []
    links_vistos = set()
    
    for r in datos:
        if r['link'] not in links_vistos:
            try:
                precio_float = limpiar_precio(r['precio'])
                if precio_float >= precio_min:
                    r['precio'] = str(precio_float)
                    links_vistos.add(r['link'])
                    unicos.append(r)
            except:
                pass
                
    return unicos

def escanear_catalogo_amazon(url_catalogo_base, categoria_db, tipo_db, precio_min=0.0, excluir_palabras=None):
    print(f"\n🕷️ [AMAZON] -> Escaneando: {url_catalogo_base} (Precio Min: {precio_min}€)")
    
    todos_los_productos_extraidos = []
    pagina_actual = 1
    hay_mas_paginas = True

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--start-maximized", "--disable-blink-features=AutomationControlled"])
        context = browser.new_context(
            no_viewport=True, 
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36", 
            locale="es-ES"
        )
        page = context.new_page()
        
        try:
            while hay_mas_paginas:
                url_con_paginacion = f"{url_catalogo_base}&page={pagina_actual}"
                print(f"\n📄 Entrando a la página {pagina_actual}... ")
                
                page.goto(url_con_paginacion, timeout=40000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)

                titulo_pagina = page.title()
                
                # Detección de Captcha (El perro de Amazon)
                if "Captcha" in titulo_pagina or "Bot Check" in titulo_pagina or page.locator('form[action="/errors/validateCaptcha"]').is_visible(timeout=2000):
                    print("⚠️ ¡CAPTCHA DETECTADO! Resuélvelo manualmente en la ventana del navegador.")
                    input("⏳ Presiona ENTER aquí en la consola cuando hayas resuelto el captcha y veas los productos...")
                
                if pagina_actual == 1:
                    try:
                        btn_cookies = page.locator('#sp-cc-accept').first
                        if btn_cookies.is_visible(timeout=3000):
                            btn_cookies.click()
                            page.wait_for_timeout(1000)
                    except:
                        pass 

                datos_pagina = extraer_productos_de_pagina_amazon(page, precio_min)
                
                if not datos_pagina:
                    print(f"⚠️ No se encontraron productos válidos en la página {pagina_actual}.")
                    hay_mas_paginas = False
                    break

                if excluir_palabras:
                    datos_filtrados = []
                    for prod in datos_pagina:
                        nombre_lower = prod['nombre'].lower()
                        if not any(palabra in nombre_lower for palabra in excluir_palabras):
                            datos_filtrados.append(prod)
                    datos_pagina = datos_filtrados
                
                todos_los_productos_extraidos.extend(datos_pagina)
                
                # Amazon a veces elimina el botón next, así que comprobamos si la url final no devolvió nada
                siguiente_deshabilitado = page.evaluate('''() => {
                    let nextBtn = document.querySelector('.s-pagination-next');
                    if (!nextBtn) return true;
                    return nextBtn.classList.contains('s-pagination-disabled');
                }''')

                # Límite estricto de páginas para evitar bucles infinitos si Amazon se buguea
                if siguiente_deshabilitado or pagina_actual >= 20:
                    hay_mas_paginas = False
                else:
                    pagina_actual += 1
                    page.wait_for_timeout(2000)

        except Exception as e:
            print(f"❌ Error en Playwright con Amazon: {e}")
        finally:
            context.close()
            browser.close()

    return guardar_productos_en_db(
        productos_extraidos=todos_los_productos_extraidos,
        nombre_tienda="Amazon",
        url_base_tienda="https://www.amazon.es",
        categoria_db=categoria_db,
        tipo_db=tipo_db
    )

# =================================================================
# ESCANEO DE TIENDAS
# =================================================================
def escanearPcComponentes():
    total_pcc = 0
    
    total_pcc += escanear_catalogo_pcc("https://www.pccomponentes.com/procesadores", 'CPU', 'HW')
    total_pcc += escanear_catalogo_pcc("https://www.pccomponentes.com/placas-base", 'MB', 'HW')
    total_pcc += escanear_catalogo_pcc("https://www.pccomponentes.com/memorias-ram", 'RAM', 'HW')
    total_pcc += escanear_catalogo_pcc("https://www.pccomponentes.com/cajas-pc", 'CASE', 'HW')
    total_pcc += escanear_catalogo_pcc("https://www.pccomponentes.com/ventiladores-cpu", 'AIR', 'HW')
    total_pcc += escanear_catalogo_pcc("https://www.pccomponentes.com/refrigeracion-liquida/kit-refrigeracion-liquida", 'LIQ', 'HW')
    total_pcc += escanear_catalogo_pcc("https://www.pccomponentes.com/tarjetas-graficas", 'GPU', 'HW')
    total_pcc += escanear_catalogo_pcc("https://www.pccomponentes.com/fuentes-alimentacion", 'PSU', 'HW')
    total_pcc += escanear_catalogo_pcc("https://www.pccomponentes.com/discos-duros", 'SSD', 'HW')
    total_pcc += escanear_catalogo_pcc("https://www.pccomponentes.com/monitores", 'MON', 'HW')
    
    # 1 HORA
    
    print(f"\n✅ [PcComponentes FIN] Se han guardado un total de {total_pcc} productos.")
    return total_pcc

def escanearCoolmod():
    total_coolmod = 0
    
    total_coolmod += escanear_catalogo_coolmod("https://www.coolmod.com/componentes-pc-procesadores/", 'CPU', 'HW')
    total_coolmod += escanear_catalogo_coolmod("https://www.coolmod.com/componentes-pc-placas-base/", 'MB', 'HW')
    total_coolmod += escanear_catalogo_coolmod("https://www.coolmod.com/componentes-pc-memorias-ram/", 'RAM', 'HW')
    total_coolmod += escanear_catalogo_coolmod("https://www.coolmod.com/componentes-pc-torres-cajas/", 'CASE', 'HW')
    total_coolmod += escanear_catalogo_coolmod("https://www.coolmod.com/componentes-pc-disipadores-ventiladores/", 'AIR', 'HW', excluir_palabras=[
        '240', '280', '360', '420', 'refrigeracion liquida', 'refrigeración líquida'
        ]
    )
    total_coolmod += escanear_catalogo_coolmod("https://www.coolmod.com/refrigeracion-liquida-kits-liquida/", 'LIQ', 'HW')
    total_coolmod += escanear_catalogo_coolmod("https://www.coolmod.com/tarjetas-graficas/", 'GPU', 'HW')
    total_coolmod += escanear_catalogo_coolmod("https://www.coolmod.com/componentes-pc-fuentes-alimentacion/", 'PSU', 'HW')
    total_coolmod += escanear_catalogo_coolmod("https://www.coolmod.com/componentes-pc-discos-duros/", 'SSD', 'HW')
    total_coolmod += escanear_catalogo_coolmod("https://www.coolmod.com/perifericos-monitores/", 'MON', 'HW')
    
    # X
    
    print(f"\n✅ [Coolmod FIN] Se han guardado un total de {total_coolmod} productos.")
    return total_coolmod

def escanearLifeInformatica():
    total_life = 0
    
    total_life += escanear_catalogo_lifeinformatica("https://lifeinformatica.com/categoria-producto/componentes/procesadores/", 'CPU', 'HW')
    total_life += escanear_catalogo_lifeinformatica("https://lifeinformatica.com/categoria-producto/componentes/placas-base/", 'MB', 'HW')
    total_life += escanear_catalogo_lifeinformatica("https://lifeinformatica.com/categoria-producto/componentes/memorias-ram/", 'RAM', 'HW')
    total_life += escanear_catalogo_lifeinformatica("https://lifeinformatica.com/categoria-producto/componentes/cajas-y-accesorios/cajas/", 'CASE', 'HW')
    total_life += escanear_catalogo_lifeinformatica("https://lifeinformatica.com/categoria-producto/componentes/refrigeracion/disipadores-de-cpu/", 'AIR', 'HW', excluir_palabras=['240', '280', '360', '420', 'liquida', 'líquida'])
    total_life += escanear_catalogo_lifeinformatica("https://lifeinformatica.com/categoria-producto/componentes/refrigeracion/kits-de-refrigeracion-liquida/", 'LIQ', 'HW')
    total_life += escanear_catalogo_lifeinformatica("https://lifeinformatica.com/categoria-producto/componentes/tarjetas-graficas/", 'GPU', 'HW')
    total_life += escanear_catalogo_lifeinformatica("https://lifeinformatica.com/categoria-producto/componentes/fuentes-de-alimentacion-y-accesorios/fuentes-de-alimentacion/", 'PSU', 'HW')
    total_life += escanear_catalogo_lifeinformatica("https://lifeinformatica.com/categoria-producto/componentes/discos-duros/", 'SSD', 'HW')
    total_life += escanear_catalogo_lifeinformatica("https://lifeinformatica.com/categoria-producto/perifericos/monitores-y-accesorios/monitores/", 'MON', 'HW')
    
    # 
    
    print(f"\n✅ [Life Informática FIN] Se han guardado un total de {total_life} productos.")
    return total_life

def escanearAlternate():
    total_alternate = 0
    
    total_alternate += escanear_catalogo_alternate("https://www.alternate.es/Procesadores", 'CPU', 'HW')
    total_alternate += escanear_catalogo_alternate("https://www.alternate.es/Placas-base", 'MB', 'HW')
    total_alternate += escanear_catalogo_alternate("https://www.alternate.es/Memoria-RAM", 'RAM', 'HW')
    total_alternate += escanear_catalogo_alternate("https://www.alternate.es/Cajas-de-PC", 'CASE', 'HW')
    total_alternate += escanear_catalogo_alternate("https://www.alternate.es/Disipadores-de-CPU", 'AIR', 'HW', excluir_palabras=['240', '280', '360', '420', 'líquida', 'liquida', 'aio', 'water'])
    total_alternate += escanear_catalogo_alternate("https://www.alternate.es/Refrigeraci%C3%B3n-l%C3%ADquida", 'LIQ', 'HW')
    total_alternate += escanear_catalogo_alternate("https://www.alternate.es/Tarjetas-gr%C3%A1ficas", 'GPU', 'HW')
    total_alternate += escanear_catalogo_alternate("https://www.alternate.es/Fuentes-de-alimentaci%C3%B3n", 'PSU', 'HW')
    total_alternate += escanear_catalogo_alternate("https://www.alternate.es/SSD", 'SSD', 'HW')
    total_alternate += escanear_catalogo_alternate("https://www.alternate.es/Monitores", 'MON', 'HW')
    
    # 
    
    print(f"\n✅ [Alternate FIN] Se han guardado un total de {total_alternate} productos.")
    return total_alternate

def escanearNeoByte():
    total_neobyte = 0
    
    total_neobyte += escanear_catalogo_neobyte("https://www.neobyte.es/procesadores-107", 'CPU', 'HW')
    total_neobyte += escanear_catalogo_neobyte("https://www.neobyte.es/placas-base-106", 'MB', 'HW')
    total_neobyte += escanear_catalogo_neobyte("https://www.neobyte.es/memorias-ram-108", 'RAM', 'HW')
    total_neobyte += escanear_catalogo_neobyte("https://www.neobyte.es/cajas-de-ordenador-112", 'CASE', 'HW')
    total_neobyte += escanear_catalogo_neobyte("https://www.neobyte.es/ventiladores-cpu-138", 'AIR', 'HW', excluir_palabras=['líquida', 'liquida', 'aio'])
    total_neobyte += escanear_catalogo_neobyte("https://www.neobyte.es/refrigeracion-liquida-139", 'LIQ', 'HW')
    total_neobyte += escanear_catalogo_neobyte("https://www.neobyte.es/tarjetas-graficas-111", 'GPU', 'HW')
    total_neobyte += escanear_catalogo_neobyte("https://www.neobyte.es/fuentes-de-alimentacion-113", 'PSU', 'HW')
    total_neobyte += escanear_catalogo_neobyte("https://www.neobyte.es/discos-duros-110", 'SSD', 'HW')
    total_neobyte += escanear_catalogo_neobyte("https://www.neobyte.es/monitores-169", 'MON', 'HW')
    
    # 
    
    print(f"\n✅ [NeoByte FIN] Se han guardado un total de {total_neobyte} productos.")
    return total_neobyte

def escanearAmazon():
    total_amazon = 0
    
    # 1. PROCESADORES (Búsqueda "procesador" dentro del nodo de componentes)
    total_amazon += escanear_catalogo_amazon("https://www.amazon.es/s?k=procesador&rh=n%3A937912031", 'CPU', 'HW', precio_min=40.0, excluir_palabras=['pasta', 'térmica', 'llavero', 'pegatina', 'celeron', 'pentium'])
    
    # 2. PLACAS BASE (Búsqueda "placa base" dentro de su nodo)
    total_amazon += escanear_catalogo_amazon("https://www.amazon.es/s?k=placa+base&rh=n%3A937911031", 'MB', 'HW', precio_min=45.0, excluir_palabras=['cable', 'tornillo', 'altavoz', 'speaker', 'antena', 'embellecedor'])
    
    # 3. MEMORIA RAM (Búsqueda "memoria ram ddr" para evitar rams de portátiles viejos o usbs)
    total_amazon += escanear_catalogo_amazon("https://www.amazon.es/s?k=memoria+ram+ddr&rh=n%3A937914031", 'RAM', 'HW', precio_min=15.0, excluir_palabras=['dummy', 'filler', 'almohadilla', 'sodimm', 'mac'])
    
    # 4. CAJAS (Búsqueda "caja pc")
    total_amazon += escanear_catalogo_amazon("https://www.amazon.es/s?k=caja+pc+atx&rh=n%3A937906031", 'CASE', 'HW', precio_min=25.0, excluir_palabras=['miniatura', 'juguete', 'funda', 'vinilo'])
    
    # 5. DISIPADORES AIRE (Búsqueda "disipador cpu")
    total_amazon += escanear_catalogo_amazon("https://www.amazon.es/s?k=disipador+cpu&rh=n%3A937908031", 'AIR', 'HW', precio_min=10.0, excluir_palabras=['líquida', 'liquida', 'aio', 'tubo', 'racor'])
    
    # 6. REFRIGERACIÓN LÍQUIDA (Búsqueda "refrigeracion liquida pc")
    total_amazon += escanear_catalogo_amazon("https://www.amazon.es/s?k=refrigeracion+liquida+pc&rh=n%3A2028682031", 'LIQ', 'HW', precio_min=35.0, excluir_palabras=['aire', 'custom', 'tubo', 'racor', 'deposito'])
    
    # 7. TARJETAS GRÁFICAS (Búsqueda "tarjeta grafica rtx rx")
    total_amazon += escanear_catalogo_amazon("https://www.amazon.es/s?k=tarjeta+grafica+rtx+rx&rh=n%3A937916031", 'GPU', 'HW', precio_min=90.0, excluir_palabras=['riser', 'bloque', 'waterblock', 'soporte'])
    
    # 8. FUENTES DE ALIMENTACIÓN (Búsqueda "fuente de alimentacion pc")
    total_amazon += escanear_catalogo_amazon("https://www.amazon.es/s?k=fuente+de+alimentacion+pc+80+plus&rh=n%3A937909031", 'PSU', 'HW', precio_min=30.0, excluir_palabras=['alargador', 'extensor', 'tester', 'probador', 'peine'])
    
    print(f"\n✅ [Amazon FIN] Se han guardado un total de {total_amazon} productos.")
    return total_amazon

# =================================================================
# INICIO DEL SCRIPT
# =================================================================
if __name__ == '__main__':
    print("🚀 INICIANDO ESCANEO MASIVO DEL CATÁLOGO DE HARDWARE...")
    
    total_general = 0
    # Escaneamos las tiendas y sumamos al total general
    
    # total_general += escanearPcComponentes()
    
    total_general += escanearAmazon()
    
    # total_general += escanearCoolmod()
    
    # total_general += escanearLifeInformatica()
    
    # total_general += escanearAlternate()
    
    # total_general += escanearNeoByte()
    
    print(f"\n🎉 ¡TODAS LAS TIENDAS ESCANEADAS! UN TOTAL DE {total_general} PRODUCTOS GUARDADOS/ACTUALIZADOS EN LA BASE DE DATOS.")