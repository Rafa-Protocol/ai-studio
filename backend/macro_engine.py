import requests
import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

COINGLASS_API_KEY = os.getenv("COINGLASS_API_KEY")
headers = {
    "CG-API-KEY": COINGLASS_API_KEY,
    "accept": "application/json"
}

def get_macro_health():
    report = []
    sentiment = "NEUTRAL"
    
    # --- 1. ETF FLOWS (Fixed: Key & Sorting) ---
    try:
        url = "https://open-api-v4.coinglass.com/api/etf/bitcoin/flow-history"
        res = requests.get(url, headers=headers).json()
        
        if res.get('code') == '0' and 'data' in res:
            data = res['data']
            
            # FIX 1: Sort by timestamp descending (Newest first)
            # This ensures we are looking at Dec 2025, not Jan 2024
            data.sort(key=lambda x: x['timestamp'], reverse=True)
            
            # Look at last 3 days of reported data
            recent = data[:3]
            
            # FIX 2: Use correct key 'flow_usd' (from your logs)
            total_flow = sum([d.get('flow_usd', 0) for d in recent])
            flow_millions = total_flow / 1_000_000
            
            # Get date of the most recent data point
            last_ts = recent[0].get('timestamp', 0)
            last_date = pd.to_datetime(last_ts, unit='ms').strftime('%Y-%m-%d')
            
            if flow_millions > 0:
                report.append(f"✅ ETF 3-Day Flows: +${flow_millions:,.1f}M (Bullish) [{last_date}]")
                sentiment = "BULLISH"
            else:
                report.append(f"❌ ETF 3-Day Flows: ${flow_millions:,.1f}M (Bearish) [{last_date}]")
                sentiment = "BEARISH"
        else:
            report.append("⚠️ ETF Data Unavailable")
            
    except Exception as e:
        report.append(f"⚠️ ETF Error: {str(e)}")

    # --- 2. FUNDING RATES (Fixed: URL) ---
    try:
        # FIX 3: Use 'oi-weight-history' endpoint (Confirmed V4)
        url = "https://open-api-v4.coinglass.com/api/futures/funding-rate/oi-weight-history?symbol=BTC&interval=8h"
        res = requests.get(url, headers=headers).json()
        
        if res.get('code') == '0' and 'data' in res:
            # Get latest candle
            latest = res['data'][-1]
            rate = latest.get('c', 0) # 'c' = close
            
            # Convert to percentage
            rate_pct = rate * 100
            
            if rate_pct > 0.02:
                report.append(f"🔥 Funding Overheated: {rate_pct:.4f}%")
                if sentiment == "BULLISH": sentiment = "CAUTIOUS"
            elif rate_pct < 0:
                report.append(f"🧊 Funding Negative: {rate_pct:.4f}% (Squeeze Potential)")
            else:
                report.append(f"🟢 Funding Healthy: {rate_pct:.4f}%")
        else:
            report.append("⚠️ Funding Data Unavailable")
            
    except Exception as e:
        report.append(f"⚠️ Funding Connection Failed: {str(e)}")

    return {
        "sentiment": sentiment,
        "details": "\n".join(report)
    }