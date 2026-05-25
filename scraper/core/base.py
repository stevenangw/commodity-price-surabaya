from abc import ABC, abstractmethod
from datetime import date
from typing import List
from scraper.utils.parser import ScrapedPriceRecord

class BaseScraper(ABC):
    """Kelas dasar abstrak untuk menjamin konsistensi antarmuka scraper."""

    @abstractmethod
    def fetch_prices(self, target_url: str, params: dict = None) -> List[ScrapedPriceRecord]:
        """
        Mengambil data harga dari URL target.
        
        Args:
            target_url: URL target API / Halaman web.
            params: Parameter pencarian HTTP query params (opsional).
            
        Returns:
            List dari ScrapedPriceRecord ter-validasi.
        """
        pass
