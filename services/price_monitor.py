import schedule
import time
from datetime import datetime
from db import SessionLocal, Product, Price, Alert
from services.predictor import PricePredictor
from services.alerts import AlertService
from scrapers.amazon_scraper import AmazonScraper
from scrapers.flipkart_scraper import FlipkartScraper
import logging

logger = logging.getLogger(__name__)

class PriceMonitor:
    def __init__(self):
        self.predictor = PricePredictor()
        self.alert_service = AlertService()
        self.scrapers = {
            'amazon': AmazonScraper(),
            'flipkart': FlipkartScraper()
        }
    
    def monitor_prices(self):
        """Check current prices and create alerts based on predictions"""
        db = SessionLocal()
        try:
            products = db.query(Product).all()
            
            for product in products:
                try:
                    # Get current price from scraper
                    scraper = self.scrapers.get(product.platform)
                    if scraper:
                        product_data = scraper.scrape_product(product.url)
                        
                        if product_data and 'price' in product_data:
                            current_price = product_data['price']
                            
                            # Get last recorded price
                            last_price = db.query(Price).filter(
                                Price.product_id == product.id
                            ).order_by(Price.scraped_at.desc()).first()
                            
                            # Record new price
                            new_price = Price(
                                product_id=product.id,
                                price=current_price,
                                discount_price=product_data.get('discount_price'),
                                discount_percentage=product_data.get('discount_percentage', 0),
                                scraped_at=datetime.utcnow()
                            )
                            db.add(new_price)
                            
                            # Check for significant price changes
                            if last_price:
                                price_change_pct = ((current_price - last_price.price) / last_price.price) * 100
                                
                                # Create alerts for significant drops
                                if price_change_pct < -5:
                                    alert = Alert(
                                        type='price_drop',
                                        message=f"🎉 Price Drop Alert! {product.name} dropped by {abs(price_change_pct):.1f}% to ₹{current_price:,.0f}",
                                        product_id=product.id,
                                        created_at=datetime.utcnow(),
                                        sent=False
                                    )
                                    db.add(alert)
                            
                            # Get ML predictions
                            if self.predictor.is_trained:
                                prediction = self.predictor.predict_price(product.id, 7)
                                
                                if 'summary' in prediction:
                                    # Alert if price expected to rise significantly
                                    if prediction['summary']['expected_change_pct'] > 10:
                                        alert = Alert(
                                            type='price_prediction',
                                            message=f"⚡ Buy Now! {product.name} expected to rise by {prediction['summary']['expected_change_pct']:.1f}% in next 7 days",
                                            product_id=product.id,
                                            created_at=datetime.utcnow(),
                                            sent=False
                                        )
                                        db.add(alert)
                
                except Exception as e:
                    logger.error(f"Error monitoring {product.name}: {str(e)}")
                    continue
            
            db.commit()
            
            # Retrain model periodically with new data
            self.predictor.train()
            
        except Exception as e:
            logger.error(f"Price monitoring error: {str(e)}")
            db.rollback()
        finally:
            db.close()
    
    def start_monitoring(self, interval_hours=6):
        """Start the price monitoring schedule"""
        schedule.every(interval_hours).hours.do(self.monitor_prices)
        
        # Run once immediately
        self.monitor_prices()
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute