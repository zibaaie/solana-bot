import asyncio
import json
import os
import re
import requests
from twikit import Client

# ----------------- تنظیمات -----------------
TELEGRAM_BOT_TOKEN = os.getenv("8913236446:AAG-Fx4BX86rf84OkYG3ikotS5kE4tJKbRY")
TELEGRAM_CHAT_ID = os.getenv("95150036")

SOLANA_WATCHLIST = [
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


def load_cookies_safely(client, file_path="cookies.json"):
    if not os.path.exists(file_path):
        print(f"⚠️ {file_path} not found!")
        return False

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        cookie_dict = {}
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "name" in item and "value" in item:
                    cookie_dict[item["name"]] = item["value"]
        elif isinstance(data, dict):
            cookie_dict = data

        if cookie_dict:
            client.set_cookies(cookie_dict)
            print("✅ Logged in via cookies.json successfully!")
            return True
        else:
            print("⚠️ Invalid cookie structure in cookies.json")
            return False

    except Exception as e:
        print(f"⚠️ Error parsing cookies.json: {e}")
        return False


async def main():
    client = Client("en-US")
    load_cookies_safely(client, "cookies.json")

    print("🚀 Solana Alpha Scanner Online...")

    while True:
        for username in SOLANA_WATCHLIST:
            try:
                user = await client.get_user_by_screen_name(username)
                tweets = await user.get_tweets("Tweets", count=2)

                for tweet in tweets:
                    if tweet.id in seen_tweet_ids:
                        continue

                    seen_tweet_ids.add(tweet.id)
                    tweet_text = tweet.full_text
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
                            f"🔗 <a href='https://x.com/{username}/status/{tweet.id}'>مشاهده توییت</a>"
                        )
                        send_telegram_alert(alert_msg)

            except Exception as e:
                print(f"Error scanning @{username}: {e}")

            await asyncio.sleep(4)
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
