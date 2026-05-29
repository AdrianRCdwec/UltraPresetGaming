import sys, os, concurrent.futures, psutil, signal, threading
from scrapper_app.utils.logger import logger

# CONFIGURACIÓN DE DJANGO
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comparador.settings')
import django
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

# 2. Importar utilidades y modelos
from api.models import Producto
from scrapper_app.utils.db_manager import desactivar_ofertas_obsoletas, CACHE_PRODUCTOS_BD
from scrapper_app.shops.hardware.factory import ScraperFactory
from scrapper_app.shops.videogames.factory import GameScraperFactory
from scrapper_app.utils.events import shutdown_event
from scrapper_app.utils.db_manager import guardar_productos_en_db
from collections import defaultdict

# 3. Importar las tiendas para que se auto-registren en la Fábrica
import scrapper_app.shops.hardware.pccomponentes
import scrapper_app.shops.hardware.coolmod
import scrapper_app.shops.hardware.lifeinformatica
import scrapper_app.shops.hardware.alternate
import scrapper_app.shops.hardware.neobyte
# import scrapper_app.shops.hardware.amazon
import scrapper_app.shops.videogames.steam

# ==========================================================
# CONFIGURACIÓN DE EJECUCIÓN
# ==========================================================
MODO_DEBUG = os.getenv("SCRAPER_DEBUG", "false").lower() == "true"
EJECUCION_SECUENCIAL = os.getenv("SCRAPER_SECUENCIAL", "false").lower() == "true"

# --- MANEJADOR DE SEÑALES (Ctrl+C o SIGTERM) ---
def signal_handler(sig, frame):
    if not shutdown_event.is_set():
        logger.warning("\n⚠️  [GRACEFUL SHUTDOWN] Señal de interrupción recibida (Ctrl+C).")
        logger.warning("Deteniendo nuevos escaneos. Esperando a que los hilos actuales guarden en BD y cierren Playwright...")
        shutdown_event.set()
    else:
        logger.error("\n❌ [FORCED KILL] Segunda señal recibida. Forzando apagado...")
        sys.exit(1)

# Registramos las señales (Windows soporta SIGINT, Linux SIGINT y SIGTERM)
signal.signal(signal.SIGINT, signal_handler)
if os.name != 'nt':
    signal.signal(signal.SIGTERM, signal_handler)

# --- CONFIGURACIÓN PARA OPTIMIZAR EL RENDIMIENTO ---
def calcular_hilos_optimos():
    """Calcula el número ideal de max_workers para el ThreadPoolExecutor."""
    try:
        memoria_virtual = psutil.virtual_memory()
        ram_libre_gb = memoria_virtual.available / (1024 ** 3)
        nucleos_cpu = psutil.cpu_count(logical=False) or 2 

        ram_utilizable_gb = ram_libre_gb - 1.5
        if ram_utilizable_gb <= 0: return 1 

        hilos_por_ram = int(ram_utilizable_gb / 0.5)
        hilos_optimos = min(hilos_por_ram, nucleos_cpu, 5)
        
        return max(1, hilos_optimos)
    except Exception as e:
        logger.error(f"Error calculando hilos: {e}")
        return 2

# --- FUNCIONES DE ESCANEO PARA CADA TIENDA ---
def escanearPcComponentes():
    total_pcc = 0
    scraper = ScraperFactory.obtener_scraper("pccomponentes", debug=MODO_DEBUG)

    def escanear(url, cat, tipo, excluir=None):
        if shutdown_event.is_set(): return
        nonlocal total_pcc
        total = scraper.escanear_catalogo(url, cat, tipo, excluir_palabras=excluir)
        total_pcc += total
        logger.info(f"\n✅ [Procesadores] Se han guardado un total de {total} procesadores." if cat == 'CPU' else 
            f"\n✅ [Placas Base] Se han guardado un total de {total} placas base." if cat == 'MB' else
            f"\n✅ [Memorias RAM] Se han guardado un total de {total} memorias RAM." if cat == 'RAM' else
            f"\n✅ [Cajas PC] Se han guardado un total de {total} cajas de pc." if cat == 'CASE' else
            f"\n✅ [Refrigeración Aire] Se han guardado un total de {total} refrigeración de aire." if cat == 'AIR' else
            f"\n✅ [Refrigeración Líquida] Se han guardado un total de {total} refrigeraciones líquidas." if cat == 'LIQ' else
            f"\n✅ [Tarjetas Gráficas] Se han guardado un total de {total} tarjetas gráficas." if cat == 'GPU' else
            f"\n✅ [Fuentes de Alimentación] Se han guardado un total de {total} fuentes de alimentación." if cat == 'PSU' else
            f"\n✅ [Discos Duros] Se han guardado un total de {total} discos duros." if cat == 'SSD' else
            f"\n✅ [Monitores] Se han guardado un total de {total} monitores.")

    scraper.iniciar_navegador()

    try:
        escanear("https://www.pccomponentes.com/procesadores", 'CPU', 'HW')
        escanear("https://www.pccomponentes.com/placas-base", 'MB', 'HW')
        escanear("https://www.pccomponentes.com/memorias-ram", 'RAM', 'HW')
        escanear("https://www.pccomponentes.com/cajas-pc", 'CASE', 'HW')
        escanear("https://www.pccomponentes.com/ventiladores-cpu", 'AIR', 'HW')
        escanear("https://www.pccomponentes.com/refrigeracion-liquida/kit-refrigeracion-liquida", 'LIQ', 'HW')
        escanear("https://www.pccomponentes.com/tarjetas-graficas", 'GPU', 'HW')
        escanear("https://www.pccomponentes.com/fuentes-alimentacion", 'PSU', 'HW')
        escanear("https://www.pccomponentes.com/discos-duros", 'SSD', 'HW')
        escanear("https://www.pccomponentes.com/monitores", 'MON', 'HW')
    finally:
        scraper.cerrar_navegador()

    logger.info(f"\n✅ [PcComponentes FIN] Se han guardado un total de {total_pcc} productos.")
    return total_pcc


def escanearCoolmod():
    total_coolmod = 0
    scraper = ScraperFactory.obtener_scraper("coolmod", debug=MODO_DEBUG)

    def escanear(url, cat, tipo, excluir=None):
        if shutdown_event.is_set(): return
        nonlocal total_coolmod
        total = scraper.escanear_catalogo(url, cat, tipo, excluir_palabras=excluir)
        total_coolmod += total
        logger.info(f"\n✅ [Procesadores] Se han guardado un total de {total} procesadores." if cat == 'CPU' else 
            f"\n✅ [Placas Base] Se han guardado un total de {total} placas base." if cat == 'MB' else
            f"\n✅ [Memorias RAM] Se han guardado un total de {total} memorias RAM." if cat == 'RAM' else
            f"\n✅ [Cajas PC] Se han guardado un total de {total} cajas de pc." if cat == 'CASE' else
            f"\n✅ [Refrigeración Aire] Se han guardado un total de {total} refrigeración de aire." if cat == 'AIR' else
            f"\n✅ [Refrigeración Líquida] Se han guardado un total de {total} refrigeraciones líquidas." if cat == 'LIQ' else
            f"\n✅ [Tarjetas Gráficas] Se han guardado un total de {total} tarjetas gráficas." if cat == 'GPU' else
            f"\n✅ [Fuentes de Alimentación] Se han guardado un total de {total} fuentes de alimentación." if cat == 'PSU' else
            f"\n✅ [Discos Duros] Se han guardado un total de {total} discos duros." if cat == 'SSD' else
            f"\n✅ [Monitores] Se han guardado un total de {total} monitores.")

    scraper.iniciar_navegador()

    try:
        escanear("https://www.coolmod.com/componentes-pc-procesadores/", 'CPU', 'HW')
        escanear("https://www.coolmod.com/componentes-pc-placas-base/", 'MB', 'HW')
        escanear("https://www.coolmod.com/componentes-pc-memorias-ram/", 'RAM', 'HW')
        escanear("https://www.coolmod.com/componentes-pc-torres-cajas/", 'CASE', 'HW')
        escanear("https://www.coolmod.com/componentes-pc-disipadores-ventiladores/", 'AIR', 'HW', 
                excluir=[
                    '240', '280', '360', '420', 'refrigeracion liquida', 
                    'refrigeración líquida', 'líquida', 'liquida', 'aio', 'water'
                ])
        escanear("https://www.coolmod.com/refrigeracion-liquida-kits-liquida/", 'LIQ', 'HW')
        escanear("https://www.coolmod.com/tarjetas-graficas/", 'GPU', 'HW')
        escanear("https://www.coolmod.com/componentes-pc-fuentes-alimentacion/", 'PSU', 'HW')
        escanear("https://www.coolmod.com/componentes-pc-discos-duros/", 'SSD', 'HW')
        escanear("https://www.coolmod.com/perifericos-monitores/", 'MON', 'HW')
    finally:
        scraper.cerrar_navegador()

    logger.info(f"\n✅ [Coolmod FIN] Se han guardado un total de {total_coolmod} productos.")
    return total_coolmod


def escanearLifeInformatica():
    total_life = 0
    scraper = ScraperFactory.obtener_scraper("lifeinformatica", debug=MODO_DEBUG)

    def escanear(url, cat, tipo, excluir=None):
        if shutdown_event.is_set(): return
        nonlocal total_life
        total = scraper.escanear_catalogo(url, cat, tipo, excluir_palabras=excluir)
        total_life += total
        logger.info(f"\n✅ [Procesadores] Se han guardado un total de {total} procesadores." if cat == 'CPU' else 
            f"\n✅ [Placas Base] Se han guardado un total de {total} placas base." if cat == 'MB' else
            f"\n✅ [Memorias RAM] Se han guardado un total de {total} memorias RAM." if cat == 'RAM' else
            f"\n✅ [Cajas PC] Se han guardado un total de {total} cajas de pc." if cat == 'CASE' else
            f"\n✅ [Refrigeración Aire] Se han guardado un total de {total} refrigeración de aire." if cat == 'AIR' else
            f"\n✅ [Refrigeración Líquida] Se han guardado un total de {total} refrigeraciones líquidas." if cat == 'LIQ' else
            f"\n✅ [Tarjetas Gráficas] Se han guardado un total de {total} tarjetas gráficas." if cat == 'GPU' else
            f"\n✅ [Fuentes de Alimentación] Se han guardado un total de {total} fuentes de alimentación." if cat == 'PSU' else
            f"\n✅ [Discos Duros] Se han guardado un total de {total} discos duros." if cat == 'SSD' else
            f"\n✅ [Monitores] Se han guardado un total de {total} monitores.")

    scraper.iniciar_navegador()

    try:
        escanear("https://lifeinformatica.com/categoria-producto/componentes/procesadores/", 'CPU', 'HW')
        escanear("https://lifeinformatica.com/categoria-producto/componentes/placas-base/", 'MB', 'HW')
        escanear("https://lifeinformatica.com/categoria-producto/componentes/memorias-ram/", 'RAM', 'HW')
        escanear("https://lifeinformatica.com/categoria-producto/componentes/cajas-y-accesorios/cajas/", 'CASE', 'HW')
        escanear("https://lifeinformatica.com/categoria-producto/componentes/refrigeracion/disipadores-de-cpu/", 'AIR', 'HW', 
                excluir=[
                    '240', '280', '360', '420', 'refrigeracion liquida', 
                    'refrigeración líquida', 'líquida', 'liquida', 'aio', 'water'
                ])
        escanear("https://lifeinformatica.com/categoria-producto/componentes/refrigeracion/kits-de-refrigeracion-liquida/", 'LIQ', 'HW')
        escanear("https://lifeinformatica.com/categoria-producto/componentes/tarjetas-graficas/", 'GPU', 'HW')
        escanear("https://lifeinformatica.com/categoria-producto/componentes/fuentes-de-alimentacion-y-accesorios/fuentes-de-alimentacion/", 'PSU', 'HW')
        escanear("https://lifeinformatica.com/categoria-producto/componentes/discos-duros/", 'SSD', 'HW')
        escanear("https://lifeinformatica.com/categoria-producto/perifericos/monitores-y-accesorios/monitores/", 'MON', 'HW')
    finally:
        scraper.cerrar_navegador()

    logger.info(f"\n✅ [Life Informática FIN] Se han guardado un total de {total_life} productos.")
    return total_life


def escanearAlternate():
    total_alternate = 0
    scraper = ScraperFactory.obtener_scraper("alternate", debug=MODO_DEBUG)

    def escanear(url, cat, tipo, excluir=None):
        if shutdown_event.is_set(): return
        nonlocal total_alternate
        total = scraper.escanear_catalogo(url, cat, tipo, excluir_palabras=excluir)
        total_alternate += total
        logger.info(f"\n✅ [Procesadores] Se han guardado un total de {total} procesadores." if cat == 'CPU' else 
            f"\n✅ [Placas Base] Se han guardado un total de {total} placas base." if cat == 'MB' else
            f"\n✅ [Memorias RAM] Se han guardado un total de {total} memorias RAM." if cat == 'RAM' else
            f"\n✅ [Cajas PC] Se han guardado un total de {total} cajas de pc." if cat == 'CASE' else
            f"\n✅ [Refrigeración Aire] Se han guardado un total de {total} refrigeración de aire." if cat == 'AIR' else
            f"\n✅ [Refrigeración Líquida] Se han guardado un total de {total} refrigeraciones líquidas." if cat == 'LIQ' else
            f"\n✅ [Tarjetas Gráficas] Se han guardado un total de {total} tarjetas gráficas." if cat == 'GPU' else
            f"\n✅ [Fuentes de Alimentación] Se han guardado un total de {total} fuentes de alimentación." if cat == 'PSU' else
            f"\n✅ [Discos Duros] Se han guardado un total de {total} discos duros." if cat == 'SSD' else
            f"\n✅ [Monitores] Se han guardado un total de {total} monitores.")

    scraper.iniciar_navegador()

    try:
        escanear("https://www.alternate.es/Procesadores", 'CPU', 'HW')
        escanear("https://www.alternate.es/Placas-base", 'MB', 'HW')
        escanear("https://www.alternate.es/Memoria-RAM", 'RAM', 'HW')
        escanear("https://www.alternate.es/Cajas-de-PC", 'CASE', 'HW')
        escanear("https://www.alternate.es/Disipadores-de-CPU", 'AIR', 'HW', 
                excluir=[
                    '240', '280', '360', '420', 'refrigeracion liquida', 
                    'refrigeración líquida', 'líquida', 'liquida', 'aio', 'water'
                ])
        escanear("https://www.alternate.es/Refrigeraci%C3%B3n-l%C3%ADquida", 'LIQ', 'HW')
        escanear("https://www.alternate.es/Tarjetas-gr%C3%A1ficas", 'GPU', 'HW')
        escanear("https://www.alternate.es/Fuentes-de-alimentaci%C3%B3n", 'PSU', 'HW')
        escanear("https://www.alternate.es/SSD", 'SSD', 'HW')
        escanear("https://www.alternate.es/Monitores", 'MON', 'HW')
    finally:
        scraper.cerrar_navegador()

    logger.info(f"\n✅ [Alternate FIN] Se han guardado un total de {total_alternate} productos.")
    return total_alternate


def escanearNeoByte():
    total_neobyte = 0
    scraper = ScraperFactory.obtener_scraper("neobyte", debug=MODO_DEBUG)

    def escanear(url, cat, tipo, excluir=None):
        if shutdown_event.is_set(): return
        nonlocal total_neobyte
        total = scraper.escanear_catalogo(url, cat, tipo, excluir_palabras=excluir)
        total_neobyte += total
        logger.info(f"\n✅ [Procesadores] Se han guardado un total de {total} procesadores." if cat == 'CPU' else 
            f"\n✅ [Placas Base] Se han guardado un total de {total} placas base." if cat == 'MB' else
            f"\n✅ [Memorias RAM] Se han guardado un total de {total} memorias RAM." if cat == 'RAM' else
            f"\n✅ [Cajas PC] Se han guardado un total de {total} cajas de pc." if cat == 'CASE' else
            f"\n✅ [Refrigeración Aire] Se han guardado un total de {total} refrigeración de aire." if cat == 'AIR' else
            f"\n✅ [Refrigeración Líquida] Se han guardado un total de {total} refrigeraciones líquidas." if cat == 'LIQ' else
            f"\n✅ [Tarjetas Gráficas] Se han guardado un total de {total} tarjetas gráficas." if cat == 'GPU' else
            f"\n✅ [Fuentes de Alimentación] Se han guardado un total de {total} fuentes de alimentación." if cat == 'PSU' else
            f"\n✅ [Discos Duros] Se han guardado un total de {total} discos duros." if cat == 'SSD' else
            f"\n✅ [Monitores] Se han guardado un total de {total} monitores.")

    scraper.iniciar_navegador()
    
    try:
        escanear("https://www.neobyte.es/procesadores-107", 'CPU', 'HW')
        escanear("https://www.neobyte.es/placas-base-106", 'MB', 'HW')
        escanear("https://www.neobyte.es/memorias-ram-108", 'RAM', 'HW')
        escanear("https://www.neobyte.es/cajas-de-ordenador-112", 'CASE', 'HW')
        escanear("https://www.neobyte.es/ventiladores-cpu-138", 'AIR', 'HW', 
                excluir=[
                    '240', '280', '360', '420', 'refrigeracion liquida', 
                    'refrigeración líquida', 'líquida', 'liquida', 'aio', 'water'
                ])
        escanear("https://www.neobyte.es/refrigeracion-liquida-139", 'LIQ', 'HW')
        escanear("https://www.neobyte.es/tarjetas-graficas-111", 'GPU', 'HW')
        escanear("https://www.neobyte.es/fuentes-de-alimentacion-113", 'PSU', 'HW')
        escanear("https://www.neobyte.es/discos-duros-110", 'SSD', 'HW')
        escanear("https://www.neobyte.es/monitores-169", 'MON', 'HW')
    finally:
        scraper.cerrar_navegador()

    logger.info(f"\n✅ [NeoByte FIN] Se han guardado un total de {total_neobyte} productos.")
    return total_neobyte

# def escanearAmazon():

def escanearSteam():
    if shutdown_event.is_set():
        return 0

    logger.info("\n🎮 Iniciando escaneo de Steam...")
    scraper = GameScraperFactory.obtener_scraper("steam")
    juegos  = scraper.scrape()

    if not juegos:
        logger.warning("⚠️ [Steam] No se obtuvieron juegos.")
        return 0

    # Agrupamos por categoría y guardamos cada grupo
    por_categoria = defaultdict(list)
    for juego in juegos:
        por_categoria[juego["categoria"]].append(juego)

    total = 0
    for categoria, items in por_categoria.items():
        guardados = guardar_productos_en_db(
            productos_extraidos=items,
            nombre_tienda="Steam",
            url_base_tienda="https://store.steampowered.com",
            categoria_db=categoria,
            tipo_db="VG",
        )
        total += guardados
        logger.info(f"  ✅ [{categoria}] {guardados} juegos guardados.")

    logger.info(f"\n✅ [Steam FIN] Se han guardado un total de {total} juegos.")
    return total

# =================================================================
# INICIO DEL SCRIPT
# =================================================================
if __name__ == "__main__":
    logger.info("🚀 INICIANDO ESCANEO MASIVO...")
    logger.info("ℹ️  Puedes pulsar Ctrl+C en cualquier momento para un apagado seguro (Graceful Shutdown).")
    total_general = 0

    categorias_usadas = [
        'CPU', 'MB', 'RAM', 'CASE', 'AIR', 'LIQ', 'GPU', 'PSU', 'SSD', 'MON',
        'VG_ACC', 'VG_AVE', 'VG_RPG', 'VG_EST', 'VG_DEP', 'VG_SIM', 'VG_TER', 'VG_IND',
    ]

    logger.info("\n📚 Precargando productos de la BD en la memoria RAM para evitar bloqueos SQLite...")
    for cat in categorias_usadas:
        CACHE_PRODUCTOS_BD[cat] = list(Producto.objects.filter(categoria=cat))
    logger.info("✅ Caché cargada con éxito. Listo para lanzar los scrapers.\n")

    funciones_scrapers = [
        escanearPcComponentes,
        escanearCoolmod,
        escanearLifeInformatica,
        escanearAlternate,
        escanearNeoByte,
        # escanearAmazon,
        escanearSteam 
    ]

    try:
        if EJECUCION_SECUENCIAL:
            logger.warning("🐞 MODO DEBUG/SECUENCIAL ACTIVADO: las tiendas se ejecutarán una a una.")
            for func in funciones_scrapers:
                if shutdown_event.is_set():
                    break
                try:
                    resultado = func()
                    total_general += resultado
                    logger.info(f"✅ {func.__name__} ha terminado y sumado {resultado} productos.")
                except Exception as e:
                    logger.error(f"❌ Error crítico en {func.__name__}: {e}")
        else:
            hilos_dinamicos = calcular_hilos_optimos()
            logger.info(
                f"📊 HARDWARE DETECTADO: {psutil.virtual_memory().available / (1024**3):.1f} GB RAM libre. "
                f"Asignando {hilos_dinamicos} hilos concurrentes."
            )

            with concurrent.futures.ThreadPoolExecutor(max_workers=hilos_dinamicos) as executor:
                futuros = {executor.submit(func): func.__name__ for func in funciones_scrapers}

                for futuro in concurrent.futures.as_completed(futuros):
                    nombre_funcion = futuros[futuro]
                    try:
                        resultado = futuro.result()
                        total_general += resultado
                        logger.info(f"✅ {nombre_funcion} ha terminado y sumado {resultado} productos.")
                    except Exception as e:
                        logger.error(f"❌ Error crítico en {nombre_funcion}: {e}")

    except KeyboardInterrupt:
        pass
    finally:
        if shutdown_event.is_set():
            logger.warning(f"\n🛑 APAGADO SEGURO COMPLETADO. Se guardaron {total_general} productos antes de abortar.")
        else:
            logger.info(f"\n🎉 ¡TODAS LAS TIENDAS ESCANEADAS! UN TOTAL DE {total_general} PRODUCTOS GUARDADOS/ACTUALIZADOS.")

    if not shutdown_event.is_set():
        desactivar_ofertas_obsoletas()