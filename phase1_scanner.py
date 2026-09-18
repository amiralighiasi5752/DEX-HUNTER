import asyncio
from geckoterminal_py import GeckoTerminalAsyncClient
import pandas as pd

async def scan_new_pools():
    """اسکن استخرهای تازه ایجاد شده در DEXها"""
    client = GeckoTerminalAsyncClient()
    
    try:
        # دریافت تمام استخرهای جدید در همه شبکه‌ها
        print("🔄 در حال دریافت استخرهای جدید از GeckoTerminal...")
        new_pools = await client.get_new_pools_all_networks()
        
        if new_pools is None or new_pools.empty:
            print("⚠️ هیچ استخر جدیدی یافت نشد.")
            return
        
        print(f"✅ {len(new_pools)} استخر جدید دریافت شد.")
        
        # فیلتر کردن بر اساس نقدینگی و حجم
        # ستون‌ها ممکن است بسته به API متفاوت باشند، اینجا فرض می‌کنیم:
        # reserve_in_usd = نقدینگی، volume_usd_h24 = حجم ۲۴ ساعته
        if 'reserve_in_usd' in new_pools.columns:
            filtered = new_pools[
                (new_pools['reserve_in_usd'] > 10000) &  # نقدینگی بالای ۱۰ هزار دلار
                (new_pools['reserve_in_usd'] < 50000000)  # نقدینگی زیر ۵۰ میلیون دلار
            ].copy()
        else:
            filtered = new_pools.copy()
        
        # مرتب‌سازی بر اساس حجم معاملات (اگر وجود داشته باشد)
        if 'volume_usd_h24' in filtered.columns:
            filtered = filtered.sort_values('volume_usd_h24', ascending=False)
        
        print(f"🎯 {len(filtered)} توکن پس از فیلتر باقی ماندند.")
        
        # ذخیره نتیجه
        output_file = "new_tokens.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"تعداد کل استخرهای جدید: {len(new_pools)}\n")
            f.write(f"تعداد پس از فیلتر: {len(filtered)}\n\n")
            f.write(filtered.to_string())
        
        print(f"\n✅ لیست در {output_file} ذخیره شد.")
        print("\n📊 ۵ توکن برتر بر اساس حجم:")
        print(filtered.head().to_string())
        
    finally:
        await client.close()

if __name__ == '__main__':
    asyncio.run(scan_new_pools())
