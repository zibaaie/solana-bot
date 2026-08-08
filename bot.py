import asyncio
import os
import re
import time
import requests

# ----------------- تنظیمات -----------------
TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN", "8913236446:AAG-Fx4BX86rf84OkYG3ikotS5kE4tJKbRY"
)
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "95150036")

# ----------------- فیلترها -----------------
MIN_5M_VOLUME = 0           # برای تست روی 0 گذاشته شد
MIN_MARKET_CAP = 0
MIN_LIQUIDITY = 0
MIN_24H_VOLUME = 0
MIN_LIQUIDITY_RATIO = 0
MAX_AGE_DAYS = 365

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


def evaluate_dex_pair(pair, mint_address):
    created_at = pair.get("pairCreatedAt", 0) / 1000.0
    age_days = (time.time() - created_at) / 86400.0 if created_at > 0 else 0

    name = pair.get("baseToken", {}).get("name", "Unknown")
    symbol = pair.get("baseToken", {}).get("symbol", "UNKNOWN")
    market_cap = pair.get("fdv", pair.get("marketCap", 0)) or 0
    liquidity = pair.get("liquidity", {}).get("usd", 0) or 0
    volume_5m = pair.get("volume", {}).get("m5", 0) or 0
    volume_24h = pair.get("volume", {}).get("h24", 0) or 0

    liq_ratio = (liquidity / market_cap) if market_cap > 0 else 0

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


def get_token_info_by_ca(mint_address):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{mint_address}"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            pairs = data.get("pairs")
            if pairs:
                sol_pairs = [p for p in pairs if p.get("chainId") == "solana"]
                if sol_pairs:
                    return evaluate_dex_pair(sol_pairs[0], mint_address)
    except Exception as e:
        print(f"DexScreener CA Error: {e}")
    return None


def get_token_info_by_ticker(ticker):
    url = f"https://api.dexscreener.com/latest/dex/search?q={ticker}"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            pairs = data.get("pairs", [])
            sol_pairs = [
                p for p in pairs 
                if p.get("chainId") == "solana" and 
                p.get("baseToken", {}).get("symbol", "").upper() == ticker.upper()
            ]
            if sol_pairs:
                sol_pairs.sort(key=lambda x: x.get("liquidity", {}).get("usd", 0), reverse=True)
                target_ca = sol_pairs[0].get("baseToken", {}).get("address")
                if target_ca:
                    return evaluate_dex_pair(sol_pairs[0], target_ca)
    except Exception as e:
        print(f"DexScreener Ticker Error: {e}")
    return None


def fetch_latest_tweet_fixupx(username):
    """دریافت مستقیم آخرین توئیت از سرویس FixupX/VxTwitter"""
    url = f"https://api.vxtwitter.com/{username}"
    headers = {"User-Agent": "TelegramBot (like TwitterBot)"}

    try:
        resp = requests.get(url, headers=headers, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            tweet_id = data.get("tweet_id") or data.get("id")
            text = data.get("text", "")

            if text:
                cas = extract_solana_address(text)
                tickers = extract_tickers(text)
                if cas or tickers:
                    return [(f"{username}_{tweet_id}_{hash(text)}", text, cas, tickers)]
    except Exception as e:
        print(f"FixupX Error for @{username}: {e}")
    return []


async def main():
    print("🚀 Solana Alpha Scanner (FixupX Direct Engine) Online...")
    send_telegram_alert(
        "⚡ <b>FixupX Real-Time Engine Active!</b>\nپایش لحظه‌ای پست‌های جدید فعال شد."
    )

    while True:
        for username in SOLANA_WATCHLIST:
            try:
                results = fetch_latest_tweet_fixupx(username)

                for tweet_id, raw_text, cas, tickers in results:
                    if not tweet_id or tweet_id in seen_tweet_ids:
                        continue

                    print(f"🎯 MATCH FOUND! @{username} -> CA: {cas}, Ticker: {tickers}")
                    token_info = None

                    if cas:
                        token_info = get_token_info_by_ca(cas[0])
                    elif tickers:
                        ignored = ["SOL", "USDC", "USDT", "BTC", "ETH"]
                        filtered_tickers = [
                            t for t in tickers if t.upper() not in ignored
                        ]
                        if filtered_tickers:
                            token_info = get_token_info_by_ticker(filtered_tickers[0])

                    if token_info:
                        seen_tweet_ids.add(tweet_id)
                        ca = token_info["ca"]

                        mc_formatted = f"${token_info['market_cap']:,.0f}" if token_info["market_cap"] else "N/A"
                        liq_formatted = f"${token_info['liquidity']:,.0f}" if token_info["liquidity"] else "N/A"

                        alert_msg = (
                            f"☀️ <b>SOLANA ALPHA DETECTED!</b>\n\n"
                            f"👤 <b>Account:</b> @{username}\n"
                            f"🪙 <b>Token:</b> {token_info['name']} (${token_info['symbol']})\n"
                            f"📊 <b>Market Cap:</b> {mc_formatted}\n"
                            f"💧 <b>Liquidity:</b> {liq_formatted}\n"
                            f"⏳ <b>Age:</b> {token_info['age_days']} روز\n\n"
                            f"🔑 <b>Solana CA:</b>\n<code>{ca}</code>\n\n"
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
