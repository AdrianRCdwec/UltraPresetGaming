class ScraperFactory:
    _scrapers = {}

    @classmethod
    def registrar_scraper(cls, nombre_tienda, clase_scraper):
        cls._scrapers[nombre_tienda] = clase_scraper

    @classmethod
    def obtener_scraper(cls, nombre_tienda, debug=False):
        clase_scraper = cls._scrapers.get(nombre_tienda)
        if not clase_scraper:
            raise ValueError(f"CRÍTICO: No existe un scraper registrado para la tienda: {nombre_tienda}")
        
        # Instanciamos la clase pasándole el parámetro debug
        return clase_scraper(debug=debug)