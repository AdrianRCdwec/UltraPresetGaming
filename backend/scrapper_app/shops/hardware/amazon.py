# backend/scrapper_app/shops/hardware/amazon.py

import os
import time
import hashlib
import hmac
import json
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
from django.db import transaction
from django.utils import timezone as django_timezone

from api.models import Producto, Tienda, Oferta
from .base_scraper import BaseScraper
from .factory import ScraperFactory
from scrapper_app.utils.logger import logger
from scrapper_app.utils.db_manager import (
    limpiar_precio,
    limpiar_nombre_producto,
    CACHE_PRODUCTOS_BD,
    REGEX_SIMILARITY_THRESHOLD,
    HIGH_SIMILARITY_THRESHOLD,
)
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Cargamos las credenciales del archivo de entorno de Amazon
load_dotenv(os.path.join(os.path.dirname(__file__), "../../../../.passwords/amazon.env"))

AMAZON_ENABLED       = os.getenv("AMAZON_ENABLED", "false").lower() == "true"
AMAZON_ACCESS_KEY    = os.getenv("AMAZON_ACCESS_KEY", "")
AMAZON_SECRET_KEY    = os.getenv("AMAZON_SECRET_KEY", "")
AMAZON_ASSOCIATE_TAG = os.getenv("AMAZON_ASSOCIATE_TAG", "")
AMAZON_HOST          = os.getenv("AMAZON_HOST", "webservices.amazon.es")
AMAZON_REGION        = os.getenv("AMAZON_REGION", "eu-west-1")
AMAZON_PARTNER_TYPE  = os.getenv("AMAZON_PARTNER_TYPE", "Associates")
AMAZON_MARKETPLACE   = os.getenv("AMAZON_MARKETPLACE", "www.amazon.es")

# -------------------------------------------------------------------
# UTILIDADES: AWS Signature V4
# Necesaria porque la PA API no acepta llamadas sin firmar correctamente
# -------------------------------------------------------------------

def _sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

def _get_signature_key(secret_key: str, date_stamp: str) -> bytes:
    k_date    = _sign(("AWS4" + secret_key).encode("utf-8"), date_stamp)
    k_region  = _sign(k_date, AMAZON_REGION)
    k_service = _sign(k_region, "ProductAdvertisingAPI")
    k_signing = _sign(k_service, "aws4_request")
    return k_signing

def _build_headers(payload: dict) -> dict:
    """
    Construye los headers firmados con AWS Signature V4.
    La PA API 5.0 exige este mecanismo de autenticación en cada llamada.
    Sin él, Amazon devuelve un error 403 (Forbidden).
    """
    now = datetime.now(timezone.utc)
    amzdate    = now.strftime("%Y%m%dT%H%M%SZ")
    datestamp  = now.strftime("%Y%m%d")

    payload_str    = json.dumps(payload, separators=(",", ":"))
    payload_hash   = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

    canonical_headers = (
        f"content-encoding:amz-1.0\n"
        f"content-type:application/json; charset=utf-8\n"
        f"host:{AMAZON_HOST}\n"
        f"x-amz-date:{amzdate}\n"
        f"x-amz-target:com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems\n"
    )
    signed_headers = "content-encoding;content-type;host;x-amz-date;x-amz-target"

    canonical_request = "\n".join([
        "POST",
        "/paapi5/searchitems",
        "",
        canonical_headers,
        signed_headers,
        payload_hash,
    ])

    credential_scope = f"{datestamp}/{AMAZON_REGION}/ProductAdvertisingAPI/aws4_request"
    string_to_sign = "\n".join([
        "AWS4-HMAC-SHA256",
        amzdate,
        credential_scope,
        hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
    ])

    signing_key = _get_signature_key(AMAZON_SECRET_KEY, datestamp)
    signature   = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    authorization_header = (
        f"AWS4-HMAC-SHA256 Credential={AMAZON_ACCESS_KEY}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    return {
        "content-encoding":  "amz-1.0",
        "content-type":      "application/json; charset=utf-8",
        "host":              AMAZON_HOST,
        "x-amz-date":        amzdate,
        "x-amz-target":      "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems",
        "Authorization":     authorization_header,
    }


# -------------------------------------------------------------------
# CLASE PRINCIPAL
# -------------------------------------------------------------------

class AmazonScraper(BaseScraper):
    """
    Scraper para Amazon ES usando la Product Advertising API 5.0.
    A diferencia del resto de scrapers, no usa Playwright ni descarga imágenes:
    las URLs de imagen de Amazon son oficiales y permanentes, así que se
    guardan directamente en el campo imagen_url del modelo Producto.
    """

    # Mapeo: categoría DB → keywords de búsqueda en Amazon
    CATEGORIAS = {
        "CPU":  "procesador intel amd",
        "MB":   "placa base motherboard",
        "RAM":  "memoria ram ddr4 ddr5",
        "CASE": "caja torre pc",
        "AIR":  "disipador cpu ventilador",
        "LIQ":  "refrigeración líquida aio",
        "GPU":  "tarjeta gráfica nvidia amd",
        "PSU":  "fuente alimentación pc",
        "SSD":  "disco ssd nvme",
        "MON":  "monitor gaming",
    }

    def iniciar_navegador(self):
        # Amazon no requiere navegador, la API es REST pura.
        # Este método existe para mantener compatibilidad con BaseScraper.
        pass

    def cerrar_navegador(self):
        # Igual que iniciar_navegador: no hay nada que cerrar.
        pass

    def _buscar_items(self, keywords: str, pagina: int = 1) -> list:
        """
        Llama al endpoint SearchItems de la PA API 5.0.
        Devuelve una lista de items tal como los devuelve Amazon.
        La API permite un máximo de 10 páginas y 10 resultados por página.
        """
        payload = {
            "Keywords":       keywords,
            "Resources": [
                "ItemInfo.Title",
                "Offers.Listings.Price",
                "Images.Primary.Large",
            ],
            "SearchIndex":    "Electronics",
            "ItemCount":      10,
            "ItemPage":       pagina,
            "PartnerTag":     AMAZON_ASSOCIATE_TAG,
            "PartnerType":    AMAZON_PARTNER_TYPE,
            "Marketplace":    AMAZON_MARKETPLACE,
        }

        headers = _build_headers(payload)
        url     = f"https://{AMAZON_HOST}/paapi5/searchitems"

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("SearchResult", {}).get("Items", [])
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ [Amazon] Error HTTP {response.status_code}: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ [Amazon] Error inesperado en la llamada a la API: {e}")
            return []

    def _normalizar_item(self, item: dict) -> dict | None:
        """
        Convierte un item bruto de la PA API al formato estándar que usa
        guardar_amazon_en_db, equivalente al item['nombre'], item['precio'],
        item['imagen'] que usa el resto de scrapers pero con imagen_url en vez de imagen.
        """
        try:
            nombre = item["ItemInfo"]["Title"]["DisplayValue"]
            precio_raw = (
                item.get("Offers", {})
                    .get("Listings", [{}])[0]
                    .get("Price", {})
                    .get("Amount", 0)
            )
            imagen_url = (
                item.get("Images", {})
                    .get("Primary", {})
                    .get("Large", {})
                    .get("URL", "")
            )
            enlace = item.get("DetailPageURL", "")

            if not nombre or not precio_raw or precio_raw <= 0:
                return None

            return {
                "nombre":     nombre,
                "precio":     precio_raw,    # Ya viene como float desde la API
                "imagen_url": imagen_url,    # URL autorizada por Amazon, no descargamos
                "link":       enlace,
            }
        except (KeyError, IndexError):
            return None

    def escanear_catalogo(self, url_catalogo_base, categoria_db, tipo_db, excluir_palabras=None):
        """
        Método principal. url_catalogo_base se ignora (Amazon no funciona por URL
        de catálogo sino por keywords), pero se mantiene la firma de BaseScraper
        para ser compatible con ScraperFactory y main_crawler.py.
        """
        if not AMAZON_ENABLED:
            logger.warning("⚠️  [Amazon] Integración desactivada (AMAZON_ENABLED=false). Saltando.")
            return 0

        keywords = self.CATEGORIAS.get(categoria_db)
        if not keywords:
            logger.warning(f"⚠️  [Amazon] No hay keywords configuradas para la categoría {categoria_db}.")
            return 0

        logger.info(f"\n🛒 [Amazon] Buscando '{keywords}' (categoría: {categoria_db})...")

        todos_los_items = []
        for pagina in range(1, 4):  # Máximo 3 páginas = 30 productos por categoría
            items = self._buscar_items(keywords, pagina=pagina)
            if not items:
                break
            todos_los_items.extend(items)
            time.sleep(1)  # Respetamos el rate limit de la PA API (1 req/seg)

        productos_normalizados = [
            normalizado for item in todos_los_items
            if (normalizado := self._normalizar_item(item)) is not None
        ]

        if excluir_palabras:
            productos_normalizados = [
                p for p in productos_normalizados
                if not any(pal in p["nombre"].lower() for pal in excluir_palabras)
            ]

        logger.info(f"  ✅ {len(productos_normalizados)} productos válidos obtenidos de Amazon.")

        return self._guardar_amazon_en_db(
            productos=productos_normalizados,
            categoria_db=categoria_db,
            tipo_db=tipo_db,
        )

    def extraer_productos_de_pagina(self, page):
        # No aplica para Amazon (sin Playwright). Existe solo por contrato de BaseScraper.
        return []

    def _guardar_amazon_en_db(self, productos: list, categoria_db: str, tipo_db: str) -> int:
        """
        Versión adaptada de guardar_productos_en_db para Amazon.
        La diferencia clave con el método genérico es que usa imagen_url (URLField)
        en lugar de imagen (ImageField), porque Amazon nos da URLs autorizadas y
        no tiene sentido descargar ni alojar esas imágenes nosotros mismos.
        """
        if not productos:
            return 0

        tienda_db, _ = Tienda.objects.get_or_create(
            nombre="Amazon",
            defaults={"url_base": "https://www.amazon.es"}
        )

        if categoria_db not in CACHE_PRODUCTOS_BD:
            CACHE_PRODUCTOS_BD[categoria_db] = list(Producto.objects.filter(categoria=categoria_db))

        productos_existentes   = CACHE_PRODUCTOS_BD[categoria_db]
        nombres_bd_limpios     = [limpiar_nombre_producto(p.nombre)["texto_limpio"] for p in productos_existentes]
        modelos_bd             = [limpiar_nombre_producto(p.nombre)["modelo_clave"]  for p in productos_existentes]

        vectorizer      = None
        tfidf_matrix_bd = None
        if nombres_bd_limpios:
            vectorizer      = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5))
            tfidf_matrix_bd = vectorizer.fit_transform(nombres_bd_limpios)

        nuevos_productos_a_crear = []
        ofertas_a_actualizar     = []
        ofertas_a_crear          = []
        guardados                = 0

        ofertas_existentes_dict = {
            oferta.producto_id: oferta
            for oferta in Oferta.objects.filter(tienda=tienda_db, producto__categoria=categoria_db)
        }

        for item in productos:
            try:
                nombre_original = item["nombre"].strip().replace('"', "").replace("'", "")
                precio_float    = float(item["precio"])
                imagen_url      = item.get("imagen_url", "")
                link            = item.get("link", "")

                if precio_float <= 0:
                    continue

                datos_comparar = limpiar_nombre_producto(nombre_original)
                texto_limpio   = datos_comparar["texto_limpio"]
                modelo_clave   = datos_comparar["modelo_clave"]

                producto_asociado = None

                # Búsqueda por modelo clave exacto (nivel 1)
                if modelo_clave:
                    for prod_bd, mod_bd in zip(productos_existentes, modelos_bd):
                        if mod_bd and mod_bd == modelo_clave:
                            producto_asociado = prod_bd
                            break

                # Búsqueda TF-IDF (nivel 2)
                if not producto_asociado and vectorizer and tfidf_matrix_bd is not None:
                    vec_nuevo   = vectorizer.transform([texto_limpio])
                    similitudes = cosine_similarity(vec_nuevo, tfidf_matrix_bd).flatten()
                    mejor_idx   = int(np.argmax(similitudes))
                    mejor_sim   = float(similitudes[mejor_idx]) * 100

                    if mejor_sim >= HIGH_SIMILARITY_THRESHOLD:
                        producto_asociado = productos_existentes[mejor_idx]

                if not producto_asociado:
                    # Producto nuevo: lo creamos con imagen_url en lugar de imagen
                    nuevo = Producto(
                        nombre=nombre_original,
                        tipo=tipo_db,
                        categoria=categoria_db,
                        imagen_url=imagen_url if imagen_url else None,
                    )
                    nuevos_productos_a_crear.append((nuevo, precio_float, link))
                    productos_existentes.append(nuevo)
                else:
                    # Producto existente: actualizamos imagen_url si no tiene ninguna
                    if imagen_url and not producto_asociado.imagen_url:
                        producto_asociado.imagen_url = imagen_url
                        producto_asociado.save(update_fields=["imagen_url"])

                    if producto_asociado.id in ofertas_existentes_dict:
                        oferta = ofertas_existentes_dict[producto_asociado.id]
                        if oferta.precio_base != precio_float or oferta.enlace_compra != link:
                            oferta.precio_base         = precio_float
                            oferta.enlace_compra       = link
                            oferta.fecha_actualizacion = django_timezone.now()
                            ofertas_a_actualizar.append(oferta)
                    else:
                        ofertas_a_crear.append(Oferta(
                            producto=producto_asociado,
                            tienda=tienda_db,
                            precio_base=precio_float,
                            enlace_compra=link,
                        ))

                guardados += 1

            except Exception as e:
                logger.warning(f"⚠️ [Amazon] Error procesando item: {e}")
                continue

        with transaction.atomic():
            if nuevos_productos_a_crear:
                solo_productos = [p[0] for p in nuevos_productos_a_crear]
                creados = Producto.objects.bulk_create(solo_productos, batch_size=500)
                Oferta.objects.bulk_create([
                    Oferta(producto=creado, tienda=tienda_db, precio_base=precio, enlace_compra=link)
                    for creado, (_, precio, link) in zip(creados, nuevos_productos_a_crear)
                ], batch_size=500)

            if ofertas_a_crear:
                Oferta.objects.bulk_create(
                    [o for o in ofertas_a_crear if o.producto.id],
                    batch_size=500
                )

            if ofertas_a_actualizar:
                Oferta.objects.bulk_update(
                    ofertas_a_actualizar,
                    ["precio_base", "enlace_compra", "fecha_actualizacion"],
                    batch_size=500
                )

        logger.info(f"💾 [Amazon] {guardados} productos guardados/actualizados en BD.")
        return guardados


# Registramos el scraper en la Fábrica, igual que el resto de tiendas
ScraperFactory.registrar_scraper("amazon", AmazonScraper)