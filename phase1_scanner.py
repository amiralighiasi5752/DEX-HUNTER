import requests
import os
import time
import json
from datetime import datetime

# ================= تنظیمات =================
MIN_LIQUIDITY = 15000
MAX_LIQUIDITY = 5000000
MIN_VOLUME_24H = 20000
MAX_AGE_HOURS = 168
MAX_TOP_HOLDER_PERCENT = 25
MAX_TOKENS_TO_CHECK = 30

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
        r = requests.get(url, timeout=15)
        if r.status_code != 200:
            return None
        data = r.json()
        if "pairs" in data and data["pairs"]:
            best = max(data["pairs"], key=lambda p: p.get("liquidity", {}).get("usd", 0) or 0)
            return {
                "symbol": best.get("baseToken", {}).get("symbol", "?"),
                "address": token_address,
                "price": best.get("priceUsd", "0"),
                "liquidity": best.get("liquidity", {}).get("usd", 0) or 0,
                "volume_24h": best.get("volume", {}).get("h24", 0) or 0,
                "price_change_24h": best.get("priceChange", {}).get("h24", 0) or 0,
                "age_hours": (time.time() * 1000 - (best.get("pairCreatedAt", time.time() * 1000))) / 3600000,
                "url": best.get("url", "N/A")
            }
    except Exception:
        return None
    return None

def check_token_security(token_address):
    """
    بررسی امنیت توکن.
    بازگشتی: dict با کلیدهای safe، reason و status
    status: "safe" | "dangerous" | "unknown"
    """
    try:
        url = f"https://api.gopluslabs.io/api/v1/solana/token_security?contract_addresses={token_address}"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return {"safe": True, "reason": "API Error - Passed", "status": "unknown"}
        
        data = r.json()
        result = data.get("result", {}).get(token_address, {})
        
        # اگر داده‌ای برنگشت، توکن تازه است - با اخطار قبول کن
        if not result:
            return {"safe": True, "reason": "No Data - New Token", "status": "unknown"}
        
        # بررسی فاکتورهای خطرناک واقعی
        risks = []
        if result.get("mintable") == "1":
            risks.append("Mintable")
        if result.get("freezable") == "1":
            risks.append("Freezable")
        
        top_holder_pct = float(result.get("top_holder_percent", 0) or 0) * 100
        if top_holder_pct > MAX_TOP_HOLDER_PERCENT:
            risks.append(f"Top {top_holder_pct:.1f}%")
        
        lp_locked = float(result.get("lp_locked_percent", 0) or 0)
        if lp_locked < 50 and lp_locked > 0:
            risks.append(f"LP {lp_locked:.0f}%")
        
        # اگر ریسک واقعی وجود دارد، رد کن
        if risks:
            return {"safe": False, "reason": ", ".join(risks), "status": "dangerous"}
        
        return {"safe": True, "reason": "OK", "status": "safe"}
    except Exception as e:
        return {"safe": True, "reason": f"Error - Passed", "status": "unknown"}

def calculate_advanced_score(t):
    score = 0
    details = []
    if t["liquidity"] > 0:
        ratio = t["volume_24h"] / t["liquidity"]
        if ratio >= 10:
            score += 30; details.append(f"V/L {ratio:.1f}x (30)")
        elif ratio >= 5:
            score += 22; details.append(f"V/L {ratio:.1f}x (22)")
        elif ratio >= 3:
            score += 15; details.append(f"V/L {ratio:.1f}x (15)")
        elif ratio >= 1:
            score += 8; details.append(f"V/L {ratio:.1f}x (8)")
    age = t["age_hours"]
    if age < 6:
        score += 25; details.append(f"Age {age:.1f}h (25)")
    elif age < 12:
        score += 20; details.append(f"Age {age:.1f}h (20)")
    elif age < 24:
        score += 15; details.append(f"Age {age:.1f}h (15)")
    elif age < 48:
        score += 8; details.append(f"Age {age:.1f}h (8)")
    else:
        score += 3; details.append(f"Age {age:.1f}h (3)")
    liq = t["liquidity"]
    if liq < 30000:
        score += 20; details.append(f"Liq ${liq:,.0f} (20)")
    elif liq < 60000:
        score += 15; details.append(f"Liq ${liq:,.0f} (15)")
    elif liq < 150000:
        score += 10; details.append(f"Liq ${liq:,.0f} (10)")
    elif liq < 500000:
        score += 5; details.append(f"Liq ${liq:,.0f} (5)")
    change = t["price_change_24h"]
    if change >= 200:
        score += 15; details.append(f"Chg {change:.0f}% (15)")
    elif change >= 100:
        score += 12; details.append(f"Chg {change:.0f}% (12)")
    elif change >= 50:
        score += 8; details.append(f"Chg {change:.0f}% (8)")
    elif change >= 20:
        score += 5; details.append(f"Chg {change:.0f}% (5)")
    elif change >= 0:
        score += 2; details.append(f"Chg {change:.0f}% (2)")
    vol = t["volume_24h"]
    if vol >= 500000:
        score += 10; details.append(f"Vol ${vol:,.0f} (10)")
    elif vol >= 200000:
        score += 7; details.append(f"Vol ${vol:,.0f} (7)")
    elif vol >= 100000:
        score += 4; details.append(f"Vol ${vol:,.0f} (4)")
    else:
        score += 2; details.append(f"Vol ${vol:,.0f} (2)")
    return score, " | ".join(details)

def apply_filters(t):
    if not t:
        return False
    if not (MIN_LIQUIDITY < t["liquidity"] < MAX_LIQUIDITY):
        return False
    if t["volume_24h"] < MIN_VOLUME_24H:
        return False
    if t["age_hours"] > MAX_AGE_HOURS:
        return False
    if t["price_change_24h"] < 0:
        return False
    return True

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
    summary.append("# 🎯 DEX Hunter - Phase 7")
    summary.append("")
    summary.append(f"**زمان اجرا:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    summary.append("")
    telegram = ["🎯 *DEX Hunter - گزارش جدید*", ""]
    try:
        history = load_history()
        known_addresses = {i["address"] for i in history}
        summary.append(f"- **تاریخچه قبلی:** `{len(history)}` توکن")
        print("دریافت توکن‌های جدید...")
        new_tokens = get_new_solana_tokens()
        summary.append(f"- **توکن‌های جدید سولانا:** `{len(new_tokens)}`")
        all_data = []
        rejected_dangerous = 0
        rejected_filters = 0
        passed_unknown = 0
        for token in new_tokens[:MAX_TOKENS_TO_CHECK]:
            addr = token.get("tokenAddress")
            if not addr:
                continue
            d = get_token_details(addr)
            if not d:
                continue
            security = check_token_security(addr)
            if not security["safe"]:
                rejected_dangerous += 1
                print(f"  ❌ {d['symbol']} خطرناک: {security['reason']}")
                continue
            if security["status"] == "unknown":
                passed_unknown += 1
            if not apply_filters(d):
                rejected_filters += 1
                continue
            d["score"], d["score_details"] = calculate_advanced_score(d)
            d["security_status"] = security["status"]
            d["security_reason"] = security["reason"]
            all_data.append(d)
            time.sleep(0.3)
        summary.append(f"- **رد شده (خطرناک):** `{rejected_dangerous}`")
        summary.append(f"- **قبول شده با اخطار (داده ناکافی):** `{passed_unknown}`")
        summary.append(f"- **رد شده (فیلتر بازار):** `{rejected_filters}`")
        summary.append(f"- **نهایی:** `{len(all_data)}`")
        summary.append("")
        truly_new = [t for t in all_data if t["address"] not in known_addresses]
        truly_new.sort(key=lambda x: x["score"], reverse=True)
        if truly_new:
            summary.append("## 🏆 توکن‌های جدید")
            summary.append("")
            summary.append("| رتبه | نماد | امتیاز | وضعیت امنیت | قیمت | لیکوییدیتی | حجم ۲۴س | تغییر ۲۴س | سن | لینک |")
            summary.append("|------|------|--------|-------------|------|------------|---------|-----------|-----|------|")
            for i, t in enumerate(truly_new[:10], 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}"
                sec_icon = "✅" if t["security_status"] == "safe" else "⚠️"
                summary.append(f"| {medal} | **{t['symbol']}** | **{t['score']}/100** | {sec_icon} {t['security_status']} | ${t['price']} | ${t['liquidity']:,.0f} | ${t['volume_24h']:,.0f} | {t['price_change_24h']:.1f}% | {t['age_hours']:.1f}h | [نمودار]({t['url']}) |")
            telegram.append(f"🚀 *{len(truly_new)} توکن جدید:*")
            telegram.append("")
            for i, t in enumerate(truly_new[:5], 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                sec_icon = "✅" if t["security_status"] == "safe" else "⚠️"
                telegram.append(f"{medal} *{t['symbol']}* — *{t['score']}/100* {sec_icon}")
                telegram.append(f"  💰 `${t['price']}` | 💧 `${t['liquidity']:,.0f}`")
                telegram.append(f"  📈 +{t['price_change_24h']:.0f}% | 📅 {t['age_hours']:.1f}h")
                telegram.append(f"  🔗 [نمودار]({t['url']})")
                telegram.append("")
        else:
            summary.append("## ⚠️ هیچ توکنی عبور نکرد")
            telegram.append("😴 *توکن جدیدی کشف نشد.*")
        print("پیگیری عملکرد توکن‌های قدیمی...")
        performance = []
        updated_history = []
        for old in history:
            addr = old["address"]
            current = get_token_details(addr)
            time.sleep(0.3)
            if not current:
                old["last_status"] = "unavailable"
                updated_history.append(old)
                performance.append({
                    "symbol": old["symbol"], "growth": 0,
                    "max_growth": old.get("max_growth", 0),
                    "max_price": old.get("max_price", "?"),
                    "current_price": "N/A",
                    "initial_price": old.get("initial_price", "?"),
                    "age_days": (datetime.utcnow() - datetime.fromisoformat(old["discovered_at"])).days,
                    "status": "unavailable",
                    "url": old.get("url", "N/A")
                })
                continue
            initial_price = safe_float(old.get("initial_price", 0))
            current_price = safe_float(current["price"])
            current_growth = ((current_price - initial_price) / initial_price) * 100 if initial_price > 0 else 0
            previous_max_price = safe_float(old.get("max_price", initial_price))
            previous_max_growth = safe_float(old.get("max_growth", 0))
            if current_price > previous_max_price:
                new_max_price = current_price
                new_max_growth = ((new_max_price - initial_price) / initial_price) * 100 if initial_price > 0 else 0
            else:
                new_max_price = previous_max_price
                new_max_growth = previous_max_growth
            if "max_price" not in old:
                old["max_price"] = current_price
                new_max_price = current_price
                new_max_growth = current_growth
            old["last_price"] = current["price"]
            old["last_growth"] = current_growth
            old["max_price"] = str(new_max_price)
            old["max_growth"] = new_max_growth
            old["last_seen"] = datetime.utcnow().isoformat()
            old["last_status"] = "active"
            performance.append({
                "symbol": old["symbol"], "growth": current_growth,
                "max_growth": new_max_growth, "max_price": str(new_max_price),
                "current_price": current["price"],
                "initial_price": old.get("initial_price", "?"),
                "age_days": (datetime.utcnow() - datetime.fromisoformat(old["discovered_at"])).days,
                "status": "active",
                "url": old.get("url", current["url"])
            })
            updated_history.append(old)
        performance.sort(key=lambda x: x["growth"], reverse=True)
        if performance:
            summary.append("")
            summary.append("## 📊 عملکرد توکن‌های قبلی")
            summary.append("")
            summary.append("| نماد | رشد فعلی | حداکثر رشد | قیمت اولیه | حداکثر قیمت | قیمت فعلی | روز | لینک |")
            summary.append("|------|-----------|------------|------------|-------------|-----------|-----|------|")
            for p in performance:
                if p["status"] == "unavailable":
                    summary.append(f"| ⚫ {p['symbol']} | نامشخص | {p['max_growth']:+.1f}% | ${p['initial_price']} | ${p['max_price']} | N/A | {p['age_days']} | [نمودار]({p['url']}) |")
                else:
                    emoji = "🟢" if p["growth"] > 0 else "🔴"
                    summary.append(f"| {emoji} {p['symbol']} | {p['growth']:+.1f}% | {p['max_growth']:+.1f}% | ${p['initial_price']} | ${p['max_price']} | ${p['current_price']} | {p['age_days']} | [نمودار]({p['url']}) |")
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
        summary.append("")
        summary.append(f"📊 **تاریخچه:** `{len(updated_history)}` توکن")
        send_telegram("\n".join(telegram))
    except Exception as e:
        summary.append("## ❌ خطا")
        summary.append(f"```\n{type(e).__name__}: {e}\n```")
        send_telegram(f"❌ *خطا:* `{type(e).__name__}: {e}`")
    txt = "\n".join(summary)
    print(txt)
    sf = os.environ.get("GITHUB_STEP_SUMMARY")
    if sf:
        with open(sf, "w", encoding="utf-8") as f:
            f.write(txt)

if __name__ == '__main__':
    main()
