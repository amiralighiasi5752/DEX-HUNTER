import ccxt
import pandas as pd
from backtesting import Backtest, Strategy

def fetch_data(symbol='BTC/USDT', timeframe='1d', limit=1000):
    exchange = ccxt.binance({'enableRateLimit': True})
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

class Breakout20(Strategy):
    lookback = 20
    def init(self):
        self.highest = self.I(lambda x: pd.Series(x).rolling(self.lookback).max().shift(1), self.data.High)
    def next(self):
        if len(self.data) < self.lookback + 1:
            return
        if self.data.Close[-1] > self.highest[-1] and not self.position:
            self.buy()
        if self.position and self.data.Close[-1] < self.data.Close[-self.lookback]:
            self.position.close()

if name == 'main':
    df = fetch_data('BTC/USDT', '1d', 2000)
    print(f"داده دریافت شد: {len(df)} کندل از {df.index[0]} تا {df.index[-1]}")
    bt = Backtest(df, Breakout20, cash=10000, commission=0.001)
    stats = bt.run()
    print(stats)
    # ذخیره نتیجه در فایل متنی
    with open('result.txt', 'w', encoding='utf-8') as f:
        f.write(str(stats))
    # ذخیره نمودار
    bt.plot(filename='result.html', open_browser=False)
