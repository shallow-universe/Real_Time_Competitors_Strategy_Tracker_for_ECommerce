"""
Utility functions for the Laptop Price Intelligence System
"""

import streamlit as st
from datetime import datetime, timedelta, time
import pandas as pd
import plotly.graph_objects as go
from typing import Dict, List, Optional
import json
import hashlib

def format_currency(amount: float, currency: str = "INR") -> str:
    """Format amount as currency"""
    if currency == "INR":
        return f"₹{amount:,.0f}"
    elif currency == "USD":
        return f"${amount:,.2f}"
    else:
        return f"{currency} {amount:,.2f}"

def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """Calculate percentage change between two values"""
    if old_value == 0:
        return 0
    return ((new_value - old_value) / old_value) * 100

def get_time_ago(timestamp: datetime) -> str:
    """Get human-readable time difference"""
    now = datetime.utcnow()
    diff = now - timestamp
    
    if diff < timedelta(minutes=1):
        return "just now"
    elif diff < timedelta(hours=1):
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    elif diff < timedelta(days=1):
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff < timedelta(days=7):
        days = diff.days
        return f"{days} day{'s' if days > 1 else ''} ago"
    else:
        return timestamp.strftime("%Y-%m-%d")

def create_sparkline(data: List[float], color: str = "#3b82f6") -> go.Figure:
    """Create a small sparkline chart"""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        y=data,
        mode='lines',
        line=dict(color=color, width=2),
        fill='tozeroy',
        fillcolor=f'rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.1)'
    ))
    
    fig.update_layout(
        height=60,
        showlegend=False,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

def export_dataframe_to_csv(df: pd.DataFrame, filename: str) -> None:
    """Export dataframe to CSV with download button"""
    csv = df.to_csv(index=False)
    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name=filename,
        mime="text/csv"
    )

def get_sentiment_color(sentiment: str) -> str:
    """Get color for sentiment display"""
    sentiment_colors = {
        'very_positive': '#10b981',
        'positive': '#34d399',
        'neutral': '#fbbf24',
        'negative': '#f87171',
        'very_negative': '#dc2626'
    }
    return sentiment_colors.get(sentiment.lower(), '#6b7280')

def validate_url(url: str) -> bool:
    """Validate if URL is from supported platforms"""
    supported_domains = ['amazon.in', 'flipkart.com']
    return any(domain in url.lower() for domain in supported_domains)

def cache_data(key: str, data: any, ttl: int = 3600) -> None:
    """Cache data in session state with TTL"""
    st.session_state[f"cache_{key}"] = {
        'data': data,
        'timestamp': datetime.utcnow(),
        'ttl': ttl
    }

def get_cached_data(key: str) -> Optional[any]:
    """Get cached data if not expired"""
    cache_key = f"cache_{key}"
    if cache_key in st.session_state:
        cache = st.session_state[cache_key]
        if datetime.utcnow() - cache['timestamp'] < timedelta(seconds=cache['ttl']):
            return cache['data']
    return None

def create_metric_card(title: str, value: any, delta: any = None, 
                      icon: str = None, color: str = None) -> str:
    """Create HTML for a metric card"""
    delta_html = ""
    if delta is not None:
        delta_color = "green" if delta > 0 else "red"
        delta_symbol = "↑" if delta > 0 else "↓"
        delta_html = f"""
        <p style='margin: 0; color: {delta_color};'>
            {delta_symbol} {abs(delta)}%
        </p>
        """
    
    icon_html = f"<span style='font-size: 2rem;'>{icon}</span>" if icon else ""
    
    return f"""
    <div class='metric-container' style='background-color: {color or '#ffffff'}; 
         text-align: center; min-height: 120px; display: flex; flex-direction: column; 
         justify-content: center;'>
        {icon_html}
        <h3 style='margin: 10px 0 5px 0;'>{title}</h3>
        <h2 style='margin: 0; color: #1f2937;'>{value}</h2>
        {delta_html}
    </div>
    """

def generate_mock_data(data_type: str, count: int = 10) -> pd.DataFrame:
    """Generate mock data for testing"""
    import random
    
    if data_type == "prices":
        dates = pd.date_range(end=datetime.now(), periods=count, freq='D')
        return pd.DataFrame({
            'date': dates,
            'price': [random.randint(30000, 150000) for _ in range(count)],
            'platform': random.choices(['amazon', 'flipkart'], k=count)
        })
    
    elif data_type == "reviews":
        return pd.DataFrame({
            'rating': [random.uniform(1, 5) for _ in range(count)],
            'sentiment': random.choices(['positive', 'negative', 'neutral'], k=count),
            'date': pd.date_range(end=datetime.now(), periods=count, freq='D')
        })
    
    return pd.DataFrame()

def show_loading_animation(message: str = "Loading..."):
    """Show custom loading animation"""
    with st.spinner(message):
        placeholder = st.empty()
        for i in range(3):
            placeholder.markdown(f"""
            <div style='text-align: center;'>
                <div style='display: inline-block; animation: pulse 1.5s infinite;'>
                    {'●' * (i + 1)}
                </div>
            </div>
            """, unsafe_allow_html=True)
            time.sleep(0.3)
        placeholder.empty()