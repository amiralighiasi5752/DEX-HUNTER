import requests
import os
import time
import json
from datetime import datetime

def get_new_solana_tokens():
    """دریافت توکن‌های تازه‌لیست‌شده سولانا"""
    url = "https://api.dexscreener.com/token-profiles/latest/v1"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    data = response.json()
    return [item for item in data if item.get("chainId") == "solana"]

def get_token_details(token_address):
    """دریافت داده‌های عمیق برای هر توکن"""
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    try:
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            return None
        data = response.json()
        if "pairs" in data and data["pairs"]:
            best_pair = max(data["pairs"], key=lambda p: p.get("liquidity", {}).get("usd", 0) or 0)
            return {
                "symbol": best_pair.get("baseToken", {}).get("symbol", "?"),
                "address": token_address,
                "price": best_pair.get("priceUsd", "N/A"),
                "liquidity": best_pair.get("liquidity", {}).get("usd", 0) or 0,
                "volume_24h": best_pair.get("volume", {}).get("h24", 0) or 0,
                "price_change_24h": best_pair.get("priceChange", {}).get("h24", 0) or 0,
                "age_hours": (time.time() * 1000 - (best_pair.get("pairCreatedAt", time.time() * 1000))) / 3600000,
                "url": best_pair.get("url", "N/A")
            }
    except Exception:
        return None
    return None

def apply_filters(token_data):
    """اعمال فیلترهای سختگیرانه"""
    if not token_data:
        return False
    if not (10000 < token_data["liquidity"] < 1000000):
        return False
    if token_data["volume_24h"] < 50000:
        return False
    if token_data["age_hours"] > 72:
        return False
    if token_data["price_change_24h"] < 0:
        return False
    return True

def load_history():
    """بارگذاری تاریخچه از فایل"""
    if os.path.exists("history.json"):
        try:
            with open("history.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history(history):
    """ذخیره تاریخچه در فایل"""
    with open("history.json", "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def main():
    summary = []
    summary.append("# 🎯 DEX Hunter - Phase 2")
    summary.append("")
    summary.append(f"**زمان اجرا:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    summary.append("")
    
    try:
        history = load_history()
        known_addresses = {item["address"] for item in history}
        summary.append(f"- **تاریخچه قبلی:** `{len(history)}` توکن")
        summary.append("")
        
        print("دریافت توکن‌های جدید سولانا...")
        new_tokens = get_new_solana_tokens()
        summary.append(f"- **توکن‌های جدید سولانا:** `{len(new_tokens)}`")
        
        print("دریافت داده‌های عمیق...")
        all_data = []
        for token in new_tokens[:15]:
            address = token.get("tokenAddress")
            if address:
                details = get_token_details(address)
                if details:
                    all_data.append(details)
            time.sleep(0.5)
        
        filtered = [t for t in all_data if apply_filters(t)]
        summary.append(f"- **توکن‌های پس از فیلتر:** `{len(filtered)}`")
        summary.append("")
        
        truly_new = [t for t in filtered if t["address"] not in known_addresses]
        summary.append(f"- **توکن‌های کاملاً جدید:** `{len(truly_new)}`")
        summary.append("")
        
        if truly_new:
            summary.append("## 🚀 توکن‌های جدید کشف‌شده")
            summary.append("")
            summary.append("| نماد | قیمت | لیکوییدیتی | حجم ۲۴س | تغییر ۲۴س | سن |")
            summary.append("|------|------|------------|---------|-----------|-----|")
            for t in truly_new[:10]:
                summary.append(f"| {t['symbol']} | ${t['price']} | ${t['liquidity']:,.0f} | ${t['volume_24h']:,.0f} | {t['price_change_24h']:.1f}% | {t['age_hours']:.1f}h |")
        
        if filtered:
            summary.append("")
            summary.append("## 📜 تاریخچه (توکن‌های فعال)")
            summary.append("")
            summary.append("| نماد | قیمت | تغییر ۲۴س | سن |")
            summary.append("|------|------|-----------|-----|")
            for t in filtered[:5]:
                marker = "🆕" if t["address"] not in known_addresses else "📌"
                summary.append(f"| {marker} {t['symbol']} | ${t['price']} | {t['price_change_24h']:.1f}% | {t['age_hours']:.1f}h |")
        
        for t in filtered:
            if t["address"] not in known_addresses:
                t["discovered_at"] = datetime.utcnow().isoformat()
                t["initial_price"] = t["price"]
                history.append(t)
        
        history = history[-100:]
        save_history(history)
        
        summary.append("")
        summary.append(f"📊 **تاریخچه به‌روزرسانی شد:** `{len(history)}` توکن")
        summary.append("")
        summary.append("---")
        summary.append("*سلب مسئولیت: این ابزار تحلیلی است و سیگنال خرید نیست.*")
        
    except Exception as e:
        summary.append("## ❌ خطا")
        summary.append(f"```\n{type(e).__name__}: {e}\n```")
    
    summary_text = "\n".join(summary)
    print(summary_text)
    
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write(summary_text)

if __name__ == '__main__':
    main()
