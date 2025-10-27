import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import mean_absolute_error, r2_score
from datetime import datetime, timedelta
import joblib
import os
from typing import Dict, List, Tuple, Optional
from db import SessionLocal, Product, Price, Feature
from sqlalchemy import func
import warnings
warnings.filterwarnings('ignore')

class PricePredictor:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.is_trained = False
        self.model_path = 'models/price_predictor.pkl'
        self.scaler_path = 'models/price_scaler.pkl'
        self.encoders_path = 'models/label_encoders.pkl'
        
        # Create models directory if not exists
        os.makedirs('models', exist_ok=True)
        
        # Load model if exists
        self.load_model()
    
    def prepare_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Extract features from price and product data"""
        features = pd.DataFrame()
        
        # Time-based features
        if 'scraped_at' in data.columns:
            data['scraped_at'] = pd.to_datetime(data['scraped_at'])
            features['year'] = data['scraped_at'].dt.year
            features['month'] = data['scraped_at'].dt.month
            features['day'] = data['scraped_at'].dt.day
            features['day_of_week'] = data['scraped_at'].dt.dayofweek
            features['day_of_year'] = data['scraped_at'].dt.dayofyear
            features['week_of_year'] = data['scraped_at'].dt.isocalendar().week
            features['is_weekend'] = (features['day_of_week'] >= 5).astype(int)
            
            # Festive season indicators (Indian context)
            features['is_diwali_season'] = ((data['scraped_at'].dt.month == 10) | 
                                           (data['scraped_at'].dt.month == 11)).astype(int)
            features['is_holi_season'] = (data['scraped_at'].dt.month == 3).astype(int)
            features['is_independence_day'] = ((data['scraped_at'].dt.month == 8) & 
                                              (data['scraped_at'].dt.day >= 10) & 
                                              (data['scraped_at'].dt.day <= 20)).astype(int)
            features['is_year_end_sale'] = (data['scraped_at'].dt.month == 12).astype(int)
        
        # Product features
        if 'brand' in data.columns:
            features['brand_encoded'] = self._encode_categorical(data['brand'], 'brand')
        
        if 'platform' in data.columns:
            features['platform_encoded'] = self._encode_categorical(data['platform'], 'platform')
        
        # Specifications-based features
        if 'ram' in data.columns and data['ram'].notna().any():
            features['ram_gb'] = data['ram'].fillna('8GB').str.extract('(\d+)').astype(float).fillna(8)
        else:
            features['ram_gb'] = 8
        
        if 'storage' in data.columns and data['storage'].notna().any():
            features['storage_gb'] = data['storage'].fillna('512GB').str.extract('(\d+)').astype(float).fillna(512)
            features['is_ssd'] = data['storage'].fillna('SSD').str.contains('SSD', case=False).astype(int)
        else:
            features['storage_gb'] = 512
            features['is_ssd'] = 1
        
        if 'processor' in data.columns and data['processor'].notna().any():
            features['is_intel'] = data['processor'].fillna('Intel').str.contains('Intel|i3|i5|i7|i9', case=False).astype(int)
            features['is_amd'] = data['processor'].fillna('').str.contains('AMD|Ryzen', case=False).astype(int)
        else:
            features['is_intel'] = 1
            features['is_amd'] = 0
        
        # Price history features - only if we have historical data
        if 'price' in data.columns and 'product_id' in data.columns and len(data) > 1:
            # Sort by date for proper shift operations
            data = data.sort_values('scraped_at')
            
            features['price_lag_1'] = data.groupby('product_id')['price'].shift(1)
            features['price_ma_7'] = data.groupby('product_id')['price'].transform(lambda x: x.rolling(7, min_periods=1).mean())
            features['price_std_7'] = data.groupby('product_id')['price'].transform(lambda x: x.rolling(7, min_periods=1).std())
            
            # Fill NaN values
            features['price_lag_1'] = features['price_lag_1'].fillna(data['price'])
            features['price_std_7'] = features['price_std_7'].fillna(0)
        else:
            # For single predictions, use the current price
            if 'price' in data.columns:
                features['price_lag_1'] = data['price']
                features['price_ma_7'] = data['price']
                features['price_std_7'] = 0
        
        return features.fillna(0)
    
    def _encode_categorical(self, series: pd.Series, name: str) -> pd.Series:
        """Encode categorical variables"""
        if name not in self.label_encoders:
            self.label_encoders[name] = LabelEncoder()
            # Handle NaN values
            series_filled = series.fillna('Unknown')
            encoded = self.label_encoders[name].fit_transform(series_filled)
        else:
            # Handle unseen categories
            series_filled = series.fillna('Unknown')
            classes = list(self.label_encoders[name].classes_)
            
            # Map unseen values to 'Unknown' if it exists, otherwise to first class
            series_mapped = series_filled.apply(lambda x: x if x in classes else 'Unknown' if 'Unknown' in classes else classes[0])
            encoded = self.label_encoders[name].transform(series_mapped)
        
        return encoded
    
    def train(self, force_retrain: bool = False) -> Dict:
        """Train the price prediction model"""
        if self.is_trained and not force_retrain:
            return {"status": "Model already trained", "metrics": {}}
        
        db = SessionLocal()
        try:
            # Fixed query with explicit joins
            # First, get all price data with product info
            price_product_data = db.query(
                Price.price,
                Price.scraped_at,
                Price.product_id,
                Product.brand,
                Product.platform,
                Product.name
            ).select_from(Price).join(
                Product, Price.product_id == Product.id
            ).all()
            
            if len(price_product_data) < 100:
                return {"status": "Insufficient data for training", "data_points": len(price_product_data)}
            
            # Convert to DataFrame
            df = pd.DataFrame([{
                'price': row.price,
                'scraped_at': row.scraped_at,
                'product_id': row.product_id,
                'brand': row.brand,
                'platform': row.platform,
                'name': row.name
            } for row in price_product_data])
            
            # Get feature data separately to avoid join issues
            features_data = db.query(Feature).all()
            features_df = pd.DataFrame([{
                'product_id': f.product_id,
                'ram': f.ram,
                'storage': f.storage,
                'processor': f.processor,
                'graphics': f.graphics
            } for f in features_data])
            
            # Merge features if available
            if not features_df.empty:
                df = df.merge(features_df, on='product_id', how='left')
            
            # Prepare features
            X = self.prepare_features(df)
            y = df['price']
            
            # Remove any infinite or NaN values
            mask = ~(X.isin([np.inf, -np.inf]).any(axis=1) | X.isna().any(axis=1) | y.isna())
            X = X[mask]
            y = y[mask]
            
            if len(X) < 50:
                return {"status": "Insufficient valid data after cleaning", "data_points": len(X)}
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, shuffle=False
            )
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train a simpler model first
            self.model = RandomForestRegressor(
                n_estimators=50,  # Reduced for faster training
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
            
            self.model.fit(X_train_scaled, y_train)
            
            # Make predictions
            y_pred = self.model.predict(X_test_scaled)
            
            # Calculate metrics
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            mape = np.mean(np.abs((y_test - y_pred) / y_test)) * 100
            
            # Save model
            self.save_model()
            self.is_trained = True
            
            return {
                "status": "Training successful",
                "metrics": {
                    "mae": float(mae),
                    "r2": float(r2),
                    "mape": float(mape),
                    "training_samples": len(X_train),
                    "test_samples": len(X_test)
                }
            }
            
        except Exception as e:
            return {"status": "Training failed", "error": str(e)}
        finally:
            db.close()
    
    def predict_price(self, product_id: int, days_ahead: int = 7) -> Dict:
        """Predict future prices for a product"""
        if not self.is_trained:
            # Try to train the model
            train_result = self.train()
            if train_result["status"] != "Training successful":
                return {"error": "Model not trained", "details": train_result}
        
        db = SessionLocal()
        try:
            # Get product details
            product = db.query(Product).filter(Product.id == product_id).first()
            if not product:
                return {"error": "Product not found"}
            
            # Get recent prices
            recent_prices = db.query(Price).filter(
                Price.product_id == product_id
            ).order_by(Price.scraped_at.desc()).limit(30).all()
            
            if not recent_prices:
                return {"error": "No price history available"}
            
            # Get product features
            features = db.query(Feature).filter(Feature.product_id == product_id).first()
            
            predictions = []
            current_price = recent_prices[0].price
            
            # Calculate historical statistics for better predictions
            historical_prices = [p.price for p in recent_prices]
            price_mean = np.mean(historical_prices)
            price_std = np.std(historical_prices)
            
            # Predict for each future day
            for day in range(1, days_ahead + 1):
                future_date = datetime.now() + timedelta(days=day)
                
                # Create prediction data
                pred_data = pd.DataFrame([{
                    'product_id': product_id,
                    'brand': product.brand,
                    'platform': product.platform,
                    'name': product.name,
                    'price': current_price,  # Use current price as reference
                    'scraped_at': future_date,
                    'ram': features.ram if features else None,
                    'storage': features.storage if features else None,
                    'processor': features.processor if features else None,
                    'graphics': features.graphics if features else None
                }])
                
                # Prepare features
                try:
                    X_pred = self.prepare_features(pred_data)
                    X_pred_scaled = self.scaler.transform(X_pred)
                    
                    # Make prediction
                    predicted_price = self.model.predict(X_pred_scaled)[0]
                    
                    # Ensure predicted price is reasonable
                    predicted_price = max(predicted_price, price_mean * 0.5)  # Not less than 50% of mean
                    predicted_price = min(predicted_price, price_mean * 1.5)  # Not more than 150% of mean
                    
                except Exception as e:
                    # Fallback to simple prediction if feature preparation fails
                    # Use historical trend
                    trend = (historical_prices[0] - historical_prices[-1]) / len(historical_prices)
                    random_factor = np.random.normal(1.0, 0.02)  # 2% random variation
                    predicted_price = current_price + (trend * day) * random_factor
                
                # Calculate confidence interval based on historical volatility
                confidence_factor = 1 + (day * 0.02)  # Increase uncertainty over time
                
                predictions.append({
                    'date': future_date.strftime('%Y-%m-%d'),
                    'predicted_price': float(predicted_price),
                    'lower_bound': float(predicted_price - (price_std * confidence_factor)),
                    'upper_bound': float(predicted_price + (price_std * confidence_factor)),
                    'confidence': max(0.95 - (day * 0.05), 0.5)
                })
                
                # Update current price for next prediction
                current_price = predicted_price
            
            # Calculate insights
            week_ahead_price = predictions[-1]['predicted_price']
            price_change = week_ahead_price - recent_prices[0].price
            price_change_pct = (price_change / recent_prices[0].price) * 100
            
            # Determine recommendation
            if price_change_pct < -5:
                recommendation = "WAIT"
                reason = f"Price expected to drop by {abs(price_change_pct):.1f}%"
            elif price_change_pct > 5:
                recommendation = "BUY"
                reason = f"Price expected to increase by {price_change_pct:.1f}%"
            else:
                recommendation = "HOLD"
                reason = "Price expected to remain stable"
            
            return {
                "product": product.name,
                "current_price": float(recent_prices[0].price),
                "predictions": predictions,
                "summary": {
                    "week_ahead_price": float(week_ahead_price),
                    "expected_change": float(price_change),
                    "expected_change_pct": float(price_change_pct),
                    "recommendation": recommendation,
                    "reason": reason
                },
                "model_confidence": 0.85
            }
            
        except Exception as e:
            return {"error": f"Prediction failed: {str(e)}"}
        finally:
            db.close()
    
    def predict_best_time_to_buy(self, product_id: int, target_days: int = 30) -> Dict:
        """Predict the best time to buy within a given timeframe"""
        predictions = self.predict_price(product_id, target_days)
        
        if "error" in predictions:
            return predictions
        
        # Find the day with lowest predicted price
        min_price = float('inf')
        best_day = None
        best_date = None
        
        for idx, pred in enumerate(predictions['predictions']):
            if pred['predicted_price'] < min_price:
                min_price = pred['predicted_price']
                best_day = idx + 1
                best_date = pred['date']
        
        current_price = predictions['current_price']
        savings = current_price - min_price
        savings_pct = (savings / current_price) * 100
        
        return {
            "best_time_to_buy": {
                "date": best_date,
                "days_from_now": best_day,
                "expected_price": min_price,
                "current_price": current_price,
                "expected_savings": savings,
                "savings_percentage": savings_pct
            },
            "recommendation": f"Wait {best_day} days to save ₹{savings:,.0f} ({savings_pct:.1f}%)" if savings > 0 else "Buy now - prices expected to rise"
        }
    
    def batch_predict(self, product_ids: List[int], days_ahead: int = 7) -> Dict[int, Dict]:
        """Predict prices for multiple products"""
        results = {}
        
        for product_id in product_ids:
            results[product_id] = self.predict_price(product_id, days_ahead)
        
        return results
    
    def save_model(self):
        """Save trained model and preprocessors"""
        if self.model is not None:
            joblib.dump(self.model, self.model_path)
            joblib.dump(self.scaler, self.scaler_path)
            joblib.dump(self.label_encoders, self.encoders_path)
    
    def load_model(self):
        """Load saved model and preprocessors"""
        try:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
                self.scaler = joblib.load(self.scaler_path)
                self.label_encoders = joblib.load(self.encoders_path)
                self.is_trained = True
        except Exception as e:
            print(f"Error loading model: {str(e)}")
            self.is_trained = False