import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import time
from mpl_toolkits.mplot3d import Axes3D

st.set_page_config(layout="wide")

st.title("Option Volatility Surface")
st.header(
    "Implied volatility is the market's expectation of how volatile the underlying asset will be in the future. "
    "It is derived from the price of an option and can be used to gauge market sentiment and make informed trading decisions. "
    "Volatility surfaces are 3D plots that show how implied volatility changes with different strike prices and expiration dates. "
    "They can help traders identify patterns and potential trading opportunities."
)

@st.cache_data(ttl=600)
def get_spot_price(ticker):
    asset = yf.Ticker(ticker)
    hist = asset.history(period="5d")
    if hist.empty:
        raise ValueError("Unable to retrieve spot price.")
    return float(hist["Close"].dropna().iloc[-1])

@st.cache_data(ttl=600)
def get_expirations(ticker):
    asset = yf.Ticker(ticker)
    return list(asset.options)

@st.cache_data(ttl=600)
def get_option_chain(ticker, expiration):
    asset = yf.Ticker(ticker)
    opt = asset.option_chain(expiration)

    calls = opt.calls.copy()
    calls["optionType"] = "call"

    puts = opt.puts.copy()
    puts["optionType"] = "put"

    chain = pd.concat([calls, puts], ignore_index=True)
    chain["expiration"] = pd.to_datetime(expiration) + pd.DateOffset(hours=23, minutes=59, seconds=59)
    chain["daysToExpiration"] = (chain["expiration"] - pd.Timestamp.now()).dt.days + 1
    return chain

@st.cache_data(ttl=600)
def get_surface_data(ticker, expirations):
    asset = yf.Ticker(ticker)
    frames = []

    for expiration in expirations:
        try:
            opt = asset.option_chain(expiration)
            calls = opt.calls.copy()
            calls["optionType"] = "call"
            calls["expiration"] = pd.to_datetime(expiration) + pd.DateOffset(hours=23, minutes=59, seconds=59)
            calls["daysToExpiration"] = (calls["expiration"] - pd.Timestamp.now()).dt.days + 1
            frames.append(calls)
            time.sleep(0.2)
        except Exception:
            continue

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)

def clean_calls_data(df, spot, strict=False):
    df = df.copy()

    numeric_cols = ["strike", "impliedVolatility", "volume", "openInterest", "bid", "ask"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Keep only rows with strike and IV
    df = df.dropna(subset=["strike", "impliedVolatility"])

    # Yahoo often returns IV in decimal form; keep a wider acceptable band
    df = df[(df["impliedVolatility"] > 0.001) & (df["impliedVolatility"] < 5.0)]

    # Moneyness filter: less restrictive
    df = df[(df["strike"] >= 0.5 * spot) & (df["strike"] <= 1.5 * spot)]

    if strict:
        # For surface only: light liquidity filter
        if {"volume", "openInterest"}.issubset(df.columns):
            df = df[
                (df["volume"].fillna(0) > 0) |
                (df["openInterest"].fillna(0) > 0)
            ]

        # Bid/ask sanity only if values exist
        if {"bid", "ask"}.issubset(df.columns):
            mask = (
                ((df["bid"].isna()) | (df["bid"] >= 0)) &
                ((df["ask"].isna()) | (df["ask"] >= 0))
            )
            df = df[mask]

    return df.sort_values("strike")

with st.sidebar:
    st.header("Select an underlying asset")
    ticker = st.text_input("Enter a ticker symbol", value="SPY").upper().strip()
    max_expiries = st.slider("Number of expirations for surface", min_value=2, max_value=8, value=4)

try:
    spot = get_spot_price(ticker)
    st.write(f"**Spot price:** {spot:.2f}")

    expirations = get_expirations(ticker)
    if not expirations:
        st.error("No listed options found for this ticker.")
        st.stop()

    selected_expiry_str = st.selectbox("Select expiration", expirations)

    # Single expiry for skew
    options_one_expiry = get_option_chain(ticker, selected_expiry_str)
    calls_one_expiry = options_one_expiry[options_one_expiry["optionType"] == "call"].copy()

    # Less strict for single-expiry skew
    raw_count = len(calls_one_expiry)
    calls_one_expiry = clean_calls_data(calls_one_expiry, spot, strict=False)
    clean_count = len(calls_one_expiry)

    st.caption(f"Calls before cleaning: {raw_count} | after cleaning: {clean_count}")

    if calls_one_expiry.empty:
        st.error("No valid call options found for this expiration after cleaning.")
        st.write("Try another expiration or relax the cleaning filters.")
        st.dataframe(options_one_expiry.head(20))
        st.stop()

    st.subheader("Implied Volatility Skew")
    fig1, ax1 = plt.subplots(figsize=(8, 4))
    ax1.plot(
        calls_one_expiry["strike"],
        calls_one_expiry["impliedVolatility"],
        marker="o"
    )
    ax1.set_title(f"Implied Volatility Skew - {selected_expiry_str}")
    ax1.set_xlabel("Strike")
    ax1.set_ylabel("Implied Volatility")
    ax1.grid(True, alpha=0.3)
    st.pyplot(fig1)

    available_strikes = sorted(calls_one_expiry["strike"].dropna().unique())
    default_idx = min(len(available_strikes) // 2, len(available_strikes) - 1)
    selected_strike = st.selectbox("Select strike", available_strikes, index=default_idx)

    # Surface data
    limited_expirations = expirations[:max_expiries]
    surface_calls = get_surface_data(ticker, limited_expirations)

    if surface_calls.empty:
        st.warning("Could not retrieve enough option data for term structure and surface.")
        st.stop()

    # Stricter cleaning for surface
    surface_calls = clean_calls_data(surface_calls, spot, strict=True)

    if surface_calls.empty:
        st.warning("No valid surface data after cleaning.")
        st.stop()

    st.subheader("Implied Volatility Term Structure")

    # Better than exact equality on strike
    strike_slice = surface_calls[np.isclose(surface_calls["strike"], selected_strike, atol=1e-8)].copy()

    if strike_slice.empty:
        st.warning("Selected strike is not available across enough expirations.")
    else:
        fig2, ax2 = plt.subplots(figsize=(8, 4))
        strike_slice = strike_slice.sort_values("expiration")
        ax2.plot(
            strike_slice["expiration"],
            strike_slice["impliedVolatility"],
            marker="o"
        )
        ax2.set_title(f"Implied Volatility Term Structure - Strike {selected_strike}")
        ax2.set_xlabel("Expiration")
        ax2.set_ylabel("Implied Volatility")
        ax2.grid(True, alpha=0.3)
        st.pyplot(fig2)

    st.subheader("Call Implied Volatility Surface")

    surface = surface_calls.pivot_table(
        values="impliedVolatility",
        index="strike",
        columns="daysToExpiration",
        aggfunc="mean"
    )

    surface = surface.dropna(thresh=max(2, surface.shape[1] // 2), axis=0)
    surface = surface.dropna(thresh=2, axis=1)

    if surface.shape[0] > 1 and surface.shape[1] > 1:
        z_df = surface.copy().sort_index().sort_index(axis=1)
        z_df = z_df.interpolate(axis=0, limit_direction="both")
        z_df = z_df.interpolate(axis=1, limit_direction="both")

        if z_df.isna().all().all():
            st.warning("Not enough data to interpolate the surface.")
        else:
            x = z_df.columns.values
            y = z_df.index.values
            z = z_df.values

            X, Y = np.meshgrid(x, y)

            fig3 = plt.figure(figsize=(10, 7))
            ax3 = fig3.add_subplot(111, projection="3d")
            ax3.plot_surface(X, Y, z, linewidth=0, antialiased=True)

            ax3.set_xlabel("Days to expiration")
            ax3.set_ylabel("Strike price")
            ax3.set_zlabel("Implied volatility")
            ax3.set_title("Call Implied Volatility Surface")

            st.pyplot(fig3)
    else:
        st.warning("Not enough data to build the volatility surface.")

except Exception as e:
    st.error(f"An error occurred: {e}")
