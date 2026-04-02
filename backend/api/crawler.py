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
    
    # 1. Si ya viene en formato americano (ej: "444.95" sin símbolo de euro ni nada extra)
    # comprobamos si solo tiene un punto al final.
    if re.match(r'^\d+\.\d+$', texto):
        return float(texto)
    
    # 2. Si viene con formato europeo o símbolos (ej: "444,95 €" o "1.250,99 €")
    numeros = re.findall(r'\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?', texto)
    if not numeros: return 0.0
    
    # Cogemos la primera coincidencia
    num_str = numeros[0]
    
    # Si tiene punto Y coma (ej: 1.250,99), es fácil: quitamos punto, coma a punto.
    if '.' in num_str and ',' in num_str:
        num_str = num_str.replace('.', '').replace(',', '.')
    # Si solo tiene coma (ej: 444,95)
    elif ',' in num_str:
        num_str = num_str.replace(',', '.')
    # Si solo tiene un punto (ej: 444.95 o 1.250)
    elif '.' in num_str:
        # Si el punto está a 2 posiciones del final (es decimal)
        if len(num_str.split('.')[-1]) == 2:
            pass # Ya está bien como float
        else:
            # Es un separador de miles
            num_str = num_str.replace('.', '')
            
    return float(num_str)

def extraer_productos_de_pagina_actual(page):
    """
    Función auxiliar que saca los datos de la página actual 
    adaptada a la estructura de PcComponentes 2024/2025.
    """
    # Hacemos scroll hacia abajo para forzar la carga de imágenes (Lazy Load)
    for _ in range(8):
        page.mouse.wheel(0, 1000)
        page.wait_for_timeout(800)

    # Extraemos la info usando sus nuevos atributos data-product-*
    datos = page.evaluate('''() => {
        let resultados = [];
        
        // Ahora PcComponentes pone toda la info estructurada en el propio enlace del producto
        let tarjetas = document.querySelectorAll('a[data-product-id], a[data-testid="normal-link"]');
        
        tarjetas.forEach(tarjeta => {
            try {
                let link = tarjeta.href;
                if(!link || link.includes('#')) return;

                // 1. Intentamos sacar el nombre y precio de sus nuevos metadatos
                let titulo = tarjeta.getAttribute('data-product-name');
                let precioStr = tarjeta.getAttribute('data-product-price');
                
                // 2. Si fallan los metadatos, usamos fallbacks visuales
                if (!titulo) {
                    let tituloEl = tarjeta.querySelector('h3, [data-e2e="title-card"]');
                    titulo = tituloEl ? tituloEl.innerText : null;
                }
                
                if (!precioStr) {
                    let precioEl = tarjeta.querySelector('[data-e2e="price-card"], .priceBase-av5at');
                    precioStr = precioEl ? precioEl.innerText : null;
                }

                // Imagen
                let imgEl = tarjeta.querySelector('img');
                let imgUrl = imgEl ? imgEl.src : null;

                if (titulo && precioStr && titulo.trim() !== '') {
                    resultados.push({
                        nombre: titulo,
                        link: link,
                        // Lo pasamos a string por si viene del atributo HTML como '444.95'
                        precio: precioStr.toString(), 
                        imagen: imgUrl
                    });
                }
            } catch(e) {}
        });
        
        // Limpiamos duplicados 
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

def escanear_catalogo(url_catalogo_base, categoria_db, tipo_db):
    """
    Escanea la tienda, saca todos los datos, cierra el navegador y luego guarda todo en Django.
    """
    print(f"\n🕷️ [ARAÑA INICIADA] -> Preparando para escanear todas las páginas de: {url_catalogo_base}")
    
    # 1. Asegurar que existe la tienda en la BD (esto lo hacemos antes de arrancar Playwright)
    tienda_pcc, _ = Tienda.objects.get_or_create(
        nombre="PcComponentes",
        defaults={"url_base": "https://www.pccomponentes.com"}
    )
    
    todos_los_productos_extraidos = []
    pagina_actual = 1
    hay_mas_paginas = True

    # ==========================================
    # FASE 1: EXTRACCIÓN CON PLAYWRIGHT
    # ==========================================
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
                            print("🍪 Banner de cookies detectado. Aceptando...")
                            btn_cookies.click()
                            page.wait_for_timeout(1000)
                    except:
                        pass 

                # Extraer de la página
                datos_pagina = extraer_productos_de_pagina_actual(page)
                
                if not datos_pagina:
                    print(f"⚠️ No se encontraron productos en la página {pagina_actual}. Fin del catálogo.")
                    hay_mas_paginas = False
                    break
                    
                print(f"📦 Extraídos {len(datos_pagina)} productos. Guardando en memoria temporal...")
                
                # Añadimos los resultados a la lista maestra
                todos_los_productos_extraidos.extend(datos_pagina)
                
                # Comprobar botón "Siguiente"
                siguiente_deshabilitado = page.evaluate('''() => {
                    let nextBtn = document.querySelector('button[aria-label="Página siguiente"], a[aria-label="Página siguiente"]');
                    if (!nextBtn) return true;
                    return nextBtn.disabled || nextBtn.classList.contains('disabled');
                }''')

                if siguiente_deshabilitado:
                    print("🏁 Se ha detectado el final de la paginación.")
                    hay_mas_paginas = False
                else:
                    pagina_actual += 1

        except Exception as e:
            print(f"❌ Error en Playwright: {e}")
        finally:
            context.close()
            browser.close()

    # ==========================================
    # FASE 2: GUARDAR EN LA BASE DE DATOS DJANGO
    # ==========================================
    print(f"\n💾 Guardando {len(todos_los_productos_extraidos)} productos en la Base de Datos...")
    
    total_productos_guardados = 0
    
    for item in todos_los_productos_extraidos:
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
                tienda=tienda_pcc,
                defaults={
                    'precio_base': precio_float,
                    'enlace_compra': item['link'],
                    'gastos_envio': 0.00,
                    'descuento_porcentaje': 0.00
                }
            )
            total_productos_guardados += 1
            print(f"{'➕ NUEVO' if creado_prod else '🔄 ACTUALIZADO'}: {nombre_limpio} -> {precio_float}€")
            
        except Exception as db_error:
            print(f"❌ Error guardando '{item.get('nombre', 'Desconocido')}': {db_error}")

    print(f"\n🎉 [¡ÉXITO TOTAL!] {total_productos_guardados} productos guardados en tu base de datos.")


if __name__ == '__main__':
    print("🚀 INICIANDO ESCANEO MASIVO DEL CATÁLOGO DE HARDWARE...")

    # 1. Procesadores (CPU)
    escanear_catalogo("https://www.pccomponentes.com/procesadores", categoria_db='CPU', tipo_db='HW')
    
    # 2. Placas Base (MB)
    escanear_catalogo("https://www.pccomponentes.com/placas-base", categoria_db='MB', tipo_db='HW')
    
    # 3. Memoria RAM (RAM)
    escanear_catalogo("https://www.pccomponentes.com/memorias-ram", categoria_db='RAM', tipo_db='HW')
    
    # 4. Cajas / Torres (CASE)
    escanear_catalogo("https://www.pccomponentes.com/cajas-pc", categoria_db='CASE', tipo_db='HW')
    
    # 5. Refrigeración aire (COOL)
    escanear_catalogo("https://www.pccomponentes.com/ventiladores-cpu", categoria_db='AIR', tipo_db='HW')
    
    # 6. Refrigeración líquida (COOL)
    escanear_catalogo("https://www.pccomponentes.com/refrigeracion-liquida/kit-refrigeracion-liquida", categoria_db='LIQ', tipo_db='HW')
    
    # 7. Tarjetas Gráficas (GPU)
    escanear_catalogo("https://www.pccomponentes.com/tarjetas-graficas", categoria_db='GPU', tipo_db='HW')
    
    # 8. Fuentes de Alimentación (PSU)
    escanear_catalogo("https://www.pccomponentes.com/fuentes-alimentacion", categoria_db='PSU', tipo_db='HW')
    
    # 9. Almacenamiento / Discos Duros (SSD)
    escanear_catalogo("https://www.pccomponentes.com/discos-duros", categoria_db='SSD', tipo_db='HW')
    
    # 10. Monitores (MON)
    escanear_catalogo("https://www.pccomponentes.com/monitores", categoria_db='MON', tipo_db='HW')
    
    # TARDA 1 HORA

    print("\n✅ ¡ESCANEO MASIVO FINALIZADO AL 100%! Toda tu base de datos está actualizada.")