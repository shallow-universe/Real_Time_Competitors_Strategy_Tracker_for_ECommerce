import os
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
from transformers import BertTokenizer, BertForSequenceClassification
import torch
from prophet import Prophet

# ---------------- Streamlit Page Config ----------------
st.set_page_config(
    page_title="E-Commerce Competitor Strategy Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.main-header {font-size:2.3rem;color:#1f77b4;text-align:center;margin-bottom:1rem;}
.section-header {font-size:1.6rem;color:#2e86ab;margin-top:2rem;margin-bottom:1rem;}
.positive-sentiment { color:#28a745; }
.negative-sentiment { color:#dc3545; }
.neutral-sentiment  { color:#ffc107; }
</style>
""", unsafe_allow_html=True)

# ---------------- Load BERT Sentiment Model ----------------
@st.cache_resource
def load_bert_model():
    tokenizer = BertTokenizer.from_pretrained("nlptown/bert-base-multilingual-uncased-sentiment")
    bert_model = BertForSequenceClassification.from_pretrained("nlptown/bert-base-multilingual-uncased-sentiment")

    return tokenizer, bert_model

tokenizer, bert_model = load_bert_model()

# ---------------- Competitor Analyzer ----------------
class CompetitorAnalyzer:
    def __init__(self):
        self.products_df = None
        self.reviews_df = None

    def analyze_sentiment(self, text):
        inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=128)
        with torch.no_grad():
            outputs = bert_model(**inputs)
            probs = torch.nn.functional.softmax(outputs.logits, dim=1)
            pred = torch.argmax(probs, dim=1).item()
            score = probs[0][pred].item()

        # Map 5-star model into 5 categories
        star_labels = {
            0: "very negative",  # 1 star
            1: "negative",       # 2 stars
            2: "neutral",        # 3 stars
            3: "positive",       # 4 stars
            4: "very positive"   # 5 stars
        }
        return star_labels[pred], score

    def get_sentiment_analysis(self, product_name):
        df = self.reviews_df[self.reviews_df["product_name"] == product_name].copy()
        if df.empty:
            return None

        sentiments = []
        for r in df["review_text"]:
            s, sc = self.analyze_sentiment(r)
            sentiments.append({"sentiment": s, "score": sc})

        s_df = pd.DataFrame(sentiments)
        return {
            "total_reviews": len(df),
            "sentiment_distribution": s_df["sentiment"].value_counts().to_dict(),
            "average_sentiment_score": s_df["score"].mean(),
            "reviews_data": df
        }


# ---------------- Dashboard Sections ----------------
def product_analysis(analyzer, product_name):
    st.markdown('<div class="section-header">Product Analysis</div>', unsafe_allow_html=True)
    prod = analyzer.products_df.query("`product_name` == @product_name").iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Price", f"₹{int(prod['price'])}")
    c2.metric("Discount", f"{prod['discount']}%")
    c3.metric("Rating", f"{prod['rating']}/5")
    c4.metric("Source", prod["source"])

    # ---- Sentiment ----
    st.subheader("Customer Sentiment")
    sdata = analyzer.get_sentiment_analysis(product_name)
    if sdata:
        col1, col2 = st.columns([2, 1])
        with col1:
            fig = px.pie(values=list(sdata["sentiment_distribution"].values()),
                         names=list(sdata["sentiment_distribution"].keys()),
                         title="Sentiment Distribution")
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            st.metric("Total Reviews", sdata["total_reviews"])
            st.metric("Avg Sentiment Score", f"{sdata['average_sentiment_score']:.2f}")
        st.markdown("### Recent Reviews")
        for _, r in sdata["reviews_data"].head(5).iterrows():
            sent, sc = analyzer.analyze_sentiment(r["review_text"])
            with st.expander(f"{r['userid']} - Rating: {r['rating']}"):
                st.write(r["review_text"])
                st.write(f"Sentiment: **{sent}** (score {sc:.2f})")
    else:
        st.info("No reviews available.")

def competitor_comparison(analyzer, product_name):
    st.markdown('<div class="section-header">Competitor Comparison</div>', unsafe_allow_html=True)
    source = analyzer.products_df.query("`product_name`==@product_name")["source"].iloc[0]
    comp = analyzer.products_df.query("source==@source and product_name!=@product_name")
    if comp.empty:
        st.info("No competitor data available.")
        return

    fig = px.bar(comp, x="product_name", y="price", color="price",
                 title=f"Competitor Price Comparison ({source})")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(comp[["product_name", "price", "discount", "rating", "url"]])

def strategic_recommendations(analyzer, product_name):
    st.markdown('<div class="section-header">Strategic Recommendations</div>', unsafe_allow_html=True)
    prod = analyzer.products_df.query("`product_name`==@product_name").iloc[0]
    sdata = analyzer.get_sentiment_analysis(product_name)

    avg_score = sdata["average_sentiment_score"] if sdata else 0
    strategy_lines = []
    if prod["price"] > 50000:
        strategy_lines.append(f"- High price detected (₹{prod['price']}). Consider discounts or EMI options.")
    elif prod["price"] < 20000:
        strategy_lines.append(f"- Competitive price (₹{prod['price']}) can be leveraged with marketing.")
    if prod["discount"] < 5:
        strategy_lines.append(f"- Current discount is low ({prod['discount']}%). Increase discounts to attract buyers.")
    elif prod["discount"] > 20:
        strategy_lines.append(f"- Generous discount ({prod['discount']}%) observed. Maintain for high conversions.")
    if avg_score < 0.2:
        strategy_lines.append("- Sentiment is neutral/negative. Improve features or customer service.")
    else:
        strategy_lines.append("- Positive sentiment! Promote strengths in campaigns.")

    st.markdown("### Recommended Strategy")
    st.markdown("\n".join(strategy_lines))

# ---------- Prophet Price Forecast ----------
def price_forecast(analyzer, product_name):
    st.markdown('<div class="section-header">Price Forecast (Prophet)</div>', unsafe_allow_html=True)
    df = analyzer.products_df.query("`product_name` == @product_name")[["product_name", "price"]].copy()
    if df.empty or len(df) < 5:
        st.warning("Not enough historical price data for forecasting.")
        return

    df["ds"] = pd.date_range(end=pd.Timestamp.today(), periods=len(df))
    df.rename(columns={"price": "y"}, inplace=True)

    model = Prophet(daily_seasonality=True)
    model.fit(df)
    future = model.make_future_dataframe(periods=30)
    forecast = model.predict(future)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["ds"], y=df["y"], mode="lines+markers", name="Historical Price"))
    fig.add_trace(go.Scatter(x=forecast["ds"], y=forecast["yhat"], mode="lines", name="Forecasted Price"))
    st.plotly_chart(fig, use_container_width=True)

# ---------------- Main App ----------------
def main():
    st.markdown('<div class="main-header">E-Commerce Competitor Strategy Dashboard</div>', unsafe_allow_html=True)
    analyzer = CompetitorAnalyzer()
    if not analyzer.load_data():
        st.stop()

    section = st.sidebar.radio("Navigate",
                               ["Product Analysis", "Competitor Comparison",
                                "Strategic Recommendations", "Price Forecast"])
    product = st.sidebar.selectbox("Select Product", analyzer.products_df["product_name"].unique())

    if section == "Product Analysis":
        product_analysis(analyzer, product)
    elif section == "Competitor Comparison":
        competitor_comparison(analyzer, product)
    elif section == "Strategic Recommendations":
        strategic_recommendations(analyzer, product)
    elif section == "Price Forecast":
        price_forecast(analyzer, product)

if __name__ == "__main__":
    main()
