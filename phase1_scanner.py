import requests
import os
import time
import json
from datetime import datetime

def send_telegram(message):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("⚠️ TELEGRAM تنظیم نشده.")
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
    except Exception as e:
        print(f"❌ خطا: {e}")
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

def safe_float(v):
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0

def calculate_score(t):
    """محاسبه امتیاز ۰ تا ۱۰۰ برای هر توکن"""
    score = 0
    details = []
    
    # === ۱. نسبت حجم به لیکوییدیتی (۳۰ امتیاز) ===
    if t["liquidity"] > 0:
        ratio = t["volume_24h"] / t["liquidity"]
        if ratio >= 10:
            score += 30
            details.append(f"حجم/لیک {ratio:.1f}x (۳۰)")
        elif ratio >= 5:
            score += 22
            details.append(f"حجم/لیک {ratio:.1f}x (۲۲)")
        elif ratio >= 3:
            score += 15
            details.append(f"حجم/لیک {ratio:.1f}x (۱۵)")
        elif ratio >= 1:
            score += 8
            details.append(f"حجم/لیک {ratio:.1f}x (۸)")
    
    # === ۲. سن توکن (۲۵ امتیاز) ===
    age = t["age_hours"]
    if age < 6:
        score += 25
        details.append(f"سن {age:.1f}h (۲۵)")
    elif age < 12:
        score += 20
        details.append(f"سن {age:.1f}h (۲۰)")
    elif age < 24:
        score += 15
        details.append(f"سن {age:.1f}h (۱۵)")
    elif age < 48:
        score += 8
        details.append(f"سن {age:.1f}h (۸)")
    else:
        score += 3
        details.append(f"سن {age:.1f}h (۳)")
    
    # === ۳. لیکوییدیتی پایین (۲۰ امتیاز) ===
    liq = t["liquidity"]
    if liq < 30000:
        score += 20
        details.append(f"لیک ${liq:,.0f} (۲۰)")
    elif liq < 60000:
        score += 15
        details.append(f"لیک ${liq:,.0f} (۱۵)")
    elif liq < 150000:
        score += 10
        details.append(f"لیک ${liq:,.0f} (۱۰)")
    elif liq < 500000:
        score += 5
        details.append(f"لیک ${liq:,.0f} (۵)")
    
    # === ۴. تغییر قیمت ۲۴ ساعته (۱۵ امتیاز) ===
    change = t["price_change_24h"]
    if change >= 200:
        score += 15
        details.append(f"تغییر {change:.0f}% (۱۵)")
    elif change >= 100:
        score += 12
        details.append(f"تغییر {change:.0f}% (۱۲)")
    elif change >= 50:
        score += 8
        details.append(f"تغییر {change:.0f}% (۸)")
    elif change >= 20:
        score += 5
        details.append(f"تغییر {change:.0f}% (۵)")
    elif change >= 0:
        score += 2
        details.append(f"تغییر {change:.0f}% (۲)")
    
    # === ۵. حجم ۲۴ ساعته (۱۰ امتیاز) ===
    vol = t["volume_24h"]
    if vol >= 500000:
        score += 10
        details.append(f"حجم ${vol:,.0f} (۱۰)")
    elif vol >= 200000:
        score += 7
        details.append(f"حجم ${vol:,.0f} (۷)")
    elif vol >= 100000:
        score += 4
        details.append(f"حجم ${vol:,.0f} (۴)")
    else:
        score += 2
        details.append(f"حجم ${vol:,.0f} (۲)")
    
    return score, " | ".join(details)

def apply_filters(t):
    if not t:
        return False
    if not (10000 < t["liquidity"] < 1000000):
        return False
    if t["volume_24h"] < 50000:
        return False
    if t["age_hours"] > 72:
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

def main():
    summary = []
    summary.append("# 🎯 DEX Hunter - Phase 5")
    summary.append("")
    summary.append(f"**زمان اجرا:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    summary.append("")
    
    telegram = ["🎯 *DEX Hunter - گزارش جدید*", ""]
    
    try:
        history = load_history()
        known_addresses = {i["address"] for i in history}
        summary.append(f"- **تاریخچه قبلی:** `{len(history)}` توکن")
        summary.append("")
        
        # === کشف توکن‌های جدید ===
        print("دریافت توکن‌های جدید...")
        new_tokens = get_new_solana_tokens()
        summary.append(f"- **توکن‌های جدید سولانا:** `{len(new_tokens)}`")
        
        all_data = []
        for token in new_tokens[:15]:
            addr = token.get("tokenAddress")
            if addr:
                d = get_token_details(addr)
                if d:
                    d["score"], d["score_details"] = calculate_score(d)
                    all_data.append(d)
            time.sleep(0.5)
        
        filtered = [t for t in all_data if apply_filters(t)]
        summary.append(f"- **توکن‌های جدید پس از فیلتر:** `{len(filtered)}`")
        summary.append("")
        
        truly_new = [t for t in filtered if t["address"] not in known_addresses]
        truly_new.sort(key=lambda x: x["score"], reverse=True)
        
        if truly_new:
            summary.append("## 🏆 توکن‌های جدید (مرتب بر اساس امتیاز)")
            summary.append("")
            summary.append("| رتبه | نماد | امتیاز | قیمت | لیکوییدیتی | حجم ۲۴س | تغییر ۲۴س | سن | لینک |")
            summary.append("|------|------|--------|------|------------|---------|-----------|-----|------|")
            for i, t in enumerate(truly_new[:10], 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}"
                summary.append(f"| {medal} | **{t['symbol']}** | **{t['score']}/100** | ${t['price']} | ${t['liquidity']:,.0f} | ${t['volume_24h']:,.0f} | {t['price_change_24h']:.1f}% | {t['age_hours']:.1f}h | [نمودار]({t['url']}) |")
            
            # جزئیات امتیاز توکن برتر
            if truly_new:
                top = truly_new[0]
                summary.append("")
                summary.append(f"### 🔍 جزئیات امتیاز توکن برتر: **{top['symbol']}**")
                summary.append("")
                summary.append(f"- **امتیاز کل:** `{top['score']}/100`")
                summary.append(f"- **جزئیات:** {top['score_details']}")
                summary.append(f"- **لینک:** [مشاهده نمودار]({top['url']})")
            
            telegram.append(f"🚀 *{len(truly_new)} توکن جدید کشف شد:*")
            telegram.append("")
            for i, t in enumerate(truly_new[:5], 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                telegram.append(f"{medal} *{t['symbol']}* — امتیاز *{t['score']}/100*")
                telegram.append(f"  💰 `${t['price']}` | 💧 `${t['liquidity']:,.0f}`")
                telegram.append(f"  📈 +{t['price_change_24h']:.0f}% | 📅 {t['age_hours']:.1f}h")
                telegram.append(f"  🔗 [نمودار]({t['url']})")
                telegram.append("")
        
        # === پیگیری عملکرد توکن‌های قبلی ===
        print("پیگیری عملکرد توکن‌های قدیمی...")
        performance = []
        updated_history = []
        
        for old in history:
            addr = old["address"]
            current = get_token_details(addr)
            time.sleep(0.4)
            
            if not current:
                old["last_status"] = "unavailable"
                updated_history.append(old)
                performance.append({
                    "symbol": old["symbol"],
                    "growth": 0,
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
            
            if initial_price > 0:
                current_growth = ((current_price - initial_price) / initial_price) * 100
            else:
                current_growth = 0
            
            previous_max_price = safe_float(old.get("max_price", initial_price))
            previous_max_growth = safe_float(old.get("max_growth", 0))
            
            if current_price > previous_max_price:
                new_max_price = current_price
                if initial_price > 0:
                    new_max_growth = ((new_max_price - initial_price) / initial_price) * 100
                else:
                    new_max_growth = 0
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
                "symbol": old["symbol"],
                "growth": current_growth,
                "max_growth": new_max_growth,
                "max_price": str(new_max_price),
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
        
        # === به‌روزرسانی تاریخچه ===
        for t in filtered:
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
        summary.append("")
        summary.append("---")
        summary.append("*امتیاز بر اساس ۵ معیار: حجم/لیک، سن، لیکوییدیتی، تغییر ۲۴س، حجم*")
        
        if not truly_new:
            telegram.append("😴 *توکن جدیدی کشف نشد.*")
        
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
