from groq import Groq
import os
from typing import Dict, List
import pandas as pd
from sqlalchemy.orm import Session
from db import SessionLocal, Product, Price, Review

class CompetitorChatbot:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.context = self._build_context()
        
    def _build_context(self):
        """Build context from database"""
        db = SessionLocal()
        try:
            # Get recent price data
            recent_prices = db.query(Price).order_by(Price.scraped_at.desc()).limit(100).all()
            
            # Get product information
            products = db.query(Product).all()
            
            context = f"""
            You are an AI assistant for a competitive intelligence system focused on laptop products.
            You have access to real-time data about laptop prices, features, and customer sentiment across different e-commerce platforms in India.
            
            Current database contains:
            - {len(products)} laptop products being tracked
            - Price data from Amazon, Flipkart, and other platforms
            - All prices are in INR (Indian Rupees)
            
            You can help with:
            1. Price comparisons across platforms
            2. Price trend analysis
            3. Identifying best deals and discounts
            4. Competitor pricing strategies
            5. Customer sentiment analysis
            6. Product feature comparisons
            
            Always provide specific, data-driven insights when possible.
            """
            
            return context
        finally:
            db.close()
    
    def chat(self, message: str, chat_history: List[Dict] = None) -> str:
        """Process user message and return response"""
        
        # Prepare messages
        messages = [
            {"role": "system", "content": self.context}
        ]
        
        # Add chat history
        if chat_history:
            for msg in chat_history[-5:]:  # Keep last 5 messages for context
                messages.append(msg)
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        # Check if the query needs data
        if self._needs_data_query(message):
            data_context = self._fetch_relevant_data(message)
            messages.append({"role": "system", "content": f"Relevant data: {data_context}"})
        
        try:
            # Get response from Groq
            completion = self.client.chat.completions.create(
                model="mixtral-8x7b-32768",  # or "llama2-70b-4096"
                messages=messages,
                temperature=0.7,
                max_tokens=1024,
                top_p=1,
                stream=False,
                stop=None
            )
            
            return completion.choices[0].message.content
        
        except Exception as e:
            return f"I apologize, but I encountered an error: {str(e)}. Please try again."
    
    def _needs_data_query(self, message: str) -> bool:
        """Check if the message requires database query"""
        data_keywords = [
            'price', 'cost', 'cheapest', 'expensive', 'discount',
            'trend', 'compare', 'versus', 'vs', 'between',
            'sentiment', 'review', 'rating', 'best', 'worst',
            'deal', 'offer', 'promotion', 'stats', 'data'
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in data_keywords)
    
    def _fetch_relevant_data(self, message: str) -> str:
        """Fetch data relevant to the user's query"""
        db = SessionLocal()
        try:
            data_points = []
            
            # Price-related queries
            if any(word in message.lower() for word in ['price', 'cost', 'cheapest', 'expensive']):
                # Get latest prices
                latest_prices = db.query(Price, Product).join(Product).order_by(
                    Price.scraped_at.desc()
                ).limit(20).all()
                
                price_summary = "Latest laptop prices:\n"
                for price, product in latest_prices:
                    price_summary += f"- {product.name}: ₹{price.price:,.0f}"
                    if price.discount_price:
                        price_summary += f" (Discounted: ₹{price.discount_price:,.0f})"
                    price_summary += f" on {product.platform}\n"
                
                data_points.append(price_summary)
            
            # Sentiment-related queries
            if any(word in message.lower() for word in ['sentiment', 'review', 'rating', 'customer']):
                # Get sentiment summary
                reviews = db.query(Review).limit(50).all()
                if reviews:
                    positive = sum(1 for r in reviews if r.sentiment == 'positive')
                    negative = sum(1 for r in reviews if r.sentiment == 'negative')
                    avg_rating = sum(r.rating for r in reviews) / len(reviews)
                    
                    sentiment_summary = f"Sentiment Analysis: {positive} positive, {negative} negative reviews. Average rating: {avg_rating:.1f}/5"
                    data_points.append(sentiment_summary)
            
            return "\n".join(data_points)
        
        finally:
            db.close()