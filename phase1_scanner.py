import requests
import pandas as pd

def fetch_dexscreener_new_tokens(chain="solana"):
    """دریافت جدیدترین توکن‌های تازه‌لیست‌شده در DEXScreener"""
    url = "https://api.dexscreener.com/token-profiles/latest/v1"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def main():
    print("=" * 60)
    print("🔄 در حال دریافت توکن‌های جدید از DEXScreener...")
    print("=" * 60)
    
    try:
        data = fetch_dexscreener_new_tokens(chain="solana")
        
        print(f"\n✅ تعداد کل توکن‌های جدید: {len(data)}\n")
        
        # نمایش مستقیم در لاگ (بدون فایل)
        print("-" * 60)
        print("📊 لیست توکن‌های تازه‌لیست‌شده:")
        print("-" * 60)
        
        for i, item in enumerate(data[:20], 1):  # ۲۰ توکن اول
            chain = item.get("chainId", "?")
            address = item.get("tokenAddress", "?")
            url = item.get("url", "?")
            print(f"\n{i}. شبکه: {chain}")
            print(f"   آدرس: {address}")
            print(f"   لینک: {url}")
        
        print("\n" + "=" * 60)
        print(f"✅ نمایش ۲۰ توکن اول از {len(data)} توکن موجود.")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ خطا: {e}")
        raise

if __name__ == '__main__':
    main()
