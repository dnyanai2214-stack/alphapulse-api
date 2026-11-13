from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import yfinance as yf
import pandas as pd
import feedparser
from datetime import datetime

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/api/live-indices")
def get_live_indices(dhan_id: str = "", dhan_token: str = ""):
    # १. थेट DhanHQ v2 Real-Time Market Quote API
    if dhan_id.strip() and dhan_token.strip():
        try:
            url = "https://api.dhan.co/v2/marketfeed/quote"
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "access-token": dhan_token.strip(),
                "client-id": dhan_id.strip()
            }
            payload = {"IDX_I": [13, 25, 27]}
            res = requests.post(url, json=payload, headers=headers, timeout=3)
            data = res.json()

            if res.status_code == 200 and data.get("status") == "success":
                idx_data = data.get("data", {}).get("IDX_I", {})
                
                def parse_quote(sec_id):
                    item = idx_data.get(str(sec_id), {})
                    ltp = float(item.get("last_price", 0))
                    prev = float(item.get("ohlc", {}).get("close", ltp))
                    chg = round(ltp - prev, 2)
                    pct = round((chg / prev) * 100, 2) if prev else 0
                    return {"price": round(ltp, 2), "change": chg, "pct": pct}

                return {
                    "status": "LIVE",
                    "source": "DHAN_REALTIME",
                    "timestamp": datetime.now().isoformat(),
                    "indices": {
                        "NIFTY": parse_quote(13),
                        "BANKNIFTY": parse_quote(25),
                        "FINNIFTY": parse_quote(27)
                    }
                }
        except Exception as e:
            pass

    # २. जर Dhan API सक्रिय नसेल, तर थेट NSE/BSE Live Feed (कोणताही काल्पनिक आकडा नाही)
    symbols = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK", "SENSEX": "^BSESN", "VIX": "^INDIAVIX"}
    result = {}
    valid_count = 0
    for name, ticker in symbols.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="1d", interval="1m")
            if not hist.empty:
                price = round(float(hist['Close'].iloc[-1]), 2)
                prev = round(float(t.fast_info['previousClose']), 2)
                chg = round(price - prev, 2)
                pct = round((chg / prev) * 100, 2) if prev else 0
                result[name] = {"price": price, "change": chg, "pct": pct}
                valid_count += 1
            else:
                result[name] = None
        except:
            result[name] = None

    if valid_count == 0:
        return {"status": "NO_DATA", "message": "Live market data unavailable. Check Dhan API."}

    return {
        "status": "LIVE",
        "source": "NSE_BSE_LIVE",
        "timestamp": datetime.now().isoformat(),
        "indices": result
    }

@app.get("/api/live-news")
def get_live_news():
    rss_urls = [
        "https://www.moneycontrol.com/rss/marketreports.xml",
        "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"
    ]
    news = []
    for url in rss_urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:6]:
                news.append({
                    "title": entry.title,
                    "published": entry.get("published", ""),
                    "link": entry.link
                })
        except:
            pass
    return {"status": "LIVE" if news else "NO_DATA", "news": news}
