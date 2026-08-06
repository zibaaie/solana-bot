import asyncio
import os
import re
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


def fetch_tweets_pub(username):
    url = f"https://s.jina.ai/https://x.com/{username}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            text = resp.text
            # استخراج تمام آدرس‌های سولانا از متن صفحه
            sol_addresses = extract_solana_address(text)
            if sol_addresses:
                # ایجاد یک ID شناور بر اساس متن و آدرس برای جلوگیری از ارسال تکراری
                fake_id = hash(f"{username}_{sol_addresses[0]}")
                return [(str(fake_id), text, sol_addresses[0])]
    except Exception as e:
        print(f"Error scanning @{username}: {e}")
    return []


async def main():
    print("🚀 Deep Web-Scraper Online...")

    while True:
        for username in SOLANA_WATCHLIST:
            try:
                results = fetch_tweets_pub(username)

                for tweet_id, raw_text, ca in results:
                    if tweet_id in seen_tweet_ids:
                        continue

                    seen_tweet_ids.add(tweet_id)
                    security_info = check_token_security(ca)

                    # جداسازی بخش کوتاه مربوط به توییت
                    clean_snippet = raw_text[:300].replace("\n", " ")

                    alert_msg = (
                        f"☀️ <b>SOLANA ALPHA DETECTED!</b>\n\n"
                        f"👤 <b>Account:</b> @{username}\n"
                        f"📝 <b>Snippet:</b> {clean_snippet}...\n\n"
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
        await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(main())
