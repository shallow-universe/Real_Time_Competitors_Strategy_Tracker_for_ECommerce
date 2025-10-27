from fastapi import FastAPI, BackgroundTasks
from apscheduler.schedulers.background import BackgroundScheduler
import uvicorn
from datetime import datetime
import logging
from services.aggregator import DataAggregator
from services.alerts import AlertService
from db import SessionLocal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Competitor Tracker API")
scheduler = BackgroundScheduler()

# Initialize services
aggregator = DataAggregator()
alert_service = AlertService()

@app.on_event("startup")
async def startup_event():
    """Start the scheduler when the app starts"""
    scheduler.add_job(
        scrape_all_products,
        'interval',
        hours=6,  # Run every 6 hours
        id='scrape_products',
        name='Scrape all products',
        replace_existing=True
    )
    
    scheduler.add_job(
        check_alerts,
        'interval',
        hours=1,  # Check alerts every hour
        id='check_alerts',
        name='Check for alerts',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Scheduler started")

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown the scheduler when the app stops"""
    scheduler.shutdown()
    logger.info("Scheduler stopped")

@app.get("/")
async def root():
    return {
        "message": "Competitor Tracker API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.post("/scrape/{product_id}")
async def scrape_product(product_id: int, background_tasks: BackgroundTasks):
    """Manually trigger scraping for a specific product"""
    background_tasks.add_task(aggregator.scrape_single_product, product_id)
    return {"message": f"Scraping started for product {product_id}"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

def scrape_all_products():
    """Background task to scrape all products"""
    logger.info("Starting scheduled scraping...")
    db = SessionLocal()
    try:
        aggregator.run_aggregation(db)
        logger.info("Scraping completed successfully")
    except Exception as e:
        logger.error(f"Error during scraping: {str(e)}")
    finally:
        db.close()

def check_alerts():
    """Background task to check and send alerts"""
    logger.info("Checking for alerts...")
    db = SessionLocal()
    try:
        alert_service.check_and_send_alerts(db)
        logger.info("Alert check completed")
    except Exception as e:
        logger.error(f"Error checking alerts: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)