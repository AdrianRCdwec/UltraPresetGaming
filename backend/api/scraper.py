import requests
from bs4 import BeautifulSoup
import re

def obtener_precio_amazon(url):
    # Cabeceras mucho más completas para parecer un navegador real de Windows
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }
    
    try:
        # Añadimos un pequeño timeout y permitimos redirecciones
        respuesta = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        soup = BeautifulSoup(respuesta.content, 'html.parser')
        
        # Amazon es un poco puñetero, a veces pone el precio en un lado y a veces en otro
        precio_entero = soup.find('span', {'class': 'a-price-whole'})
        precio_decimal = soup.find('span', {'class': 'a-price-fraction'})
        
        # Segunda opción por si falla la primera (a veces Amazon usa otra clase)
        if not precio_entero:
            precio_alternativo = soup.find('span', {'class': 'a-offscreen'})
            if precio_alternativo:
                # Extraer solo los números del texto "190,50€"
                numeros = re.findall(r'\d+[,\.]?\d*', precio_alternativo.text)
                if numeros:
                    return float(numeros[0].replace(',', '.'))
            return None
            
        if precio_entero:
            entero = re.sub(r'[^\d]', '', precio_entero.text)
            decimal = re.sub(r'[^\d]', '', precio_decimal.text) if precio_decimal else "00"
            return float(f"{entero}.{decimal}")
            
    except Exception as e:
        print(f"Error en Amazon: {e}")
    return None

def obtener_precio_pccomponentes(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'es-ES,es;q=0.9',
    }
    
    try:
        respuesta = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(respuesta.content, 'html.parser')
        
        # En PcComponentes el precio suele estar en un div específico
        precio_elemento = soup.find('div', id='precio-main')
        if precio_elemento and 'data-price' in precio_elemento.attrs:
            return float(precio_elemento['data-price'])
            
        # Alternativa si cambia el diseño
        span_precio = soup.find('span', {'class': 'h3 m-0 font-weight-bold'})
        if span_precio:
            # Extraer número de "145,99€"
            numeros = re.findall(r'\d+[,\.]?\d*', span_precio.text)
            if numeros:
                return float(numeros[0].replace(',', '.'))
                
    except Exception as e:
        print(f"Error en PcComponentes: {e}")
    return None

def actualizar_precio_oferta(oferta):
    nuevo_precio = None
    url = oferta.enlace_compra.lower()
    
    if 'amazon' in url:
        nuevo_precio = obtener_precio_amazon(oferta.enlace_compra)
    elif 'pccomponentes' in url:
        nuevo_precio = obtener_precio_pccomponentes(oferta.enlace_compra)
        
    if nuevo_precio:
        oferta.precio_base = nuevo_precio
        oferta.save()
        return True
    return False
