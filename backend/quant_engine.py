import requests
import pandas as pd
import pandas_ta_classic as ta 
import os
from dotenv import load_dotenv
from dex_config import TOKEN_MAP
from cachetools import TTLCache 

load_dotenv()
BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY")
TAAPI_API_KEY = os.getenv("TAAPI_API_KEY")

# --- CACHE SETUP ---
# separate caches for different data types to avoid key collisions
# ttl=60 means data is fresh for 60 seconds. Adjust as needed.
fundamental_cache = TTLCache(maxsize=100, ttl=60)
technical_cache = TTLCache(maxsize=100, ttl=60)

def get_headers(chain):
    """Generates headers for the specific chain"""
    return {
        "X-API-KEY": BIRDEYE_API_KEY,
        "accept": "application/json",
        "x-chain": chain 
    }

def get_token_data(ticker):
    """Fetches Fundamental Data (Liquidity, Market Cap) with Caching"""
    ticker_upper = ticker.upper()
    
    # 1. Check Cache
    if ticker_upper in fundamental_cache:
        print(f"⚡ CACHE HIT: Fundamentals for {ticker_upper}")
        return fundamental_cache[ticker_upper]

    token_info = TOKEN_MAP.get(ticker_upper)
    if not token_info: return None

    address = token_info['address']
    chain = token_info['chain']
    headers = get_headers(chain)

    url = f"https://public-api.birdeye.so/defi/token_overview?address={address}"
    
    try:
        res = requests.get(url, headers=headers).json()
        
        if not res.get('success'):
            print(f"⚠️ FUNDAMENTAL ERROR ({ticker}): {res}") 
            return None
        
        data = res['data']
        
        # 2. Store in Cache
        fundamental_cache[ticker_upper] = data
        return data

    except Exception as e:
        print(f"⚠️ EXCEPTION ({ticker}): {e}")
        return None

def get_taapi_value(symbol, indicator, params=None):
    """Helper to fetch a single indicator from Taapi"""
    base_url = f"https://api.taapi.io/{indicator}"
    
    # Default params for Top 1000 coins (Binance is the most liquid source)
    payload = {
        'secret': TAAPI_API_KEY,
        'exchange': 'binance',
        'symbol': f"{symbol}/USDT",
        'interval': '1h' # 1 Hour candles
    }
    
    if params:
        payload.update(params)

    try:
        response = requests.get(base_url, params=payload, timeout=5)
        response.raise_for_status()
        return response.json().get('value')
    except Exception as e:
        print(f"⚠️ Taapi Error ({indicator} for {symbol}): {e}")
        return None

def analyze_technicals(ticker):
    """
    Fetches pre-calculated RSI, EMA, and Price from Taapi.io
    """
    ticker_upper = ticker.upper()

    # 1. CHECK CACHE
    if ticker_upper in technical_cache:
        print(f"⚡ CACHE HIT: {ticker_upper}")
        return technical_cache[ticker_upper]

    print(f"🔄 Fetching Taapi data for {ticker_upper}...")

    # 2. FETCH INDICATORS (3 API Calls per token)
    # Taapi provides these pre-calculated. No local math needed.
    
    # Call A: Get RSI (14)
    rsi = get_taapi_value(ticker_upper, "rsi", {'period': 14})
    
    # Call B: Get EMA (20)
    ema = get_taapi_value(ticker_upper, "ema", {'period': 20})
    
    # Call C: Get Current Price (via their 'candle' or 'price' endpoint)
    # Note: Taapi doesn't have a simple 'price' endpoint in all tiers, 
    # but we can grab the 'close' of the latest candle.
    current_price = None
    try:
        candle = requests.get(
            "https://api.taapi.io/candle", 
            params={
                'secret': TAAPI_API_KEY, 
                'exchange': 'binance', 
                'symbol': f"{ticker_upper}/USDT", 
                'interval': '1h'
            }
        ).json()
        current_price = candle.get('close')
    except:
        pass

    # 3. VALIDATE DATA
    if rsi is None or ema is None or current_price is None:
        return {
            "signal": "NEUTRAL", 
            "reason": "Data unavailable (Coin might not be on Binance/Taapi)"
        }

    # 4. SIGNAL LOGIC
    signal = "NEUTRAL"
    reasons = []

    # RSI Logic
    if rsi < 30: 
        signal = "BUY"
        reasons.append(f"Oversold ({round(rsi, 2)})")
    elif rsi > 70: 
        signal = "SELL"
        reasons.append(f"Overbought ({round(rsi, 2)})")
    else:
        reasons.append(f"RSI Neutral ({round(rsi, 2)})")
    
    # Trend Logic
    if current_price > ema:
        reasons.append("Trend: Bullish (Price > EMA)")
    else:
        reasons.append("Trend: Bearish (Price < EMA)")

    result = {
        "signal": signal,
        "rsi": round(rsi, 2),
        "ema": round(ema, 4),
        "price": current_price,
        "rationale": " | ".join(reasons)
    }

    # 5. STORE IN CACHE
    technical_cache[ticker_upper] = result
    
    return result