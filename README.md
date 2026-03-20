# 📈 Option Volatility Surface Dashboard

Interactive Python application to visualize and analyze **implied volatility dynamics** across strikes and maturities, inspired by real-world trading desk tools.

---

## 🚀 Overview

This project builds a **volatility surface analytics dashboard** using equity options data.

It allows users to explore key volatility dimensions:

- **Volatility Skew (Smile)** → IV across strikes  
- **Term Structure** → IV across maturities  
- **3D Volatility Surface** → global market view  

The app is built with **Streamlit** for real-time interaction.

---

## ⚙️ Features

- 📊 Volatility skew visualization  
- ⏳ Term structure analysis (selected strike)  
- 🌐 3D implied volatility surface  
- 🔍 Data filtering:
  - Moneyness (ATM-focused)
  - Liquidity (volume / open interest)
- 🧹 Data cleaning:
  - Removal of extreme IV values  
  - Bid-ask consistency checks  
- ⚡ Performance optimization:
  - Caching (`st.cache_data`)  
  - Rate-limit handling (Yahoo Finance)

---

## 🧠 Methodology

1. **Data Retrieval**  
   - Option chains via `yfinance`

2. **Cleaning & Filtering**  
   - Remove illiquid and inconsistent quotes  
   - Filter unrealistic implied volatility values  
   - Focus on relevant strike ranges  

3. **Feature Engineering**  
   - Compute time to maturity  
   - Structure data into a volatility surface  

4. **Visualization**  
   - 2D plots (skew, term structure)  
   - 3D surface representation  

---

## 🛠️ Tech Stack

- Python  
- Streamlit  
- Pandas / NumPy  
- Matplotlib  
- yFinance  

---

## ▶️ Run Locally

```bash
git clone https://github.com/yourusername/volatility-surface.git
cd volatility-surface
pip install -r requirements.txt
streamlit run app.py
