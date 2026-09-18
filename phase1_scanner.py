import asyncio
from laakhay.data import HyperliquidProvider, MarketType, Timeframe

async def fetch_data():
    # ایجاد پرووایدر برای Hyperliquid
    provider = HyperliquidProvider(market_type=MarketType.FUTURES)
    try:
        # دریافت کندل‌های BTC به عنوان تست
        candles = await provider.get_candles("BTC", Timeframe.H1, limit=100)
        print(f"✅ اتصال به Hyperliquid برقرار شد. تعداد کندل‌های دریافت شده: {len(candles)}")
        print(f"آخرین قیمت BTC: {candles[-1].close}")
    finally:
        await provider.close()

if __name__ == '__main__':
    asyncio.run(fetch_data())
