import asyncio
import os
import re
import requests
import xml.etree.ElementTree as ET

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

# سرورهای عمومی RSS/Nitter جهت پشتیبان‌گیری
NITTER_INSTANCES = [
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
    "https://nitter.lucabased.xyz",
]


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
    solana_pattern = (
        r"\b[1-9A-HJ-NP-Za-km-z]{32,44}pump\b|\b[1-9A-HJ-NP-Za-km-z]{43,44}\b"
    )
    return re.findall(solana_pattern, text)


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
            risk_details = [f"• {r.get('name')}" for r in risks[:3]]
            risk_text = "\n".join(risk_details) if risk_details else "• پاک"

            return (
                f"🛡️ <b>RugCheck Analysis:</b>\n"
                f"Score: {score} | Verdict: {risk_label}\n"
                f"<b>Risks:</b>\n{risk_text}\n"
            )
        return "🛡️ <b>RugCheck:</b> در حال بروزرسانی..."
    except Exception:
        return "🛡️ <b>RugCheck:</b> خطا در استعلام API"


def fetch_tweets_rss(username):
    for instance in NITTER_INSTANCES:
        url = f"{instance}/{username}/rss"
        try:
            resp = requests.get(url, timeout=7)
            if resp.status_code == 200:
                root = ET.fromstring(resp.content)
                tweets = []
                for item in root.findall("./channel/item"):
                    guid = item.find("guid").text if item.find("guid") is not None else ""
                    title = item.find("title").text if item.find("title") is not None else ""
                    tweets.append((guid, title))
                return tweets
        except Exception:
            continue
    return []


async def main():
    print("🚀 Fast RSS/Nitter Solana Scanner Online...")

    while True:
        for username in SOLANA_WATCHLIST:
            try:
                tweets = fetch_tweets_rss(username)

                for tweet_id, tweet_text in tweets[:3]:
                    if not tweet_id or tweet_id in seen_tweet_ids:
                        continue

                    seen_tweet_ids.add(tweet_id)
                    sol_contracts = extract_solana_address(tweet_text)

                    if sol_contracts:
                        ca = sol_contracts[0]
                        security_info = check_token_security(ca)

                        alert_msg = (
                            f"☀️ <b>SOLANA ALPHA DETECTED!</b>\n\n"
                            f"👤 <b>Account:</b> @{username}\n"
                            f"📝 <b>Tweet:</b> {tweet_text}\n\n"
                            f"🔑 <b>Solana CA:</b>\n<code>{ca}</code>\n\n"
                            f"{security_info}\n"
                            f"🦅 <a href='https://dexscreener.com/solana/{ca}'>DexScreener</a> | "
                            f"🧪 <a href='https://photon-sol.tinyastro.io/en/lp/{ca}'>Photon</a>\n\n"
                            f"🔗 <a href='https://x.com/{username}'>مشاهده اکانت</a>"
                        )
                        send_telegram_alert(alert_msg)

            except Exception as e:
                print(f"Skip @{username}: {e}")

            await asyncio.sleep(2)
        await asyncio.sleep(15)


if __name__ == "__main__":
    asyncio.run(main())
