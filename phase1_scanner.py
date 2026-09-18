import requests
import json

def fetch_hyperliquid_meta():
    """دریافت لیست تمام مارکت‌های Hyperliquid"""
    url = "https://api.hyperliquid.xyz/info"
    payload = {"type": "meta"}
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()

def fetch_all_mids():
    """دریافت آخرین قیمت تمام مارکت‌ها"""
    url = "https://api.hyperliquid.xyz/info"
    payload = {"type": "allMids"}
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()

if __name__ == '__main__':
    # تست اتصال
    print("🔄 در حال اتصال به Hyperliquid...")
    meta = fetch_hyperliquid_meta()
    mids = fetch_all_mids()
    
    universe = meta.get("universe", [])
    print(f"✅ اتصال برقرار شد!")
    print(f"تعداد مارکت‌های موجود در Hyperliquid: {len(universe)}")
    print(f"تعداد قیمت‌های دریافت شده: {len(mids)}")
    
    # نمایش ۵ مارکت اول به عنوان نمونه
    print("\n📊 نمونه مارکت‌ها:")
    for asset in universe[:5]:
        name = asset.get("name", "?")
        price = mids.get(name, "N/A")
        print(f"  - {name}: ${price}")
    
    # ذخیره لیست کامل در فایل
    with open("markets.txt", "w", encoding="utf-8") as f:
        f.write(f"تعداد مارکت‌ها: {len(universe)}\n\n")
        for asset in universe:
            name = asset.get("name", "?")
            price = mids.get(name, "N/A")
            f.write(f"{name}: {price}\n")
    
    print("\n✅ لیست کامل در markets.txt ذخیره شد.")
