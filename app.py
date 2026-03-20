import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime as dt
from mpl_toolkits.mplot3d import Axes3D

st.set_page_config(layout="wide")
st.title("Option Volatility Surface")
st.header(
    "Implied volatility is the market's expectation of how volatile the underlying asset will be in the future. "
    "It is derived from the price of an option and can be used to gauge market sentiment and make informed trading decisions."
)

@st.cache_data(ttl=600)
def option_chains(ticker):
    asset = yf.Ticker(ticker)
    expirations = asset.options
    chains = pd.DataFrame()

    expirations = expirations[:5]  # max 5 maturités
    for expiration in expirations:
        opt = asset.option_chain(expiration)

        calls = opt.calls.copy()
        calls["optionType"] = "call"

        puts = opt.puts.copy()
        puts["optionType"] = "put"

        chain = pd.concat([calls, puts], ignore_index=True)
        chain["expiration"] = pd.to_datetime(expiration) + pd.DateOffset(hours=23, minutes=59, seconds=59)

        chains = pd.concat([chains, chain], ignore_index=True)

    chains["daysToExpiration"] = (chains["expiration"] - pd.Timestamp.today()).dt.days + 1
    return chains

with st.sidebar:
    st.header("Select an underlying asset")
    ticker = st.text_input("Enter a ticker symbol", value="SPY").upper()

try:
    options = option_chains(ticker)

    calls = options[options["optionType"] == "call"].copy()

    if calls.empty:
        st.error("No call options found for this ticker.")
    else:
        expirations = sorted(calls["expiration"].dropna().unique())
        selected_expiry = st.selectbox("Select expiration", expirations)

        calls_at_expiry = calls[calls["expiration"] == selected_expiry].copy()
        filtered_calls_at_expiry = calls_at_expiry[calls_at_expiry["impliedVolatility"] >= 0.001]

        st.subheader("Implied Volatility Skew")
        fig1, ax1 = plt.subplots(figsize=(7, 4))
        filtered_calls_at_expiry[["strike", "impliedVolatility"]].set_index("strike").plot(ax=ax1)
        ax1.set_title("Implied Volatility Skew")
        ax1.set_ylabel("Implied Volatility")
        st.pyplot(fig1)

        available_strikes = sorted(calls["strike"].dropna().unique())
        selected_strike = st.selectbox("Select strike", available_strikes, index=min(len(available_strikes)//2, len(available_strikes)-1))

        call_strike = calls[calls["strike"] == selected_strike].copy()
        filtered_call_strike = call_strike[call_strike["impliedVolatility"] >= 0.001]

        st.subheader("Implied Volatility Term Structure")
        fig2, ax2 = plt.subplots(figsize=(7, 4))
        filtered_call_strike[["expiration", "impliedVolatility"]].set_index("expiration").plot(ax=ax2)
        ax2.set_title("Implied Volatility Term Structure")
        ax2.set_ylabel("Implied Volatility")
        st.pyplot(fig2)

        st.subheader("Call Implied Volatility Surface")
        surface = (
            calls[["daysToExpiration", "strike", "impliedVolatility"]]
            .pivot_table(values="impliedVolatility", index="strike", columns="daysToExpiration")
        )

        # garder seulement les zones exploitables
        surface = surface.dropna(axis=0, how="all").dropna(axis=1, how="all")

        if surface.shape[0] > 1 and surface.shape[1] > 1:
            x = surface.columns.values
            y = surface.index.values
            z = surface.values

            # remplace les NaN restants par interpolation simple ou suppression
            mask = ~np.isnan(z)
            valid_rows = mask.any(axis=1)
            valid_cols = mask.any(axis=0)

            z = z[valid_rows][:, valid_cols]
            y = y[valid_rows]
            x = x[valid_cols]

            X, Y = np.meshgrid(x, y)

            fig3 = plt.figure(figsize=(10, 8))
            ax3 = fig3.add_subplot(111, projection="3d")
            ax3.plot_surface(X, Y, z)

            ax3.set_xlabel("Days to expiration")
            ax3.set_ylabel("Strike price")
            ax3.set_zlabel("Implied volatility")
            ax3.set_title("Call implied volatility surface")

            st.pyplot(fig3)
        else:
            st.warning("Not enough data to build the volatility surface.")

except Exception as e:
    st.error(f"An error occurred: {e}")
