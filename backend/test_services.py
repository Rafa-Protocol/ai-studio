import os
import requests
from dotenv import load_dotenv
from quant_engine import analyze_technicals, get_token_data


load_dotenv()

def test_coinglass():
    print("\n--- DIAGNOSTIC: COINGLASS V4 ---")
    api_key = os.getenv("COINGLASS_API_KEY")
    headers = {"CG-API-KEY": api_key}

    # 1. TEST FUNDING RATE (Fixed URL)
    # The correct endpoint uses "funding-rate" (kebab-case)
    url_funding = "https://open-api-v4.coinglass.com/api/futures/funding-rate/ohlc-aggregated-history?symbol=BTC&interval=8h"
    
    try:
        res = requests.get(url_funding, headers=headers)
        if res.status_code == 200:
            data = res.json()
            if data.get("data"):
                rate = data["data"][-1]['c'] # 'c' = close
                print(f"✅ Funding Rate URL Fixed! Rate: {rate*100:.4f}%")
            else:
                print(f"⚠️ Funding Data Empty: {data}")
        else:
            print(f"❌ Funding Failed: {res.status_code} {res.text}")
    except Exception as e:
        print(f"❌ Funding Error: {e}")

    # 2. TEST ETF FLOWS (Key Parsing Fix)
    url_etf = "https://open-api-v4.coinglass.com/api/etf/bitcoin/flow-history"
    
    try:
        res = requests.get(url_etf, headers=headers)
        data = res.json()
        if data.get("data"):
            # FIX: We now look for 'flow_usd' based on your previous log
            latest = data["data"][0] 
            flow = latest.get('flow_usd')
            print(f"✅ ETF Data Structure confirmed.")
            print(f"   Latest Flow: ${flow:,}")
            print(f"   Keys found: {list(latest.keys())}")
        else:
            print("⚠️ ETF Data Empty")
            
    except Exception as e:
        print(f"❌ ETF Error: {e}")



def test_vision():
    print("\n--- 🟢 TESTING BASE VISION (UNI) ---")
    
    # 1. Test Technical Analysis (Charts)
    # uni_tech = analyze_technicals("UNI")
    # if uni_tech.get('signal') != 'ERROR':
    #     print(f"✅ Technicals: Price ${uni_tech.get('price')} | RSI {uni_tech.get('rsi')}")
    #     print(f"   Signal: {uni_tech.get('signal')}")
    # else:
    #     print(f"❌ Technicals Failed: {uni_tech}")
        
    # 2. Test Fundamentals (Liquidity)
    # uni_fund = get_token_data("SOL")
    # if uni_fund:
    #     liq = uni_fund.get('liquidity', 0)
    #     print(f"✅ Fundamentals: Liquidity ${liq:,.0f}")
    # else:
    #     print("❌ Fundamentals Failed")

    # print("\n--- 🟣 TESTING SOLANA VISION (SOL) ---")
    
    # 1. Test Technical Analysis (Charts)
    sol_tech = analyze_technicals("SOL")
    if sol_tech.get('signal') != 'ERROR':
        print(f"✅ Technicals: Price ${sol_tech.get('price')} | RSI {sol_tech.get('rsi')}")
        print(f"   Chain Used: {sol_tech.get('chain')}")
    else:
        print(f"❌ Technicals Failed: {sol_tech}")

    # # 2. Test Fundamentals (Liquidity)
    # sol_fund = get_token_data("SOL")
    # if sol_fund:
    #     liq = sol_fund.get('liquidity', 0)
    #     print(f"✅ Fundamentals: Liquidity ${liq:,.0f}")
    # else:
    #     print("❌ Fundamentals Failed")

if __name__ == "__main__":

    # test_coinglass()
    test_vision()
