import asyncio
import os
import re
import time
import requests

# ----------------- تنظیمات متغیرهای محیطی -----------------
TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN", "8913236446:AAG-Fx4BX86rf84OkYG3ikotS5kE4tJKbRY"
)
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "95150036")

# ----------------- فیلترهای مالی و تکنیکال -----------------
MIN_5M_VOLUME = 1000         # حداقل حجم معاملات ۵ دقیقه اخیر (دلار)
MIN_MARKET_CAP = 10000       # حداقل مارکت‌کپ (دلار)
MIN_LIQUIDITY = 3000         # حداقل نقدینگی (دلار)
MIN_24H_VOLUME = 5000        # حداقل حجم معاملات ۲۴ ساعته (دلار)
MIN_LIQUIDITY_RATIO = 0.10   # حداقل نسبت نقدینگی به مارکت‌کپ (۱۰٪)
MAX_AGE_DAYS = 90            # حداکثر سن توکن (روز)

# ----------------- لیست اکانت‌ها -----------------
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
    ticker_pattern = r"\$([A-Za-z0-9_]{2,10})\b"
    return re.findall(ticker_pattern, str(text))


def evaluate_filters(data, mint_address):
    """اعمال کامل فیلترهای عددی روی دیتای GMGN"""
    created_at = data.get("creation_timestamp", 0)
    age_days = (time.time() - created_at) / 86400.0 if created_at > 0 else 0

    name = data.get("name", "Unknown")
    symbol = data.get("symbol", "UNKNOWN")
    market_cap = data.get("market_cap", 0) or data.get("fdv", 0) or 0
    liquidity = data.get("liquidity", 0) or 0
    volume_5m = data.get("volume_5m", 0) or 0
    volume_24h = data.get("volume_24h", 0) or 0

    liq_ratio = (liquidity / market_cap) if market_cap > 0 else 0

    # بررسی تک‌تک فیلترها
    is_valid = (
        volume_5m >= MIN_5M_VOLUME
        and age_days <= MAX_AGE_DAYS
        and market_cap >= MIN_MARKET_CAP
        and liquidity >= MIN_LIQUIDITY
        and volume_24h >= MIN_24H_VOLUME
        and liq_ratio >= MIN_LIQUIDITY_RATIO
    )

    return {
        "ca": mint_address,
        "name": name,
        "symbol": symbol,
        "market_cap": market_cap,
        "liquidity": liquidity,
        "volume_5m": volume_5m,
        "volume_24h": volume_24h,
        "liq_ratio": round(liq_ratio * 100, 1),
        "age_days": round(age_days, 1),
        "valid": is_valid,
    }


def get_gmgn_info_by_ca(mint_address):
    url = f"https://gmgn.ai/defi/quotation/v1/tokens/sol/{mint_address}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            res = resp.json()
            if res.get("code") == 0:
                data = res.get("data", {}).get("token", {})
                return evaluate_filters(data, mint_address)
    except Exception as e:
        print(f"GMGN CA Error: {e}")
    return None


def get_gmgn_info_by_ticker(ticker):
    url = f"https://gmgn.ai/api/v1/search?q={ticker}&chain=sol"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            res = resp.json()
            tokens = res.get("data", {}).get("tokens", [])
            sol_tokens = [
                t for t in tokens if t.get("symbol", "").upper() == ticker.upper()
            ]
            if sol_tokens:
                sol_tokens.sort(key=lambda x: x.get("liquidity", 0), reverse=True)
                target_ca = sol_tokens[0].get("address")
                if target_ca:
                    return get_gmgn_info_by_ca(target_ca)
    except Exception as e:
        print(f"GMGN Ticker Error: {e}")
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


def fetch_tweets_syndication(username):
    url = f"https://syndication.twitter.com/srv/timeline-profile/history?screen_name={username}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            raw_html = data.get("body", "")
            if not raw_html:
                return []

            cas = extract_solana_address(raw_html)
            tickers = extract_tickers(raw_html)

            if cas or tickers:
                tweet_id = f"{username}_{hash(raw_html[:200])}"
                return [(tweet_id, raw_html, cas, tickers)]
    except Exception as e:
        print(f"Syndication Error for @{username}: {e}")
    return []


async def main():
    print("🚀 GMGN Solana Alpha Scanner Started...")
    send_telegram_alert(
        "⚡ <b>GMGN Pro Scanner Online!</b>\nفیلترهای نقدینگی، مارکت‌کپ و حجم معاملات فعال شدند."
    )

    while True:
        for username in SOLANA_WATCHLIST:
            try:
                results = fetch_tweets_syndication(username)

                for tweet_id, raw_text, cas, tickers in results:
                    if not tweet_id or tweet_id in seen_tweet_ids:
                        continue

                    token_info = None

                    if cas:
                        token_info = get_gmgn_info_by_ca(cas[0])
                    elif tickers:
                        ignored = ["SOL", "USDC", "USDT", "BTC", "ETH"]
                        filtered_tickers = [
                            t for t in tickers if t.upper() not in ignored
                        ]
                        if filtered_tickers:
                            token_info = get_gmgn_info_by_ticker(filtered_tickers[0])

                    if token_info:
                        # رد کردن توکن‌هایی که شروط فیلتر را پاس نکنند
                        if not token_info["valid"]:
                            continue

                        seen_tweet_ids.add(tweet_id)
                        ca = token_info["ca"]
                        security_info = check_token_security(ca)
                        mc_formatted = (
                            f"${token_info['market_cap']:,.0f}"
                            if token_info["market_cap"]
                            else "N/A"
                        )
                        liq_formatted = (
                            f"${token_info['liquidity']:,.0f}"
                            if token_info["liquidity"]
                            else "N/A"
                        )
                        vol_5m_formatted = (
                            f"${token_info['volume_5m']:,.0f}"
                            if token_info["volume_5m"]
                            else "N/A"
                        )

                        alert_msg = (
                            f"☀️ <b>SOLANA ALPHA DETECTED (GMGN)!</b>\n\n"
                            f"👤 <b>Account:</b> @{username}\n"
                            f"🪙 <b>Token:</b> {token_info['name']} (${token_info['symbol']})\n"
                            f"⚡ <b>5m Volume:</b> {vol_5m_formatted}\n"
                            f"📊 <b>Market Cap:</b> {mc_formatted}\n"
                            f"💧 <b>Liquidity:</b> {liq_formatted} (نسبت: {token_info['liq_ratio']}%)\n"
                            f"⏳ <b>Age:</b> {token_info['age_days']} روز\n\n"
                            f"🔑 <b>Solana CA:</b>\n<code>{ca}</code>\n\n"
                            f"{security_info}\n\n"
                            f"🐸 <a href='https://gmgn.ai/sol/token/{ca}'>GMGN Chart</a> | "
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
