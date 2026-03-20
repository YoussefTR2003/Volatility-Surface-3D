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
    "It is derived from the price of an option and can be used to gauge market sentiment and make informed trading decisions."
)

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
    chain["daysToExpiration"] = (chain["expiration"] - pd.Timestamp.today()).dt.days + 1
    return chain

@st.cache_data(ttl=600)
def get_surface_data(ticker, expirations):
    frames = []
    asset = yf.Ticker(ticker)

    for expiration in expirations:
        try:
            opt = asset.option_chain(expiration)

            calls = opt.calls.copy()
            calls["optionType"] = "call"
            calls["expiration"] = pd.to_datetime(expiration) + pd.DateOffset(hours=23, minutes=59, seconds=59)
            calls["daysToExpiration"] = (calls["expiration"] - pd.Timestamp.today()).dt.days + 1

            frames.append(calls)
            time.sleep(0.4)
        except Exception:
            continue

    if frames:
        return pd.concat(frames, ignore_index=True)
    return pd.DataFrame()

with st.sidebar:
    st.header("Select an underlying asset")
    ticker = st.text_input("Enter a ticker symbol", value="SPY").upper()

try:
    expirations = get_expirations(ticker)

    if not expirations:
        st.error("No listed options found for this ticker.")
        st.stop()

    selected_expiry_str = st.selectbox("Select expiration", expirations)

    options_one_expiry = get_option_chain(ticker, selected_expiry_str)
    calls_one_expiry = options_one_expiry[options_one_expiry["optionType"] == "call"].copy()
    calls_one_expiry = calls_one_expiry[calls_one_expiry["impliedVolatility"] >= 0.001]

    if calls_one_expiry.empty:
        st.error("No valid call options found for this expiration.")
        st.stop()

    st.subheader("Implied Volatility Skew")
    fig1, ax1 = plt.subplots(figsize=(7, 4))
    calls_one_expiry[["strike", "impliedVolatility"]].set_index("strike").sort_index().plot(ax=ax1)
    ax1.set_title(f"Implied Volatility Skew - {selected_expiry_str}")
    ax1.set_ylabel("Implied Volatility")
    ax1.set_xlabel("Strike")
    st.pyplot(fig1)

    available_strikes = sorted(calls_one_expiry["strike"].dropna().unique())
    default_idx = min(len(available_strikes) // 2, len(available_strikes) - 1)
    selected_strike = st.selectbox("Select strike", available_strikes, index=default_idx)

    limited_expirations = expirations[:5]
    surface_calls = get_surface_data(ticker, limited_expirations)

    if surface_calls.empty:
        st.warning("Could not retrieve enough option data for term structure and surface.")
        st.stop()

    surface_calls = surface_calls[surface_calls["impliedVolatility"] >= 0.001]

    st.subheader("Implied Volatility Term Structure")
    strike_slice = surface_calls[surface_calls["strike"] == selected_strike].copy()

    if strike_slice.empty:
        st.warning("Selected strike is not available across enough expirations.")
    else:
        fig2, ax2 = plt.subplots(figsize=(7, 4))
        strike_slice[["expiration", "impliedVolatility"]].set_index("expiration").sort_index().plot(ax=ax2)
        ax2.set_title(f"Implied Volatility Term Structure - Strike {selected_strike}")
        ax2.set_ylabel("Implied Volatility")
        ax2.set_xlabel("Expiration")
        st.pyplot(fig2)

    st.subheader("Call Implied Volatility Surface")
    surface = (
        surface_calls[["daysToExpiration", "strike", "impliedVolatility"]]
        .pivot_table(values="impliedVolatility", index="strike", columns="daysToExpiration")
        .dropna(axis=0, how="all")
        .dropna(axis=1, how="all")
    )

    if surface.shape[0] > 1 and surface.shape[1] > 1:
        x = surface.columns.values
        y = surface.index.values
        z = surface.values

        row_mask = ~np.all(np.isnan(z), axis=1)
        col_mask = ~np.all(np.isnan(z), axis=0)

        z = z[row_mask][:, col_mask]
        y = y[row_mask]
        x = x[col_mask]

        if z.shape[0] > 1 and z.shape[1] > 1:
            X, Y = np.meshgrid(x, y)

            fig3 = plt.figure(figsize=(10, 8))
            ax3 = fig3.add_subplot(111, projection="3d")
            ax3.plot_surface(X, Y, z)

            ax3.set_xlabel("Days to expiration")
            ax3.set_ylabel("Strike price")
            ax3.set_zlabel("Implied volatility")
            ax3.set_title("Call Implied Volatility Surface")

            st.pyplot(fig3)
        else:
            st.warning("Not enough cleaned data to build the volatility surface.")
    else:
        st.warning("Not enough data to build the volatility surface.")

except Exception as e:
    st.error(f"An error occurred: {e}")
