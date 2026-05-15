import os
import json
import requests
from datetime import date
from backend.scrapper_app.shops.videogames.base_scraper import BaseGameScraper
from backend.scrapper_app.shops.videogames.factory import GameScraperFactory

LIMITE_DIARIO = 100_000
CONTADOR_PATH = os.path.join(os.path.dirname(__file__), "steam_request_counter.json")

# Ruta al archivo de contraseñas desde la raíz del proyecto
_PASSWORDS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..", ".passwords", "steamAPI"
)


def _leer_api_key() -> str:
    with open(_PASSWORDS_PATH, "r") as f:
        for line in f:
            if line.startswith("STEAM_API_KEY"):
                return line.split("=", 1)[1].strip()
    raise ValueError("No se encontró STEAM_API_KEY en .passwords/steamAPI")


def _leer_contador() -> dict:
    if os.path.exists(CONTADOR_PATH):
        with open(CONTADOR_PATH, "r") as f:
            return json.load(f)
    return {"fecha": str(date.today()), "contador": 0}


def _guardar_contador(data: dict):
    with open(CONTADOR_PATH, "w") as f:
        json.dump(data, f)


def _registrar_peticion() -> bool:
    data = _leer_contador()
    hoy = str(date.today())

    if data["fecha"] != hoy:
        data = {"fecha": hoy, "contador": 0}

    if data["contador"] >= LIMITE_DIARIO:
        return False

    data["contador"] += 1
    _guardar_contador(data)
    return True


class SteamScraper(BaseGameScraper):
    BASE_URL = "https://store.steampowered.com/api/"
    API_KEY = _leer_api_key()

    def scrape(self) -> list[dict]:
        scraped_games = []
        categories = {
            "featured": "VG_TEND",
            "coming_soon": "VG_RES",
            "specials": "VG_REC"
        }

        for category_name, category_type in categories.items():
            if not _registrar_peticion():
                print("Límite diario de peticiones a Steam alcanzado.")
                return scraped_games

            url = f"{self.BASE_URL}featuredcategories/?l=es&key={self.API_KEY}"
            try:
                response = requests.get(url)
                response.raise_for_status()
                data = response.json()

                if category_name in data and "items" in data[category_name]:
                    for item in data[category_name]["items"]:
                        app_id = item.get("id")
                        if not app_id:
                            continue

                        if not _registrar_peticion():
                            print("Límite diario de peticiones a Steam alcanzado.")
                            return scraped_games

                        app_details_url = f"{self.BASE_URL}appdetails?appids={app_id}&cc=es&l=es&key={self.API_KEY}"
                        try:
                            app_response = requests.get(app_details_url)
                            app_response.raise_for_status()
                            app_data = app_response.json()

                            if app_data and str(app_id) in app_data and app_data[str(app_id)]["success"]:
                                game_data = app_data[str(app_id)]["data"]
                                price_overview = game_data.get("price_overview")

                                price = "N/A"
                                if price_overview and "final_formatted" in price_overview:
                                    price = price_overview["final_formatted"]
                                elif game_data.get("is_free"):
                                    price = "Gratis"
                                elif price_overview and "initial_formatted" in price_overview:
                                    price = price_overview["initial_formatted"]

                                scraped_games.append({
                                    "nombre": game_data.get("name"),
                                    "imagen": game_data.get("header_image"),
                                    "precio": price,
                                    "link": f"https://store.steampowered.com/app/{app_id}",
                                    "categoria": category_type
                                })
                        except requests.exceptions.RequestException as e:
                            print(f"Error al obtener detalles del juego {app_id}: {e}")

            except requests.exceptions.RequestException as e:
                print(f"Error al obtener categorías de Steam para {category_name}: {e}")

        return scraped_games


GameScraperFactory.registrar_scraper("steam", SteamScraper)