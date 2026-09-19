import requests
import os
import time

def get_new_solana_tokens():
    """مرحله ۱: دریافت توکن‌های تازه‌لیست‌شده سولانا"""
    url = "https://api.dexscreener.com/token-profiles/latest/v1"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    data = response.json()
    
    # فیلتر فقط توکن‌های سولانا
    solana_tokens = [item for item in data if item.get("chainId") == "solana"]
    return solana_tokens

def get_token_details(token_address):
    """مرحله ۲: دریافت داده‌های عمیق برای هر توکن"""
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    try:
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            return None
        data = response.json()
        
        # اگر جفتی برای این توکن وجود داشته باشد
        if "pairs" in data and data["pairs"]:
            # بهترین جفت را بر اساس لیکوییدیتی انتخاب کن
            best_pair = max(data["pairs"], key=lambda p: p.get("liquidity", {}).get("usd", 0) or 0)
            return {
                "symbol": best_pair.get("baseToken", {}).get("symbol", "?"),
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
    """مرحله ۳: اعمال فیلترهای سختگیرانه برای شکار جهش"""
    if not token_data:
        return False
    
    # فیلترهای پیشنهادی برای شکار جهش ۱۰۰۰٪:
    # - لیکوییدیتی بین ۱۰ هزار تا ۱ میلیون دلار (توکن‌های کوچک)
    # - حجم ۲۴ ساعته بالای ۵۰ هزار دلار (فعالیت واقعی)
    # - سن کمتر از ۷۲ ساعت (توکن‌های تازه)
    # - تغییر قیمت ۲۴ ساعته مثبت (روند صعودی)
    
    if not (10000 < token_data["liquidity"] < 1000000):
        return False
    if token_data["volume_24h"] < 50000:
        return False
    if token_data["age_hours"] > 72:
        return False
    if token_data["price_change_24h"] < 0:
        return False
    
    return True

def main():
    summary = []
    summary.append("# 🎯 DEX Hunter - Phase 2")
    summary.append("")
    summary.append("## 📊 خلاصه اجرا")
    summary.append("")
    
    try:
        # مرحله ۱: دریافت توکن‌های جدید سولانا
        print("🔄 دریافت توکن‌های جدید سولانا...")
        new_tokens = get_new_solana_tokens()
        summary.append(f"- **توکن‌های جدید سولانا:** `{len(new_tokens)}`")
        summary.append("")
        
        # مرحله ۲: دریافت داده‌های عمیق
        print(f"🔍 دریافت داده‌های عمیق برای {len(new_tokens)} توکن...")
        all_data = []
        for token in new_tokens[:15]:  # فقط ۱۵ توکن اول برای رعایت محدودیت API
            address = token.get("tokenAddress")
            if address:
                details = get_token_details(address)
                if details:
                    all_data.append(details)
            time.sleep(0.5)  # تاخیر برای رعایت محدودیت
        
        summary.append(f"- **توکن‌های با داده کامل:** `{len(all_data)}`")
        summary.append("")
        
        # مرحله ۳: اعمال فیلترها
        print("🎯 اعمال فیلترها...")
        filtered = [t for t in all_data if apply_filters(t)]
        summary.append(f"- **توکن‌های پس از فیلتر:** `{len(filtered)}`")
        summary.append("")
        
        # نمایش نتایج
        if filtered:
            summary.append("## 🚀 توکن‌های کاندید")
            summary.append("")
            summary.append("| نماد | قیمت | لیکوییدیتی | حجم ۲۴س | تغییر ۲۴س | سن |")
            summary.append("|------|------|------------|---------|-----------|-----|")
            for t in filtered[:10]:
                summary.append(f"| {t['symbol']} | ${t['price']} | ${t['liquidity']:,.0f} | ${t['volume_24h']:,.0f} | {t['price_change_24h']:.1f}% | {t['age_hours']:.1f}h |")
        else:
            summary.append("## ⚠️ هیچ توکنی فیلترها را رد نکرد")
            summary.append("")
            summary.append("این طبیعی است چون فیلترها سختگیرانه هستند.")
            summary.append("در اجراهای بعدی ممکن است توکن‌های بهتری پیدا شوند.")
        
        summary.append("")
        summary.append("---")
        summary.append("*سلب مسئولیت: این یک ابزار تحلیلی است و سیگنال خرید نیست.*")
        
    except Exception as e:
        summary.append("## ❌ خطا")
        summary.append(f"```\n{type(e).__name__}: {e}\n```")
    
    # نمایش در خلاصه ورک‌فلو
    summary_text = "\n".join(summary)
    print(summary_text)
    
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write(summary_text)

if __name__ == '__main__':
    main()
