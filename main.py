from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import yfinance as yf
from datetime import datetime

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/api/live-indices")
def get_live_indices(dhan_id: str = "", dhan_token: str = ""):
    # १. थेट DhanHQ v2 Market Quote API (Super Fast - Zero Delay)
    if dhan_id.strip() and dhan_token.strip():
        try:
            url = "https://api.dhan.co/v2/marketfeed/quote"
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "access-token": dhan_token.strip(),
                "client-id": dhan_id.strip()
            }
            # NSE Indices: 13 = NIFTY 50, 25 = BANK NIFTY, 27 = FINNIFTY | BSE: 51 = SENSEX
            payload = {
                "IDX_I": [13, 25, 27]
            }
            res = requests.post(url, json=payload, headers=headers, timeout=3)
            data = res.json()

            if res.status_code == 200 and data.get("status") == "success":
                idx_data = data.get("data", {}).get("IDX_I", {})
                nifty_info = idx_data.get("13", {})
                bnf_info = idx_data.get("25", {})
                fin_info = idx_data.get("27", {})

                def format_dhan(item):
                    ltp = float(item.get("last_price", 0))
                    prev = float(item.get("ohlc", {}).get("close", ltp))
                    chg = round(ltp - prev, 2)
                    pct = round((chg / prev) * 100, 2) if prev else 0
                    return {"price": round(ltp, 2), "change": chg, "pct": pct}

                return {
                    "source": "DHAN_LIVE_FAST",
                    "timestamp": datetime.now().isoformat(),
                    "indices": {
                        "NIFTY": format_dhan(nifty_info),
                        "BANKNIFTY": format_dhan(bnf_info),
                        "FINNIFTY": format_dhan(fin_info),
                        "VIX": {"price": 13.5, "change": 0, "pct": 0}
                    }
                }
            else:
                # Dhan कडून एरर आल्यास कारण दाखवा (उदा. Data API Subscription)
                dhan_error = data.get("remarks", data)
        except Exception as e:
            dhan_error = str(e)
    else:
        dhan_error = "No Dhan Credentials Provided"

    # २. बॅकअप फीड (जर Dhan Data API सक्रिय नसेल तर)
    symbols = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK", "SENSEX": "^BSESN", "VIX": "^INDIAVIX"}
    result = {}
    for name, ticker in symbols.items():
        try:
            t = yf.Ticker(ticker)
            price = round(float(t.fast_info['lastPrice']), 2)
            prev = round(float(t.fast_info['previousClose']), 2)
            chg = round(price - prev, 2)
            pct = round((chg / prev) * 100, 2)
            result[name] = {"price": price, "change": chg, "pct": pct}
        except:
            result[name] = {"price": 0, "change": 0, "pct": 0}

    return {
        "source": "BACKUP_FEED",
        "dhan_status": dhan_error,
        "timestamp": datetime.now().isoformat(),
        "indices": result
    }
