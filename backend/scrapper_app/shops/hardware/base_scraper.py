from abc import ABC, abstractmethod

class BaseScraper(ABC):
    def __init__(self, debug=False):
        self.debug = debug
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def iniciar_navegador(self):
        pass

    def cerrar_navegador(self):
        if self.context: self.context.close()
        if self.browser: self.browser.close()
        if self.playwright: self.playwright.stop()

    @abstractmethod
    def escanear_catalogo(self, url_catalogo_base, categoria_db, tipo_db, excluir_palabras=None):
        pass

    @abstractmethod
    def extraer_productos_de_pagina(self, page):
        pass
