import os, django, sys, re, requests
from fuzzywuzzy import fuzz
from urllib.parse import urlparse
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from api.models import Producto, Tienda, Oferta, DecisionIA
from .stealth import obtener_perfil_navegador 
from .ia_matcher import evaluar_productos_ia_sync
from scrapper_app.utils.logger import logger

# CONFIGURACIÓN DE PATRONES DE LIMPIEZA
PALABRAS_BASURA = [
    "procesador", "tarjeta grafica", "tarjeta gráfica", "placa base", "memoria ram",
    "disco duro", "fuente de alimentacion", "fuente de alimentación", "caja de pc",
    "caja pc", "torre", "refrigeracion liquida", "refrigeración líquida", "kit",
    "disipador", "ventilador", "sin ventilador", "no cooler", "box", "tray",
    "edition", "oem", "retail", "v2", "v3", "reacondicionado", "refurbished",
    "frecuencia", "base", "turbo", "gráficos", "graficos", "overclocking",
    "núcleos", "nucleos", "ghz", "ecc", "lga", "socket", "threads", "hilos",
    "ia integrada", "intel ai boost", "npu", "radeon", "vega", "integrados"
]

PATRON_PALABRAS_BASURA = re.compile(
    r'\b(?:' + '|'.join(re.escape(palabra) for palabra in PALABRAS_BASURA) + r')\b',
    re.IGNORECASE
)

PATRON_CARACTERES_ESPECIALES = re.compile(r'[^a-z0-9\.\-\s]')
PATRON_ESPACIOS_MULTIPLES = re.compile(r'\s+')

PATRON_INTEL = re.compile(r'((?:i[3579]|ultra\s*[579])-?\s*\d{3,5}[a-z]*)', re.IGNORECASE)
PATRON_AMD = re.compile(r'((?:ryzen\s*[3579]|r[3579])-?\s*\d{4}[a-z0-9]*)', re.IGNORECASE)
PATRON_XEON = re.compile(r'(xeon\s+[a-z0-9\-]+)', re.IGNORECASE)
PATRON_THREADRIPPER = re.compile(r'(threadripper\s*\d{4}[a-z]*)', re.IGNORECASE)

PATRON_GPU_NVIDIA = re.compile(r'(rtx|gtx|quadro)\s*\d{4}\s*(?:ti|super)?[a-z]*', re.IGNORECASE)
PATRON_GPU_AMD = re.compile(r'rx\s*\d{4}\s*(?:xtx|xt|super)?[a-z]*', re.IGNORECASE)
PATRON_GPU_INTEL = re.compile(r'(arc\s*a\d{3})', re.IGNORECASE)

PATRON_MB = re.compile(r'\b([zhbxab]\d{2,3}[a-z]*)\b', re.IGNORECASE)
PATRON_RAM = re.compile(r'(ddr[45])\s*(\d{2}gb)?\s*(\d{4})(?:\s*cl\d+)?', re.IGNORECASE)
PATRON_SSD = re.compile(r'(\d{1,2}(?:tb|gb))\s*(nvme|pcie\s*4\.0|pcie\s*5\.0|sata)?', re.IGNORECASE)
PATRON_PSU = re.compile(r'(\d{3,4}w)\s*(bronze|silver|gold|platinum|titanium)?', re.IGNORECASE)
PATRON_MONITOR = re.compile(r'(\d{2})\s*(?:pulgadas?)?\s*([24]k|1080p|1440p|uhd)?\s*(\d{2,3}hz)?', re.IGNORECASE)
PATRON_AIO = re.compile(r'(?:aio|liquida)\s*(\d{3})', re.IGNORECASE)

# CONFIGURACIÓN DE DJANGO
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comparador.settings')
django.setup()

# --- CONFIGURACIÓN DE CACHÉ ---
CACHE_PRODUCTOS_BD = {}

# LIMPIAR LOS PUNTOS Y COMAS DE LOS PRECIOS
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

# LIMPIAR EL NOMBRE DEL PRODUCTO
def limpiar_nombre_producto(nombre):
    nombre_limpio = str(nombre).lower().strip()

    nombre_limpio = PATRON_PALABRAS_BASURA.sub(' ', nombre_limpio)

    modelo_extraido = ""

    match_intel = PATRON_INTEL.search(nombre_limpio)
    match_amd = PATRON_AMD.search(nombre_limpio)
    match_xeon = PATRON_XEON.search(nombre_limpio)
    match_tr = PATRON_THREADRIPPER.search(nombre_limpio)

    match_gpu_nvidia = PATRON_GPU_NVIDIA.search(nombre_limpio)
    match_gpu_amd = PATRON_GPU_AMD.search(nombre_limpio)
    match_gpu_intel = PATRON_GPU_INTEL.search(nombre_limpio)

    match_mb = PATRON_MB.search(nombre_limpio)
    match_ram = PATRON_RAM.search(nombre_limpio)
    match_ssd = PATRON_SSD.search(nombre_limpio)
    match_psu = PATRON_PSU.search(nombre_limpio)
    match_monitor = PATRON_MONITOR.search(nombre_limpio)
    match_aio = PATRON_AIO.search(nombre_limpio)

    if match_intel:
        modelo_extraido = match_intel.group(1).replace(" ", "").replace("-", "")
    elif match_amd:
        modelo_extraido = match_amd.group(1).replace(" ", "").replace("-", "")
        if modelo_extraido.startswith("r") and not modelo_extraido.startswith("ryzen"):
            modelo_extraido = modelo_extraido.replace("r", "ryzen", 1)
    elif match_xeon:
        modelo_extraido = match_xeon.group(1).replace(" ", "").replace("-", "")
    elif match_tr:
        modelo_extraido = match_tr.group(1).replace(" ", "")
    elif match_gpu_nvidia:
        modelo_extraido = match_gpu_nvidia.group(0).replace(" ", "")
    elif match_gpu_amd:
        modelo_extraido = match_gpu_amd.group(0).replace(" ", "")
    elif match_gpu_intel:
        modelo_extraido = match_gpu_intel.group(1).replace(" ", "")
    elif match_mb:
        modelo_extraido = match_mb.group(1).replace(" ", "")
    elif match_ram:
        tipo = match_ram.group(1)
        capacidad = match_ram.group(2) or ""
        frecuencia = match_ram.group(3)
        modelo_extraido = f"{tipo}-{capacidad}{frecuencia}".replace(" ", "")
    elif match_ssd:
        capacidad = match_ssd.group(1)
        interfaz = match_ssd.group(2) or ""
        modelo_extraido = f"{capacidad}-{interfaz}".replace(" ", "")
    elif match_psu:
        potencia = match_psu.group(1)
        cert = match_psu.group(2) or ""
        modelo_extraido = f"{potencia}-{cert}".replace(" ", "")
    elif match_monitor:
        tamano = match_monitor.group(1)
        resolucion = match_monitor.group(2) or ""
        hz = match_monitor.group(3) or ""
        modelo_extraido = f"{tamano}-{resolucion}-{hz}".replace(" ", "")
    elif match_aio:
        modelo_extraido = f"aio-{match_aio.group(1)}mm"

    nombre_limpio = PATRON_CARACTERES_ESPECIALES.sub(' ', nombre_limpio)
    nombre_limpio = PATRON_ESPACIOS_MULTIPLES.sub(' ', nombre_limpio).strip()

    return {
        "texto_limpio": nombre_limpio,
        "modelo_clave": modelo_extraido
    }

# DESACTIVAR OFERTAS OBSOLETAS
def desactivar_ofertas_obsoletas():
    """
    Busca ofertas que no se han visto en el último escaneo (más de 24 horas).
    Las marca como no disponibles para que no aparezcan productos fantasma o sin stock.
    """
    logger.info("\n🧹 Iniciando limpieza de ofertas caducadas/sin stock...")
    limite = timezone.now() - timedelta(days=1)
    
    # Filtramos usando TU campo 'fecha_actualizacion'
    ofertas_obsoletas = Oferta.objects.filter(fecha_actualizacion__lt=limite, disponible=True)
    cantidad = ofertas_obsoletas.count()
    
    if cantidad > 0:
        ofertas_obsoletas.update(disponible=False)
        logger.info(f"✅ Se han marcado {cantidad} ofertas como NO disponibles (fuera de stock).")
    else:
        logger.info("✅ Todas las ofertas están vigentes. No hay stock fantasma.")

# GUARDAR PRODUCTOS EN LA BASE DE DATOS
def guardar_productos_en_db(productos_extraidos, nombre_tienda, url_base_tienda, categoria_db, tipo_db):
    if not productos_extraidos:
        return 0
        
    global CACHE_PRODUCTOS_BD

    logger.info(f"\n💾 Guardando {len(productos_extraidos)} productos en la BD para la tienda {nombre_tienda}...\n")
    
    tienda_db, _ = Tienda.objects.get_or_create(nombre=nombre_tienda, defaults={'url_base': url_base_tienda})
    productos_guardados_exitosamente = 0
    UMBRAL_SIMILITUD = 70
    
    # 1. CARGA DE CACHÉ
    if categoria_db not in CACHE_PRODUCTOS_BD:
        logger.info(f"🔄 [Caché] Cargando la categoría '{categoria_db}' desde SQLite a la memoria RAM...")
        CACHE_PRODUCTOS_BD[categoria_db] = list(Producto.objects.filter(categoria=categoria_db))
    else:
        logger.info(f"⚡ [Caché] Leyendo la categoría '{categoria_db}' directamente desde la RAM.")
        
    productos_existentes = CACHE_PRODUCTOS_BD[categoria_db]
    
    # 2. LISTAS PARA EL BULK (Operaciones Masivas)
    nuevos_productos_a_crear = []  # Lista de tuplas: (Producto, precio, link)
    ofertas_a_actualizar = []      # Lista de objetos Oferta
    ofertas_a_crear = []           # Lista de objetos Oferta
    
    # Pre-cargamos las ofertas existentes de esta tienda en un diccionario para acceso instantáneo (O(1))
    ofertas_existentes_dict = {
        oferta.producto_id: oferta 
        for oferta in Oferta.objects.filter(tienda=tienda_db, producto__categoria=categoria_db)
    }

    # 3. PROCESAMIENTO EN MEMORIA (Fuera de la base de datos)
    for item in productos_extraidos:
        try:
            nombre_original = item['nombre'].strip().replace('"', '').replace("'", "")
            precio_float = limpiar_precio(item['precio'])
            
            if precio_float <= 0:
                continue

            datos_comparar = limpiar_nombre_producto(nombre_original)
            nombre_para_comparar = datos_comparar['texto_limpio']
            modelo_para_comparar = datos_comparar['modelo_clave']
            
            producto_asociado = None
            mejor_score = 0
            
            candidatos_dudosos = []
            
            for prod_bd in productos_existentes:
                datos_bd = limpiar_nombre_producto(prod_bd.nombre)
                nombre_bd_limpio = datos_bd['texto_limpio']
                modelo_bd = datos_bd['modelo_clave']

                if modelo_para_comparar and modelo_bd:
                    if modelo_para_comparar != modelo_bd:
                        continue  # Rechazo instantáneo
                    else:
                        score = fuzz.token_set_ratio(nombre_para_comparar, nombre_bd_limpio)
                        if score == 100:
                            mejor_score = score
                            producto_asociado = prod_bd
                            break

                score = fuzz.token_set_ratio(nombre_para_comparar, nombre_bd_limpio)
                if score == 100:
                    mejor_score = score
                    producto_asociado = prod_bd
                    break

                if score > UMBRAL_SIMILITUD:
                    if score > mejor_score:
                        mejor_score = score
                        producto_asociado = prod_bd
                elif score > 60:
                    candidatos_dudosos.append(prod_bd)

            if not producto_asociado and candidatos_dudosos:
                candidatos_top = candidatos_dudosos[:5]
                nombres_candidatos = [c.nombre for c in candidatos_top]
                
                # 1. Comprobar si ya existe la decisión en la BD para evitar llamar a la IA
                decisiones_guardadas = DecisionIA.objects.filter(
                    nombre_tienda=nombre_original,
                    nombre_candidato_db__in=nombres_candidatos
                )
                
                # 2. Diccionario para acceso rápido O(1)
                cache_decisiones = {d.nombre_candidato_db: d.es_mismo_producto for d in decisiones_guardadas}
                
                candidatos_para_ia = []
                indices_para_ia = []
                resultados_finales = [False] * len(nombres_candidatos)
                
                for idx, nombre_cand in enumerate(nombres_candidatos):
                    if nombre_cand in cache_decisiones:
                        # Usamos el valor guardado en BD
                        resultados_finales[idx] = cache_decisiones[nombre_cand]
                    else:
                        # Requiere consulta a Llama 3
                        candidatos_para_ia.append(nombre_cand)
                        indices_para_ia.append(idx)
                
                # 3. Llamar a Ollama solo para los nuevos
                if candidatos_para_ia:
                    resultados_ia = evaluar_productos_ia_sync(nombre_original, candidatos_para_ia)

                    decisiones_a_guardar = []
                    for i, resultado in enumerate(resultados_ia):
                        idx_original = indices_para_ia[i]
                        resultados_finales[idx_original] = resultado

                        decisiones_a_guardar.append(DecisionIA(
                            nombre_tienda=nombre_original,
                            nombre_candidato_db=candidatos_para_ia[i],
                            es_mismo_producto=resultado
                        ))

                    # 4. Guardar masivamente en BD (usando ignore_conflicts por si hay repetidos)
                    if decisiones_a_guardar:
                        DecisionIA.objects.bulk_create(decisiones_a_guardar, ignore_conflicts=True)
                
                # 5. Asignar producto si hubo coincidencia en Caché o en IA
                for idx, es_match in enumerate(resultados_finales):
                    if es_match:
                        producto_asociado = candidatos_top[idx]
                        break

            # --- DECISIÓN: CREAR O ACTUALIZAR ---
            if not producto_asociado:
                nuevo_prod = Producto(
                    nombre=nombre_original,
                    tipo=tipo_db,
                    categoria=categoria_db,
                    descripcion=item.get('link', ''),
                )
                
                # --- NUEVO: DESCARGAR Y GUARDAR IMAGEN ---
                url_imagen = item.get('imagen')
                if url_imagen and url_imagen.startswith('http'):
                    try:
                        # Hacer la petición GET a la imagen
                        headers_img = obtener_perfil_navegador()['headers']
                        respuesta_img = requests.get(url_imagen, headers=headers_img, timeout=5)
                        
                        if respuesta_img.status_code == 200:
                            # Extraer la extensión original (jpg, png, webp)
                            parsed_url = urlparse(url_imagen)
                            nombre_archivo = os.path.basename(parsed_url.path)
                            if not nombre_archivo or '.' not in nombre_archivo:
                                nombre_archivo = "imagen_producto.jpg"
                                
                            # Guardar en el ImageField usando ContentFile
                            nuevo_prod.imagen.save(nombre_archivo, ContentFile(respuesta_img.content), save=False)
                    except Exception as e:
                        # Fallo silencioso para no parar el crawler si la imagen no carga
                        pass

                nuevos_productos_a_crear.append((nuevo_prod, precio_float, item.get('link', '')))
                productos_existentes.append(nuevo_prod)  # Actualiza la caché en vivo
            else:
                if producto_asociado.id and producto_asociado.id in ofertas_existentes_dict:
                    oferta_existente = ofertas_existentes_dict[producto_asociado.id]
                    if oferta_existente.precio_base != precio_float or oferta_existente.enlace_compra != item.get('link', ''):
                        oferta_existente.precio_base = precio_float
                        oferta_existente.enlace_compra = item.get('link', '')
                        oferta_existente.fecha_actualizacion = timezone.now()
                        ofertas_a_actualizar.append(oferta_existente)
                else:
                    nueva_oferta = Oferta(
                        producto=producto_asociado,
                        tienda=tienda_db,
                        precio_base=precio_float,
                        enlace_compra=item.get('link', '')
                    )
                    ofertas_a_crear.append(nueva_oferta)
                    
            productos_guardados_exitosamente += 1
            
        except Exception as e:
            logger.warning(f"⚠️ Error procesando item: {e}")
            continue

    # 4. TRANSACCIÓN MASIVA FINAL (Solo entra a SQLite 1 vez)
    with transaction.atomic():
        # A) Crear Productos Nuevos
        if nuevos_productos_a_crear:
            productos_solo = [p[0] for p in nuevos_productos_a_crear]
            # bulk_create devuelve los objetos con sus IDs en SQLite (Django > 2.2)
            productos_creados = Producto.objects.bulk_create(productos_solo, batch_size=500)
            
            nuevas_ofertas_masivas = []
            for i, prod_creado in enumerate(productos_creados):
                _, precio, link = nuevos_productos_a_crear[i]
                nuevas_ofertas_masivas.append(Oferta(
                    producto=prod_creado,
                    tienda=tienda_db,
                    precio_base=precio,
                    enlace_compra=link
                ))
            Oferta.objects.bulk_create(nuevas_ofertas_masivas, batch_size=500)

        # B) Crear Ofertas Nuevas (para productos que ya existían pero no estaban en esta tienda)
        if ofertas_a_crear:
            # Filtramos aquellas ofertas que tienen un producto sin ID (por un edge case de la caché asíncrona)
            ofertas_a_crear_validas = [o for o in ofertas_a_crear if o.producto.id is not None]
            Oferta.objects.bulk_create(ofertas_a_crear_validas, batch_size=500)

        # C) Actualizar Ofertas Existentes
        if ofertas_a_actualizar:
            Oferta.objects.bulk_update(
                ofertas_a_actualizar, 
                ['precio_base', 'enlace_compra', 'fecha_actualizacion'], 
                batch_size=500
            )

    return productos_guardados_exitosamente
