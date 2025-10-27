from .base import BaseScraper
import re

class FlipkartScraper(BaseScraper):
    def scrape_product(self, url: str) -> dict:
        soup = self.get_soup(url)
        
        product_data = {
            'url': url,
            'platform': 'flipkart',
            'name': self._extract_name(soup),
            'brand': self._extract_brand(soup),
            'price': self._extract_price(soup),
            'discount_price': self._extract_discount_price(soup),
            'rating': self._extract_rating(soup),
            'features': self._extract_features(soup),
            'in_stock': self._check_stock(soup)
        }
        
        return product_data
    
    def _extract_name(self, soup):
        try:
            return soup.find('span', {'class': 'B_NuCI'}).text.strip()
        except:
            return None
    
    def _extract_brand(self, soup):
        try:
            title = soup.find('span', {'class': 'B_NuCI'}).text.strip()
            return title.split()[0]  # Usually first word is brand
        except:
            return None
    
    def _extract_price(self, soup):
        try:
            price_element = soup.find('div', {'class': '_30jeq3 _16Jk6d'})
            if price_element:
                price_text = price_element.text.replace('₹', '').replace(',', '').strip()
                return float(price_text)
        except:
            return None
    
    def _extract_discount_price(self, soup):
        try:
            original_price = soup.find('div', {'class': '_3I9_wc _2p6lqe'})
            if original_price:
                price_text = original_price.text.replace('₹', '').replace(',', '').strip()
                return float(price_text)
        except:
            return None
    
    def _extract_rating(self, soup):
        try:
            rating_element = soup.find('div', {'class': '_3LWZlK'})
            if rating_element:
                return float(rating_element.text.strip())
        except:
            return None
    
    def _extract_features(self, soup):
        features = {}
        try:
            specs = soup.find_all('li', {'class': '_21Ahn-'})
            for spec in specs:
                text = spec.text.strip()
                if 'Processor' in text:
                    features['processor'] = text
                elif 'RAM' in text:
                    features['ram'] = text
                elif 'Storage' in text or 'SSD' in text or 'HDD' in text:
                    features['storage'] = text
                elif 'Display' in text or 'Screen' in text:
                    features['display'] = text
        except:
            pass
        return features
    
    def _check_stock(self, soup):
        try:
            sold_out = soup.find('div', {'class': '_16FRp0'})
            return sold_out is None
        except:
            return True
    
    def scrape_reviews(self, product_url: str) -> list:
        # Simplified - in production, navigate to reviews section
        return []