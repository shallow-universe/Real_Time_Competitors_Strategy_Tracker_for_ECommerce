from transformers import pipeline
import torch
from typing import Dict, List
import re

class SentimentAnalyzer:
    def __init__(self):
        # Use a pre-trained sentiment analysis model
        self.analyzer = pipeline(
            "sentiment-analysis",
            model="nlptown/bert-base-multilingual-uncased-sentiment",
            device=0 if torch.cuda.is_available() else -1
        )
        
    def analyze_review(self, review_text: str) -> Dict:
        """Analyze sentiment of a single review"""
        # Clean text
        cleaned_text = self._clean_text(review_text)
        
        # Get sentiment
        result = self.analyzer(cleaned_text[:512])[0]  # BERT max length
        
        # Convert star rating to sentiment
        label = result['label']
        score = result['score']
        
        sentiment_map = {
            '1 star': 'very_negative',
            '2 stars': 'negative',
            '3 stars': 'neutral',
            '4 stars': 'positive',
            '5 stars': 'very_positive'
        }
        
        return {
            'sentiment': sentiment_map.get(label, 'neutral'),
            'score': score,
            'rating': int(label.split()[0])
        }
    
    def _clean_text(self, text: str) -> str:
        """Clean review text"""
        # Remove URLs
        text = re.sub(r'http\S+', '', text)
        # Remove special characters
        text = re.sub(r'[^a-zA-Z0-9\s\.]', '', text)
        # Remove extra whitespace
        text = ' '.join(text.split())
        return text
    
    def analyze_batch(self, reviews: List[str]) -> List[Dict]:
        """Analyze multiple reviews"""
        results = []
        for review in reviews:
            try:
                result = self.analyze_review(review)
                results.append(result)
            except Exception as e:
                results.append({
                    'sentiment': 'neutral',
                    'score': 0.5,
                    'error': str(e)
                })
        return results
    
    def get_sentiment_summary(self, reviews: List[Dict]) -> Dict:
        """Get summary statistics of sentiments"""
        if not reviews:
            return {}
        
        sentiments = [r.get('sentiment', 'neutral') for r in reviews]
        ratings = [r.get('rating', 3) for r in reviews]
        
        sentiment_counts = {
            'very_positive': sentiments.count('very_positive'),
            'positive': sentiments.count('positive'),
            'neutral': sentiments.count('neutral'),
            'negative': sentiments.count('negative'),
            'very_negative': sentiments.count('very_negative')
        }
        
        return {
            'average_rating': sum(ratings) / len(ratings),
            'sentiment_distribution': sentiment_counts,
            'total_reviews': len(reviews),
            'positive_percentage': (sentiment_counts['very_positive'] + sentiment_counts['positive']) / len(reviews) * 100
        }