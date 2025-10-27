from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()
engine = create_engine(os.getenv("DATABASE_URL", "sqlite:///./data/tracker.db"))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)  # ADD THIS LINE
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    brand = Column(String)
    model = Column(String)
    category = Column(String, default="laptop")
    url = Column(String, unique=True)
    platform = Column(String)  # amazon, flipkart, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    
    prices = relationship("Price", back_populates="product")
    reviews = relationship("Review", back_populates="product")
    features = relationship("Feature", back_populates="product")

class Price(Base):
    __tablename__ = "prices"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    price = Column(Float)
    discount_price = Column(Float, nullable=True)
    discount_percentage = Column(Float, nullable=True)
    currency = Column(String, default="INR")
    in_stock = Column(Boolean, default=True)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    
    product = relationship("Product", back_populates="prices")

class Review(Base):
    __tablename__ = "reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    rating = Column(Float)
    title = Column(String)
    content = Column(Text)
    sentiment = Column(String)  # positive, negative, neutral
    sentiment_score = Column(Float)
    review_date = Column(DateTime)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    
    product = relationship("Product", back_populates="reviews")

class Feature(Base):
    __tablename__ = "features"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    processor = Column(String)
    ram = Column(String)
    storage = Column(String)
    display = Column(String)
    graphics = Column(String)
    battery = Column(String)
    weight = Column(String)
    
    product = relationship("Product", back_populates="features")

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String)  # price_drop, new_competitor, sentiment_change
    message = Column(Text)
    product_id = Column(Integer, ForeignKey("products.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    sent = Column(Boolean, default=False)

Base.metadata.create_all(bind=engine)