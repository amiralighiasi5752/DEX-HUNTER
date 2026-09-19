import requests
import os
import time
import json
from datetime import datetime

# ================= تنظیمات =================
MIN_LIQUIDITY = 8000
MAX_LIQUIDITY = 3000000
MIN_VOLUME_24H = 10000
MAX_AGE_HOURS = 1
MAX_TOKENS_TO_CHECK = 30
MAX_GROWTH_AT_DISCOVERY = 150

def send_telegram(message):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        r = requests.post(url, json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }, timeout=15)
        return r.status_code == 200
    except Exception:
        return False

def get_new_solana_tokens():
    url = "https://api.dexscreener.com/token-profiles/latest/v1"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return [i for i in r.json() if i.get("chainId") == "solana"]

def get_token_details(token_address):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        if "pairs" in data and data["pairs"]:
            best = max(data["pairs"], key=lambda p: p.get("liquidity", {}).get("usd", 0) or 0)
            txns = best.get("txns", {}).get("h24", {})
            buys = txns.get("buys", 0) or 0
            sells = txns.get("sells", 0) or 0
            buy_sell_ratio = buys / sells if sells > 0 else (buys if buys > 0 else 0)
            return {
                "symbol": best.get("baseToken", {}).get("symbol", "?"),
                "address": token_address,
                "price": best.get("priceUsd", "0"),
                "liquidity": best.get("liquidity", {}).get("usd", 0) or 0,
                "volume_24h": best.get("volume", {}).get("h24", 0) or 0,
                "price_change_24h": best.get("priceChange", {}).get("h24", 0) or 0,
                "age_hours": (time.time() * 1000 - (best.get("pairCreatedAt", time.time() * 1000))) / 3600000,
                "url": best.get("url", "N/A"),
                "buys": buys,
                "sells": sells,
                "buy_sell_ratio": buy_sell_ratio
            }
    except Exception:
        return None
    return None

def apply_early_filters(t):
    """فیلترهای شکار زودهنگام"""
    if not t:
        return False
    if not (MIN_LIQUIDITY < t["liquidity"] < MAX_LIQUIDITY):
        return False
    if t["volume_24h"] < MIN_VOLUME_24H:
        return False
    # فقط توکن‌های تازه متولد شده
    if t["age_hours"] > MAX_AGE_HOURS:
        return False
    # فقط توکن‌هایی که هنوز رشد نکرده‌اند
    if t["price_change_24h"] > MAX_GROWTH_AT_DISCOVERY:
        return False
    if t["price_change_24h"] < 0:
        return False
    # نسبت خرید به فروش باید حداقل ۱ باشد
    if t["buy_sell_ratio"] < 1:
        return False
    return True

def calculate_score(t):
    score = 0
    if t["liquidity"] > 0:
        ratio = t["volume_24h"] / t["liquidity"]
        if ratio >= 5: score += 30
        elif ratio >= 3: score += 20
        elif ratio >= 1: score += 10
    age = t["age_hours"]
    if age < 0.5: score += 30
    elif age < 1: score += 20
    elif age < 2: score += 10
    if t["buy_sell_ratio"] >= 5: score += 25
    elif t["buy_sell_ratio"] >= 3: score += 20
    elif t["buy_sell_ratio"] >= 1.5: score += 15
    change = t["price_change_24h"]
    if 20 <= change <= 100: score += 15
    elif 0 < change < 20: score += 10
    return score

def load_history():
    if os.path.exists("history.json"):
        try:
            with open("history.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history(h):
    with open("history.json", "w", encoding="utf-8") as f:
        json.dump(h, f, ensure_ascii=False, indent=2)

def safe_float(v):
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0

def main():
    summary = []
    summary.append("# 🎯 DEX Hunter - Early Sniper")
    summary.append("")
    summary.append(f"**زمان اجرا:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    summary.append("")
    telegram = ["🎯 *DEX Hunter - گزارش جدید*", ""]
    try:
        history = load_history()
        known_addresses = {i["address"] for i in history}
        print("دریافت توکن‌های جدید...")
        new_tokens = get_new_solana_tokens()
        summary.append(f"- **توکن‌های جدید:** `{len(new_tokens)}`")
        all_data = []
        for token in new_tokens[:MAX_TOKENS_TO_CHECK]:
            addr = token.get("tokenAddress")
            if not addr:
                continue
            d = get_token_details(addr)
            if not d:
                continue
            if not apply_early_filters(d):
                continue
            d["score"] = calculate_score(d)
            all_data.append(d)
            time.sleep(0.2)
        summary.append(f"- **توکن‌های واجد شرایط:** `{len(all_data)}`")
        truly_new = [t for t in all_data if t["address"] not in known_addresses]
        truly_new.sort(key=lambda x: x["score"], reverse=True)
        if truly_new:
            summary.append("## 🏆 توکن‌های جدید (شکار زودهنگام)")
            summary.append("")
            summary.append("| رتبه | نماد | امتیاز | قیمت | لیکوییدیتی | Buy/Sell | تغییر ۲۴س | سن | لینک |")
            summary.append("|------|------|--------|------|------------|----------|-----------|-----|------|")
            for i, t in enumerate(truly_new[:10], 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}"
                summary.append(f"| {medal} | **{t['symbol']}** | **{t['score']}/100** | ${t['price']} | ${t['liquidity']:,.0f} | {t['buy_sell_ratio']:.1f}x | {t['price_change_24h']:.1f}% | {t['age_hours']:.2f}h | [نمودار]({t['url']}) |")
            telegram.append(f"🚀 *{len(truly_new)} توکن زودهنگام:*")
            telegram.append("")
            for i, t in enumerate(truly_new[:5], 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                telegram.append(f"{medal} *{t['symbol']}* — *{t['score']}/100*")
                telegram.append(f"  💰 `${t['price']}` | 💧 `${t['liquidity']:,.0f}`")
                telegram.append(f"  📊 Buy/Sell: {t['buy_sell_ratio']:.1f}x | 📅 {t['age_hours']:.2f}h")
                telegram.append(f"  🔗 [نمودار]({t['url']})")
                telegram.append("")
        else:
            telegram.append("😴 *توکن واجد شرایطی یافت نشد.*")
        
        # پیگیری عملکرد
        performance = []
        updated_history = []
        for old in history:
            addr = old["address"]
            current = get_token_details(addr)
            time.sleep(0.2)
            if not current:
                old["last_status"] = "unavailable"
                updated_history.append(old)
                continue
            initial_price = safe_float(old.get("initial_price", 0))
            current_price = safe_float(current["price"])
            current_growth = ((current_price - initial_price) / initial_price) * 100 if initial_price > 0 else 0
            previous_max_price = safe_float(old.get("max_price", initial_price))
            if current_price > previous_max_price:
                new_max_price = current_price
                new_max_growth = ((new_max_price - initial_price) / initial_price) * 100 if initial_price > 0 else 0
            else:
                new_max_price = previous_max_price
                new_max_growth = safe_float(old.get("max_growth", 0))
            old["last_price"] = current["price"]
            old["last_growth"] = current_growth
            old["max_price"] = str(new_max_price)
            old["max_growth"] = new_max_growth
            old["last_seen"] = datetime.utcnow().isoformat()
            old["last_status"] = "active"
            performance.append({"symbol": old["symbol"], "growth": current_growth, "max_growth": new_max_growth, "current_price": current["price"], "initial_price": old.get("initial_price", "?"), "age_days": (datetime.utcnow() - datetime.fromisoformat(old["discovered_at"])).days, "url": old.get("url", current["url"])})
            updated_history.append(old)
        performance.sort(key=lambda x: x["growth"], reverse=True)
        if performance:
            summary.append("")
            summary.append(f"## 📜 لیست کامل ({len(performance)} توکن)")
            summary.append("")
            summary.append("| نماد | رشد فعلی | حداکثر رشد | قیمت اولیه | قیمت فعلی | لینک |")
            summary.append("|------|-----------|------------|------------|-----------|------|")
            for p in performance:
                emoji = "🟢" if p["growth"] > 0 else "🔴"
                summary.append(f"| {emoji} {p['symbol']} | {p['growth']:+.1f}% | {p['max_growth']:+.1f}% | ${p['initial_price']} | ${p['current_price']} | [نمودار]({p['url']}) |")
            winners = [p for p in performance if p["max_growth"] >= 100]
            mega = [p for p in performance if p["max_growth"] >= 1000]
            summary.append("")
            summary.append(f"📊 **آمار:** {len(winners)} برنده | {len(mega)} شکارچی ۱۰۰۰٪")
            telegram.append("")
            telegram.append(f"📊 *آمار:* {len(mega)} شکارچی ۱۰۰۰٪ از {len(performance)} توکن")
        for t in all_data:
            if t["address"] not in known_addresses:
                price_str = str(t["price"])
                t["discovered_at"] = datetime.utcnow().isoformat()
                t["initial_price"] = price_str
                t["max_price"] = price_str
                t["max_growth"] = 0
                t["last_status"] = "active"
                updated_history.append(t)
        updated_history = updated_history[-200:]
        save_history(updated_history)
        send_telegram("\n".join(telegram))
    except Exception as e:
        summary.append(f"## ❌ خطا\n```\n{type(e).__name__}: {e}\n```")
        send_telegram(f"❌ *خطا:* `{type(e).__name__}: {e}`")
    txt = "\n".join(summary)
    print(txt)
    sf = os.environ.get("GITHUB_STEP_SUMMARY")
    if sf:
        with open(sf, "w", encoding="utf-8") as f:
            f.write(txt)

if __name__ == '__main__':
    main()
