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

# ----------------- فیلترها (جهت دریافت همه سیگنال‌ها روی 0 تنظیم شده‌اند) -----------------
MIN_5M_VOLUME = 0            # حداقل حجم ۵ دقیقه
MIN_MARKET_CAP = 0           # حداقل مارکت‌کپ
MIN_LIQUIDITY = 0            # حداقل نقدینگی
MIN_24H_VOLUME = 0           # حداقل حجم ۲۴ ساعته
MIN_LIQUIDITY_RATIO = 0.0    # حداقل نسبت نقدینگی
MAX_AGE_DAYS = 365           # حداکثر سن توکن (روز)

SOLANA_WATCHLIST = {
    # Top Alpha Callers & Key Influencers
    "blkn0iz06": "Ansem - Top Meme Callers (Fartcoin, WIF, BOME)",
    "idrawfire": "Mitch - Senior Trader & Alpha Caller",
    "LarpVonTrier": "LarpVonTrier - Early Meme Alpha Finder",
    "Theunipcs": "Theunipcs - Bonk & WIF Whale Holder",
    "CrashiusClay69": "Crashius Clay - Top Solana Trader",
    "artsch00lreject": "Artschool Reject - Solana Alpha",
    "arrogantfrfr": "Arrogant - On-Chain Trader",
    "0xVonGogh": "VonGogh - Gem Finder & Low Cap Specialist",
    "MuroCrypto": "Muro - Price Action & Low Cap Analysis",

    # On-Chain & Smart Money Trackers
    "lookonchain": "Lookonchain - Whale Tracker & Smart Money",
    "bubblemaps": "Bubblemaps - Insider & Cluster Detection",
    "OnChainDataNerd": "Onchain Data Nerd - Smart Money Analytics",
    "SolanaFloor": "Solana Floor - Ecosystem News & Analytics",

    # High-Volume Meme Callers & Channels
    "Poe_Ether": "Poe - High-Volume Meme Caller",
    "thecexoffender": "CEX Offender - Solana Meme Caller",
    "Renzofks": "Renzo - Alpha Trader & Caller",
    "larpalt": "Larp Alt - Secondary Alpha Account",
    "iambroots": "Broots - Meme Coin Caller",
    "UniswapVillain": "Uniswap Villain - On-Chain Trader",
    "solana_daily": "Solana Daily - Daily Tokens & Ecosystem News",
    "SOLBigBrain": "SOL Big Brain - Solana Ecosystem Analyst",
    "MemeCoinCalls": "MemeCoin Calls - Meme Coin Signals",
    "SolMemeAlpha": "Sol Meme Alpha - Specialized Meme Alpha",
    "PumpFunCalls": "PumpFun Calls - Pump.fun Token Tracker",
    "SolanaGems": "Solana Gems - High Potential Gem Finder",
    "DegenerateNews": "Degen News - Degen Trends & News Coverage",
    "ZackXBT": "ZachXBT - Web3 Investigator & Scam Tracker",
    "RektFencer": "Rekt Fencer - Alpha Trader & Caller",
    "0xFastHand": "Fast Hand - Fast On-Chain Scalper",
    "CryptoWizardd": "Crypto Wizard - Market Analyst & Price Action",
    "SolanaWhaleAlert": "Solana Whale Alert - Large Transfer Alerts",
    "RaydiumProtocol": "Raydium Protocol - DEX Official Announcements",
    "PhotonSolana": "Photon Solana - Trading Platform Alerts",

    # Personal Accounts
    "SynthetixTrade": "Synthetix Trade - Personal Tracking Account",
    "sierasfx": "sierasfx - Personal Tracking Account",
}

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
        resp = requests.post(url, json=payload, timeout=5)
        print(f"Telegram response status: {resp.status_code}")
    except Exception as e:
        print(f"Error sending Telegram alert: {e}")


def extract_solana_address(text):
    if not text:
        return []
    solana_pattern = (
        r"\b[1-9A-HJ-NP-Za-km-z]{32,44}pump\b|\b[1-9A-HJ-NP-Za-km-z]{43,44}\b"
    )
    return re.findall(solana_pattern, str(text))


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

            return (
                f"🛡️ <b>RugCheck Analysis:</b>\n"
                f"Score: {score} | Verdict: {risk_label}\n"
                f"<b>Risks:</b>\n{risk_text}\n"
            )
        return "🛡️ <b>RugCheck:</b> در حال بروزرسانی..."
    except Exception:
        return "🛡️ <b>RugCheck:</b> خطا در استعلام API"


def get_token_data_and_evaluate(ca):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            pairs = data.get("pairs")
            if pairs:
                sol_pairs = [p for p in pairs if p.get("chainId") == "solana"]
                if sol_pairs:
                    pair = sol_pairs[0]
                    created_at = pair.get("pairCreatedAt", 0) / 1000.0
                    age_days = (
                        (time.time() - created_at) / 86400.0 if created_at > 0 else 0
                    )

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
                        "name": name,
                        "symbol": symbol,
                        "market_cap": market_cap,
                        "liquidity": liquidity,
                        "volume_5m": volume_5m,
                        "volume_24h": volume_24h,
                        "liq_ratio": round(liq_ratio * 100, 1),
                        "age_days": round(age_days, 1),
                        "valid": is_valid,
                        "found": True
                    }
    except Exception as e:
        print(f"Error fetching DexScreener data for {ca}: {e}")
    
    return {"valid": True, "found": False, "market_cap": 0, "liquidity": 0, "volume_5m": 0, "symbol": "NEW_TOKEN", "age_days": 0}


def fetch_tweets_fast_rss(username):
    instances = [
        "https://nitter.net",
        "https://nitter.poast.org",
        "https://nitter.privacydev.net",
        "https://nitter.space",
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    for instance in instances:
        try:
            url = f"{instance}/{username}/rss"
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                text = resp.text
                sol_addresses = extract_solana_address(text)
                if sol_addresses:
                    ca = sol_addresses[0]
                    tweet_id = f"{username}_{ca}"
                    return [(tweet_id, text, ca)]
        except Exception:
            continue

    try:
        backup_url = f"https://fixupx.com/{username}"
        resp = requests.get(backup_url, headers=headers, timeout=5)
        if resp.status_code == 200:
            text = resp.text
            sol_addresses = extract_solana_address(text)
            if sol_addresses:
                ca = sol_addresses[0]
                return [(f"{username}_{ca}", text, ca)]
    except Exception:
        pass

    return []


async def main():
    print("🚀 Instant Solana Scanner Engine Started...")
    send_telegram_alert(
        "⚡ <b>Instant Scanner Active!</b>\nسیستم فعال شد و تمام محدودیت‌ها جهت تست برداشته شدند."
    )

    while True:
        for username, info in SOLANA_WATCHLIST.items():
            try:
                results = fetch_tweets_fast_rss(username)

                for tweet_id, raw_text, ca in results:
                    if not tweet_id or tweet_id in seen_tweet_ids:
                        continue

                    token_info = get_token_data_and_evaluate(ca)

                    # ثبت آیدی توئیت
                    seen_tweet_ids.add(tweet_id)
                    security_info = check_token_security(ca)

                    mc_formatted = f"${token_info['market_cap']:,.0f}" if token_info["found"] else "N/A"
                    liq_formatted = f"${token_info['liquidity']:,.0f}" if token_info["found"] else "N/A"
                    vol5m_formatted = f"${token_info['volume_5m']:,.0f}" if token_info["found"] else "N/A"
                    symbol = token_info["symbol"]

                    alert_msg = (
                        f"☀️ <b>SOLANA ALPHA DETECTED!</b>\n\n"
                        f"👤 <b>Account:</b> @{username} ({info})\n"
                        f"🪙 <b>Token:</b> ${symbol}\n"
                        f"⚡ <b>5m Volume:</b> {vol5m_formatted}\n"
                        f"📊 <b>Market Cap:</b> {mc_formatted}\n"
                        f"💧 <b>Liquidity:</b> {liq_formatted}\n"
                        f"⏳ <b>Age:</b> {token_info['age_days']} روز\n\n"
                        f"🔑 <b>Solana CA:</b>\n<code>{ca}</code>\n\n"
                        f"{security_info}\n"
                        f"🐸 <a href='https://gmgn.ai/sol/token/{ca}'>GMGN Chart</a> | "
                        f"🦅 <a href='https://dexscreener.com/solana/{ca}'>DexScreener</a> | "
                        f"🧪 <a href='https://photon-sol.tinyastro.io/en/lp/{ca}'>Photon</a>\n\n"
                        f"🔗 <a href='https://x.com/{username}'>مشاهده اکانت</a>"
                    )
                    send_telegram_alert(alert_msg)

            except Exception as e:
                print(f"Error checking @{username}: {e}")

            await asyncio.sleep(1.5)
        await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(main())
