class GameScraperFactory:
    _scrapers = {}

    @classmethod
    def registrar_scraper(cls, nombre, clase):
        cls._scrapers[nombre] = clase

    @classmethod
    def obtener_scraper(cls, nombre):
        clase_scraper = cls._scrapers.get(nombre)
        if not clase_scraper:
            raise ValueError(f"CRÍTICO: No existe un scraper registrado para el videojuego: {nombre}")
        
        return clase_scraper()
