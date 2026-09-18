import requests
import pandas as pd
import json

def fetch_dexscreener_new_tokens(chain="solana"):
    """
    دریافت جدیدترین پروفایل توکن‌های تازه‌لیست‌شده در DEXScreener.
    از endpoint عمومی token-profiles استفاده می‌کند که به API Key نیاز ندارد [citation:5][citation:10].
    """
    url = "https://api.dexscreener.com/token-profiles/latest/v1"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    
    # استخراج توکن‌ها
    tokens = []
    for item in data:
        tokens.append({
            "chain": item.get("chainId", "?"),
            "token_address": item.get("tokenAddress", "?"),
            "url": item.get("url", "?")
        })
    
    return pd.DataFrame(tokens)

def filter_tokens_by_criteria(df, chain_filter="solana"):
    """
    فیلتر توکن‌ها بر اساس شبکه و معیارهای اولیه.
    """
    if df.empty:
        return df
    
    # فیلتر بر اساس شبکه
    if chain_filter:
        df = df[df["chain"] == chain_filter]
    
    return df

if __name__ == '__main__':
    print("🔄 در حال دریافت توکن‌های جدید از DEXScreener...")
    
    try:
        df = fetch_dexscreener_new_tokens(chain="solana")
        print(f"✅ {len(df)} توکن جدید دریافت شد.")
        
        # فیلتر بر اساس شبکه سولانا
        filtered = filter_tokens_by_criteria(df, chain_filter="solana")
        print(f"🎯 {len(filtered)} توکن پس از فیلتر شبکه سولانا.")
        
        # ذخیره نتیجه
        output_file = "new_tokens.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"تعداد کل توکن‌های جدید: {len(df)}\n")
            f.write(f"تعداد پس از فیلتر: {len(filtered)}\n\n")
            f.write(filtered.to_string())
        
        print(f"\n✅ لیست در {output_file} ذخیره شد.")
        print("\n📊 ۵ توکن اول:")
        print(filtered.head().to_string())
        
    except Exception as e:
        print(f"❌ خطا: {e}")
        raise
