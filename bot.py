import asyncio
import os
import re
import time
from datetime import datetime
import requests

# ----------------- تنظیمات -----------------
TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN", "8913236446:AAG-Fx4BX86rf84OkYG3ikotS5kE4tJKbRY"
)
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "95150036")

SOLANA_WATCHLIST = [
    "SynthetixTrade",
    "sierasfx",
    "blknoiz06",
    "LarpVonTrier",
    "artsch00lreject",
    "Poe_Ether",
    "thecexoffender",
    "arrogantfrfr",
    "Theunipcs",
    "0xVonGogh",
    "Renzofks",
    "CrashiusClay69",
    "larpalt",
    "iambroots",
    "UniswapVillain",
    "SolanaFloor",
    "solana_daily",
    "SOLBigBrain",
    "MemeCoinCalls",
    "SolMemeAlpha",
    "PumpFunCalls",
    "SolanaGems",
    "lookonchain",
    "bubblemaps",
    "DegenerateNews",
    "ZackXBT",
    "RektFencer",
    "0xFastHand",
    "CryptoWizardd",
    "SolanaWhaleAlert",
    "RaydiumProtocol",
    "PhotonSolana",
]

seen_tweet_ids = set()


def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Error sending Telegram alert: {e}")


def extract_solana_address(text):
    if not text:
        return []
    solana_pattern = (
        r"\b[1-9A-HJ-NP-Za-km-z]{32,44}pump\b|\b[1-9A-HJ-NP-Za-km-z]{43,44}\b"
    )
    return re.findall(solana_pattern, str(text))


def extract_tickers(text):
    if not text:
        return []
    # استخراج کلماتی که با $ شروع می‌شوند (مثل $BONK)
    ticker_pattern = r"\$([A-Za-z0-9_]{2,10})\b"
    return re.findall(ticker_pattern, str(text))


def get_dex_info_by_ca(mint_address):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{mint_address}"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            pairs = data.get("pairs")
            if pairs:
                # انتخاب برترین جفت معاملاتی سولانا
                sol_pairs = [p for p in pairs if p.get("chainId") == "solana"]
                if sol_pairs:
                    pair = sol_pairs[0]
                    created_at = pair.get("pairCreatedAt", 0) / 1000.0
                    
                    # محاسبه سن توکن (به روز)
                    age_days = (time.time() - created_at) / 86400.0 if created_at > 0 else 0
                    
                    name = pair.get("baseToken", {}).get("name", "Unknown")
                    symbol = pair.get("baseToken", {}).get("symbol", "UNKNOWN")
                    market_cap = pair.get("fdv", pair.get("marketCap", 0))
                    liquidity = pair.get("liquidity", {}).get("usd", 0)
                    
                    return {
                        "ca": mint_address,
                        "name": name,
                        "symbol": symbol,
                        "market_cap": market_cap,
                        "liquidity": liquidity,
                        "age_days": round(age_days, 1),
                        "valid": age_days <= 90  # فیلتر حداکثر ۳ ماه سن
                    }
    except Exception as e:
        print(f"DexScreener CA Error: {e}")
    return None


def get_dex_info_by_ticker(ticker):
    url = f"https://api.dexscreener.com/latest/dex/search?q={ticker}"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            pairs = data.get("pairs", [])
            sol_pairs = [p for p in pairs if p.get("chainId") == "solana" and p.get("baseToken", {}).get("symbol", "").upper() == ticker.upper()]
            
            if sol_pairs:
                # مرتب‌سازی بر اساس بالاترین نقدینگی
                sol_pairs.sort(key=lambda x: x.get("liquidity", {}).get("usd", 0), reverse=True)
                pair = sol_pairs[0]
                
                created_at = pair.get("pairCreatedAt", 0) / 1000.0
                age_days = (time.time() - created_at) / 86400.0 if created_at > 0 else 0
                mint_address = pair.get("baseToken", {}).get("address")
                
                return {
                    "ca": mint_address,
                    "name": pair.get("baseToken", {}).get("name", "Unknown"),
                    "symbol": pair.get("baseToken", {}).get("symbol", "UNKNOWN"),
                    "market_cap": pair.get("fdv", pair.get("marketCap", 0)),
                    "liquidity": pair.get("liquidity", {}).get("usd", 0),
                    "age_days": round(age_days, 1),
                    "valid": age_days <= 90
                }
    except Exception as e:
        print(f"DexScreener Ticker Error: {e}")
    return None


def check_token_security(mint_address):
    url = f"https://api.rugcheck.xyz/v1/tokens/{mint_address}/report/summary"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            score = data.get("score", 0)

            if score < 1000:
                risk_label = "🟢 <b>Low Risk</b>"
            elif score < 5000:
                risk_label = "🟡 <b>Medium Risk</b>"
            else:
                risk_label = "🔴 <b>High Risk</b>"

            risks = data.get("risks", [])
            risk_details = [f"• {r.get('name')}" for r in risks[:3]] if risks else []
            risk_text = "\n".join(risk_details) if risk_details else "• پاک"

            return f"🛡️ <b>RugCheck Score:</b> {score} ({risk_label})\n<b>Risks:</b>\n{risk_text}"
        return "🛡️ <b>RugCheck:</b> اطلاعات در دسترس نیست"
    except Exception:
        return "🛡️ <b>RugCheck:</b> خطا در دریافت استعلام"


def fetch_tweets_fast_rss(username):
    instances = [
        "https://nitter.poast.org",
        "https://nitter.privacydev.net",
        "https://nitter.net"
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    for instance in instances:
        try:
            url = f"{instance}/{username}/rss"
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                text = resp.text
                cas = extract_solana_address(text)
                tickers = extract_tickers(text)
                if cas or tickers:
                    tweet_id = f"{username}_{hash(text)}"
                    return [(tweet_id, text, cas, tickers)]
        except Exception:
            continue
    return []


async def main():
    print("🚀 Advanced Solana Alpha Scanner Started...")
    send_telegram_alert("⚡ <b>Pro Scanner Online!</b>\nتحلیل مارکت‌کپ، سن توکن و $TICKER فعال شد.")

    while True:
        for username in SOLANA_WATCHLIST:
            try:
                results = fetch_tweets_fast_rss(username)

                for tweet_id, raw_text, cas, tickers in results:
                    if not tweet_id or tweet_id in seen_tweet_ids:
                        continue

                    token_info = None

                    # ۱. اولویت با آدرس کانترکت (CA)
                    if cas:
                        token_info = get_dex_info_by_ca(cas[0])
                    # ۲. اگر CA نبود، جستجو بر اساس Ticker
                    elif tickers:
                        # حذف تیکرهای عمومی بازار
                        ignored = ["SOL", "USDC", "USDT", "BTC", "ETH"]
                        filtered_tickers = [t for t in tickers if t.upper() not in ignored]
                        if filtered_tickers:
                            token_info = get_dex_info_by_ticker(filtered_tickers[0])

                    if token_info:
                        # بررسی شرط حداکثر ۳ ماه سن
                        if not token_info["valid"]:
                            continue

                        seen_tweet_ids.add(tweet_id)
                        ca = token_info["ca"]
                        security_info = check_token_security(ca)
                        mc_formatted = f"${token_info['market_cap']:,.0f}" if token_info['market_cap'] else "N/A"
                        liq_formatted = f"${token_info['liquidity']:,.0f}" if token_info['liquidity'] else "N/A"

                        alert_msg = (
                            f"☀️ <b>SOLANA ALPHA DETECTED!</b>\n\n"
                            f"👤 <b>Account:</b> @{username}\n"
                            f"🪙 <b>Token:</b> {token_info['name']} (${token_info['symbol']})\n"
                            f"📊 <b>Market Cap:</b> {mc_formatted}\n"
                            f"💧 <b>Liquidity:</b> {liq_formatted}\n"
                            f"⏳ <b>Age:</b> {token_info['age_days']} روز\n\n"
                            f"🔑 <b>Solana CA:</b>\n<code>{ca}</code>\n\n"
                            f"{security_info}\n\n"
                            f"🦅 <a href='https://dexscreener.com/solana/{ca}'>DexScreener</a> | "
                            f"🧪 <a href='https://photon-sol.tinyastro.io/en/lp/{ca}'>Photon</a>\n"
                            f"🔗 <a href='https://x.com/{username}'>مشاهده اکانت</a>"
                        )
                        send_telegram_alert(alert_msg)

            except Exception as e:
                print(f"Error checking @{username}: {e}")

            await asyncio.sleep(1.5)
        await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(main())
