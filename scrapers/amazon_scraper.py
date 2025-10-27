from .base import BaseScraper
import re

class AmazonScraper(BaseScraper):
    def scrape_product(self, url: str) -> dict:
        soup = self.get_soup(url)
        
        # Extract product details
        product_data = {
            'url': url,
            'platform': 'amazon',
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
            return soup.find('span', {'id': 'productTitle'}).text.strip()
        except:
            return None
    
    def _extract_brand(self, soup):
        try:
            return soup.find('a', {'id': 'bylineInfo'}).text.replace('Brand: ', '').strip()
        except:
            return None
    
    def _extract_price(self, soup):
        try:
            price_element = soup.find('span', {'class': 'a-price-whole'})
            if price_element:
                price_text = price_element.text.replace(',', '').replace('₹', '').strip()
                return float(price_text)
        except:
            return None
    
    def _extract_discount_price(self, soup):
        try:
            original_price = soup.find('span', {'class': 'a-price a-text-price a-size-base'})
            if original_price:
                price_text = original_price.text.replace(',', '').replace('₹', '').strip()
                return float(price_text)
        except:
            return None
    
    def _extract_rating(self, soup):
        try:
            rating = soup.find('span', {'class': 'a-icon-alt'})
            if rating:
                return float(rating.text.split()[0])
        except:
            return None
    
    def _extract_features(self, soup):
        features = {}
        try:
            # Extract from technical details or feature bullets
            feature_list = soup.find_all('span', {'class': 'a-list-item'})
            for item in feature_list:
                text = item.text.strip()
                if 'Processor' in text:
                    features['processor'] = text
                elif 'RAM' in text:
                    features['ram'] = text
                elif 'Storage' in text:
                    features['storage'] = text
                elif 'Display' in text:
                    features['display'] = text
        except:
            pass
        return features
    
    def _check_stock(self, soup):
        try:
            availability = soup.find('div', {'id': 'availability'})
            if availability:
                return 'in stock' in availability.text.lower()
        except:
            return True
    
    def scrape_reviews(self, product_url: str) -> list:
        # Simplified review scraping
        reviews = []
        # In production, you'd navigate to reviews page and scrape
        return reviews