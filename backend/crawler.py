import sys
import os
import django
import re
import random
import openai
import json
from playwright.sync_api import sync_playwright
from fuzzywuzzy import fuzz
from django.db import transaction
from fake_useragent import UserAgent

# --- CONFIGURACIÓN DEL AGENTE OLLAMA (LOCAL) ---
cliente_ia = openai.OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)

def es_mismo_producto_ia(nombre_base, nombre_oferta):
    """
    Agente de IA que decide si dos textos de hardware se refieren EXACTAMENTE al mismo producto.
    """
    prompt_sistema = """
    Eres un sistema estricto de validación de productos de hardware de PC.
Tu única tarea es decidir si dos nombres de producto describen EXACTAMENTE el mismo producto base.

IMPORTANTE:
- Si tienes cualquier duda, responde false.
- Si falta información crítica en uno de los textos, responde false.
- No intentes adivinar.
- No uses sentido comercial general ni aproximaciones.
- Solo responde true si los atributos esenciales coinciden de forma exacta.

DEFINICIÓN DE "MISMO PRODUCTO":
Dos textos representan el mismo producto SOLO si describen el mismo modelo base real.
Si cambia un atributo técnico esencial, NO es el mismo producto.

ORDEN OBLIGATORIO DE ANÁLISIS:
1. Detecta la categoría.
2. Extrae los atributos técnicos esenciales.
3. Compara los atributos esenciales.
4. Ignora solo palabras decorativas o comerciales.
5. Responde con JSON.

SI NO PUEDES IDENTIFICAR CON CLARIDAD LA CATEGORÍA O EL MODELO:
{"mismo_producto": false}

==================================================
1) REGLA GENERAL DE SEGURIDAD
==================================================

Responde false si ocurre cualquiera de estas situaciones:
- Las categorías parecen distintas.
- El modelo exacto no coincide.
- El sufijo no coincide.
- La capacidad no coincide.
- La versión no coincide.
- El formato no coincide.
- La interfaz no coincide.
- El chipset no coincide.
- La serie o familia no coincide.
- Hay ambigüedad.
- Un texto parece incompleto y no permite confirmar igualdad exacta.

Nunca respondas true por parecido general del texto.

==================================================
2) PALABRAS QUE NORMALMENTE DEBES IGNORAR
==================================================

Ignora solo palabras no esenciales como:
- box
- tray
- oferta
- reacondicionado
- refurbished
- nuevo
- gaming
- overclocking
- ai
- ia
- frecuencia
- base
- turbo
- núcleos
- hilos
- cache
- caché
- graphics
- gráficos integrados
- sin ventilador
- con ventilador
- wof
- processor
- procesador
- cpu
- gpu
- retail

Estas palabras NO cambian el modelo base por sí solas.

==================================================
3) REGLAS POR CATEGORÍA
==================================================

-------------------------
A. PROCESADORES (CPU)
-------------------------

Atributos esenciales:
- Marca: Intel o AMD
- Familia: Core i3/i5/i7/i9, Core Ultra 5/7/9, Ryzen 3/5/7/9, Xeon, Threadripper
- Modelo numérico: 12400, 14700, 265, 7800, 7600, etc.
- Sufijo exacto: K, KF, F, X, X3D, G, GT, etc.

Regla:
Dos CPUs solo son el mismo producto si marca + familia + número de modelo + sufijo coinciden exactamente.

Ejemplos:
- i7-14700K != i7-14700KF
- i7-14700 != i7-14700K
- Ryzen 5 7600 != Ryzen 5 7600X
- Ryzen 7 7800X3D != Ryzen 7 7700X
- Core Ultra 7 265K != Core Ultra 7 265KF
- Xeon E-2414 != Xeon E-2478

Notas:
- La velocidad en GHz no define el producto si el modelo exacto ya está claro.
- “Box” y “Tray” se pueden ignorar.
- Si el modelo exacto no aparece claro en ambos textos, responde false.

-------------------------
B. TARJETAS GRÁFICAS (GPU)
-------------------------

Atributos esenciales:
- Fabricante del chip: NVIDIA / AMD / Intel
- Serie exacta del chip: RTX 4060, RTX 4060 Ti, RTX 4070 Super, RX 7800 XT, RX 7600, Arc A770, etc.
- Sufijo del chip: Ti, Super, XT, XTX, etc.
- Memoria VRAM si forma parte del modelo comercial diferenciador.

Regla:
Dos GPUs solo son el mismo producto si el chip exacto coincide.
Si cambia 4060 por 4060 Ti, o 7800 XT por 7800 XTX, responde false.

Importante:
- La ensambladora puede variar si tu sistema quiere agrupar por chip base: MSI, ASUS, Gigabyte, Zotac, Sapphire pueden considerarse equivalentes.
- Pero si cambia la VRAM y eso define el modelo comercial, responde false.
- Si un texto tiene 8GB y otro 16GB, por defecto responde false.

Ejemplos:
- RTX 4060 != RTX 4060 Ti
- RTX 4070 != RTX 4070 Super
- RX 7800 XT != RX 7800 XTX
- RTX 3060 8GB != RTX 3060 12GB

-------------------------
C. PLACAS BASE
-------------------------

Atributos esenciales:
- Socket: AM4, AM5, LGA1700, etc.
- Chipset: B650, X670, Z790, B760, H610, etc.
- Formato si aparece en el nombre del modelo: B650M, B650I, etc.

Regla:
Dos placas base solo son el mismo producto si socket + chipset + formato/modelo coinciden.
Si cambia B650 por B650M, responde false.
Si cambia B760 por Z790, responde false.

Ejemplos:
- B650 != B650M
- X670 != X670E
- B760 != Z790

-------------------------
D. MEMORIA RAM
-------------------------

Atributos esenciales:
- Capacidad total: 16GB, 32GB, 64GB
- Configuración del kit: 1x16, 2x8, 2x16, etc.
- Tipo: DDR4 o DDR5
- Frecuencia: 3200, 3600, 5600, 6000, etc.
- Latencia si aparece y diferencia el modelo: CL16, CL30, CL36, etc.

Regla:
Dos kits de RAM solo son el mismo producto si coinciden capacidad total + distribución del kit + tipo + frecuencia.
Si cambia DDR4 por DDR5, responde false.
Si cambia 2x16 por 1x32, responde false.
Si cambia CL30 por CL36, por defecto responde false.

Ejemplos:
- 32GB DDR5 6000 CL30 != 32GB DDR5 6000 CL36
- 16GB (2x8) != 16GB (1x16)
- DDR4 3200 != DDR5 5600

-------------------------
E. SSD / ALMACENAMIENTO
-------------------------

Atributos esenciales:
- Tipo: SSD / HDD
- Formato: M.2, 2.5", PCIe card, etc.
- Interfaz/generación: SATA, NVMe, PCIe 3.0, PCIe 4.0, PCIe 5.0
- Capacidad: 500GB, 1TB, 2TB, etc.

Regla:
Dos unidades de almacenamiento solo son el mismo producto si coinciden tipo + formato + interfaz + capacidad.
Si cambia 1TB por 2TB, responde false.
Si cambia SATA por NVMe, responde false.
Si cambia PCIe 4.0 por PCIe 5.0, responde false.

Ejemplos:
- SSD NVMe 1TB != SSD NVMe 2TB
- M.2 NVMe != SSD SATA 2.5
- PCIe 4.0 != PCIe 5.0

-------------------------
F. FUENTES DE ALIMENTACIÓN (PSU)
-------------------------

Atributos esenciales:
- Potencia: 650W, 750W, 850W, etc.
- Certificación: Bronze, Gold, Platinum, etc.
- Modularidad si aparece como parte del modelo: modular, semi-modular, no modular
- Formato si aparece: ATX, SFX, etc.

Regla:
Dos PSUs solo son el mismo producto si coinciden potencia + certificación + formato/modelo.
Si cambia 750W por 850W, responde false.
Si cambia Gold por Bronze, responde false.
Si cambia ATX por SFX, responde false.

-------------------------
G. REFRIGERACIÓN
-------------------------

Atributos esenciales:
- Tipo: aire o líquida
- Tamaño del radiador si es líquida: 120, 240, 280, 360, 420
- Modelo exacto

Regla:
Dos sistemas de refrigeración NO son iguales si cambia el tipo o el tamaño del radiador.
Ejemplos:
- líquida 240 != líquida 360
- aire != líquida

-------------------------
H. MONITORES
-------------------------

Atributos esenciales:
- Tamaño: 24, 27, 32 pulgadas
- Resolución: 1080p, 1440p, 4K
- Frecuencia: 60Hz, 144Hz, 165Hz, 240Hz
- Panel si aparece y forma parte del modelo: IPS, VA, OLED, etc.

Regla:
Dos monitores solo son el mismo producto si coinciden tamaño + resolución + refresco + modelo.
Si cambia 27" por 32", responde false.
Si cambia 144Hz por 165Hz, responde false.
Si cambia 1440p por 4K, responde false.

==================================================
4) MARCAS Y FABRICANTES
==================================================

Diferencia entre marca de chip y marca comercial:
- En CPU, Intel y AMD son marcas esenciales.
- En GPU, NVIDIA/AMD/Intel definen el chip; MSI/ASUS/Gigabyte/Sapphire/Zotac pueden ser solo ensambladoras.
- En RAM, SSD, PSU, refrigeración y monitores, la marca comercial suele ser importante si el modelo exacto no está claro.

Si la marca comercial cambia y no puedes confirmar con seguridad el mismo modelo exacto, responde false.

==================================================
5) REGLAS DE DESEMPATE
==================================================

- Si un texto es mucho más largo pero ambos contienen el mismo modelo exacto, responde true.
- Si uno contiene datos extra y el otro no, solo responde true si el modelo exacto coincide sin conflicto.
- Si un atributo crítico entra en conflicto, responde false.
- Si un sufijo crítico falta en uno de los dos textos, responde false.
- Si ves dos números de modelo distintos, responde false.
- Si ves dos capacidades distintas, responde false.
- Si ves dos chipsets distintos, responde false.

==================================================
6) EJEMPLOS
==================================================

Texto A: "Intel Core i5-12400 2.5 GHz"
Texto B: "Intel Core Ultra 9 285K IA Integrada 3.2/5.7GHz Box"
Respuesta correcta:
{"mismo_producto": false}

Texto A: "Intel Core Ultra 7 265KF 3.3/5.5GHz Box"
Texto B: "Intel Core Ultra 7 265K 3.3/5.5GHz Box"
Respuesta correcta:
{"mismo_producto": false}

Texto A: "AMD Ryzen 5 3400G 4 Núcleos 3.7 GHz"
Texto B: "AMD Ryzen 5 3400G 3.7GHz Box"
Respuesta correcta:
{"mismo_producto": true}

Texto A: "RTX 4060 8GB"
Texto B: "RTX 4060 Ti 8GB"
Respuesta correcta:
{"mismo_producto": false}

Texto A: "SSD NVMe 1TB PCIe 4.0"
Texto B: "SSD NVMe 2TB PCIe 4.0"
Respuesta correcta:
{"mismo_producto": false}

Texto A: "B650"
Texto B: "B650M"
Respuesta correcta:
{"mismo_producto": false}

Texto A: "DDR5 32GB 6000 CL30"
Texto B: "DDR5 32GB 6000 CL30"
Respuesta correcta:
{"mismo_producto": true}

==================================================
7) FORMATO DE SALIDA
==================================================

Devuelve ÚNICAMENTE un JSON válido.
No expliques nada.
No uses markdown.
No añadas texto adicional.

Formato exacto:
{"mismo_producto": true}

o

{"mismo_producto": false}
"""

    prompt_usuario = f"Producto 1: '{nombre_base}'\nProducto 2: '{nombre_oferta}'"
    
    try:
        respuesta = cliente_ia.chat.completions.create(
            model="llama3",
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": prompt_usuario}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        
        # Leemos el JSON que nos devuelve Llama 3
        contenido = respuesta.choices[0].message.content
        datos_json = json.loads(contenido)
        return datos_json.get("mismo_producto", False)
        
    except Exception as e:
        print(f"⚠️ Aviso: Error consultando a Ollama ({e}). Se asume False por seguridad.")
        return False

# --- CONFIGURACIÓN PARA AGENTE ALEATORIO ---
USER_AGENTS_MODERNOS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/123.0.0.0 Safari/537.36"
]

def obtener_user_agent_aleatorio():
    """Devuelve un User-Agent realista de nuestra lista segura."""
    return random.choice(USER_AGENTS_MODERNOS)

# --- CONFIGURACIÓN PARA MAYOR VELOCIDAD ---
def bloquear_recursos_innecesarios(route):
    """Evita que Playwright descargue imágenes, CSS y fuentes para ir más rápido."""
    tipo = route.request.resource_type
    if tipo in ['image', 'stylesheet', 'font', 'media']:
        route.abort()
    else:
        route.continue_()

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
def limpiar_nombre_producto(nombre):
    nombre_limpio = nombre.lower()
    
    # 1. Quitar palabras basura
    palabras_basura = [
        "procesador", "tarjeta grafica", "tarjeta gráfica", "placa base", "memoria ram", 
        "disco duro", "fuente de alimentacion", "fuente de alimentación", "caja de pc", 
        "caja pc", "torre", "refrigeracion liquida", "refrigeración líquida", "kit", 
        "disipador", "ventilador", "sin ventilador", "no cooler", "box", "tray", 
        "edition", "oem", "retail", "v2", "v3", "reacondicionado", "refurbished",
        "frecuencia", "base", "turbo", "gráficos", "graficos", "overclocking", 
        "núcleos", "nucleos", "ghz", "ecc", "lga", "socket", "threads", "hilos",
        "ia integrada", "intel ai boost", "npu", "radeon 780m", "vega 11"
    ]
    for palabra in palabras_basura:
        # Usamos \b para asegurar que borramos la palabra entera y no partes de otras
        nombre_limpio = re.sub(rf'\b{palabra}\b', '', nombre_limpio)

    # 2. Expresiones regulares para capturar el "Corazón" del hardware
    modelo_extraido = ""
    
    # -- PROCESADORES --
    match_intel_core = re.search(r'(i[3579]-?\s*\d{4,5}[a-z]*)', nombre_limpio)
    match_intel_ultra = re.search(r'(ultra\s*[579]\s*\d{3}[a-z]*)', nombre_limpio) # Atrapa "Ultra 7 265K"
    match_xeon  = re.search(r'(xeon\s+[a-z0-9\-]+)', nombre_limpio)
    match_amd   = re.search(r'(ryzen\s*[3579]\s*\d{4}[a-z0-9]*|r[3579]-?\d{4}[a-z]*)', nombre_limpio)
    match_tr    = re.search(r'(threadripper\s*\d{4}[a-z]*)', nombre_limpio)
    
    # -- TARJETAS GRÁFICAS --
    match_rtx = re.search(r'(rtx\s*\d{4}\s*(?:ti|super)?)', nombre_limpio)
    match_gtx = re.search(r'(gtx\s*\d{4}\s*(?:ti|super)?)', nombre_limpio)
    match_rx  = re.search(r'(rx\s*\d{4}\s*(?:xtx|xt)?)', nombre_limpio)

    # -- PLACAS BASE (Chipsets) --
    match_mb = re.search(r'\b([zhbxab]\d{2,3}[a-z]*)\b', nombre_limpio)

    # Asignar el modelo extraído siguiendo un orden de prioridad
    if match_intel_core:
        modelo_extraido = match_intel_core.group(1).replace(" ", "").replace("-", "")
    elif match_intel_ultra:
        modelo_extraido = match_intel_ultra.group(1).replace(" ", "")
    elif match_xeon:
        modelo_extraido = match_xeon.group(1).replace(" ", "").replace("-", "")
    elif match_amd:
        modelo_extraido = match_amd.group(1).replace(" ", "").replace("-", "")
    elif match_tr:
        modelo_extraido = match_tr.group(1).replace(" ", "")
    elif match_rtx:
        modelo_extraido = match_rtx.group(1).replace(" ", "")
    elif match_gtx:
        modelo_extraido = match_gtx.group(1).replace(" ", "")
    elif match_rx:
        modelo_extraido = match_rx.group(1).replace(" ", "")
    elif match_mb:
        modelo_extraido = match_mb.group(1).replace(" ", "")

    # 3. Limpiar caracteres especiales para el Fuzzing
    nombre_limpio = re.sub(r'[^a-z0-9\.\-\s]', ' ', nombre_limpio)
    nombre_limpio = ' '.join(nombre_limpio.split()).strip()

    return {
        "texto_limpio": nombre_limpio,
        "modelo_clave": modelo_extraido
    }

def guardar_productos_en_db(productos_extraidos, nombre_tienda, url_base_tienda, categoria_db, tipo_db):
    if not productos_extraidos:
        return 0

    print(f"\n💾 Guardando {len(productos_extraidos)} productos en la BD para la tienda {nombre_tienda}...\n")

    tienda_db, _ = Tienda.objects.get_or_create(
        nombre=nombre_tienda, 
        defaults={'url_base': url_base_tienda}
    )

    productos_guardados_exitosamente = 0
    UMBRAL_SIMILITUD = 70
    productos_existentes = list(Producto.objects.filter(categoria=categoria_db))

    with transaction.atomic():
        for item in productos_extraidos:
            try:
                nombre_original = item['nombre'].strip()
                precio_float = limpiar_precio(item['precio'])
                
                if precio_float <= 0:
                    continue
                    
                # Obtenemos el diccionario con el texto normal y el modelo extraído por Regex
                datos_comparar = limpiar_nombre_producto(nombre_original)
                nombre_para_comparar = datos_comparar["texto_limpio"]
                modelo_para_comparar = datos_comparar["modelo_clave"]
                
                producto_asociado = None
                mejor_score = 0
                
                for prod_bd in productos_existentes:
                    # Hacemos lo mismo con los productos que ya tenemos en la base de datos
                    datos_bd = limpiar_nombre_producto(prod_bd.nombre)
                    nombre_bd_limpio = datos_bd["texto_limpio"]
                    modelo_bd = datos_bd["modelo_clave"]
                    
                    # REGLA DE ORO: Evitar falsos positivos entre modelos distintos
                    if modelo_para_comparar and modelo_bd and modelo_para_comparar != modelo_bd:
                        continue 
                    
                    # 1. Primer filtro: FuzzyWuzzy matemático (rápido y gratis)
                    score = fuzz.token_set_ratio(nombre_para_comparar, nombre_bd_limpio)
                    
                    if score >= UMBRAL_SIMILITUD:
                        # 2. Segundo filtro: El Juez de IA (Ollama)
                        # Solo llamamos a la IA si FuzzyWuzzy cree que son iguales (>= 85%)
                        if es_mismo_producto_ia(nombre_original, prod_bd.nombre):
                            mejor_score = score
                            producto_asociado = prod_bd
                            break

                creado_prod = False
                # Si el FuzzyWuzzy supera el umbral, unimos la oferta al producto existente
                if mejor_score >= UMBRAL_SIMILITUD and producto_asociado:
                    producto = producto_asociado
                else:
                    # Si no supera el umbral, creamos un producto nuevo "base" en la BD
                    producto = Producto.objects.create(
                        nombre=nombre_original,
                        tipo=tipo_db,
                        categoria=categoria_db
                    )
                    productos_existentes.append(producto)
                    creado_prod = True

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

                if creado_prod:
                    print(f"[NUEVO] {nombre_original} ({mejor_score}%) - {precio_float}€")
                else:
                    print(f"[OFERTA] {nombre_original} -> {producto.nombre} ({mejor_score}%) - {precio_float}€")

            except Exception as db_error:
                print(f"❌ Error guardando {item.get('nombre', 'Desconocido')}: {db_error}")

    return productos_guardados_exitosamente

# =================================================================
# LÓGICA EXCLUSIVA DE PC COMPONENTES
# =================================================================
def escanear_catalogo_pcc(url_catalogo_base, categoria_db, tipo_db):
    print(f"\n🕷️ [PCC] -> Escaneando: {url_catalogo_base}")
    
    todos_los_productos_extraidos = []
    pagina_actual = 1
    hay_mas_paginas = True

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True, 
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu"
            ]
        )

        nuevo_user_agent = obtener_user_agent_aleatorio()
        ancho_viewport = random.randint(1366, 1920)
        alto_viewport = random.randint(768, 1080)

        context = browser.new_context(
            viewport={'width': ancho_viewport, 'height': alto_viewport},
            user_agent=nuevo_user_agent, 
            locale="es-ES",
            timezone_id="Europe/Madrid",
            extra_http_headers={
                "Accept-Language": "es-ES,es;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Sec-Ch-Ua": '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1"
            }
        )
        page = context.new_page()
        
        page.route("**/*", bloquear_recursos_innecesarios)
        
        # Script fundamental para borrar la huella de Playwright del navegador antes de que cargue la página
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = { runtime: {} };
        """)
        
        try:
            while hay_mas_paginas:
                url_con_paginacion = f"{url_catalogo_base}?page={pagina_actual}"
                print(f"\n📄 Entrando a la página {pagina_actual}... ({url_con_paginacion})")
                
                page.goto(url_con_paginacion, timeout=40000, wait_until="domcontentloaded")
                try:
                    # Espera máximo 5 segundos a que aparezca al menos un producto en el DOM
                    page.wait_for_selector('a[data-testid="normal-link"]', state='attached', timeout=5000)
                except:
                    pass

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
                siguiente_deshabilitado = page.evaluate(r'''() => {
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

def extraer_productos_de_pagina_pcc(page):
    """Extrae productos de la vista actual adaptado a PcComponentes"""
    ultimo_conteo = 0
    intentos_sin_crecer = 0

    for _ in range(10):
        page.mouse.wheel(0, 1500)
        page.wait_for_timeout(150)

        conteo_actual = page.locator('a[data-testid="normal-link"]').count()

        if conteo_actual > ultimo_conteo:
            ultimo_conteo = conteo_actual
            intentos_sin_crecer = 0
        else:
            intentos_sin_crecer += 1
            
        # Si hemos hecho scroll 2 veces y no han aparecido productos nuevos, asumimos que ya cargó todo
        if intentos_sin_crecer >= 2:
            break

    datos = page.evaluate(r'''() => {
        let resultados = [];
        let tarjetas = document.querySelectorAll('a[data-product-id], a[data-testid="normal-link"]');
        
        tarjetas.forEach(tarjeta => {
            try {
                let link = tarjeta.href;
                if (!link || link.includes('#')) return;

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

                // La imagen la intentamos sacar, pero al haberlas bloqueado, probablemente venga null o un placeholder.
                // Está bien, tu comparador prioriza el texto.
                let imgEl = tarjeta.querySelector('img');
                let imgUrl = imgEl ? imgEl.src : null;

                if (titulo && precioStr && titulo.trim() !== "") {
                    resultados.push({
                        nombre: titulo,
                        link: link,
                        precio: precioStr.toString(),
                        imagen: imgUrl
                    });
                }
            } catch(e) {}
        });

        // Filtramos duplicados en JS
        let unicos = [];
        let linksVistos = new Set();
        resultados.forEach(r => {
            if (!linksVistos.has(r.link)) {
                linksVistos.add(r.link);
                unicos.push(r);
            }
        });
        return unicos;
    }''')
    
    return datos

# =================================================================
# LÓGICA EXCLUSIVA DE COOLMOD
# =================================================================
def escanear_catalogo_coolmod(url_catalogo_base, categoria_db, tipo_db, excluir_palabras=None):
    print(f"\n🕷️ [COOLMOD] -> Escaneando: {url_catalogo_base}")
    
    todos_los_productos_extraidos = []
    pagina_actual = 1
    hay_mas_paginas = True

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True, 
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu"
            ]
        )
        
        nuevo_user_agent = obtener_user_agent_aleatorio()
        ancho_viewport = random.randint(1366, 1920)
        alto_viewport = random.randint(768, 1080)
        
        context = browser.new_context(
            viewport={'width': ancho_viewport, 'height': alto_viewport},
            user_agent=nuevo_user_agent, 
            locale="es-ES",
            timezone_id="Europe/Madrid",
            extra_http_headers={
                "Accept-Language": "es-ES,es;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Sec-Ch-Ua": '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1"
            }
        )
        page = context.new_page()
        
        page.route("**/*", bloquear_recursos_innecesarios)
        
        # Script fundamental para borrar la huella de Playwright del navegador antes de que cargue la página
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = { runtime: {} };
        """)
        
        try:
            while hay_mas_paginas:
                # Coolmod utiliza el parámetro '?pagina=X' o '&pagina=X'
                separador = "&" if "?" in url_catalogo_base else "?"
                url_con_paginacion = f"{url_catalogo_base}{separador}pagina={pagina_actual}"
                
                print(f"\n📄 Entrando a la página {pagina_actual}... ({url_con_paginacion})")
                
                page.goto(url_con_paginacion, timeout=40000, wait_until="domcontentloaded")
                try:
                    # Espera máximo 5 segundos a que aparezca al menos un producto en el DOM
                    page.wait_for_selector('article.product-card', state='attached', timeout=5000)
                except:
                    pass

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
                siguiente_deshabilitado = page.evaluate(r'''() => {
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

def extraer_productos_de_pagina_coolmod(page):
    """Extrae productos de la vista actual adaptado a Coolmod"""
    # Hacemos algo de scroll para asegurar que carguen las imágenes (Lazy Load)
    
    ultimo_conteo = 0
    intentos_sin_crecer = 0
    
    for _ in range(10):
        page.mouse.wheel(0, 1500)
        page.wait_for_timeout(150)

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

# =================================================================
# LÓGICA EXCLUSIVA DE LIFE INFORMÁTICA
# =================================================================
def escanear_catalogo_lifeinformatica(url_catalogo_base, categoria_db, tipo_db, excluir_palabras=None):
    print(f"\n🕷️ [LIFE INFO] -> Escaneando: {url_catalogo_base}")
    
    todos_los_productos_extraidos = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True, 
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu"
            ]
        )
        
        nuevo_user_agent = obtener_user_agent_aleatorio()
        ancho_viewport = random.randint(1366, 1920)
        alto_viewport = random.randint(768, 1080)
        
        context = browser.new_context(
            viewport={'width': ancho_viewport, 'height': alto_viewport},
            user_agent=nuevo_user_agent, 
            locale="es-ES",
            timezone_id="Europe/Madrid",
            extra_http_headers={
                "Accept-Language": "es-ES,es;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Sec-Ch-Ua": '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1"
            }
        )
        page = context.new_page()
        
        page.route("**/*", bloquear_recursos_innecesarios)
        
        # Script fundamental para borrar la huella de Playwright del navegador antes de que cargue la página
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = { runtime: {} };
        """)
        
        try:
            page.goto(url_catalogo_base, timeout=40000, wait_until="domcontentloaded")
            try:
                # Espera máximo 5 segundos a que aparezca al menos un producto en el DOM
                page.wait_for_selector('a[data-testid="normal-link"]', state='attached', timeout=5000)
            except:
                pass

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
    
    ultimo_conteo = 0
    intentos_sin_crecer = 0
    
    for _ in range(10):
        page.mouse.wheel(0, 1500)
        page.wait_for_timeout(150)

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
def escanear_catalogo_alternate(url_catalogo_base, categoria_db, tipo_db, excluir_palabras=None):
    print(f"\n🕷️ [ALTERNATE] -> Escaneando: {url_catalogo_base}")
    
    todos_los_productos_extraidos = []
    pagina_actual = 1
    hay_mas_paginas = True

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True, 
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu"
            ]
        )
        
        nuevo_user_agent = obtener_user_agent_aleatorio()
        ancho_viewport = random.randint(1366, 1920)
        alto_viewport = random.randint(768, 1080)
        
        context = browser.new_context(
            viewport={'width': ancho_viewport, 'height': alto_viewport},
            user_agent=nuevo_user_agent, 
            locale="es-ES",
            timezone_id="Europe/Madrid",
            extra_http_headers={
                "Accept-Language": "es-ES,es;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Sec-Ch-Ua": '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1"
            }
        )
        page = context.new_page()
        
        page.route("**/*", bloquear_recursos_innecesarios)
        
        # Script fundamental para borrar la huella de Playwright del navegador antes de que cargue la página
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = { runtime: {} };
        """)
        
        try:
            while hay_mas_paginas:
                url_con_paginacion = f"{url_catalogo_base}?page={pagina_actual}"
                print(f"\n📄 Entrando a la página {pagina_actual}... ({url_con_paginacion})")

                page.goto(url_con_paginacion, timeout=40000, wait_until="domcontentloaded")
                try:
                    # Espera máximo 5 segundos a que aparezca al menos un producto en el DOM
                    page.wait_for_selector('a.productBox', state='attached', timeout=5000)
                except:
                    pass

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
                siguiente_deshabilitado = page.evaluate(r'''() => {
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

def extraer_productos_de_pagina_alternate(page):
    """Extrae productos de la vista actual adaptado a Alternate"""
    # Scroll suave para que carguen las imágenes
    
    ultimo_conteo = 0
    intentos_sin_crecer = 0
    
    for _ in range(10):
        page.mouse.wheel(0, 1500)
        page.wait_for_timeout(150)

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

# =================================================================
# LÓGICA EXCLUSIVA DE NEOBYTE
# =================================================================
def escanear_catalogo_neobyte(url_catalogo_base, categoria_db, tipo_db, excluir_palabras=None):
    print(f"\n🕷️ [NEOBYTE] -> Escaneando: {url_catalogo_base}")
    
    todos_los_productos_extraidos = []
    pagina_actual = 1
    hay_mas_paginas = True

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True, 
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu"
            ]
        )
        
        nuevo_user_agent = obtener_user_agent_aleatorio()
        ancho_viewport = random.randint(1366, 1920)
        alto_viewport = random.randint(768, 1080)
        
        context = browser.new_context(
            viewport={'width': ancho_viewport, 'height': alto_viewport},
            user_agent=nuevo_user_agent, 
            locale="es-ES",
            timezone_id="Europe/Madrid",
            extra_http_headers={
                "Accept-Language": "es-ES,es;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Sec-Ch-Ua": '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1"
            }
        )
        page = context.new_page()
        
        page.route("**/*", bloquear_recursos_innecesarios)
        
        # Script fundamental para borrar la huella de Playwright del navegador antes de que cargue la página
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = { runtime: {} };
        """)
        
        try:
            while hay_mas_paginas:
                url_con_paginacion = f"{url_catalogo_base}?page={pagina_actual}"
                print(f"\n📄 Entrando a la página {pagina_actual}... ({url_con_paginacion})")
                
                page.goto(url_con_paginacion, timeout=40000, wait_until="domcontentloaded")
                try:
                    # Espera máximo 5 segundos a que aparezca al menos un producto en el DOM
                    page.wait_for_selector('article.product-miniature', state='attached', timeout=5000)
                except:
                    pass

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

def extraer_productos_de_pagina_neobyte(page):
    """Extrae productos de la vista actual adaptado a NeoByte"""
    # Hacemos scroll para asegurar que las imágenes y elementos carguen (Lazy Load)
    
    ultimo_conteo = 0
    intentos_sin_crecer = 0
    
    for _ in range(10):
        page.mouse.wheel(0, 1500)
        page.wait_for_timeout(150)

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

# =================================================================
# LÓGICA EXCLUSIVA DE AMAZON
# =================================================================
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
                siguiente_deshabilitado = page.evaluate(r'''() => {
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

# =================================================================
# ESCANEO DE TIENDAS
# =================================================================
def escanearPcComponentes():
    total_pcc = 0
    total_productos = 0

    total_productos = escanear_catalogo_pcc("https://www.pccomponentes.com/procesadores", 'CPU', 'HW')
    total_pcc += total_productos
    print(f"\n✅ [Procesadores] Se han guardado un total de {total_productos} procesadores.")
    
    total_productos = escanear_catalogo_pcc("https://www.pccomponentes.com/placas-base", 'MB', 'HW')
    total_pcc += total_productos
    print(f"\n✅ [Placas Base] Se han guardado un total de {total_productos} placas base.")
    
    total_productos = escanear_catalogo_pcc("https://www.pccomponentes.com/memorias-ram", 'RAM', 'HW')
    total_pcc += total_productos
    print(f"\n✅ [Memorias RAM] Se han guardado un total de {total_productos} memorias RAM.")
    
    total_productos = escanear_catalogo_pcc("https://www.pccomponentes.com/cajas-pc", 'CASE', 'HW')
    total_pcc += total_productos
    print(f"\n✅ [Cajas PC] Se han guardado un total de {total_productos} cajas de pc.")
    
    total_productos = escanear_catalogo_pcc("https://www.pccomponentes.com/ventiladores-cpu", 'AIR', 'HW')
    total_pcc += total_productos
    print(f"\n✅ [Refrigeración Aire] Se han guardado un total de {total_productos} refrigeración de aire.")
    
    total_productos = escanear_catalogo_pcc("https://www.pccomponentes.com/refrigeracion-liquida/kit-refrigeracion-liquida", 'LIQ', 'HW')
    total_pcc += total_productos
    print(f"\n✅ [Refrigeración Líquida] Se han guardado un total de {total_productos} refrigeraciones líquidas.")
    
    total_productos = escanear_catalogo_pcc("https://www.pccomponentes.com/tarjetas-graficas", 'GPU', 'HW')
    total_pcc += total_productos
    print(f"\n✅ [Tarjetas Gráficas] Se han guardado un total de {total_productos} tarjetas gráficas.")
    
    total_productos = escanear_catalogo_pcc("https://www.pccomponentes.com/fuentes-alimentacion", 'PSU', 'HW')
    total_pcc += total_productos
    print(f"\n✅ [Fuentes de Alimentación] Se han guardado un total de {total_productos} fuentes de alimentación.")
    
    total_productos = escanear_catalogo_pcc("https://www.pccomponentes.com/discos-duros", 'SSD', 'HW')
    total_pcc += total_productos
    print(f"\n✅ [Discos Duros] Se han guardado un total de {total_productos} discos duros.")
    
    total_productos = escanear_catalogo_pcc("https://www.pccomponentes.com/monitores", 'MON', 'HW')
    total_pcc += total_productos
    print(f"\n✅ [Monitores] Se han guardado un total de {total_productos} monitores.")


    print(f"\n✅ [PcComponentes FIN] Se han guardado un total de {total_pcc} productos.")
    return total_pcc

def escanearCoolmod():
    total_coolmod = 0
    total_productos = 0

    total_productos = escanear_catalogo_coolmod("https://www.coolmod.com/componentes-pc-procesadores/", 'CPU', 'HW')
    total_coolmod += total_productos
    print(f"\n✅ [Procesadores] Se han guardado un total de {total_productos} procesadores.")
    
    
    total_productos = escanear_catalogo_coolmod("https://www.coolmod.com/componentes-pc-placas-base/", 'MB', 'HW')
    total_coolmod += total_productos
    print(f"\n✅ [Placas Base] Se han guardado un total de {total_productos} placas base.")
    
    total_productos = escanear_catalogo_coolmod("https://www.coolmod.com/componentes-pc-memorias-ram/", 'RAM', 'HW')
    total_coolmod += total_productos
    print(f"\n✅ [Memorias RAM] Se han guardado un total de {total_productos} memorias RAM.")
    
    total_productos = escanear_catalogo_coolmod("https://www.coolmod.com/componentes-pc-torres-cajas/", 'CASE', 'HW')
    total_coolmod += total_productos
    print(f"\n✅ [Cajas PC] Se han guardado un total de {total_productos} cajas de pc.")
    
    total_productos = escanear_catalogo_coolmod("https://www.coolmod.com/componentes-pc-disipadores-ventiladores/", 'AIR', 'HW', excluir_palabras=[
        '240', '280', '360', '420', 'refrigeracion liquida', 'refrigeración líquida', 'líquida', 'liquida', 'aio', 'water'
        ]
    )
    total_coolmod += total_productos
    print(f"\n✅ [Refrigeración Aire] Se han guardado un total de {total_productos} refrigeración de aire.")
    
    total_productos = escanear_catalogo_coolmod("https://www.coolmod.com/refrigeracion-liquida-kits-liquida/", 'LIQ', 'HW')
    total_coolmod += total_productos
    print(f"\n✅ [Refrigeración Líquida] Se han guardado un total de {total_productos} refrigeraciones líquidas.")
    
    total_productos = escanear_catalogo_coolmod("https://www.coolmod.com/tarjetas-graficas/", 'GPU', 'HW')
    total_coolmod += total_productos
    print(f"\n✅ [Tarjetas Gráficas] Se han guardado un total de {total_productos} tarjetas gráficas.")
    
    total_productos = escanear_catalogo_coolmod("https://www.coolmod.com/componentes-pc-fuentes-alimentacion/", 'PSU', 'HW')
    total_coolmod += total_productos
    print(f"\n✅ [Fuentes de Alimentación] Se han guardado un total de {total_productos} fuentes de alimentación.")
    
    total_productos = escanear_catalogo_coolmod("https://www.coolmod.com/componentes-pc-discos-duros/", 'SSD', 'HW')
    total_coolmod += total_productos
    print(f"\n✅ [Discos Duros] Se han guardado un total de {total_productos} discos duros.")
    
    total_productos = escanear_catalogo_coolmod("https://www.coolmod.com/perifericos-monitores/", 'MON', 'HW')
    total_coolmod += total_productos
    print(f"\n✅ [Monitores] Se han guardado un total de {total_productos} monitores.")

    print(f"\n✅ [Coolmod FIN] Se han guardado un total de {total_coolmod} productos.")
    return total_coolmod

def escanearLifeInformatica():
    total_life = 0
    total_productos = 0

    total_productos = escanear_catalogo_lifeinformatica("https://lifeinformatica.com/categoria-producto/componentes/procesadores/", 'CPU', 'HW')
    total_life += total_productos
    print(f"\n✅ [Procesadores] Se han guardado un total de {total_productos} procesadores.")
    
    total_productos = escanear_catalogo_lifeinformatica("https://lifeinformatica.com/categoria-producto/componentes/placas-base/", 'MB', 'HW')
    total_life += total_productos
    print(f"\n✅ [Placas Base] Se han guardado un total de {total_productos} placas base.")
    
    total_productos = escanear_catalogo_lifeinformatica("https://lifeinformatica.com/categoria-producto/componentes/memorias-ram/", 'RAM', 'HW')
    total_life += total_productos
    print(f"\n✅ [Memorias RAM] Se han guardado un total de {total_productos} memorias RAM.")
    
    total_productos = escanear_catalogo_lifeinformatica("https://lifeinformatica.com/categoria-producto/componentes/cajas-y-accesorios/cajas/", 'CASE', 'HW')
    total_life += total_productos
    print(f"\n✅ [Cajas PC] Se han guardado un total de {total_productos} cajas de pc.")
    
    total_productos = escanear_catalogo_lifeinformatica("https://lifeinformatica.com/categoria-producto/componentes/refrigeracion/disipadores-de-cpu/", 'AIR', 'HW', excluir_palabras=[
        '240', '280', '360', '420', 'refrigeracion liquida', 'refrigeración líquida', 'líquida', 'liquida', 'aio', 'water'
        ]
    )
    total_life += total_productos
    print(f"\n✅ [Refrigeración Aire] Se han guardado un total de {total_productos} refrigeración de aire.")
    
    total_productos = escanear_catalogo_lifeinformatica("https://lifeinformatica.com/categoria-producto/componentes/refrigeracion/kits-de-refrigeracion-liquida/", 'LIQ', 'HW')
    total_life += total_productos
    print(f"\n✅ [Refrigeración Líquida] Se han guardado un total de {total_productos} refrigeraciones líquidas.")
    
    total_productos = escanear_catalogo_lifeinformatica("https://lifeinformatica.com/categoria-producto/componentes/tarjetas-graficas/", 'GPU', 'HW')
    total_life += total_productos
    print(f"\n✅ [Tarjetas Gráficas] Se han guardado un total de {total_productos} tarjetas gráficas.")
    
    total_productos = escanear_catalogo_lifeinformatica("https://lifeinformatica.com/categoria-producto/componentes/fuentes-de-alimentacion-y-accesorios/fuentes-de-alimentacion/", 'PSU', 'HW')
    total_life += total_productos
    print(f"\n✅ [Fuentes de Alimentación] Se han guardado un total de {total_productos} fuentes de alimentación.")
    
    total_productos = escanear_catalogo_lifeinformatica("https://lifeinformatica.com/categoria-producto/componentes/discos-duros/", 'SSD', 'HW')
    total_life += total_productos
    print(f"\n✅ [Discos Duros] Se han guardado un total de {total_productos} discos duros.")
    
    total_productos = escanear_catalogo_lifeinformatica("https://lifeinformatica.com/categoria-producto/perifericos/monitores-y-accesorios/monitores/", 'MON', 'HW')
    total_life += total_productos
    print(f"\n✅ [Monitores] Se han guardado un total de {total_productos} monitores.")

    print(f"\n✅ [Life Informática FIN] Se han guardado un total de {total_life} productos.")
    return total_life

def escanearAlternate():
    total_alternate = 0
    total_productos = 0

    total_productos = escanear_catalogo_alternate("https://www.alternate.es/Procesadores", 'CPU', 'HW')
    total_alternate += total_productos
    print(f"\n✅ [Procesadores] Se han guardado un total de {total_productos} procesadores.")
    
    total_productos = escanear_catalogo_alternate("https://www.alternate.es/Placas-base", 'MB', 'HW')
    total_alternate += total_productos
    print(f"\n✅ [Placas Base] Se han guardado un total de {total_productos} placas base.")
    
    total_productos = escanear_catalogo_alternate("https://www.alternate.es/Memoria-RAM", 'RAM', 'HW')
    total_alternate += total_productos
    print(f"\n✅ [Memorias RAM] Se han guardado un total de {total_productos} memorias RAM.")
    
    total_productos = escanear_catalogo_alternate("https://www.alternate.es/Cajas-de-PC", 'CASE', 'HW')
    total_alternate += total_productos
    print(f"\n✅ [Cajas PC] Se han guardado un total de {total_productos} cajas de pc.")
    
    total_productos = escanear_catalogo_alternate("https://www.alternate.es/Disipadores-de-CPU", 'AIR', 'HW', excluir_palabras=[
        '240', '280', '360', '420', 'refrigeracion liquida', 'refrigeración líquida', 'líquida', 'liquida', 'aio', 'water'
        ]
    )
    total_alternate += total_productos
    print(f"\n✅ [Refrigeración Aire] Se han guardado un total de {total_productos} refrigeración de aire.")
    
    total_productos = escanear_catalogo_alternate("https://www.alternate.es/Refrigeraci%C3%B3n-l%C3%ADquida", 'LIQ', 'HW')
    total_alternate += total_productos
    print(f"\n✅ [Refrigeración Líquida] Se han guardado un total de {total_productos} refrigeraciones líquidas.")
    
    total_productos = escanear_catalogo_alternate("https://www.alternate.es/Tarjetas-gr%C3%A1ficas", 'GPU', 'HW')
    total_alternate += total_productos
    print(f"\n✅ [Tarjetas Gráficas] Se han guardado un total de {total_productos} tarjetas gráficas.")
    
    total_productos = escanear_catalogo_alternate("https://www.alternate.es/Fuentes-de-alimentaci%C3%B3n", 'PSU', 'HW')
    total_alternate += total_productos
    print(f"\n✅ [Fuentes de Alimentación] Se han guardado un total de {total_productos} fuentes de alimentación.")
    
    total_productos = escanear_catalogo_alternate("https://www.alternate.es/SSD", 'SSD', 'HW')
    total_alternate += total_productos
    print(f"\n✅ [Discos Duros] Se han guardado un total de {total_productos} discos duros.")
    
    total_productos = escanear_catalogo_alternate("https://www.alternate.es/Monitores", 'MON', 'HW')
    total_alternate += total_productos
    print(f"\n✅ [Monitores] Se han guardado un total de {total_productos} monitores.")

    print(f"\n✅ [Alternate FIN] Se han guardado un total de {total_alternate} productos.")
    return total_alternate

def escanearNeoByte():
    total_neobyte = 0
    total_productos = 0

    total_productos = escanear_catalogo_neobyte("https://www.neobyte.es/procesadores-107", 'CPU', 'HW')
    total_neobyte += total_productos
    print(f"\n✅ [Procesadores] Se han guardado un total de {total_productos} procesadores.")
    
    total_productos = escanear_catalogo_neobyte("https://www.neobyte.es/placas-base-106", 'MB', 'HW')
    total_neobyte += total_productos
    print(f"\n✅ [Placas Base] Se han guardado un total de {total_productos} placas base.")
    
    total_productos = escanear_catalogo_neobyte("https://www.neobyte.es/memorias-ram-108", 'RAM', 'HW')
    total_neobyte += total_productos
    print(f"\n✅ [Memorias RAM] Se han guardado un total de {total_productos} memorias RAM.")
    
    total_productos = escanear_catalogo_neobyte("https://www.neobyte.es/cajas-de-ordenador-112", 'CASE', 'HW')
    total_neobyte += total_productos
    print(f"\n✅ [Cajas PC] Se han guardado un total de {total_productos} cajas de pc.")
    
    total_productos = escanear_catalogo_neobyte("https://www.neobyte.es/ventiladores-cpu-138", 'AIR', 'HW', excluir_palabras=[
        '240', '280', '360', '420', 'refrigeracion liquida', 'refrigeración líquida', 'líquida', 'liquida', 'aio', 'water'
        ]
    )
    total_neobyte += total_productos
    print(f"\n✅ [Refrigeración Aire] Se han guardado un total de {total_productos} refrigeración de aire.")
    
    total_productos = escanear_catalogo_neobyte("https://www.neobyte.es/refrigeracion-liquida-139", 'LIQ', 'HW')
    total_neobyte += total_productos
    print(f"\n✅ [Refrigeración Líquida] Se han guardado un total de {total_productos} refrigeraciones líquidas.")
    
    total_productos = escanear_catalogo_neobyte("https://www.neobyte.es/tarjetas-graficas-111", 'GPU', 'HW')
    total_neobyte += total_productos
    print(f"\n✅ [Tarjetas Gráficas] Se han guardado un total de {total_productos} tarjetas gráficas.")
    
    total_productos = escanear_catalogo_neobyte("https://www.neobyte.es/fuentes-de-alimentacion-113", 'PSU', 'HW')
    total_neobyte += total_productos
    print(f"\n✅ [Fuentes de Alimentación] Se han guardado un total de {total_productos} fuentes de alimentación.")
    
    total_productos = escanear_catalogo_neobyte("https://www.neobyte.es/discos-duros-110", 'SSD', 'HW')
    total_neobyte += total_productos
    print(f"\n✅ [Discos Duros] Se han guardado un total de {total_productos} discos duros.")
    
    total_productos = escanear_catalogo_neobyte("https://www.neobyte.es/monitores-169", 'MON', 'HW')
    total_neobyte += total_productos
    print(f"\n✅ [Monitores] Se han guardado un total de {total_productos} monitores.")

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
    
    total_general += escanearPcComponentes()
    
    # total_general += escanearAmazon()
    
    total_general += escanearCoolmod()
    
    total_general += escanearLifeInformatica()
    
    total_general += escanearAlternate()
    
    total_general += escanearNeoByte()
    
    print(f"\n🎉 ¡TODAS LAS TIENDAS ESCANEADAS! UN TOTAL DE {total_general} PRODUCTOS GUARDADOS/ACTUALIZADOS EN LA BASE DE DATOS.")