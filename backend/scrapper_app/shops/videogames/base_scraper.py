from abc import ABC, abstractmethod

class BaseGameScraper(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def scrape(self) -> list[dict]:
        pass