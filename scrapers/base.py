from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import time
import random

class BaseScraper(ABC):
    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()
        
    def get_headers(self):
        return {
            'User-Agent': self.ua.random,
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Connection': 'keep-alive',
        }
    
    def get_soup(self, url: str) -> BeautifulSoup:
        time.sleep(random.uniform(1, 3))  # Rate limiting
        response = self.session.get(url, headers=self.get_headers())
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')
    
    @abstractmethod
    def scrape_product(self, url: str) -> Dict:
        pass
    
    @abstractmethod
    def scrape_reviews(self, product_id: str) -> List[Dict]:
        pass