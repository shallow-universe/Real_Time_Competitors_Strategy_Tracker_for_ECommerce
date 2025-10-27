import random
from datetime import datetime, timedelta
from db import SessionLocal, Base, engine, Product, Price, Review, Feature, Alert, User
from sqlalchemy import create_engine
import numpy as np
import hashlib

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

# Sample laptop data with realistic Indian market products
SAMPLE_LAPTOPS = [
    # Dell Laptops (10)
    {"name": "Dell Inspiron 15 3520 Intel Core i5-1235U", "brand": "Dell", "model": "Inspiron 3520", "platform": "amazon", "url": "https://www.amazon.in/dp/B0BPZ5V93Q", "base_price": 52990},
    {"name": "Dell Vostro 3420 Intel Core i3-1215U", "brand": "Dell", "model": "Vostro 3420", "platform": "flipkart", "url": "https://www.flipkart.com/dell-vostro-3420/p/itm123", "base_price": 38990},
    {"name": "Dell G15 5520 Gaming Intel Core i5-12500H", "brand": "Dell", "model": "G15 5520", "platform": "amazon", "url": "https://www.amazon.in/dp/B0BS3TZJ8K", "base_price": 75990},
    {"name": "Dell Inspiron 14 5420 Intel Core i7-1255U", "brand": "Dell", "model": "Inspiron 5420", "platform": "flipkart", "url": "https://www.flipkart.com/dell-inspiron-5420/p/itm456", "base_price": 68990},
    {"name": "Dell XPS 13 9315 Intel Core i5-1230U", "brand": "Dell", "model": "XPS 13", "platform": "amazon", "url": "https://www.amazon.in/dp/B0BT452T9K", "base_price": 99990},
    {"name": "Dell Alienware x14 R2 Gaming", "brand": "Dell", "model": "Alienware x14", "platform": "amazon", "url": "https://www.amazon.in/dp/B0BZRX8PJB", "base_price": 149990},
    {"name": "Dell Latitude 3420 Business Laptop", "brand": "Dell", "model": "Latitude 3420", "platform": "flipkart", "url": "https://www.flipkart.com/dell-latitude-3420/p/itm789", "base_price": 45990},
    {"name": "Dell Inspiron 16 5620", "brand": "Dell", "model": "Inspiron 5620", "platform": "amazon", "url": "https://www.amazon.in/dp/B0C1N2VCGP", "base_price": 62990},
    {"name": "Dell G15 5511 Gaming Laptop", "brand": "Dell", "model": "G15 5511", "platform": "flipkart", "url": "https://www.flipkart.com/dell-g15-5511/p/itm012", "base_price": 82990},
    {"name": "Dell Vostro 3510 Intel Core i5", "brand": "Dell", "model": "Vostro 3510", "platform": "amazon", "url": "https://www.amazon.in/dp/B09SKTHHXG", "base_price": 55990},
    
    # HP Laptops (10)
    {"name": "HP Pavilion 15 AMD Ryzen 5 5600H", "brand": "HP", "model": "Pavilion 15-ec2004AX", "platform": "amazon", "url": "https://www.amazon.in/dp/B098QBT8KT", "base_price": 58990},
    {"name": "HP 15s Intel Core i3-1215U", "brand": "HP", "model": "15s-fq5007TU", "platform": "flipkart", "url": "https://www.flipkart.com/hp-15s-i3/p/itm345", "base_price": 36990},
    {"name": "HP Victus Gaming 16 AMD Ryzen 5", "brand": "HP", "model": "Victus 16", "platform": "amazon", "url": "https://www.amazon.in/dp/B0B5RYXKX8", "base_price": 69990},
    {"name": "HP Omen 16 Intel Core i7", "brand": "HP", "model": "Omen 16", "platform": "flipkart", "url": "https://www.flipkart.com/hp-omen-16/p/itm678", "base_price": 124990},
    {"name": "HP Envy x360 13 Convertible", "brand": "HP", "model": "Envy x360", "platform": "amazon", "url": "https://www.amazon.in/dp/B0B4N3Y5KG", "base_price": 89990},
    {"name": "HP ProBook 440 G9", "brand": "HP", "model": "ProBook 440", "platform": "flipkart", "url": "https://www.flipkart.com/hp-probook-440/p/itm901", "base_price": 72990},
    {"name": "HP 14s Intel Core i5-1235U", "brand": "HP", "model": "14s-dq5138tu", "platform": "amazon", "url": "https://www.amazon.in/dp/B0B6F5X8QB", "base_price": 54990},
    {"name": "HP Pavilion Gaming 15", "brand": "HP", "model": "Pavilion Gaming 15", "platform": "flipkart", "url": "https://www.flipkart.com/hp-pavilion-gaming/p/itm234", "base_price": 65990},
    {"name": "HP ZBook Firefly 14 G9", "brand": "HP", "model": "ZBook Firefly", "platform": "amazon", "url": "https://www.amazon.in/dp/B0BH3JQMWD", "base_price": 135990},
    {"name": "HP 255 G8 AMD Ryzen 3", "brand": "HP", "model": "255 G8", "platform": "flipkart", "url": "https://www.flipkart.com/hp-255-g8/p/itm567", "base_price": 32990},
    
    # Lenovo Laptops (10)
    {"name": "Lenovo IdeaPad Gaming 3 AMD Ryzen 5", "brand": "Lenovo", "model": "IdeaPad Gaming 3", "platform": "flipkart", "url": "https://www.flipkart.com/lenovo-gaming-3/p/itm890", "base_price": 62990},
    {"name": "Lenovo ThinkPad E14 Intel Core i5", "brand": "Lenovo", "model": "ThinkPad E14", "platform": "amazon", "url": "https://www.amazon.in/dp/B0BF52FT8H", "base_price": 68990},
    {"name": "Lenovo IdeaPad Slim 3 Intel Core i3", "brand": "Lenovo", "model": "IdeaPad Slim 3", "platform": "amazon", "url": "https://www.amazon.in/dp/B0BS73MJT5", "base_price": 35990},
    {"name": "Lenovo Legion 5 Pro AMD Ryzen 7", "brand": "Lenovo", "model": "Legion 5 Pro", "platform": "flipkart", "url": "https://www.flipkart.com/lenovo-legion-5-pro/p/itm123abc", "base_price": 139990},
    {"name": "Lenovo Yoga Slim 7 Intel Core i7", "brand": "Lenovo", "model": "Yoga Slim 7", "platform": "amazon", "url": "https://www.amazon.in/dp/B09VGFVDCB", "base_price": 94990},
    {"name": "Lenovo ThinkBook 15 G3", "brand": "Lenovo", "model": "ThinkBook 15", "platform": "flipkart", "url": "https://www.flipkart.com/lenovo-thinkbook-15/p/itm456def", "base_price": 58990},
    {"name": "Lenovo V15 Intel Core i3", "brand": "Lenovo", "model": "V15", "platform": "amazon", "url": "https://www.amazon.in/dp/B0B8HB3VQC", "base_price": 32990},
    {"name": "Lenovo IdeaPad Flex 5", "brand": "Lenovo", "model": "IdeaPad Flex 5", "platform": "flipkart", "url": "https://www.flipkart.com/lenovo-flex-5/p/itm789ghi", "base_price": 76990},
    {"name": "Lenovo Legion 7 Intel Core i9", "brand": "Lenovo", "model": "Legion 7", "platform": "amazon", "url": "https://www.amazon.in/dp/B0C4PFCZFB", "base_price": 229990},
    {"name": "Lenovo ThinkPad X1 Carbon", "brand": "Lenovo", "model": "X1 Carbon", "platform": "flipkart", "url": "https://www.flipkart.com/lenovo-x1-carbon/p/itm012jkl", "base_price": 185990},
    
    # ASUS Laptops (10)
    {"name": "ASUS TUF Gaming F15 Intel Core i5", "brand": "ASUS", "model": "TUF F15", "platform": "amazon", "url": "https://www.amazon.in/dp/B0B7RTVFK4", "base_price": 67990},
    {"name": "ASUS VivoBook 15 Intel Core i3", "brand": "ASUS", "model": "VivoBook 15", "platform": "flipkart", "url": "https://www.flipkart.com/asus-vivobook-15/p/itm345mno", "base_price": 34990},
    {"name": "ASUS ROG Strix G15 AMD Ryzen 7", "brand": "ASUS", "model": "ROG Strix G15", "platform": "amazon", "url": "https://www.amazon.in/dp/B0B56YBF5N", "base_price": 94990},
    {"name": "ASUS TUF Dash F15 Intel Core i7", "brand": "ASUS", "model": "TUF Dash F15", "platform": "flipkart", "url": "https://www.flipkart.com/asus-dash-f15/p/itm678pqr", "base_price": 85990},
    {"name": "ASUS ZenBook 14 OLED", "brand": "ASUS", "model": "ZenBook 14", "platform": "amazon", "url": "https://www.amazon.in/dp/B09S6VQL8P", "base_price": 79990},
    {"name": "ASUS ROG Zephyrus G14", "brand": "ASUS", "model": "Zephyrus G14", "platform": "flipkart", "url": "https://www.flipkart.com/asus-zephyrus-g14/p/itm901stu", "base_price": 124990},
    {"name": "ASUS VivoBook K15 OLED", "brand": "ASUS", "model": "VivoBook K15", "platform": "amazon", "url": "https://www.amazon.in/dp/B09NFVNGL7", "base_price": 46990},
    {"name": "ASUS ProArt StudioBook 16", "brand": "ASUS", "model": "ProArt StudioBook", "platform": "flipkart", "url": "https://www.flipkart.com/asus-proart-16/p/itm234vwx", "base_price": 189990},
    {"name": "ASUS ExpertBook B1", "brand": "ASUS", "model": "ExpertBook B1", "platform": "amazon", "url": "https://www.amazon.in/dp/B0B2H8B7HT", "base_price": 42990},
    {"name": "ASUS ROG Flow X13", "brand": "ASUS", "model": "ROG Flow X13", "platform": "flipkart", "url": "https://www.flipkart.com/asus-flow-x13/p/itm567yz0", "base_price": 154990},
    
    # Acer Laptops (5)
    {"name": "Acer Aspire 7 Gaming Intel Core i5", "brand": "Acer", "model": "Aspire 7", "platform": "flipkart", "url": "https://www.flipkart.com/acer-aspire-7/p/itm890123", "base_price": 54990},
    {"name": "Acer Nitro 5 Gaming AMD Ryzen 5", "brand": "Acer", "model": "Nitro 5", "platform": "amazon", "url": "https://www.amazon.in/dp/B0B9S7YBF5", "base_price": 72990},
    {"name": "Acer Swift 3 Intel Evo", "brand": "Acer", "model": "Swift 3", "platform": "flipkart", "url": "https://www.flipkart.com/acer-swift-3/p/itm456abc", "base_price": 69990},
    {"name": "Acer Predator Helios 300", "brand": "Acer", "model": "Predator Helios 300", "platform": "amazon", "url": "https://www.amazon.in/dp/B0C1234567", "base_price": 119990},
    {"name": "Acer Aspire 5 Intel Core i3", "brand": "Acer", "model": "Aspire 5", "platform": "flipkart", "url": "https://www.flipkart.com/acer-aspire-5/p/itm789def", "base_price": 38990},
    
    # Apple MacBooks (3)
    {"name": "Apple MacBook Air M2 8GB 256GB", "brand": "Apple", "model": "MacBook Air M2", "platform": "amazon", "url": "https://www.amazon.in/dp/B0B3B5JZZ5", "base_price": 119900},
    {"name": "Apple MacBook Pro 14 M2 Pro", "brand": "Apple", "model": "MacBook Pro 14", "platform": "flipkart", "url": "https://www.flipkart.com/macbook-pro-14/p/itm012ghi", "base_price": 199900},
    {"name": "Apple MacBook Air M1 8GB 256GB", "brand": "Apple", "model": "MacBook Air M1", "platform": "amazon", "url": "https://www.amazon.in/dp/B08N5W4NNB", "base_price": 92900},
    
    # MSI Laptops (2)
    {"name": "MSI GF63 Thin Gaming Intel Core i5", "brand": "MSI", "model": "GF63 Thin", "platform": "flipkart", "url": "https://www.flipkart.com/msi-gf63/p/itm345jkl", "base_price": 52990},
    {"name": "MSI Modern 14 Intel Core i5", "brand": "MSI", "model": "Modern 14", "platform": "amazon", "url": "https://www.amazon.in/dp/B0B789QWXYZ", "base_price": 48990},
]

# Sample review templates
POSITIVE_REVIEWS = [
    {"title": "Excellent laptop for the price!", "content": "Amazing performance and build quality. The display is crisp and battery life is great. Highly recommend!", "rating": 5},
    {"title": "Great value for money", "content": "Been using for 2 months now. No issues whatsoever. Fast processor and good graphics for casual gaming.", "rating": 5},
    {"title": "Perfect for work and entertainment", "content": "Sleek design, lightweight, and powerful. The keyboard is comfortable for long typing sessions.", "rating": 4},
    {"title": "Impressed with the performance", "content": "Boots up quickly, runs multiple applications smoothly. The cooling system works well even under heavy load.", "rating": 5},
    {"title": "Solid build quality", "content": "Premium feel at this price point. Screen quality is excellent and speakers are surprisingly good.", "rating": 4},
]

NEUTRAL_REVIEWS = [
    {"title": "Decent laptop with some trade-offs", "content": "Good performance but battery life could be better. Suitable for general use but not heavy gaming.", "rating": 3},
    {"title": "Average but does the job", "content": "Nothing exceptional but works fine for daily tasks. Build quality is okay for the price.", "rating": 3},
    {"title": "Mixed feelings", "content": "Fast processor but the display could be brighter. Keyboard is fine but trackpad needs improvement.", "rating": 3},
]

NEGATIVE_REVIEWS = [
    {"title": "Disappointed with the quality", "content": "Started having issues after 3 months. Customer service is not helpful. Battery drains too quickly.", "rating": 2},
    {"title": "Not worth the price", "content": "Overheats frequently, fan noise is too loud. Build quality feels cheap despite the high price.", "rating": 1},
    {"title": "Many problems", "content": "WiFi keeps disconnecting, touchpad stopped working after a month. Very frustrated with this purchase.", "rating": 2},
]

def create_price_history(product_id, base_price, num_points=15):
    """Generate realistic price history with trends and fluctuations"""
    prices = []
    current_date = datetime.now()
    
    # Create seasonal price pattern
    for i in range(num_points):
        days_ago = num_points - i
        date = current_date - timedelta(days=days_ago)
        
        # Base price with some trend
        trend_factor = 1.0 - (i * 0.001)  # Slight downward trend
        
        # Seasonal variations
        if date.month in [10, 11]:  # Festive season (Diwali)
            seasonal_factor = 0.85  # 15% discount
        elif date.month in [1, 7]:  # Sale periods
            seasonal_factor = 0.92  # 8% discount
        else:
            seasonal_factor = 1.0
        
        # Random daily fluctuations
        daily_variation = random.uniform(0.97, 1.03)
        
        # Weekend effect
        weekend_factor = 0.98 if date.weekday() in [5, 6] else 1.0
        
        # Calculate final price
        price = base_price * trend_factor * seasonal_factor * daily_variation * weekend_factor
        
        # Discount calculation
        if random.random() < 0.3:  # 30% chance of discount
            discount_percentage = random.uniform(5, 25)
            discount_price = price * (1 - discount_percentage / 100)
        else:
            discount_percentage = 0
            discount_price = None
        
        prices.append({
            'product_id': product_id,
            'price': round(price, -1),  # Round to nearest 10
            'discount_price': round(discount_price, -1) if discount_price else None,
            'discount_percentage': round(discount_percentage, 1) if discount_percentage > 0 else None,
            'currency': 'INR',
            'in_stock': random.random() > 0.1,  # 90% chance in stock
            'scraped_at': date
        })
    
    return prices

def create_product_features(product):
    """Generate realistic laptop features based on price range"""
    price = product['base_price']
    
    # Determine specs based on price range
    if price < 40000:  # Budget
        ram_options = ['4GB DDR4', '8GB DDR4']
        processor_options = ['Intel Core i3-1115G4', 'AMD Ryzen 3 5300U', 'Intel Core i3-1215U']
        storage_options = ['256GB SSD', '512GB SSD', '1TB HDD']
        graphics_options = ['Intel UHD Graphics', 'Intel Iris Xe', 'AMD Radeon Graphics']
    elif price < 70000:  # Mid-range
        ram_options = ['8GB DDR4', '16GB DDR4']
        processor_options = ['Intel Core i5-1235U', 'AMD Ryzen 5 5600H', 'Intel Core i5-11400H']
        storage_options = ['512GB SSD', '512GB SSD + 1TB HDD']
        graphics_options = ['NVIDIA GTX 1650', 'Intel Iris Xe', 'AMD Radeon RX 5500M']
    elif price < 100000:  # Premium
        ram_options = ['16GB DDR4', '16GB DDR5']
        processor_options = ['Intel Core i7-1255U', 'AMD Ryzen 7 5800H', 'Intel Core i7-12700H']
        storage_options = ['512GB SSD', '1TB SSD']
        graphics_options = ['NVIDIA RTX 3050', 'NVIDIA RTX 3060', 'AMD Radeon RX 6600M']
    else:  # High-end
        ram_options = ['16GB DDR5', '32GB DDR5']
        processor_options = ['Intel Core i7-12700H', 'Intel Core i9-12900H', 'AMD Ryzen 9 5900HX']
        storage_options = ['1TB SSD', '2TB SSD']
        graphics_options = ['NVIDIA RTX 3070', 'NVIDIA RTX 3080', 'NVIDIA RTX 4060']
    
    return {
        'processor': random.choice(processor_options),
        'ram': random.choice(ram_options),
        'storage': random.choice(storage_options),
        'display': random.choice(['13.3 inch FHD', '14 inch FHD', '15.6 inch FHD', '15.6 inch 4K']),
        'graphics': random.choice(graphics_options),
        'battery': random.choice(['45Wh', '56Wh', '70Wh', '86Wh']),
        'weight': f"{random.uniform(1.2, 2.5):.1f}kg"
    }

def seed_database():
    """Seed the database with sample data"""
    db = SessionLocal()
    
    try:
        # Clear existing data (optional - comment out if you want to keep existing data)
        print("Clearing existing data...")
        db.query(Review).delete()
        db.query(Price).delete()
        db.query(Feature).delete()
        db.query(Alert).delete()
        db.query(Product).delete()
        db.commit()
        
        print("Seeding products...")
        # Add products
        for laptop_data in SAMPLE_LAPTOPS:
            product = Product(
                name=laptop_data['name'],
                brand=laptop_data['brand'],
                model=laptop_data['model'],
                category='laptop',
                url=laptop_data['url'],
                platform=laptop_data['platform'],
                created_at=datetime.now() - timedelta(days=30)  # Created 30 days ago
            )
            db.add(product)
            db.flush()  # Get the product ID
            
            # Add product features
            features_data = create_product_features(laptop_data)
            features = Feature(
                product_id=product.id,
                processor=features_data['processor'],
                ram=features_data['ram'],
                storage=features_data['storage'],
                display=features_data['display'],
                graphics=features_data['graphics'],
                battery=features_data['battery'],
                weight=features_data['weight']
            )
            db.add(features)
            
            # Add price history (15 data points)
            print(f"Adding price history for {product.name}...")
            price_history = create_price_history(product.id, laptop_data['base_price'], 15)
            for price_data in price_history:
                price = Price(**price_data)
                db.add(price)
            
            # Add reviews with sentiments (10-15 reviews per product)
            print(f"Adding reviews for {product.name}...")
            num_reviews = random.randint(10, 15)
            
            # Distribution: 60% positive, 20% neutral, 20% negative
            num_positive = int(num_reviews * 0.6)
            num_neutral = int(num_reviews * 0.2)
            num_negative = num_reviews - num_positive - num_neutral
            
            review_pool = (
                random.choices(POSITIVE_REVIEWS, k=num_positive) +
                random.choices(NEUTRAL_REVIEWS, k=num_neutral) +
                random.choices(NEGATIVE_REVIEWS, k=num_negative)
            )
            random.shuffle(review_pool)
            
            for i, review_template in enumerate(review_pool):
                # Add some variation to review dates
                review_date = datetime.now() - timedelta(days=random.randint(1, 60))
                
                # Determine sentiment based on rating
                if review_template['rating'] >= 4:
                    sentiment = 'positive'
                    sentiment_score = random.uniform(0.7, 0.95)
                elif review_template['rating'] == 3:
                    sentiment = 'neutral'
                    sentiment_score = random.uniform(0.4, 0.6)
                else:
                    sentiment = 'negative'
                    sentiment_score = random.uniform(0.1, 0.3)
                
                review = Review(
                    product_id=product.id,
                    rating=review_template['rating'],
                    title=review_template['title'],
                    content=review_template['content'] + f" (Review #{i+1} for {product.brand})",
                    sentiment=sentiment,
                    sentiment_score=sentiment_score,
                    review_date=review_date,
                    scraped_at=review_date + timedelta(hours=random.randint(1, 24))
                )
                db.add(review)
        
        # Create some sample alerts
        print("Creating sample alerts...")
        
        # Get some random products for alerts
        all_products = db.query(Product).all()
        
        # Active alerts
        active_alerts = [
            {
                'type': 'price_drop',
                'message': f'Price dropped by 15% for {random.choice(all_products).name}',
                'product_id': random.choice(all_products).id,
                'sent': False,
                'created_at': datetime.now() - timedelta(hours=2)
            },
            {
                'type': 'new_competitor',
                'message': 'New competitor laptop launched in gaming category',
                'product_id': None,
                'sent': False,
                'created_at': datetime.now() - timedelta(hours=5)
            },
            {
                'type': 'stock_alert',
                'message': f'{random.choice(all_products).name} is back in stock',
                'product_id': random.choice(all_products).id,
                'sent': False,
                'created_at': datetime.now() - timedelta(hours=8)
            },
            {
                'type': 'sentiment_change',
                'message': f'Sentiment improved for {random.choice(all_products).name} - now 85% positive',
                'product_id': random.choice(all_products).id,
                'sent': False,
                'created_at': datetime.now() - timedelta(hours=12)
            }
        ]
        
        # Historical (sent) alerts
        historical_alerts = [
            {
                'type': 'price_drop',
                'message': f'Flash sale: 20% off on {random.choice(all_products).name}',
                'product_id': random.choice(all_products).id,
                'sent': True,
                'created_at': datetime.now() - timedelta(days=1)
            },
            {
                'type': 'price_increase',
                'message': f'Price increased by 10% for {random.choice(all_products).name}',
                'product_id': random.choice(all_products).id,
                'sent': True,
                'created_at': datetime.now() - timedelta(days=2)
            },
            {
                'type': 'review_alert',
                'message': f'New negative reviews detected for {random.choice(all_products).name}',
                'product_id': random.choice(all_products).id,
                'sent': True,
                'created_at': datetime.now() - timedelta(days=3)
            }
        ]
        
        for alert_data in active_alerts + historical_alerts:
            alert = Alert(**alert_data)
            db.add(alert)
        
        # Create default users if not exist
        admin_exists = db.query(User).filter(User.username == "admin").first()
        if not admin_exists:
            admin_user = User(
                username="admin",
                email="admin@example.com",
                name="Administrator",
                hashed_password=hashlib.sha256("admin123".encode()).hexdigest(),
                is_active=True,
                created_at=datetime.now()
            )
            db.add(admin_user)
        
        # Commit all changes
        db.commit()
        
        # Print summary
        print("\n✅ Database seeded successfully!")
        print(f"📦 Products: {len(SAMPLE_LAPTOPS)}")
        print(f"💰 Price points per product: 15")
        print(f"💬 Reviews per product: 10-15")
        print(f"🚨 Active alerts: {len(active_alerts)}")
        print(f"📜 Historical alerts: {len(historical_alerts)}")
        
        # Print some statistics
        total_prices = db.query(Price).count()
        total_reviews = db.query(Review).count()
        # avg_price = db.query(avg(Price.price)).scalar()
        
        print(f"\n📊 Statistics:")
        print(f"- Total price records: {total_prices}")
        print(f"- Total reviews: {total_reviews}")
        # print(f"- Average laptop price: ₹{avg_price:,.0f}")
        
        # Sample data preview
        print("\n🔍 Sample Products:")
        sample_products = db.query(Product).limit(5).all()
        for p in sample_products:
            latest_price = db.query(Price).filter(Price.product_id == p.id).order_by(Price.scraped_at.desc()).first()
            print(f"- {p.name}: ₹{latest_price.price:,.0f} ({p.platform})")
        
    except Exception as e:
        print(f"❌ Error seeding database: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("🌱 Starting database seeding...")
    seed_database()
    print("\n✨ Done! You can now run your Streamlit app and test all features.")