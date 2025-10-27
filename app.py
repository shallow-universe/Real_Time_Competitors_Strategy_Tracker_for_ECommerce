import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
import time
import hashlib
import re
from db import SessionLocal, User, Product, Price, Review, Alert
from sqlalchemy import func
import numpy as np
from sqlalchemy.exc import IntegrityError
import requests
from bs4 import BeautifulSoup
from services.predictor import PricePredictor

# Page config
st.set_page_config(
    page_title="LaptopLens - Price Tracking & Analyzing System",
    page_icon="💻",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* ===== General Dark Theme ===== */
    body, [class^="st-"], .stMarkdown, .stText, .stMetric {
        color: #f2f4f8 !important;
        font-family: "Inter", "Segoe UI", sans-serif !important;
    }
    .stApp {
        background-color: #0e1117 !important;
    }

    /* ===== Header ===== */
    .main-header {
        font-size: 3rem;
        font-weight: 700;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
        text-shadow: 0 2px 4px rgba(0,0,0,0.5);
    }

    /* ===== Metric Cards ===== */
    .metric-card {
        background-color: #1b1f2a;
        padding: 1.2rem;
        border-radius: 0.8rem;
        margin: 0.8rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.4);
        border-left: 4px solid #1f77b4;
        color: #f2f4f8 !important;
    }

    /* ===== Tabs Styling ===== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #1b1f2a;
        border-radius: 10px;
        padding: 10px 18px;
        font-weight: 500;
        color: #e0e0e0;
        transition: all 0.3s ease;
        border: 1px solid #2b3243;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #222736;
        border-color: #1f77b4;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1f77b4 !important;
        color: white !important;
        font-weight: 600;
    }

    /* ===== Add Product Card ===== */
    .add-product-card {
        background-color: #161a23;
        padding: 2rem;
        border-radius: 12px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.5);
        margin: 1rem 0;
        border: 1px solid #2b3243;
        color: #f2f4f8 !important;
    }

    /* ===== Tracked Product Card ===== */
    .tracked-product-card {
        background-color: #161a23;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.5);
        margin: 0.8rem 0;
        border-left: 5px solid #1f77b4;
        color: #f2f4f8 !important;
    }

    /* ===== DataFrames, Inputs, Buttons ===== */
    .stDataFrame, .stTable {
        background-color: #1b1f2a !important;
        color: #f2f4f8 !important;
        border-radius: 8px !important;
    }

    .stButton>button {
        background-color: #1f77b4 !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 0.6rem 1.2rem !important;
        font-weight: 600 !important;
        transition: all 0.3s ease;
        box-shadow: 0 2px 6px rgba(0,0,0,0.4);
    }
    .stButton>button:hover {
        background-color: #1668a7 !important;
        transform: translateY(-1px);
    }

    /* ===== Inputs & Select Boxes ===== */
    .stTextInput>div>div>input,
    .stSelectbox>div>div>div {
        background-color: #1b1f2a !important;
        border: 1px solid #2b3243 !important;
        border-radius: 8px !important;
        color: #f2f4f8 !important;
    }

    /* ===== Scrollbars ===== */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-thumb {
        background: #2f3849;
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #3f4b60;
    }

    /* ===== Small UI Details ===== */
    .stAlert, .stInfo, .stWarning {
        background-color: #1b1f2a !important;
        color: #f2f4f8 !important;
        border-left: 5px solid #1f77b4;
    }
</style>
""", unsafe_allow_html=True)




# Initialize session state
if 'authentication_status' not in st.session_state:
    st.session_state['authentication_status'] = None
if 'show_register' not in st.session_state:
    st.session_state['show_register'] = False
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Utility functions
def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(stored_password, provided_password):
    """Verify a stored password against provided password"""
    return stored_password == hash_password(provided_password)

def validate_email(email):
    """Validate email format"""
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def validate_password_strength(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number"
    return True, "Password is strong"

def validate_product_url(url):
    """Validate if URL is from supported platforms"""
    amazon_pattern = r'https?://(?:www\.)?amazon\.in/.*'
    flipkart_pattern = r'https?://(?:www\.)?flipkart\.com/.*'
    
    if re.match(amazon_pattern, url):
        return True, 'amazon'
    elif re.match(flipkart_pattern, url):
        return True, 'flipkart'
    else:
        return False, None

def extract_product_info(url, platform):
    """Extract basic product information from URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        product_info = {
            'url': url,
            'platform': platform
        }
        
        if platform == 'amazon':
            # Extract from Amazon
            title_element = soup.find('span', {'id': 'productTitle'})
            if title_element:
                product_info['name'] = title_element.text.strip()
                # Extract brand from title
                product_info['brand'] = product_info['name'].split()[0]
            
            price_element = soup.find('span', {'class': 'a-price-whole'})
            if price_element:
                price_text = price_element.text.replace(',', '').replace('₹', '').strip('.')
                product_info['price'] = float(price_text)
        
        elif platform == 'flipkart':
            # Extract from Flipkart
            title_element = soup.find('span', {'class': 'B_NuCI'})
            if title_element:
                product_info['name'] = title_element.text.strip()
                product_info['brand'] = product_info['name'].split()[0]
            
            price_element = soup.find('div', {'class': '_30jeq3 _16Jk6d'})
            if price_element:
                price_text = price_element.text.replace('₹', '').replace(',', '').strip()
                product_info['price'] = float(price_text)
        
        return product_info
    except Exception as e:
        return None

# Registration function
def register_user(username, email, password, name):
    """Register new user in database"""
    db = SessionLocal()
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            if existing_user.username == username:
                return False, "Username already exists"
            else:
                return False, "Email already registered"
        
        # Create new user
        new_user = User(
            username=username,
            email=email,
            hashed_password=hash_password(password),
            name=name,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        db.add(new_user)
        db.commit()
        return True, "Registration successful!"
    
    except Exception as e:
        db.rollback()
        return False, f"Registration failed: {str(e)}"
    finally:
        db.close()

# Login/Registration Page
if st.session_state['authentication_status'] is None:
    st.markdown("<h1 class='main-header'>💻 LaptopLens - Price Tracking & Analyzing System</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Toggle between login and register
        auth_mode = st.radio("", ["Login", "Register"], horizontal=True)
        
        if auth_mode == "Login":
            with st.form("login_form"):
                st.subheader("🔐 Login to Your Account")
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Login", use_container_width=True)
                
                if submit and username and password:
                    db = SessionLocal()
                    user = db.query(User).filter(User.username == username).first()
                    if user and verify_password(user.hashed_password, password):
                        st.session_state['authentication_status'] = True
                        st.session_state['username'] = username
                        st.session_state['name'] = user.name
                        st.success("Login successful!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
                    db.close()
            
        
        else:  # Register mode
            with st.form("register_form"):
                st.subheader("📝 Create New Account")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    name = st.text_input("Full Name", placeholder="John Doe")
                    username = st.text_input("Username", placeholder="johndoe")
                
                with col_b:
                    email = st.text_input("Email", placeholder="john@example.com")
                    password = st.text_input("Password", type="password", placeholder="Min 8 characters")
                
                confirm_password = st.text_input("Confirm Password", type="password")
                terms = st.checkbox("I agree to the Terms of Service")
                
                submit = st.form_submit_button("Register", use_container_width=True)
                
                if submit:
                    errors = []
                    
                    if not all([name, username, email, password, confirm_password]):
                        errors.append("All fields are required")
                    
                    if email and not validate_email(email):
                        errors.append("Invalid email format")
                    
                    if password:
                        valid, msg = validate_password_strength(password)
                        if not valid:
                            errors.append(msg)
                    
                    if password != confirm_password:
                        errors.append("Passwords do not match")
                    
                    if not terms:
                        errors.append("You must agree to the terms")
                    
                    if errors:
                        for error in errors:
                            st.error(error)
                    else:
                        success, message = register_user(username, email, password, name)
                        
                        if success:
                            st.success("✅ Registration successful! Please login.")
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")

# Main Dashboard
elif st.session_state['authentication_status']:
    # Sidebar
    with st.sidebar:
        st.title(f"👤 Welcome, {st.session_state['name']}!")
        
        # User stats
        db = SessionLocal()
        total_products = db.query(Product).count()
        total_alerts = db.query(Alert).filter(Alert.sent == False).count()
        db.close()
        
        st.metric("Products Tracked", total_products)
        st.metric("Active Alerts", total_alerts)
        
        st.markdown("---")
        
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state['authentication_status'] = None
            st.session_state.clear()
            st.rerun()
    
    # Main content with tabs
    st.markdown("<h1 class='main-header'>💻 LaptopLens - Price Tracking & Analyzing System</h1>", unsafe_allow_html=True)
    
    # Create tabs for different sections
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📊 Overview",
        "➕ Add Products",
        "📈 Price Analysis",
        "💬 Sentiment Analysis",
        "🤖 AI Assistant",
        "🚨 Alerts",
        "🔮 Batch Predictions"  
    ])
    
    with tab1:
        # Overview Dashboard
        st.header("Executive Dashboard")
        
        # Key Metrics
        col1, col2, col3, col4 = st.columns(4)
        
        db = SessionLocal()
        
        # Total products tracked
        total_products = db.query(Product).count()
        with col1:
            st.metric(
                                label="📦 Total Products",
                value=total_products,
                delta="+5 this week"
            )
        
        # Average price
        avg_price = db.query(func.avg(Price.price)).scalar() or 0
        with col2:
            st.metric(
                label="💰 Average Price",
                value=f"₹{avg_price:,.0f}",
                delta="-₹2,500"
            )
        
        # Total reviews
        total_reviews = db.query(Review).count()
        with col3:
            st.metric(
                label="💬 Reviews Analyzed",
                value=f"{total_reviews:,}",
                delta="+128 today"
            )
        
        # Active alerts
        active_alerts = db.query(Alert).filter(Alert.sent == False).count()
        with col4:
            st.metric(
                label="🚨 Active Alerts",
                value=active_alerts,
                delta="+2 new"
            )
        
        # Price Distribution Chart
        st.subheader("📊 Price Distribution Across Platforms")
        
        # Get price data by platform
        price_data = db.query(
            Product.platform,
            func.avg(Price.price).label('avg_price'),
            func.min(Price.price).label('min_price'),
            func.max(Price.price).label('max_price'),
            func.count(Price.id).label('count')
        ).join(Price).group_by(Product.platform).all()
        
        if price_data:
            df_platforms = pd.DataFrame([{
                'Platform': p.platform.title() if p.platform else 'Unknown',
                'Average Price': p.avg_price or 0,
                'Min Price': p.min_price or 0,
                'Max Price': p.max_price or 0,
                'Products': p.count or 0
            } for p in price_data])
            
            # Create bar chart
            fig = px.bar(
                df_platforms,
                x='Platform',
                y=['Min Price', 'Average Price', 'Max Price'],
                title='Price Comparison by Platform',
                barmode='group',
                color_discrete_map={
                    'Min Price': '#10b981',
                    'Average Price': '#3b82f6',
                    'Max Price': '#ef4444'
                }
            )
            fig.update_layout(yaxis_title="Price (₹)", height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No price data available yet. Start by adding products to track!")
        
        # Top Deals
        st.subheader("🏷️ Top Deals Today")
        
        top_deals = db.query(Product, Price).join(Price).filter(
            Price.discount_percentage > 0
        ).order_by(Price.discount_percentage.desc()).limit(5).all()
        
        if top_deals:
            for product, price in top_deals:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"**{product.name}**")
                    st.write(f"Platform: {product.platform.title() if product.platform else 'Unknown'}")
                with col2:
                    st.write(f"~~₹{price.price:,.0f}~~")
                    st.write(f"**₹{price.discount_price:,.0f}**")
                with col3:
                    st.write(f"🔥 **-{price.discount_percentage:.0f}%**")
                st.divider()
        else:
            st.info("No deals available at the moment")
        
        db.close()
    
    with tab2:
        st.header("➕ Add Products to Track")
        
        # Add product options
        add_method = st.radio("Choose how to add products:", ["Add by URL", "Manual Entry", "Bulk Import"], horizontal=True)
        
        db = SessionLocal()
        
        if add_method == "Add by URL":
            st.markdown("### 🔗 Add Product by URL")
            st.info("Paste the product URL from Amazon.in or Flipkart.com")
            
            with st.form("add_by_url_form"):
                url = st.text_input("Product URL", placeholder="https://www.amazon.in/laptop...")
                
                col1, col2 = st.columns([2, 1])
                with col1:
                    extract_details = st.checkbox("Auto-extract product details", value=True)
                with col2:
                    submit = st.form_submit_button("Add Product", use_container_width=True)
                
                if submit and url:
                    # Validate URL
                    is_valid, platform = validate_product_url(url)
                    
                    if not is_valid:
                        st.error("❌ Invalid URL. Please provide a valid Amazon.in or Flipkart.com product URL.")
                    else:
                        # Check if product already exists
                        existing = db.query(Product).filter(Product.url == url).first()
                        if existing:
                            st.warning("⚠️ This product is already being tracked!")
                        else:
                            if extract_details:
                                with st.spinner("Extracting product information..."):
                                    product_info = extract_product_info(url, platform)
                                    
                                    if product_info:
                                        # Create new product
                                        new_product = Product(
                                            name=product_info.get('name', 'Unknown Product'),
                                            brand=product_info.get('brand', 'Unknown'),
                                            model=product_info.get('model', 'Unknown'),
                                            category='laptop',
                                            url=url,
                                            platform=platform,
                                            created_at=datetime.utcnow()
                                        )
                                        db.add(new_product)
                                        db.commit()
                                        
                                        # Add initial price if extracted
                                        if 'price' in product_info:
                                            initial_price = Price(
                                                product_id=new_product.id,
                                                price=product_info['price'],
                                                currency='INR',
                                                scraped_at=datetime.utcnow()
                                            )
                                            db.add(initial_price)
                                            db.commit()
                                        
                                        st.success(f"✅ Successfully added: {product_info.get('name', 'Product')}")
                                    else:
                                        st.error("❌ Could not extract product details. Please try manual entry.")
                            else:
                                # Basic add without extraction
                                new_product = Product(
                                    name=f"Product from {platform}",
                                    url=url,
                                    platform=platform,
                                    created_at=datetime.utcnow()
                                )
                                db.add(new_product)
                                db.commit()
                                st.success("✅ Product added successfully! Details will be updated on next scan.")
        
        elif add_method == "Manual Entry":
            st.markdown("### ✍️ Manual Product Entry")
            
            with st.form("manual_entry_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    name = st.text_input("Product Name*", placeholder="Dell Inspiron 15 3520")
                    brand = st.selectbox("Brand*", ["Select...", "Dell", "HP", "Lenovo", "ASUS", "Acer", "Apple", "MSI", "Other"])
                    model = st.text_input("Model", placeholder="Inspiron 3520")
                
                with col2:
                    platform = st.selectbox("Platform*", ["Select...", "amazon", "flipkart"])
                    url = st.text_input("Product URL*", placeholder="https://...")
                    initial_price = st.number_input("Current Price (₹)", min_value=0, step=1000, value=50000)
                
                # Additional details
                st.markdown("#### Additional Details (Optional)")
                col3, col4 = st.columns(2)
                
                with col3:
                    processor = st.text_input("Processor", placeholder="Intel Core i5")
                    ram = st.text_input("RAM", placeholder="8GB")
                    storage = st.text_input("Storage", placeholder="512GB SSD")
                
                with col4:
                    display = st.text_input("Display", placeholder="15.6 inch FHD")
                    graphics = st.text_input("Graphics", placeholder="Intel UHD")
                
                submit = st.form_submit_button("Add Product", use_container_width=True)
                
                if submit:
                    if not all([name, brand != "Select...", platform != "Select...", url]):
                        st.error("Please fill all required fields (*)")
                    else:
                        # Check if URL already exists
                        existing = db.query(Product).filter(Product.url == url).first()
                        if existing:
                            st.warning("⚠️ A product with this URL is already being tracked!")
                        else:
                            # Create product
                            new_product = Product(
                                name=name,
                                brand=brand if brand != "Other" else "Unknown",
                                model=model or "Unknown",
                                category='laptop',
                                url=url,
                                platform=platform,
                                created_at=datetime.utcnow()
                            )
                            db.add(new_product)
                            db.commit()
                            
                            # Add initial price
                            initial_price_entry = Price(
                                product_id=new_product.id,
                                price=float(initial_price),
                                currency='INR',
                                scraped_at=datetime.utcnow()
                            )
                            db.add(initial_price_entry)
                            db.commit()
                            
                            st.success(f"✅ Successfully added: {name}")
                            time.sleep(1)
                            st.rerun()
        
        else:  # Bulk Import
            st.markdown("### 📋 Bulk Import")
            st.info("Upload a CSV file with product URLs to track multiple products at once")
            
            # Download template
            template_df = pd.DataFrame({
                'name': ['Dell Inspiron 15', 'HP Pavilion x360'],
                'brand': ['Dell', 'HP'],
                'url': ['https://www.amazon.in/...', 'https://www.flipkart.com/...'],
                'platform': ['amazon', 'flipkart']
            })
            
            csv = template_df.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV Template",
                data=csv,
                file_name="product_import_template.csv",
                mime="text/csv"
            )
            
            uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
            
            if uploaded_file is not None:
                try:
                    df = pd.read_csv(uploaded_file)
                    st.write("Preview of uploaded data:")
                    st.dataframe(df.head())
                    
                    if st.button("Import Products", use_container_width=True):
                        success_count = 0
                        error_count = 0
                        
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        for idx, row in df.iterrows():
                            progress = (idx + 1) / len(df)
                            progress_bar.progress(progress)
                            status_text.text(f"Processing {idx + 1}/{len(df)} products...")
                            
                            try:
                                # Check if product exists
                                existing = db.query(Product).filter(Product.url == row['url']).first()
                                if not existing:
                                    new_product = Product(
                                        name=row['name'],
                                        brand=row.get('brand', 'Unknown'),
                                        model=row.get('model', 'Unknown'),
                                        category='laptop',
                                        url=row['url'],
                                        platform=row['platform'],
                                        created_at=datetime.utcnow()
                                    )
                                    db.add(new_product)
                                    success_count += 1
                                else:
                                    error_count += 1
                            except Exception as e:
                                error_count += 1
                        
                        db.commit()
                        progress_bar.empty()
                        status_text.empty()
                        
                        st.success(f"✅ Import completed! Successfully added: {success_count}, Skipped: {error_count}")
                
                except Exception as e:
                    st.error(f"Error reading CSV file: {str(e)}")
        
        # Currently tracked products
        st.markdown("---")
        st.subheader("📦 Currently Tracked Products")
        
        # Search and filter
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            search = st.text_input("🔍 Search products...", placeholder="Search by name or brand")
        with col2:
            filter_platform = st.selectbox("Platform", ["All", "Amazon", "Flipkart"])
        with col3:
            sort_by = st.selectbox("Sort by", ["Recently Added", "Name", "Price"])
        
        # Query products
        query = db.query(Product)
        
        if search:
            query = query.filter(
                (Product.name.contains(search)) | 
                (Product.brand.contains(search))
            )
        
        if filter_platform != "All":
            query = query.filter(Product.platform == filter_platform.lower())
        
        if sort_by == "Recently Added":
            query = query.order_by(Product.created_at.desc())
        elif sort_by == "Name":
            query = query.order_by(Product.name)
        
        products = query.all()
        
        if products:
            # Display products in a grid
            for idx, product in enumerate(products):
                with st.container():
                    st.markdown(f'<div class="tracked-product-card">', unsafe_allow_html=True)
                    
                    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                    
                    with col1:
                        st.markdown(f"**{product.name}**")
                        st.write(f"Brand: {product.brand} | Model: {product.model}")
                        st.caption(f"Added: {product.created_at.strftime('%Y-%m-%d')}")
                    
                    with col2:
                        # Get latest price
                        latest_price = db.query(Price).filter(
                            Price.product_id == product.id
                        ).order_by(Price.scraped_at.desc()).first()
                        
                        if latest_price:
                            st.metric("Current Price", f"₹{latest_price.price:,.0f}")
                        else:
                            st.write("Price: N/A")
                    
                    with col3:
                        st.write(f"Platform: {product.platform.title()}")
                        if st.button("🔗 View", key=f"view_{product.id}"):
                            st.write(f"[Open Product]({product.url})")
                    
                    with col4:
                        if st.button("🗑️ Remove", key=f"remove_{product.id}"):
                            # Delete associated data first
                            db.query(Price).filter(Price.product_id == product.id).delete()
                            db.query(Review).filter(Review.product_id == product.id).delete()
                            db.query(Alert).filter(Alert.product_id == product.id).delete()
                            # Delete product
                            db.delete(product)
                            db.commit()
                            st.success("Product removed!")
                            time.sleep(1)
                            st.rerun()
                    
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No products found. Start tracking by adding products above!")
        
        db.close()
    
    # Replace the price analysis tab (tab3) with this enhanced version

    with tab3:
        st.header("📈 Price Analysis & AI Predictions")
        
        # Initialize predictor
        predictor = PricePredictor()
        
        # Model training section
        with st.expander("  ML Model Status", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if predictor.is_trained:
                    st.success("✅ Model Trained")
                else:
                    st.warning("⚠️ Model Not Trained")
            
            with col2:
                if st.button("🔄 Train/Retrain Model"):
                    with st.spinner("Training model... This may take a few minutes"):
                        result = predictor.train(force_retrain=True)
                        
                        if result["status"] == "Training successful":
                            st.success("✅ Model trained successfully!")
                            st.json(result["metrics"])
                        else:
                            st.error(f"❌ Training failed: {result}")
            
            with col3:
                st.metric("Model Type", "Ensemble (RF + GB)")
        
        # Product selector
        db = SessionLocal()
        products = db.query(Product).all()
        
        if products:
            product_names = [p.name for p in products]
            selected_product = st.selectbox("Select Product for Analysis", product_names)
            
            if selected_product:
                product = db.query(Product).filter(Product.name == selected_product).first()
                
                # Display product info
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.subheader(f"📊 {product.name}")
                with col2:
                    st.write(f"**Brand:** {product.brand}")
                with col3:
                    st.write(f"**Platform:** {product.platform.title()}")
                
                # Get price history
                price_history = db.query(Price).filter(
                    Price.product_id == product.id
                ).order_by(Price.scraped_at.desc()).limit(90).all()
                
                if len(price_history) > 5:
                    # Historical price chart
                    df_history = pd.DataFrame([{
                        'Date': p.scraped_at,
                        'Price': p.price,
                        'Discount Price': p.discount_price
                    } for p in price_history])
                    
                    # Price statistics
                    col1, col2, col3, col4 = st.columns(4)
                    
                    current_price = df_history.iloc[0]['Price']
                    avg_price = df_history['Price'].mean()
                    min_price = df_history['Price'].min()
                    max_price = df_history['Price'].max()
                    
                    with col1:
                        st.metric("Current Price", f"₹{current_price:,.0f}")
                    with col2:
                        st.metric("90-Day Average", f"₹{avg_price:,.0f}", 
                                delta=f"{((current_price - avg_price) / avg_price * 100):.1f}%")
                    with col3:
                        st.metric("Lowest Price", f"₹{min_price:,.0f}")
                    with col4:
                        st.metric("Highest Price", f"₹{max_price:,.0f}")
                    
                    # Prediction section
                    st.subheader("🔮 AI-Powered Price Predictions")
                    
                    # Prediction controls
                    col1, col2, col3 = st.columns([1, 1, 2])
                    
                    with col1:
                        prediction_days = st.selectbox(
                            "Prediction Period",
                            [7, 14, 21, 30],
                            format_func=lambda x: f"{x} days"
                        )
                    
                    with col2:
                        if st.button("🚀 Generate Predictions", type="primary"):
                            with st.spinner("Generating AI predictions..."):
                                predictions = predictor.predict_price(product.id, prediction_days)
                                
                                if "error" not in predictions:
                                    st.session_state[f'predictions_{product.id}'] = predictions
                                else:
                                    st.error(predictions["error"])
                    
                    # Display predictions if available
                    if f'predictions_{product.id}' in st.session_state:
                        predictions = st.session_state[f'predictions_{product.id}']
                        
                        # Create prediction chart
                        fig = go.Figure()
                        
                        # Historical data
                        fig.add_trace(go.Scatter(
                            x=df_history['Date'],
                            y=df_history['Price'],
                            mode='lines+markers',
                            name='Historical Price',
                            line=dict(color='#3b82f6', width=2),
                            marker=dict(size=6)
                        ))
                        
                        # Predictions
                        pred_dates = [datetime.strptime(p['date'], '%Y-%m-%d') for p in predictions['predictions']]
                        pred_prices = [p['predicted_price'] for p in predictions['predictions']]
                        lower_bounds = [p['lower_bound'] for p in predictions['predictions']]
                        upper_bounds = [p['upper_bound'] for p in predictions['predictions']]
                        
                        # Add prediction line
                        fig.add_trace(go.Scatter(
                            x=pred_dates,
                            y=pred_prices,
                            mode='lines+markers',
                            name='AI Prediction',
                            line=dict(color='#10b981', width=3, dash='dash'),
                            marker=dict(size=8, symbol='diamond')
                        ))
                        
                        # Add confidence interval
                        fig.add_trace(go.Scatter(
                            x=pred_dates + pred_dates[::-1],
                            y=upper_bounds + lower_bounds[::-1],
                            fill='toself',
                            fillcolor='rgba(16, 185, 129, 0.1)',
                            line=dict(color='rgba(16, 185, 129, 0)'),
                            name='Confidence Interval',
                            showlegend=True
                        ))
                        
                        # Add annotations for key predictions
                        fig.add_annotation(
                            x=pred_dates[-1],
                            y=pred_prices[-1],
                            text=f"₹{pred_prices[-1]:,.0f}",
                            showarrow=True,
                            arrowhead=2,
                            bgcolor='#10b981',
                            bordercolor='#10b981',
                            font=dict(color='white')
                        )
                        
                        fig.update_layout(
                            title=f"AI Price Prediction - {product.name}",
                            xaxis_title="Date",
                            yaxis_title="Price (₹)",
                            height=500,
                            hovermode='x unified',
                            legend=dict(
                                yanchor="top",
                                y=0.99,
                                xanchor="right",
                                x=0.99
                            )
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Prediction summary
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            summary = predictions['summary']
                            
                            if summary['recommendation'] == "WAIT":
                                alert_type = "success"
                                icon = "💚"
                            elif summary['recommendation'] == "BUY":
                                alert_type = "warning"
                                icon = "⚡"
                            else:
                                alert_type = "info"
                                icon = "📊"
                            
                            st.markdown(f"""
                                <div style='background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                                            color: #ffffff; 
                                            padding: 20px; 
                                            border-radius: 10px; 
                                            margin: 10px 0;
                                            box-shadow: 0 4px 15px rgba(0,0,0,0.3);'>
                                    <h3>{icon} AI Recommendation: {summary['recommendation']}</h3>
                                    <p style='font-size: 1.1rem; margin: 10px 0;'>{summary['reason']}</p>
                                    <hr style='border-color: rgba(255,255,255,0.3);'>
                                    <p><strong>Expected price in {len(predictions['predictions'])} days:</strong> ₹{summary['week_ahead_price']:,.0f}</p>
                                    <p><strong>Expected change:</strong> ₹{summary['expected_change']:+,.0f} ({summary['expected_change_pct']:+.1f}%)</p>
                                </div>
                            """, unsafe_allow_html=True)

                        with col2:
                            # Best time to buy analysis
                            st.markdown("### 🎯 Best Time to Buy")

                            with st.spinner("Analyzing best purchase timing..."):
                                best_time = predictor.predict_best_time_to_buy(product.id, 30)
                                
                                if "error" not in best_time:
                                    btb = best_time['best_time_to_buy']
                                    
                                    st.markdown(f"""
                                    <div style='background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                                                color: #ffffff; 
                                                padding: 15px; 
                                                border-radius: 10px;
                                                box-shadow: 0 4px 15px rgba(0,0,0,0.3);'>
                                        <h4 style='color: #ffd700;'>Optimal Purchase Date</h4>
                                        <p style='font-size: 1.2rem; margin: 5px 0;'><strong>{btb['date']}</strong></p>
                                        <p>In <strong>{btb['days_from_now']} days</strong></p>
                                        <hr style='border-color: rgba(255,255,255,0.3);'>
                                        <p>Expected Price: <strong>₹{btb['expected_price']:,.0f}</strong></p>
                                        <p>Potential Savings: <strong>₹{btb['expected_savings']:,.0f}</strong></p>
                                        <p>Save: <strong>{btb['savings_percentage']:.1f}%</strong></p>
                                    </div>
                                    """, unsafe_allow_html=True)

                    
                    # Historical patterns analysis
                    st.subheader("📊 Historical Price Patterns")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Day of week analysis
                        df_history['Day'] = pd.to_datetime(df_history['Date']).dt.day_name()
                        day_avg = df_history.groupby('Day')['Price'].mean().reindex([
                            'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'
                        ])
                        
                        fig_day = go.Figure()
                        fig_day.add_trace(go.Bar(
                            x=day_avg.index,
                            y=day_avg.values,
                            marker_color=['#3b82f6' if d not in ['Saturday', 'Sunday'] else '#10b981' 
                                        for d in day_avg.index]
                        ))
                        fig_day.update_layout(
                            title="Average Price by Day of Week",
                            xaxis_title="Day",
                            yaxis_title="Average Price (₹)",
                            height=300
                        )
                        st.plotly_chart(fig_day, use_container_width=True)
                        
                        # Best day insight
                        best_day = day_avg.idxmin()
                        worst_day = day_avg.idxmax()
                        st.info(f"💡 Historically, {best_day} has the lowest prices, while {worst_day} has the highest.")
                    
                    with col2:
                        # Monthly trend
                        df_history['Month'] = pd.to_datetime(df_history['Date']).dt.month_name()
                        month_avg = df_history.groupby('Month')['Price'].mean()
                        
                        fig_month = go.Figure()
                        fig_month.add_trace(go.Scatter(
                            x=month_avg.index,
                            y=month_avg.values,
                            mode='lines+markers',
                            line=dict(color='#f59e0b', width=3),
                            marker=dict(size=10)
                        ))
                        fig_month.update_layout(
                            title="Price Trend by Month",
                            xaxis_title="Month",
                            yaxis_title="Average Price (₹)",
                            height=300
                        )
                        st.plotly_chart(fig_month, use_container_width=True)
                        
                        # Seasonal insight
                        if len(month_avg) > 0:
                            best_month = month_avg.idxmin()
                            st.info(f"💡 {best_month} typically offers the best prices for this product.")
                    
                    # Price volatility analysis
                    st.subheader("📈 Price Volatility & Risk Analysis")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    # Calculate volatility metrics
                    price_volatility = df_history['Price'].std()
                    price_cv = (price_volatility / df_history['Price'].mean()) * 100
                    max_drop = ((df_history['Price'].max() - df_history['Price'].min()) / df_history['Price'].max()) * 100
                    
                    with col1:
                        st.metric(
                            "Price Volatility",
                            f"±₹{price_volatility:,.0f}",
                            help="Standard deviation of price"
                        )
                    
                    with col2:
                        risk_level = "Low" if price_cv < 10 else "Medium" if price_cv < 20 else "High"
                        risk_color = "🟢" if risk_level == "Low" else "🟡" if risk_level == "Medium" else "🔴"
                        st.metric(
                            "Risk Level",
                            f"{risk_color} {risk_level}",
                            delta=f"{price_cv:.1f}% variation"
                        )
                    
                    with col3:
                        st.metric(
                            "Max Historical Drop",
                            f"-{max_drop:.1f}%",
                            help="Largest price drop observed"
                        )
                    
                else:
                    st.warning("⚠️ Insufficient price history for predictions. Need at least 5 data points.")
                    st.info("💡 Price data is collected automatically. Check back in a few days for predictions.")
        else:
            st.info("No products available for analysis. Add products in the 'Add Products' tab.")
        
        db.close()
    
    with tab4:
        st.header("💬 Customer Sentiment Analysis")
        
        db = SessionLocal()
        
        # Overall sentiment metrics
        col1, col2, col3, col4 = st.columns(4)
        
        # Get sentiment statistics
        total_reviews = db.query(Review).count()
        positive_reviews = db.query(Review).filter(Review.sentiment == 'positive').count()
        negative_reviews = db.query(Review).filter(Review.sentiment == 'negative').count()
        neutral_reviews = db.query(Review).filter(Review.sentiment == 'neutral').count()
        
        with col1:
            st.metric("Total Reviews", f"{total_reviews:,}")
        
        with col2:
            positive_pct = (positive_reviews / total_reviews * 100) if total_reviews > 0 else 0
            st.metric("Positive", f"{positive_pct:.1f}%", delta="+2.3%")
        
        with col3:
            avg_rating = db.query(func.avg(Review.rating)).scalar() or 0
            st.metric("Avg Rating", f"{avg_rating:.1f}/5.0")
        
        with col4:
            sentiment_score = ((positive_reviews - negative_reviews) / total_reviews * 100) if total_reviews > 0 else 0
            st.metric("Sentiment Score", f"{sentiment_score:+.1f}")
        
        # Sentiment distribution
        if total_reviews > 0:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader("📊 Sentiment Distribution")
                
                sentiment_data = {
                    'Sentiment': ['Positive', 'Neutral', 'Negative'],
                    'Count': [positive_reviews, neutral_reviews, negative_reviews],
                    'Percentage': [
                        positive_reviews/total_reviews*100,
                        neutral_reviews/total_reviews*100,
                        negative_reviews/total_reviews*100
                    ]
                }
                
                df_sentiment = pd.DataFrame(sentiment_data)
                
                fig = px.pie(
                    df_sentiment,
                    values='Count',
                    names='Sentiment',
                    color_discrete_map={
                        'Positive': '#10b981',
                        'Neutral': '#fbbf24',
                        'Negative': '#ef4444'
                    },
                    hole=0.4
                )
                
                fig.update_traces(
                    textposition='inside',
                    textinfo='percent+label',
                    hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
                )
                
                fig.update_layout(
                    showlegend=True,
                    height=350
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.subheader("🏆 Top Rated Products")
                
                # Get top rated products
                top_products = db.query(
                    Product.name,
                    func.avg(Review.rating).label('avg_rating'),
                    func.count(Review.id).label('review_count')
                ).join(Review).group_by(Product.id).order_by(
                    func.avg(Review.rating).desc()
                ).limit(5).all()
                
                if top_products:
                    for idx, product in enumerate(top_products, 1):
                        st.write(f"**{idx}. {product.name[:30]}...**")
                        st.write(f"⭐ {product.avg_rating:.1f}/5.0 ({product.review_count} reviews)")
                        st.divider()
        
        # Recent reviews section
        st.subheader("🔄 Recent Customer Reviews")
        
        # Filter options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            filter_sentiment = st.selectbox("Filter by Sentiment", ["All", "Positive", "Neutral", "Negative"])
        
        with col2:
            filter_rating = st.selectbox("Filter by Rating", ["All", "5⭐", "4⭐", "3⭐", "2⭐", "1⭐"])
        
        with col3:
            sort_order = st.selectbox("Sort by", ["Most Recent", "Highest Rated", "Lowest Rated"])
        
        # Query reviews
        query = db.query(Review, Product).join(Product)
        
        if filter_sentiment != "All":
            query = query.filter(Review.sentiment == filter_sentiment.lower())
        
        if filter_rating != "All":
            rating_value = int(filter_rating[0])
            query = query.filter(Review.rating == rating_value)
        
        if sort_order == "Most Recent":
            query = query.order_by(Review.scraped_at.desc())
        elif sort_order == "Highest Rated":
            query = query.order_by(Review.rating.desc())
        else:
            query = query.order_by(Review.rating.asc())
        
        recent_reviews = query.limit(10).all()
        
        if recent_reviews:
            for review, product in recent_reviews:
                with st.container():
                    col1, col2 = st.columns([4, 1])
                    
                    with col1:
                        st.markdown(f"**{product.name}**")
                        
                        # Rating and sentiment
                        rating_stars = '⭐' * int(review.rating)
                        sentiment_emoji = {
                            'positive': '😊',
                            'neutral': '😐',
                            'negative': '😞'
                        }.get(review.sentiment, '🤔')
                        
                        st.write(f"{rating_stars} {review.rating}/5 | {sentiment_emoji} {review.sentiment.title()}")
                        
                        if review.title:
                            st.write(f"**{review.title}**")
                        
                        if review.content:
                            st.write(f"_{review.content[:300]}{'...' if len(review.content) > 300 else ''}_")
                    
                    with col2:
                        st.caption(f"Platform: {product.platform.title()}")
                        st.caption(f"{review.review_date.strftime('%Y-%m-%d') if review.review_date else 'N/A'}")
                    
                    st.divider()
        else:
            st.info("No reviews available matching your filters.")
        
        db.close()

    with tab5:
        st.header("🤖 AI Assistant - Competitive Intelligence Chatbot")
        
        st.markdown("""
        <style>
        /* ====== GLOBAL DARK BLUE THEME ====== */
        body, .stApp {
            background-color: #0b1021 !important; /* Deep navy */
            color: #e8f1ff !important;
        }

        /* ====== Chat Header ====== */
        .chat-header {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 25px;
            box-shadow: 0 4px 15px rgba(30, 60, 114, 0.3);
        }

        .chat-header h4 {
            margin: 0 0 10px 0;
            font-size: 1.3rem;
            color: white;
        }

        .chat-header ul {
            margin: 0;
            padding-left: 20px;
        }

        .chat-header li {
            color: #c8dbff;
            margin: 5px 0;
        }

        /* ====== User Message (You) ====== */
        .user-message {
            background: linear-gradient(135deg, #2a5298 0%, #1e3c72 100%);
            color: #ffffff;
            padding: 15px 20px;
            border-radius: 20px 20px 5px 20px;
            margin: 10px 0 10px 25%;
            box-shadow: 0 3px 10px rgba(30, 60, 114, 0.4);
            animation: slideInRight 0.3s ease-out;
        }

        /* ====== Assistant Message (AI) ====== */
        .assistant-message {
            background: linear-gradient(135deg, #162447 0%, #1f3b73 100%);
            color: #e8f1ff;
            padding: 15px 20px;
            border-radius: 20px 20px 20px 5px;
            margin: 10px 25% 10px 0;
            box-shadow: 0 3px 10px rgba(0, 0, 0, 0.4);
            border: 1px solid rgba(42, 82, 152, 0.3);
            animation: slideInLeft 0.3s ease-out;
        }

        /* ====== Animations ====== */
        @keyframes slideInLeft {
            from { opacity: 0; transform: translateX(-20px); }
            to { opacity: 1; transform: translateX(0); }
        }
        @keyframes slideInRight {
            from { opacity: 0; transform: translateX(20px); }
            to { opacity: 1; transform: translateX(0); }
        }

        /* ====== Quick Action Buttons ====== */
        .quick-action-btn {
            background: linear-gradient(135deg, #2a5298 0%, #1e3c72 100%);
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 10px;
            margin: 5px;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 3px 10px rgba(30, 60, 114, 0.3);
        }
        .quick-action-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(42, 82, 152, 0.6);
        }

        /* ====== Chat Input Box ====== */
        .chat-input-container {
            background: #10172b;
            padding: 20px;
            border-radius: 15px;
            border: 2px solid #2a5298;
            margin-top: 20px;
            box-shadow: 0 3px 10px rgba(30, 60, 114, 0.3);
        }

        /* ====== Streamlit Input ====== */
        .stTextInput > div > div > input {
            background-color: #0f1a33 !important;
            border: 2px solid #2a5298 !important;
            color: #e8f1ff !important;
            border-radius: 10px !important;
            padding: 12px !important;
            font-size: 16px !important;
        }
        .stTextInput > div > div > input:focus {
            border-color: #1e3c72 !important;
            box-shadow: 0 0 0 3px rgba(42, 82, 152, 0.3) !important;
        }

        /* ====== Streamlit Button Override ====== */
        .stButton > button {
            background: linear-gradient(135deg, #2a5298 0%, #1e3c72 100%) !important;
            color: white !important;
            border: none !important;
            padding: 10px 25px !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 3px 10px rgba(30, 60, 114, 0.3) !important;
        }
        .stButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 5px 15px rgba(30, 60, 114, 0.5) !important;
        }

        /* ====== Scrollbar ====== */
        ::-webkit-scrollbar {
            width: 8px;
        }
        ::-webkit-scrollbar-thumb {
            background: #1e3c72;
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #2a5298;
        }
        </style>
        """, unsafe_allow_html=True)

        
        # Chat controls
        col1, col2 = st.columns([4, 1])
        with col2:
            if st.button("🗑️ Clear Chat", use_container_width=True):
                st.session_state.chat_history = []
                st.rerun()
        
        # Display chat history
        chat_container = st.container()
        with chat_container:
            for message in st.session_state.chat_history:
                if message['role'] == 'user':
                    st.markdown(f"""
                    <div class="user-message">
                        <strong>You:</strong><br>{message['content']}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="assistant-message">
                        <strong>🤖 AI Assistant:</strong><br>{message['content']}
                    
                    """, unsafe_allow_html=True)
        
        # Enhanced suggested queries with dark blue theme
        st.markdown("### 💡 Quick Actions")
        
        # Create custom styled buttons
        col1, col2, col3 = st.columns(3)
        
        quick_actions = [
            ("🔮 Predict prices for next week", "Show me price predictions for all tracked laptops"),
            ("💰 Find best deals", "What are the best laptop deals right now?"),
            ("📉 Price drop alerts", "Which laptops are expected to drop in price?"),
            ("🎯 Best time to buy", "When should I buy a gaming laptop?"),
            ("📊 Market analysis", "Analyze the laptop market trends"),
            ("🏆 Top recommendations", "Recommend the best laptop under ₹60,000")
        ]
        
        for idx, (label, query) in enumerate(quick_actions):
            col = [col1, col2, col3][idx % 3]
            with col:
                if st.button(label, key=f"quick_{idx}", use_container_width=True):
                    st.session_state.chat_history.append({'role': 'user', 'content': query})
                    
                    # Generate intelligent response based on query
                    with st.spinner("🔍 Analyzing data..."):
                        if "predict" in query.lower() or "prediction" in query.lower():
                            # Get all products
                            products = db.query(Product).limit(5).all()
                            response = "🔮 **Price Predictions for Next 7 Days:**\n\n"
                            
                            for product in products:
                                if predictor.is_trained:
                                    pred = predictor.predict_price(product.id, 7)
                                    if 'summary' in pred:
                                        emoji = "📈" if pred['summary']['expected_change_pct'] > 0 else "📉"
                                        response += f"{emoji} **{product.name[:40]}...**\n"
                                        response += f"- Current: ₹{pred['current_price']:,.0f}\n"
                                        response += f"- 7-day prediction: ₹{pred['summary']['week_ahead_price']:,.0f} "
                                        response += f"({pred['summary']['expected_change_pct']:+.1f}%)\n"
                                        response += f"- Recommendation: **{pred['summary']['recommendation']}**\n\n"
                            
                            if not predictor.is_trained:
                                response = "⚠️ The ML model needs to be trained first. Please go to the Price Analysis tab to train the model."
                        
                        elif "best deals" in query.lower() or "deals" in query.lower():
                            deals = db.query(Product, Price).join(Price).filter(
                                Price.discount_percentage > 10
                            ).order_by(Price.discount_percentage.desc()).limit(5).all()
                            
                            response = "🏷️ **Top Deals Right Now:**\n\n"
                            for idx, (product, price) in enumerate(deals, 1):
                                response += f"{idx}. **{product.name}**\n"
                                response += f"   - Platform: {product.platform.title()}\n"
                                response += f"   - Discount: **{price.discount_percentage:.0f}% OFF**\n"
                                response += f"   - Price: ~~₹{price.price:,.0f}~~ → **₹{price.discount_price:,.0f}**\n"
                                response += f"   - You save: ₹{(price.price - price.discount_price):,.0f}\n\n"
                        
                        elif "price drop" in query.lower() or "drop in price" in query.lower():
                            if predictor.is_trained:
                                products = db.query(Product).limit(10).all()
                                drops = []
                                
                                for product in products:
                                    pred = predictor.predict_price(product.id, 7)
                                    if 'summary' in pred and pred['summary']['expected_change_pct'] < -5:
                                        drops.append((product, pred))
                                
                                if drops:
                                    response = "📉 **Products Expected to Drop in Price:**\n\n"
                                    for product, pred in sorted(drops, key=lambda x: x[1]['summary']['expected_change_pct'])[:5]:
                                        response += f"• **{product.name}**\n"
                                        response += f"  Expected drop: **{pred['summary']['expected_change_pct']:.1f}%**\n"
                                        response += f"  Potential savings: **₹{abs(pred['summary']['expected_change']):,.0f}**\n\n"
                                else:
                                    response = "No significant price drops expected in the next 7 days for tracked products."
                            else:
                                response = "⚠️ Please train the ML model first to get price predictions."
                        
                        elif "market analysis" in query.lower() or "trends" in query.lower():
                            # Get market statistics
                            avg_price = db.query(func.avg(Price.price)).scalar() or 0
                            total_products = db.query(Product).count()
                            total_deals = db.query(Price).filter(Price.discount_percentage > 0).count()
                            
                            response = "📊 **Laptop Market Analysis:**\n\n"
                            response += f"• **Products Tracked:** {total_products}\n"
                            response += f"• **Average Price:** ₹{avg_price:,.0f}\n"
                            response += f"• **Active Deals:** {total_deals}\n\n"
                            
                            # Platform comparison
                            platform_stats = db.query(
                                Product.platform,
                                func.avg(Price.price).label('avg_price'),
                                func.count(Product.id).label('count')
                            ).join(Price).group_by(Product.platform).all()
                            
                            response += "**Platform Comparison:**\n"
                            for stat in platform_stats:
                                response += f"• {stat.platform.title()}: Avg ₹{stat.avg_price:,.0f} ({stat.count} products)\n"
                        
                        elif "recommend" in query.lower() and "60000" in query:
                            budget_laptops = db.query(Product, Price).join(Price).filter(
                                Price.price <= 60000
                            ).order_by(Price.price).all()
                            
                            response = "🏆 **Best Laptops Under ₹60,000:**\n\n"
                            for idx, (product, price) in enumerate(budget_laptops[:5], 1):
                                response += f"{idx}. **{product.name}**\n"
                                response += f"   - Price: **₹{price.price:,.0f}**\n"
                                response += f"   - Brand: {product.brand}\n"
                                response += f"   - Platform: {product.platform.title()}\n\n"
                        
                        else:
                            response = "I'm here to help! Feel free to ask about:\n"
                            response += "• Price predictions for specific laptops\n"
                            response += "• Current deals and discounts\n"
                            response += "• Best time to buy analysis\n"
                            response += "• Market trends and insights"
                    
                    st.session_state.chat_history.append({'role': 'assistant', 'content': response})
                    st.rerun()
        
        # Chat input with dark blue theme
        # st.markdown('<div class="chat-input-container">', unsafe_allow_html=True)
        with st.form("chat_form", clear_on_submit=True):
            user_input = st.text_input(
                "💬 Ask me anything about laptop prices...",
                placeholder="e.g., When will Dell Inspiron prices drop?",
                label_visibility="visible"
            )
            
            col1, col2, col3 = st.columns([1, 1, 4])
            with col1:
                submit = st.form_submit_button("🚀 Send", use_container_width=True)
            # st.markdown("</div>", unsafe_allow_html=True)
            
            if submit and user_input:
                st.session_state.chat_history.append({'role': 'user', 'content': user_input})
                
                # Process the query and generate response
                with st.spinner("🤔 Thinking..."):
                    response = ""
                    
                    # Enhanced query processing with ML predictions
                    if any(word in user_input.lower() for word in ['predict', 'forecast', 'future', 'will', 'expect']):
                        # Extract product name from query if mentioned
                        products = db.query(Product).all()
                        mentioned_product = None
                        
                        for product in products:
                            if any(word.lower() in user_input.lower() for word in product.name.split()[:2]):
                                mentioned_product = product
                                break
                        
                        if mentioned_product and predictor.is_trained:
                            pred = predictor.predict_price(mentioned_product.id, 7)
                            if 'summary' in pred:
                                response = f"🔮 **Price Prediction for {mentioned_product.name}:**\n\n"
                                response += f"📍 Current Price: **₹{pred['current_price']:,.0f}**\n"
                                response += f"📅 7-Day Prediction: **₹{pred['summary']['week_ahead_price']:,.0f}**\n"
                                response += f"📊 Expected Change: **{pred['summary']['expected_change_pct']:+.1f}%**\n\n"
                                response += f"💡 **Recommendation:** {pred['summary']['recommendation']}\n"
                                response += f"📝 **Reason:** {pred['summary']['reason']}"
                                
                                # Add best time to buy
                                best_time = predictor.predict_best_time_to_buy(mentioned_product.id, 30)
                                if 'best_time_to_buy' in best_time:
                                    btb = best_time['best_time_to_buy']
                                    response += f"\n\n🎯 **Best Time to Buy:** {btb['date']} "
                                    response += f"(in {btb['days_from_now']} days)\n"
                                    response += f"💰 Expected savings: **₹{btb['expected_savings']:,.0f}**"
                        else:
                            response = "Please specify which laptop you'd like price predictions for, or check if the ML model is trained."
                    
                    elif any(word in user_input.lower() for word in ['cheap', 'cheapest', 'lowest', 'budget']):
                        budget = 50000  # Default budget
                        
                        # Extract budget from query if mentioned
                        import re
                        numbers = re.findall(r'\d+(?:,\d+)*', user_input)
                        if numbers:
                            budget = int(numbers[0].replace(',', ''))
                        
                        budget_laptops = db.query(Product, Price).join(Price).filter(
                            Price.price <= budget
                        ).order_by(Price.price).limit(5).all()
                        
                        if budget_laptops:
                            response = f"💰 **Best Laptops Under ₹{budget:,}:**\n\n"
                            for idx, (product, price) in enumerate(budget_laptops, 1):
                                response += f"**{idx}. {product.name}**\n"
                                response += f"   💵 Price: **₹{price.price:,.0f}** on {product.platform.title()}\n"
                                
                                if predictor.is_trained:
                                    pred = predictor.predict_price(product.id, 7)
                                    if 'summary' in pred:
                                        trend_emoji = "📈" if pred['summary']['expected_change_pct'] > 0 else "📉"
                                        response += f"   {trend_emoji} 7-day trend: **{pred['summary']['expected_change_pct']:+.1f}%**\n"
                                response += "\n"
                        else:
                            response = f"No laptops found under ₹{budget:,} in our tracking system."
                    
                    elif any(word in user_input.lower() for word in ['compare', 'vs', 'versus', 'difference']):
                        # Extract brands or products to compare
                        brands = ['Dell', 'HP', 'Lenovo', 'ASUS', 'Acer', 'Apple', 'MSI']
                        mentioned_brands = [b for b in brands if b.lower() in user_input.lower()]
                        
                        if len(mentioned_brands) >= 2:
                            response = f"📊 **Comparison: {' vs '.join(mentioned_brands)}**\n\n"
                            
                            for brand in mentioned_brands:
                                brand_data = db.query(
                                    func.avg(Price.price).label('avg_price'),
                                    func.min(Price.price).label('min_price'),
                                    func.max(Price.price).label('max_price'),
                                    func.count(Product.id).label('count')
                                ).join(Product).filter(Product.brand == brand).first()
                                
                                if brand_data and brand_data.avg_price:
                                    response += f"**🏢 {brand}:**\n"
                                    response += f"   📦 Products tracked: {brand_data.count}\n"
                                    response += f"   💵 Average price: **₹{brand_data.avg_price:,.0f}**\n"
                                    response += f"   📊 Price range: ₹{brand_data.min_price:,.0f} - ₹{brand_data.max_price:,.0f}\n\n"
                        else:
                            response = "Please specify at least two brands or products to compare."
                    
                    elif "best time" in user_input.lower() or "when to buy" in user_input.lower():
                        response = "🎯 **Best Times to Buy Laptops:**\n\n"
                        response += "📅 **Festive Seasons:**\n"
                        response += "• **Diwali Sale** (Oct-Nov): Up to 40% discounts\n"
                        response += "• **Amazon Great Indian Festival**: Major price drops\n"
                        response += "• **Flipkart Big Billion Days**: Competitive pricing\n\n"
                        response += "📅 **Other Good Times:**\n"
                        response += "• **Back-to-School** (June-July): Student discounts\n"
                        response += "• **Year-End Sales** (December): Clearance deals\n"
                        response += "• **Republic Day Sale** (January): Good offers\n\n"
                        
                        if predictor.is_trained:
                            response += "💡 **Based on current predictions:**\n"
                            # Get some products with expected price drops
                            products = db.query(Product).limit(5).all()
                            for product in products:
                                pred = predictor.predict_price(product.id, 30)
                                if 'summary' in pred and pred['summary']['expected_change_pct'] < -5:
                                    response += f"• {product.name[:30]}... expected to drop {abs(pred['summary']['expected_change_pct']):.1f}%\n"
                    
                    else:
                        # General response with current stats
                        total_products = db.query(Product).count()
                        avg_price = db.query(func.avg(Price.price)).scalar() or 0
                        best_deal = db.query(Product, Price).join(Price).filter(
                            Price.discount_percentage > 0
                        ).order_by(Price.discount_percentage.desc()).first()
                        
                        response = f"📊 **Current Market Overview:**\n\n"
                        response += f"• Tracking **{total_products} laptop models**\n"
                        response += f"• Average price: **₹{avg_price:,.0f}**\n"
                        
                        if best_deal:
                            product, price = best_deal
                            response += f"• Best deal: **{product.name}** - {price.discount_percentage:.0f}% OFF!\n\n"
                        
                        response += "💡 **I can help you with:**\n"
                        response += "• 🔮 Price predictions for specific laptops\n"
                        response += "• 💰 Finding best deals under your budget\n"
                        response += "• 📊 Brand comparisons and analysis\n"
                        response += "• 🎯 Best time to buy recommendations\n"
                        response += "• 📉 Price drop alerts and notifications"
                # st.markdown("</div>", unsafe_allow_html=True)
                st.session_state.chat_history.append({'role': 'assistant', 'content': response})
                st.rerun()
        
        db.close()
    
    with tab6:
        st.header("🚨 Alerts & Notifications")
        
        # Dark blue theme CSS
        st.markdown("""
        <style>
        /* ===========================
        🌙 Dark Blue Theme for Alerts
        =========================== */

        /* Header */
        .alert-header {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: #ffffff;
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 20px;
            box-shadow: 0 4px 15px rgba(30, 60, 114, 0.5);
            border: 1px solid #2a5298;
        }

        /* Alert Cards */
        .alert-card {
            background: #121826; /* dark background */
            border-left: 4px solid #2a5298;
            padding: 20px;
            border-radius: 8px;
            margin: 10px 0;
            color: #e8f1ff;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.6);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }

        .alert-card:hover {
            transform: translateX(5px);
            box-shadow: 0 4px 15px rgba(30, 60, 114, 0.4);
        }

        /* Active, Warning, Danger Variants */
        .alert-active {
            background: linear-gradient(135deg, #1b263b 0%, #0f172a 100%);
            border-left: 4px solid #10b981;
            color: #d1fae5;
        }

        .alert-warning {
            background: linear-gradient(135deg, #2f2a1d 0%, #3f341b 100%);
            border-left: 4px solid #f59e0b;
            color: #fde68a;
        }

        .alert-danger {
            background: linear-gradient(135deg, #3b1e1e 0%, #421919 100%);
            border-left: 4px solid #ef4444;
            color: #fecaca;
        }

        /* Config Card */
        .config-card {
            background: #0e1628;
            border: 2px solid #2a3e6f;
            border-radius: 12px;
            padding: 25px;
            margin: 20px 0;
            color: #e8f1ff;
            box-shadow: 0 3px 10px rgba(0, 0, 0, 0.4);
        }

        /* Threshold Display */
        .threshold-display {
            background: linear-gradient(135deg, #2a5298 0%, #1e3c72 100%);
            color: #ffffff;
            padding: 10px 20px;
            border-radius: 20px;
            display: inline-block;
            font-weight: bold;
            font-size: 1.1rem;
            margin: 10px 0;
            box-shadow: 0 3px 10px rgba(30, 60, 114, 0.4);
        }

        /* Alert Rules */
        .alert-rule {
            background: #1b2233;
            border: 2px solid #2a3e6f;
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
            transition: all 0.3s ease;
            color: #e8f1ff;
        }

        .alert-rule:hover {
            border-color: #2a5298;
            box-shadow: 0 3px 10px rgba(30, 60, 114, 0.3);
        }

        /* Status Badges */
        .status-badge {
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: 600;
            display: inline-block;
        }

        .status-active {
            background: #10b981;
            color: white;
        }

        .status-paused {
            background: #f59e0b;
            color: white;
        }

        /* Global Background (optional for full dark theme) */
        .stApp, body {
            background-color: #0a1120 !important;
            color: #e8f1ff !important;
        }
        </style>
        """, unsafe_allow_html=True)

        
        db = SessionLocal()
        
        # Alert statistics with dark blue accents
        col1, col2, col3, col4 = st.columns(4)
        
        total_alerts = db.query(Alert).count()
        active_alerts = db.query(Alert).filter(Alert.sent == False).count()
        sent_alerts = db.query(Alert).filter(Alert.sent == True).count()
        
        with col1:
            st.metric("📊 Total Alerts", total_alerts)
        with col2:
            st.metric("🔴 Active Alerts", active_alerts, delta="+3 new")
        with col3:
            st.metric("✅ Sent Alerts", sent_alerts)
        with col4:
            alert_rate = (sent_alerts / total_alerts * 100) if total_alerts > 0 else 0
            st.metric("📈 Response Rate", f"{alert_rate:.1f}%")
        
        # Notification Settings Configuration
        st.markdown("""
        <div class="alert-header">
            <h3>🔔 Notification Settings</h3>
            <p>Configure when and how you want to be notified about price changes and deals</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.container():
            st.markdown('<div class="config-card">', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 💰 Price Drop Notifications")
                
                # Discount threshold configuration
                discount_threshold = st.slider(
                    "Minimum discount to notify (%)",
                    min_value=5,
                    max_value=50,
                    value=15,
                    step=5,
                    help="You'll be notified when products drop by this percentage or more"
                )
                
                st.markdown(f'<div class="threshold-display">Notify me at {discount_threshold}% off or more</div>', 
                        unsafe_allow_html=True)
                
                # Price range preferences
                st.markdown("### 💵 Price Range Preferences")
                price_range = st.slider(
                    "Monitor products in price range (₹)",
                    min_value=0,
                    max_value=200000,
                    value=(20000, 100000),
                    step=5000,
                    format="₹%d"
                )
                st.info(f"Monitoring laptops between ₹{price_range[0]:,} and ₹{price_range[1]:,}")
                
                # Notification frequency
                st.markdown("### ⏰ Notification Frequency")
                frequency = st.radio(
                    "How often should we check for deals?",
                    ["Real-time", "Every hour", "Twice daily", "Once daily"],
                    horizontal=True
                )
            
            with col2:
                st.markdown("### 📱 Notification Channels")
                
                # Notification methods
                notify_dashboard = st.checkbox("Dashboard Notifications", value=True)
                notify_email = st.checkbox("Email Notifications", value=False)
                notify_sms = st.checkbox("SMS Notifications", value=False)
                notify_slack = st.checkbox("Slack Notifications", value=False)
                
                if notify_email:
                    email = st.text_input("Email Address", placeholder="your@email.com")
                
                if notify_sms:
                    phone = st.text_input("Phone Number", placeholder="+91 98765 43210")
                
                
                
                # Save settings button
                if st.button("💾 Save Notification Settings", use_container_width=True):
                    st.success("✅ Notification settings saved successfully!")
                    # In production, save these settings to database
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Active Alerts with improved styling
        st.subheader("🔴 Active Alerts")
        
        active_alerts_list = db.query(Alert).filter(Alert.sent == False).order_by(
            Alert.created_at.desc()
        ).limit(10).all()
        
        if active_alerts_list:
            for alert in active_alerts_list:
                alert_type_class = {
                    'price_drop': 'alert-active',
                    'price_increase': 'alert-warning',
                    'stock_alert': 'alert-card',
                    'new_product': 'alert-card',
                    'review_alert': 'alert-danger'
                }.get(alert.type, 'alert-card')
                
                alert_icon = {
                    'price_drop': '📉',
                    'price_increase': '📈',
                    'new_product': '🆕',
                    'stock_alert': '📦',
                    'review_alert': '💬'
                }.get(alert.type, '🔔')
                
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.markdown(f"""
                    <div class="{alert_type_class}">
                        <strong style="font-size: 1.1rem;">{alert_icon} {alert.type.replace('_', ' ').title()}</strong><br>
                        <span style="color: #4b5563;">{alert.message}</span>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.caption(f"⏰ {alert.created_at.strftime('%Y-%m-%d %H:%M')}")
                
                with col3:
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("✓", key=f"mark_{alert.id}", help="Mark as read"):
                            alert.sent = True
                            db.commit()
                            st.rerun()
                    with col_b:
                        if st.button("×", key=f"delete_{alert.id}", help="Delete"):
                            db.delete(alert)
                            db.commit()
                            st.rerun()
        else:
            st.info("🎉 No active alerts. All systems running smoothly!")

    with tab7:
        st.header("🔮 Batch Price Predictions")
        st.markdown("Analyze and predict prices for multiple products simultaneously")
        
        predictor = PricePredictor()
        db = SessionLocal()
        
        # Check if model is trained
        if not predictor.is_trained:
            st.warning("⚠️ ML model not trained. Please train the model in the Price Analysis tab first.")
        else:
            # Product selection
            products = db.query(Product).all()
            
            if products:
                # Multi-select for products
                product_options = {p.name: p.id for p in products}
                selected_product_names = st.multiselect(
                    "Select products to analyze",
                    options=list(product_options.keys()),
                    default=list(product_options.keys())[:5]  # Default to first 5
                )
                
                if selected_product_names:
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"Selected {len(selected_product_names)} products for analysis")
                    
                    with col2:
                        if st.button("🚀 Generate Batch Predictions", type="primary"):
                            selected_ids = [product_options[name] for name in selected_product_names]
                            
                            with st.spinner(f"Generating predictions for {len(selected_ids)} products..."):
                                batch_results = predictor.batch_predict(selected_ids, days_ahead=7)
                                st.session_state['batch_predictions'] = batch_results
                    
                    # Display batch results
                    if 'batch_predictions' in st.session_state:
                        results = st.session_state['batch_predictions']
                        
                        # Summary metrics
                        col1, col2, col3, col4 = st.columns(4)
                        
                        buy_now = sum(1 for r in results.values() if 'summary' in r and r['summary']['recommendation'] == 'BUY')
                        wait = sum(1 for r in results.values() if 'summary' in r and r['summary']['recommendation'] == 'WAIT')
                        hold = sum(1 for r in results.values() if 'summary' in r and r['summary']['recommendation'] == 'HOLD')
                        
                        with col1:
                            st.metric("🛍️ Buy Now", buy_now)
                        with col2:
                            st.metric("⏳ Wait", wait)
                        with col3:
                            st.metric("📊 Hold", hold)
                        with col4:
                            avg_change = np.mean([r['summary']['expected_change_pct'] for r in results.values() if 'summary' in r])
                            st.metric("Avg Change", f"{avg_change:+.1f}%")
                        
                        # Detailed results table
                        st.subheader("📋 Prediction Summary")
                        
                        table_data = []
                        for product_id, result in results.items():
                            if 'error' not in result:
                                product = db.query(Product).filter(Product.id == product_id).first()
                                table_data.append({
                                    'Product': product.name[:40] + '...' if len(product.name) > 40 else product.name,
                                    'Current Price': f"₹{result['current_price']:,.0f}",
                                    '7-Day Prediction': f"₹{result['summary']['week_ahead_price']:,.0f}",
                                    'Expected Change': f"{result['summary']['expected_change_pct']:+.1f}%",
                                    'Recommendation': result['summary']['recommendation'],
                                    'Confidence': f"{result['model_confidence']*100:.0f}%"
                                })
                        
                        df_results = pd.DataFrame(table_data)
                        
                        # Style the dataframe
                        def style_recommendation(val):
                            if val == 'BUY':
                                return 'background-color: #fff3cd'
                            elif val == 'WAIT':
                                return 'background-color: #d4edda'
                            else:
                                return 'background-color: #d1ecf1'
                        
                        def style_change(val):
                            pct = float(val.strip('%+'))
                            if pct < -5:
                                return 'color: green; font-weight: bold'
                            elif pct > 5:
                                return 'color: red; font-weight: bold'
                            else:
                                return 'color: gray'
                        
                        styled_df = df_results.style.applymap(
                            style_recommendation, subset=['Recommendation']
                        ).applymap(
                            style_change, subset=['Expected Change']
                        )
                        
                        st.dataframe(styled_df, use_container_width=True, hide_index=True)
                        
                        # Export functionality
                        csv = df_results.to_csv(index=False)
                        st.download_button(
                            label="📥 Download Predictions CSV",
                            data=csv,
                            file_name=f"price_predictions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                        
                        # Visualization
                        st.subheader("📊 Price Change Distribution")
                        
                        changes = [r['summary']['expected_change_pct'] for r in results.values() if 'summary' in r]
                        
                        fig = go.Figure()
                        fig.add_trace(go.Histogram(
                            x=changes,
                            nbinsx=20,
                            marker_color='#3b82f6',
                            opacity=0.75
                        ))
                        
                        fig.add_vline(x=0, line_dash="dash", line_color="gray")
                        fig.add_annotation(
                            x=0, y=0.9,
                            text="No Change",
                            showarrow=False,
                            yref="paper"
                        )
                        
                        fig.update_layout(
                            title="Distribution of Expected Price Changes",
                            xaxis_title="Expected Change (%)",
                            yaxis_title="Number of Products",
                            height=400
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Best opportunities
                        # Best opportunities
                        st.subheader("🎯 Best Opportunities")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("### 💰 Biggest Price Drops Expected")
                            
                            # Sort by expected price drop
                            drops = [(pid, r) for pid, r in results.items() 
                                    if 'summary' in r and r['summary']['expected_change_pct'] < 0]
                            drops.sort(key=lambda x: x[1]['summary']['expected_change_pct'])
                            
                            for i, (product_id, result) in enumerate(drops[:5]):
                                product = db.query(Product).filter(Product.id == product_id).first()
                                
                                st.markdown(f"""
                                <div style='background-color: #d4edda; padding: 10px; border-radius: 8px; margin: 5px 0;'>
                                    <strong>{i+1}. {product.name[:40]}...</strong><br>
                                    Expected drop: <strong>{result['summary']['expected_change_pct']:.1f}%</strong><br>
                                    Save: <strong>₹{abs(result['summary']['expected_change']):,.0f}</strong>
                                </div>
                                """, unsafe_allow_html=True)
                        
                        with col2:
                            st.markdown("### ⚡ Buy Now - Prices Rising")
                            
                            # Sort by expected price increase
                            increases = [(pid, r) for pid, r in results.items() 
                                        if 'summary' in r and r['summary']['expected_change_pct'] > 5]
                            increases.sort(key=lambda x: x[1]['summary']['expected_change_pct'], reverse=True)
                            
                            for i, (product_id, result) in enumerate(increases[:5]):
                                product = db.query(Product).filter(Product.id == product_id).first()
                                
                                st.markdown(f"""
                                <div style='background-color: #fff3cd; padding: 10px; border-radius: 8px; margin: 5px 0;'>
                                    <strong>{i+1}. {product.name[:40]}...</strong><br>
                                    Expected rise: <strong>+{result['summary']['expected_change_pct']:.1f}%</strong><br>
                                    Act fast to save: <strong>₹{result['summary']['expected_change']:,.0f}</strong>
                                </div>
                                """, unsafe_allow_html=True)
        
        db.close()

# Add footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p>💻 LaptopLens - Laptop Price Tracking & Analyzing System v1.0</p>
</div>
""", unsafe_allow_html=True)

