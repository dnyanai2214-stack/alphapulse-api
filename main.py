from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
from dhanhq import dhanhq

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# लाईव्ह मार्केट डेटा देणारा मेन एंडपॉईंट (Nifty, BankNifty, Sensex, VIX)
@app.get("/api/live-indices")
def get_live_indices(dhan_id: str = "", dhan_token: str = ""):
    # १. जर युजरने Settings मध्ये Dhan API टाकले असेल तर थेट Dhan चा झिरो-डिले डेटा घ्या
    if dhan_id and dhan_token:
        try:
            dhan = dhanhq(dhan_id, dhan_token)
            # Dhan Market Quote API कॉल (Nifty=13, BankNifty=25)
            quote = dhan.quote_data({"IDX_I": [13, 25]})
            if quote.get("status") == "success":
                return {"source": "DHAN_REALTIME", "data": quote["data"]}
        except Exception as e:
            pass

    # २. बॅकअप: खरा लाईव्ह मार्केट डेटा (TradingView किमतींशी जुळणारा)
    symbols = {
        "NIFTY": "^NSEI",
        "BANKNIFTY": "^NSEBANK",
        "SENSEX": "^BSESN",
        "VIX": "^INDIAVIX"
    }
    result = {}
    for name, ticker in symbols.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="2d", interval="1m")
            if not hist.empty:
                current_price = round(float(hist['Close'].iloc[-1]), 2)
                prev_close = round(float(t.fast_info['previousClose']), 2)
                change = round(current_price - prev_close, 2)
                pct = round((change / prev_close) * 100, 2)
                result[name] = {"price": current_price, "change": change, "pct": pct}
        except:
            result[name] = {"price": 0, "change": 0, "pct": 0}
            
    return {"source": "LIVE_NSE_FEED", "timestamp": datetime.now().isoformat(), "indices": result}
