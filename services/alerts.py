import os
from datetime import datetime
from sqlalchemy.orm import Session
from db import Alert, Product, Price
import requests
import json
import logging

logger = logging.getLogger(__name__)

class AlertService:
    def __init__(self):
        self.slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    
    def create_alert(self, db: Session, alert_type: str, message: str, product_id: int = None):
        """Create a new alert"""
        alert = Alert(
            type=alert_type,
            message=message,
            product_id=product_id,
            created_at=datetime.utcnow(),
            sent=False
        )
        db.add(alert)
        db.commit()
        return alert
    
    def check_and_send_alerts(self, db: Session):
        """Check for unsent alerts and send them"""
        unsent_alerts = db.query(Alert).filter(Alert.sent == False).all()
        
        for alert in unsent_alerts:
            try:
                self.send_alert(alert)
                alert.sent = True
                db.commit()
            except Exception as e:
                logger.error(f"Failed to send alert {alert.id}: {str(e)}")
    
    def send_alert(self, alert: Alert):
        """Send alert via Slack"""
        if not self.slack_webhook_url:
            logger.warning("Slack webhook URL not configured")
            return
        
        # Format message
        emoji_map = {
            'price_drop': '💰',
            'new_competitor': '🆕',
            'sentiment_change': '📊',
            'stock_alert': '📦'
        }
        
        emoji = emoji_map.get(alert.type, '🔔')
        
        payload = {
            "text": f"{emoji} *Competitor Tracker Alert*",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Type:* {alert.type.replace('_', ' ').title()}\n*Message:* {alert.message}\n*Time:* {alert.created_at.strftime('%Y-%m-%d %H:%M')}"
                    }
                }
            ]
        }
        
        response = requests.post(
            self.slack_webhook_url,
            data=json.dumps(payload),
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code != 200:
            raise Exception(f"Slack API error: {response.status_code}")