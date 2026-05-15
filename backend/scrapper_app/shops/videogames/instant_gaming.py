import requests
from bs4 import BeautifulSoup
import time

from backend.scrapper_app.shops.videogames.base_scraper import BaseGameScraper
from backend.scrapper_app.shops.videogames.factory import GameScraperFactory

class InstantGamingScraper(BaseGameScraper):
    def __init__(self):
        self.base_url = "https://www.instant-gaming.com/es/"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def scrape(self) -> list[dict]:
        games = []
        try:
            response = requests.get(self.base_url, headers=self.headers)
            response.raise_for_status() # Lanza una excepción para errores HTTP
            time.sleep(1)

            soup = BeautifulSoup(response.text, "html.parser")

            # Encontrar todos los elementos que representan un juego en la página principal
            # La estructura de Instant Gaming puede cambiar, por lo que este selector puede necesitar ajuste
            game_elements = soup.select("div.item") # Este es un selector común, verificar con la página real

            for game_element in game_elements:
                # Extraer nombre
                name_element = game_element.select_one("div.title")
                name = name_element.get_text(strip=True) if name_element else "N/A"

                # Extraer imagen (URL absoluta)
                image_element = game_element.select_one("div.picture img")
                image_url = image_element["src"] if image_element and "src" in image_element else "N/A"
                if not image_url.startswith("http"):
                    image_url = f"https://www.instant-gaming.com{image_url}"

                # Extraer precio
                price_element = game_element.select_one("div.price")
                price = price_element.get_text(strip=True) if price_element else "N/A"

                # Extraer link (URL del juego)
                link_element = game_element.select_one("a.item-link") # Ajustar este selector si es necesario
                game_link = link_element["href"] if link_element and "href" in link_element else "N/A"

                # Categoría fija
                category = "VG_TEND"

                if all(val != "N/A" for val in [name, image_url, price, game_link]):
                    games.append({
                        "nombre": name,
                        "imagen": image_url,
                        "precio": price,
                        "link": game_link,
                        "categoria": category
                    })
        except requests.exceptions.RequestException as e:
            print(f"Error al realizar la petición a Instant Gaming: {e}")
        except Exception as e:
            print(f"Ocurrió un error durante el scraping de Instant Gaming: {e}")
        
        return games

# Auto-registro del scraper
GameScraperFactory.registrar_scraper("instant_gaming", InstantGamingScraper)
