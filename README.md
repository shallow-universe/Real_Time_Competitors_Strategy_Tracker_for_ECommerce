# 🧠 AI-Powered Price Intelligence Dashboard

An advanced **Streamlit + FastAPI** application that combines **web scraping, machine learning, and real-time analytics** to monitor, predict, and analyze product prices across e-commerce platforms.

---

## 🚀 Features

### 🔍 Product Tracking
- Automatically scrapes product prices and discount information from multiple platforms (Amazon, Flipkart, etc.)
- Stores product and price history in a PostgreSQL database

### 🤖 AI-Powered Predictions
- Ensemble ML model (Random Forest + Gradient Boosting)
- Predicts future prices for 7, 14, 21, or 30 days
- Confidence intervals and visualized prediction charts
- Recommendation engine that suggests:
  - **💚 WAIT** if prices are expected to drop  
  - **⚡ BUY** if prices are at their lowest  
  - **📊 HOLD** if trends are neutral  

### 📈 Interactive Price Analysis
- Visualizes 90-day historical data  
- Shows volatility, risk, and market behavior  
- Detects best days and months to buy  
- Highlights price drops and seasonal patterns  

### 🎯 Smart Alerts
- Create custom price thresholds  
- Automatically notifies when price conditions are met  
- Alert categories: Active, Warning, Critical  
- Fully styled **dark blue theme UI**

### 💬 AI Assistant
- Built-in conversational agent for:
  - Explaining price patterns  
  - Summarizing predictions  
  - Finding best deals  
  - Suggesting purchase timing  

---

## 🧩 Tech Stack

| Component | Technology |
|------------|-------------|
| **Frontend** | Streamlit (Custom Dark Blue Theme) |
| **Backend API** | FastAPI |
| **Database** | PostgreSQL + SQLAlchemy ORM |
| **Scraping** | BeautifulSoup, Requests, Asyncio |
| **Machine Learning** | Scikit-learn (Random Forest, Gradient Boosting) |
| **Visualization** | Plotly, Altair |
| **Authentication** | JWT-based login system |
| **Containerization** | Docker, Docker Compose |

---

## ⚙️ Setup & Installation

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/yourusername/price-intelligence-dashboard.git
cd price-intelligence-dashboard
2️⃣ Create and Activate Virtual Environment
bash
Copy code
python -m venv myenv
myenv\\Scripts\\activate   # (Windows)
source myenv/bin/activate  # (Mac/Linux)
3️⃣ Install Dependencies
bash
Copy code
pip install -r requirements.txt
4️⃣ Setup Environment Variables
Create a .env file in the root directory:

env
Copy code
DATABASE_URL=postgresql://username:password@localhost:5432/price_db
SECRET_KEY=your_secret_key
ALGORITHM=HS256
5️⃣ Initialize Database
bash
Copy code
python seed_db.py
6️⃣ Run FastAPI Backend
bash
Copy code
uvicorn main:app --reload
7️⃣ Run Streamlit Frontend
bash
Copy code
streamlit run app.py
Access the dashboard at 👉 http://localhost:8501

🧠 AI Model Overview
The ensemble model is trained on:

Historical product price data

Time-based features (day, week, month)

Discount trends and moving averages

It uses Random Forest Regressor and Gradient Boosting Regressor, combined via weighted averaging for robust predictions.



🧑‍💻 Author
Dev Shyara

📧 vasudevahir2006@gmail.com

📜 License
This project is licensed under the MIT License – free to use, modify, and distribute with attribution.

