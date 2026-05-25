import time
import requests

from scrapper_app.shops.videogames.base_scraper import BaseGameScraper
from scrapper_app.shops.videogames.factory import GameScraperFactory
from scrapper_app.utils.events import shutdown_event
from scrapper_app.utils.logger import logger

STORE_API = "https://store.steampowered.com/api"
SEARCH_API = "https://store.steampowered.com/api/storesearch"
STEAM_URL_BASE = "https://store.steampowered.com"

BUSQUEDAS = [
    ("accion", "VG_ACC"),
    ("aventura", "VG_AVE"),
    ("rpg", "VG_RPG"),
    ("estrategia", "VG_EST"),
    ("deportes", "VG_DEP"),
    ("simulacion", "VG_SIM"),
    ("terror", "VG_TER"),
    ("indie", "VG_IND"),
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9",
    "Accept": "application/json, text/plain, */*",
}


def _hacer_get(url: str, params: dict, timeout: int = 15):
    return requests.get(url, params=params, headers=HEADERS, timeout=timeout)


def _buscar_appids_por_termino(termino: str, max_resultados: int = 20) -> list[int]:
    try:
        resp = _hacer_get(
            SEARCH_API,
            {
                "term": termino,
                "l": "spanish",
                "cc": "ES",
                "count": max_resultados,
            },
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        return [item["id"] for item in items if item.get("id")]
    except Exception as e:
        logger.warning(f"⚠️ [Steam] Error buscando '{termino}': {e}")
        return []


def _obtener_detalle(appid: int) -> dict | None:
    try:
        resp = _hacer_get(
            f"{STORE_API}/appdetails",
            {
                "appids": appid,
                "cc": "es",
                "l": "spanish",
            },
        )
        resp.raise_for_status()

        bloque = resp.json().get(str(appid), {})
        if not bloque.get("success"):
            return None

        game = bloque.get("data", {})
        if not game:
            return None

        if game.get("type") != "game":
            return None

        nombre = (game.get("name") or "").strip()
        if not nombre:
            return None

        price_overview = game.get("price_overview")
        if price_overview and price_overview.get("final") is not None:
            precio = price_overview["final"] / 100
        elif game.get("is_free"):
            precio = 0.0
        else:
            return None

        return {
            "nombre": nombre,
            "precio": str(precio),
            "imagen": game.get("header_image", "") or "",
            "link": f"{STEAM_URL_BASE}/app/{appid}",
        }

    except Exception as e:
        logger.warning(f"⚠️ [Steam] Error obteniendo detalle de appid {appid}: {e}")
        return None


class SteamScraper(BaseGameScraper):
    def scrape(self) -> list[dict]:
        logger.info("🎮 [Steam] Iniciando recolección de videojuegos...")
        juegos = []
        appids_vistos = set()

        for termino, categoria in BUSQUEDAS:
            if shutdown_event.is_set():
                logger.warning("🛑 [Steam] Apagado seguro detectado antes de una nueva categoría.")
                break

            logger.info(f"🔎 [Steam] Buscando juegos para '{termino}' ({categoria})...")
            appids = _buscar_appids_por_termino(termino, max_resultados=20)

            if not appids:
                logger.warning(f"⚠️ [Steam] Sin resultados para '{termino}'.")
                continue

            añadidos_categoria = 0

            for appid in appids:
                if shutdown_event.is_set():
                    logger.warning("🛑 [Steam] Apagado seguro detectado durante la obtención de detalles.")
                    return juegos

                if appid in appids_vistos:
                    continue

                appids_vistos.add(appid)

                detalle = _obtener_detalle(appid)
                if not detalle:
                    time.sleep(0.7)
                    continue

                detalle["categoria"] = categoria
                juegos.append(detalle)
                añadidos_categoria += 1

                logger.info(
                    f"✅ [Steam] Juego obtenido: {detalle['nombre']} | {detalle['precio']}€ | {categoria}"
                )

                time.sleep(0.7)

            logger.info(f"📦 [Steam] Categoría {categoria}: {añadidos_categoria} juegos preparados.")

        logger.info(f"💾 [Steam] Total de juegos obtenidos: {len(juegos)}")
        return juegos


GameScraperFactory.registrar_scraper("steam", SteamScraper)