import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGO_URL)
db = client.rafa_db

async def seed():
    strategies = [
        # --- 1. TREND FOLLOWING ---
        {
            "_id": "momentum_breakout",
            "name": "🌊 Momentum Breakout (Whale Surfer)",
            "description": "Capitalizes on assets with surging volume and strong price action.",
            "condition": "bullish",
            "rules": """
            1. Price > EMA_20 (Uptrend)
            2. RSI is 50-70 (Strong but not topped)
            3. Volume > 1.5x Average (High conviction)
            EXECUTION: Aggressive Size (5%). Trail Stop Loss.
            """,
            "risk_profile": "aggressive"
        },
        {
            "_id": "golden_cross",
            "name": "✨ Golden Cross (Trend Reversal)",
            "description": "Classic long-term trend shift signal.",
            "condition": "bullish_long_term",
            "rules": """
            1. EMA_50 crosses ABOVE EMA_200
            2. Asset Liquidity > $1M
            EXECUTION: Large Size (10%). Hold for weeks.
            """,
            "risk_profile": "moderate"
        },

        # --- 2. MEAN REVERSION ---
        {
            "_id": "mean_reversion",
            "name": "🎯 Mean Reversion (Dip Sniper)",
            "description": "Buys fundamentally strong assets that are temporarily oversold.",
            "condition": "bearish",
            "rules": """
            1. RSI < 30 (Oversold)
            2. Price < EMA_20 (Below trend)
            3. Liquidity > $500k (Safety)
            EXECUTION: Small Size (2%). Quick Profit Take at EMA_20.
            """,
            "risk_profile": "moderate"
        },
        {
            "_id": "liquidity_sweep",
            "name": "🧹 Liquidity Sweep (Turtle Soup)",
            "description": "Buys when price sweeps a previous low but closes back above it (Fakeout).",
            "condition": "choppy",
            "rules": """
            1. Price breaks 24h Low
            2. RSI Bullish Divergence (Price Lower, RSI Higher)
            3. Candle closes back inside range
            EXECUTION: Medium Size. Stop loss just below the wick.
            """,
            "risk_profile": "aggressive"
        },

        # --- 3. VOLATILITY & VOLUME ---
        {
            "_id": "volatility_squeeze",
            "name": "🐍 Volatility Squeeze",
            "description": "Enters when low volatility periods end with an explosive move.",
            "condition": "sideways",
            "rules": """
            1. Price consolidates (low variance) for >24h
            2. Sudden Volume Spike (>2x Avg)
            3. Price breaks resistance
            EXECUTION: Medium Size.
            """,
            "risk_profile": "aggressive"
        },
        {
            "_id": "vwap_pullback",
            "name": "⚓ VWAP Pullback",
            "description": "Institutional entry strategy during uptrends.",
            "condition": "bullish",
            "rules": """
            1. Macro Trend is Bullish (ETF Flows > 0)
            2. Price touches VWAP line
            3. RSI is Neutral (40-60)
            EXECUTION: Medium Size. It's a 'Fair Value' entry.
            """,
            "risk_profile": "conservative"
        },

        # --- 4. MACRO & SENTIMENT ---
        {
            "_id": "funding_squeeze",
            "name": "🍋 Funding Squeeze Hunter",
            "description": "Contrarian play against over-eager shorters.",
            "condition": "volatile",
            "rules": """
            1. Bitcoin Funding Rate < 0% (Bears paying Bulls)
            2. ETF Flows > 0 (Institutions Buying)
            3. RSI < 40
            EXECUTION: Aggressive Long. Target short liquidations.
            """,
            "risk_profile": "aggressive"
        },
        {
            "_id": "sentiment_surfer",
            "name": "📰 News Sentiment Momentum",
            "description": "Rides the wave of breaking positive news.",
            "condition": "news_event",
            "rules": """
            1. Tavily Sentiment is 'Positive'
            2. Volume is Rising
            3. Price has not yet pumped >10% (Early Entry)
            EXECUTION: Scalp trade. Sell on news fade.
            """,
            "risk_profile": "high_risk"
        },

        # --- 5. DEFENSIVE & CORRELATION ---
        {
            "_id": "beta_rotation",
            "name": "🔗 Beta Rotation (ETH Follower)",
            "description": "Trades L2 tokens (Base) when ETH moves first.",
            "condition": "bullish_eth",
            "rules": """
            1. ETH 24h Change > 5%
            2. Base Token 24h Change < 2% (Laggard)
            3. Correlation > 0.8
            EXECUTION: Buy the Laggard. Catch up trade.
            """,
            "risk_profile": "moderate"
        },
        {
            "_id": "capital_preservation",
            "name": "🛡️ Capital Preservation Protocol",
            "description": "Emergency defensive mode.",
            "condition": "crash",
            "rules": """
            1. ETF Flows < -$50M
            2. BTC Price < EMA_200
            EXECUTION: NO BUYS. Sell weak positions. Hold Stablecoins.
            """,
            "risk_profile": "conservative"
        }
    ]
    
    print(f">> Injecting {len(strategies)} Quant Strategies into RAFA Brain...")
    for strat in strategies:
        await db.strategies.replace_one({"_id": strat["_id"]}, strat, upsert=True)
    print(">> Success! RAFA Playbook Updated.")

if __name__ == "__main__":
    asyncio.run(seed())