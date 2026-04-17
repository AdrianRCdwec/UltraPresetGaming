from abc import ABC, abstractmethod

class BaseScraper(ABC):
    def __init__(self, debug=False):
        self.debug = debug

    @abstractmethod
    def escanear_catalogo(self, url_catalogo_base, categoria_db, tipo_db, excluir_palabras=None):
        pass

    @abstractmethod
    def extraer_productos_de_pagina(self, page):
        pass
