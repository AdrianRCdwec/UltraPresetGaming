import random, re
from fake_useragent import UserAgent
from scrapper_app.utils.logger import logger

# --- CONFIGURACIÓN DE TRACKERS ---
TRACKERS_Y_ADS = [
    'google-analytics',
    'googletagmanager',
    'googleadservices',
    'doubleclick',
    'facebook.com/tr',
    'connect.facebook.net',
    'clarity.ms',
    'hotjar',
    'criteo',
    'adzerk',
    'analytics',
    'tracking'
]

# --- CONFIGURACIÓN PARA MAYOR VELOCIDAD ---
def bloquear_recursos_innecesarios(route):
    """Bloquea imágenes/CSS y aborta peticiones a servicios de analíticas y ads"""
    peticion = route.request
    tipo = peticion.resource_type
    url = peticion.url.lower()

    # 1. Bloquear por tipo de recurso (lo que ya tenías + ping/beacon que usan los trackers)
    if tipo in ['stylesheet', 'font', 'media', 'ping', 'beacon', 'csp_report']:
        route.abort()
        return

    # 2. Bloquear por coincidencia en la URL (Trackers y Ads)
    if any(tracker in url for tracker in TRACKERS_Y_ADS):
        route.abort()
        return

    # Si pasa los filtros, dejamos que la petición continúe
    route.continue_()

# Obtener un User-Agent aleatorio
def obtener_perfil_navegador():
    """
    Obtiene un User-Agent aleatorio consumiendo un listado vivo,
    y genera los headers de Client-Hints (Sec-Ch-Ua) obligatorios para Cloudflare.
    """
    # 1. Consumimos los datos para obtener un UA muy reciente (Chrome/Edge en Windows/Mac)
    # min_percentage=1.0 asegura que solo nos dé navegadores muy populares hoy en día
    ua = UserAgent(os=['windows', 'macos'], browsers=['chrome', 'edge'], min_percentage=1.0)
    random_ua = ua.random

    # 2. Extraer el nombre del navegador y la versión mayor (ej: "124" de "Chrome/124.0.0.0")
    match_version = re.search(r'(Chrome|Edg)/(\d+)\.', random_ua)
    
    if match_version:
        navegador = match_version.group(1)
        version = match_version.group(2)
        
        # 3. Construir los Client Hints dinámicos y coherentes
        if navegador == 'Chrome':
            sec_ch_ua = f'"Chromium";v="{version}", "Google Chrome";v="{version}", "Not-A.Brand";v="99"'
        else: # Edge
            sec_ch_ua = f'"Chromium";v="{version}", "Microsoft Edge";v="{version}", "Not-A.Brand";v="99"'
            
        plataforma = '"Windows"' if 'Windows' in random_ua else '"macOS"'
        
        headers = {
            "Sec-Ch-Ua": sec_ch_ua,
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": plataforma,
            "Upgrade-Insecure-Requests": "1"
        }
    else:
        # Fallback de seguridad ultra-robusto por si toca un string atípico
        headers = {
            "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Upgrade-Insecure-Requests": "1"
        }
        
    return {
        "user_agent": random_ua,
        "headers": headers
    }

# Resolvemos posibles Captchas
def resolver_captcha_cloudflare(page):
    try:
        # 1. Detectar si estamos en la pantalla de Cloudflare
        # Cloudflare suele inyectar un iframe o un div con id="cf-turnstile" o similar
        # También el título de la página suele ser "Just a moment..."
        
        titulo = page.title()
        if "Just a moment" not in titulo and not page.locator('#cf-please-wait').is_visible(timeout=1000):
            return True # No hay captcha, todo en orden
            
        logger.info("🛡️ [Anti-Bot] Detectado desafío Cloudflare Turnstile. Intentando resolver...")
        
        # 2. Esperar a que el widget interactivo cargue completamente (hasta 10s)
        checkbox = page.locator('input[type="checkbox"], #cf-stage iframe, .ctp-checkbox-label').first
        
        if checkbox.is_visible(timeout=10000):
            # 3. Simular comportamiento humano (movimiento del ratón previo)
            box = checkbox.bounding_box()
            if box:
                # Mover el ratón desde una posición aleatoria hacia el centro del botón
                x_inicio = random.randint(100, 800)
                y_inicio = random.randint(100, 600)
                page.mouse.move(x_inicio, y_inicio)
                page.wait_for_timeout(random.uniform(500, 1500))
                
                # Mover al centro del checkbox
                x_centro = box['x'] + box['width'] / 2
                y_centro = box['y'] + box['height'] / 2
                
                # steps=10 hace que el ratón no se teletransporte, sino que se deslice en 10 pasos
                page.mouse.move(x_centro, y_centro, steps=10)
                page.wait_for_timeout(random.uniform(300, 800))
                
                # Hacer clic
                page.mouse.click(x_centro, y_centro, delay=random.uniform(50, 150))
                logger.info("🖱️ [Anti-Bot] Clic humano simulado en Turnstile.")
        
        # 4. Esperar a que el título cambie o el elemento de Cloudflare desaparezca (hasta 15s)
        # Si resolvemos el captcha, Cloudflare nos redirige a la web real.
        page.wait_for_function('document.title !== "Just a moment..."', timeout=15000)
        logger.info("✅ [Anti-Bot] Desafío superado. Entrando a la web...")
        return True
        
    except Exception as e:
        logger.error(f"❌ [Anti-Bot] Imposible resolver Cloudflare. El scraper podría fallar: {e}")
        return False

# SCROLL HUMANO AVANZADO
def scroll_humano_avanzado(page, repeticiones=5, max_y=1500):
    """
    Simula a un humano haciendo scroll por una tienda:
    - Distancias de scroll irregulares.
    - Tiempos de pausa caóticos entre "ruedazos".
    - Movimientos parásitos del ratón mientras lee.
    """
    for _ in range(repeticiones):
        # 1. Scroll aleatorio: el humano a veces gira mucho la rueda, a veces poco
        distancia_scroll = random.randint(300, max_y)
        page.mouse.wheel(0, distancia_scroll)
        
        # 2. Pausa de lectura biométrica (entre 0.3s y 1.2s como pedía tu requisito)
        tiempo_lectura = random.uniform(300, 1200)
        page.wait_for_timeout(tiempo_lectura)
        
        # 3. Comportamiento parásito: el 30% de las veces, el humano mueve el ratón sin motivo
        if random.random() < 0.3:
            x_origen = random.randint(100, 800)
            y_origen = random.randint(100, 600)
            x_destino = x_origen + random.randint(-200, 200)
            y_destino = y_origen + random.randint(-200, 200)
            
            # Movimiento curvo/suave simulado con pasos
            page.mouse.move(x_origen, y_origen)
            page.mouse.move(x_destino, y_destino, steps=random.randint(5, 15))

# --- CONFIGURACIÓN DE PROXY ---
USAR_PROXY = False  

# Datos
PROXY_SERVER = "http://gate.smartproxy.com:7000" 
PROXY_USERNAME = "tu_usuario"
PROXY_PASSWORD = "tu_password"

def obtener_configuracion_proxy():
    if not USAR_PROXY:
        return None
    return {
        "server": PROXY_SERVER,
        "username": PROXY_USERNAME,
        "password": PROXY_PASSWORD
    }