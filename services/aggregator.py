from typing import List, Dict
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from db import Product, Price, Review, Feature
from scrapers.amazon_scraper import AmazonScraper
from scrapers.flipkart_scraper import FlipkartScraper
from services.sentiment import SentimentAnalyzer
from services.alerts import AlertService

logger = logging.getLogger(__name__)

class DataAggregator:
    def __init__(self):
        self.scrapers = {
            'amazon': AmazonScraper(),
            'flipkart': FlipkartScraper(),
        }
        self.sentiment_analyzer = SentimentAnalyzer()
        self.alert_service = AlertService()
    
    def run_aggregation(self, db: Session):
        """Main aggregation pipeline"""
        products = db.query(Product).all()
        
        for product in products:
            try:
                # Scrape product data
                scraper = self.scrapers.get(product.platform)
                if not scraper:
                    logger.warning(f"No scraper available for platform: {product.platform}")
                    continue
                
                # Scrape product info
                product_data = scraper.scrape_product(product.url)
                
                if product_data:
                    # Store price data
                    self._store_price_data(db, product, product_data)
                    
                    # Store features
                    self._store_features(db, product, product_data.get('features', {}))
                    
                    # Scrape and analyze reviews
                    reviews = scraper.scrape_reviews(product.url)
                    if reviews:
                        self._store_reviews(db, product, reviews)
                    
                    # Check for alerts
                    self._check_product_alerts(db, product, product_data)
                    
                logger.info(f"Successfully scraped product: {product.name}")
                
            except Exception as e:
                logger.error(f"Error scraping product {product.name}: {str(e)}")
                continue
        
        db.commit()
    
    def scrape_single_product(self, product_id: int):
        """Scrape a single product"""
        db = SessionLocal()
        try:
            product = db.query(Product).filter(Product.id == product_id).first()
            if product:
                scraper = self.scrapers.get(product.platform)
                if scraper:
                    product_data = scraper.scrape_product(product.url)
                    if product_data:
                        self._store_price_data(db, product, product_data)
                        db.commit()
        except Exception as e:
            logger.error(f"Error scraping single product: {str(e)}")
        finally:
            db.close()
    
    def _store_price_data(self, db: Session, product: Product, data: Dict):
        """Store price information"""
        price = Price(
            product_id=product.id,
            price=data.get('price'),
            discount_price=data.get('discount_price'),
            discount_percentage=self._calculate_discount_percentage(
                data.get('price'),
                data.get('discount_price')
            ),
            in_stock=data.get('in_stock', True),
            scraped_at=datetime.utcnow()
        )
        db.add(price)
    
    def _store_features(self, db: Session, product: Product, features: Dict):
        """Store or update product features"""
        existing_feature = db.query(Feature).filter(
            Feature.product_id == product.id
        ).first()
        
        if existing_feature:
            # Update existing features
            for key, value in features.items():
                if hasattr(existing_feature, key):
                    setattr(existing_feature, key, value)
        else:
            # Create new feature record
            feature = Feature(
                product_id=product.id,
                processor=features.get('processor'),
                ram=features.get('ram'),
                storage=features.get('storage'),
                display=features.get('display'),
                graphics=features.get('graphics'),
                battery=features.get('battery'),
                weight=features.get('weight')
            )
            db.add(feature)
    
    def _store_reviews(self, db: Session, product: Product, reviews: List[Dict]):
        """Store reviews with sentiment analysis"""
        for review_data in reviews:
            # Analyze sentiment
            sentiment_result = self.sentiment_analyzer.analyze_review(
                review_data.get('content', '')
            )
            
            review = Review(
                product_id=product.id,
                rating=review_data.get('rating'),
                title=review_data.get('title'),
                content=review_data.get('content'),
                sentiment=sentiment_result['sentiment'],
                sentiment_score=sentiment_result['score'],
                review_date=review_data.get('date', datetime.utcnow()),
                scraped_at=datetime.utcnow()
            )
            db.add(review)
    
    def _calculate_discount_percentage(self, original_price, discount_price):
        """Calculate discount percentage"""
        if original_price and discount_price:
            return ((original_price - discount_price) / original_price) * 100
        return 0
    
    def _check_product_alerts(self, db: Session, product: Product, data: Dict):
        """Check if any alert conditions are met"""
        # Price drop alert
        last_price = db.query(Price).filter(
            Price.product_id == product.id
        ).order_by(Price.scraped_at.desc()).first()
        
        if last_price and data.get('price'):
            price_change = ((last_price.price - data['price']) / last_price.price) * 100
            if price_change > 10:  # More than 10% drop
                self.alert_service.create_alert(
                    db,
                    alert_type='price_drop',
                    message=f"Price drop alert! {product.name} dropped by {price_change:.1f}%",
                    product_id=product.id
                )