import asyncio
import os
import re
import time
from collections import defaultdict
import requests

# ----------------- تنظیمات متغیرهای محیطی -----------------
TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN", "8913236446:AAG-Fx4BX86rf84OkYG3ikotS5kE4tJKbRY"
)
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "95150036")

# ----------------- فیلترهای مالی و تکنیکال -----------------
MIN_5M_VOLUME = 0          # بدون فیلتر حجم ۵ دقیقه
MIN_MARKET_CAP = 100       # حداقل مارکت‌کپ ۱۰۰ دلار
MIN_LIQUIDITY = 100        # حداقل نقدینگی ۱۰۰ دلار
MIN_24H_VOLUME = 100       # حداقل حجم ۲۴ ساعته ۱۰۰ دلار
MIN_LIQUIDITY_RATIO = 0.01 # حداقل نسبت ۱٪
# تنظیمات Confluence (هم‌زمانی سیگنال‌ها)
CONFLUENCE_WINDOW_SECONDS = 1800  # بازه زمانی ۳۰ دقیقه
MAX_AGE_DAYS = 90  # حداکثر سن توکن (روز)
# ----------------- لیست اکانت‌ها با مشخصات انگلیسی -----------------
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
    "sierasfx": "sierasfx - Personal Tracking Account"
}

seen_tweet_ids = set()
token_mentions = defaultdict(list)


async def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    # تلاش مجدد ۳ باره غیربلاک‌کننده با تایم‌اوت ۱۵ ثانیه
    for attempt in range(3):
        try:
            resp = requests.post(url, json=payload, timeout=15)
            if resp.status_code == 200:
                break
        except Exception as e:
            if attempt == 2:
                print(f"Error sending Telegram alert after 3 attempts: {e}")
            await asyncio.sleep(2)


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


def evaluate_pair(pair, mint_address):
    created_at = pair.get("pairCreatedAt", 0) / 1000.0
    age_days = (time.time() - created_at) / 86400.0 if created_at > 0 else 0

    name = pair.get("baseToken", {}).get("name", "Unknown")
    symbol = pair.get("baseToken", {}).get("symbol", "UNKNOWN")
    market_cap = pair.get("fdv", pair.get("marketCap", 0)) or 0
    liquidity = pair.get("liquidity", {}).get("usd", 0) or 0
    volume_5m = pair.get("volume", {}).get("m5", 0) or 0
    volume_24h = pair.get("volume", {}).get("h24", 0) or 0

    liq_ratio = (liquidity / market_cap) if market_cap > 0 else 0

    # تعریف مستقیم برای جلوگیری از خطای متغیر تعریف‌نشده
    max_age = globals().get("MAX_AGE_DAYS", 90)

    is_valid = (
        volume_5m >= MIN_5M_VOLUME
        and age_days <= max_age
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
    
    liq_ratio = (liquidity / market_cap) if market_cap > 0 else 0
    
    # ارزیابی بر اساس اولویت حجم ۵ دقیقه و مابقی فیلترها
    is_valid = (
        volume_5m >= MIN_5M_VOLUME and
        age_days <= MAX_AGE_DAYS and
        market_cap >= MIN_MARKET_CAP and
        liquidity >= MIN_LIQUIDITY and
        volume_24h >= MIN_24H_VOLUME and
        liq_ratio >= MIN_LIQUIDITY_RATIO
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
        "valid": is_valid
    }


def get_dex_info_by_ca(mint_address):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{mint_address}"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            pairs = data.get("pairs")
            if pairs:
                sol_pairs = [p for p in pairs if p.get("chainId") == "solana"]
                if sol_pairs:
                    return evaluate_pair(sol_pairs[0], mint_address)
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
            sol_pairs = [
                p for p in pairs 
                if p.get("chainId") == "solana" and 
                p.get("baseToken", {}).get("symbol", "").upper() == ticker.upper()
            ]
            if sol_pairs:
                sol_pairs.sort(key=lambda x: x.get("liquidity", {}).get("usd", 0), reverse=True)
                mint_address = sol_pairs[0].get("baseToken", {}).get("address")
                return evaluate_pair(sol_pairs[0], mint_address)
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


def check_confluence(ca, username):
    now = time.time()
    token_mentions[ca] = [
        m for m in token_mentions[ca] if now - m[1] <= CONFLUENCE_WINDOW_SECONDS
    ]
    token_mentions[ca].append((username, now))
    unique_callers = list(set(m[0] for m in token_mentions[ca]))
    return len(unique_callers), unique_callers


async def main():
    print("🚀 Solana Priority 5m Volume Bot Started...")

    while True:
        try:
            for username, user_desc in SOLANA_WATCHLIST.items():
                try:
                    results = fetch_tweets_fast_rss(username)

                    for tweet_id, raw_text, cas, tickers in results:
                        if not tweet_id or tweet_id in seen_tweet_ids:
                            continue

                        token_info = None

                        if cas:
                            token_info = get_dex_info_by_ca(cas[0])
                        elif tickers:
                            ignored = ["SOL", "USDC", "USDT", "BTC", "ETH"]
                            filtered_tickers = [t for t in tickers if t.upper() not in ignored]
                            if filtered_tickers:
                                token_info = get_dex_info_by_ticker(filtered_tickers[0])

                        if token_info:
                            if not token_info["valid"]:
                                continue

                            seen_tweet_ids.add(tweet_id)
                            ca = token_info["ca"]
                            
                            caller_count, callers_list = check_confluence(ca, username)
                            security_info = check_token_security(ca)
                            
                            mc_formatted = f"${token_info['market_cap']:,.0f}" if token_info['market_cap'] else "N/A"
                            liq_formatted = f"${token_info['liquidity']:,.0f}" if token_info['liquidity'] else "N/A"
                            vol_5m_formatted = f"${token_info['volume_5m']:,.0f}" if token_info['volume_5m'] else "N/A"
                            vol_24h_formatted = f"${token_info['volume_24h']:,.0f}" if token_info['volume_24h'] else "N/A"

                            if caller_count > 1:
                                header = f"🔥 <b>HOT CONFLUENCE DETECTED! ({caller_count} Callers)</b>"
                                callers_str = ", ".join([f"@{c}" for c in callers_list])
                            else:
                                header = "☀️ <b>SOLANA ALPHA DETECTED!</b>"
                                callers_str = f"@{username} ({user_desc})"

                            alert_msg = (
                                f"{header}\n\n"
                                f"👥 <b>Callers:</b> {callers_str}\n"
                                f"🪙 <b>Token:</b> {token_info['name']} (${token_info['symbol']})\n"
                                f"⚡ <b>5m Volume:</b> {vol_5m_formatted}\n"
                                f"📊 <b>Market Cap:</b> {mc_formatted}\n"
                                f"💧 <b>Liquidity:</b> {liq_formatted} (نسبت: {token_info['liq_ratio']}%)\n"
                                f"📈 <b>24h Volume:</b> {vol_24h_formatted}\n"
                                f"⏳ <b>Age:</b> {token_info['age_days']} روز\n\n"
                                f"🔑 <b>Solana CA:</b>\n<code>{ca}</code>\n\n"
                                f"{security_info}\n\n"
                                f"🦅 <a href='https://dexscreener.com/solana/{ca}'>DexScreener</a> | "
                                f"🧪 <a href='https://photon-sol.tinyastro.io/en/lp/{ca}'>Photon</a>\n"
                                f"🔗 <a href='https://x.com/{username}'>مشاهده اکانت</a>"
                            )
                            await send_telegram_alert(alert_msg)

                except Exception as e:
                    print(f"Error checking @{username}: {e}")

                await asyncio.sleep(1.5)
        except Exception as global_e:
            print(f"Global Loop Error: {global_e}")
        
        await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(main())
