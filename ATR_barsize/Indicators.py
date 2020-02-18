#
# Python Script with indicators 
# calculations
#
# (c) Andres Estrada Cadavid
# QSociety

import pandas as pd
import numpy as np

class Indicators():
    def SMA(self, data, period):
        sma = data.rolling(period).mean()
        return sma
    
    def EMA(self, data, period):
        ema = data.ewm(span=period, min_periods=period, adjust=False).mean()
        return ema

    def MACD(self, data, slow_period=26, fast_period=12, signal_period=9, type='macd'):
        macd = self.EMA(data=data, period=fast_period) - self.EMA(data=data, period=slow_period)
        signal = self.EMA(data=macd, period=signal_period)
        if type == 'macd':
            indicator = macd
        elif type == 'signal':
            indicator = signal
        elif type == 'histogram':
            indicator = macd - signal
        return indicator
    
    def RSI(self, data, period=14):
        deltas = data.diff()
        seed = deltas[:period+1]
        up = seed[seed>=0].sum()/period
        down = -seed[seed<0].sum()/period
        rs = up/down
        rsi = np.zeros(len(deltas))
        rsi[period] = 100 - 100/(rs+1)

        for i in range(period+1,len(deltas)):
            delta = deltas[i]
            if delta >= 0:
                upval = delta; downval = 0
            else:
                upval = 0; downval = abs(delta)
            up = (up*(period-1) + upval)/period
            down = (down*(period-1) + downval)/period
            rs = up/down
            rsi[i] = 100 - (100/(rs+1))
        return rsi
    
    def ATR(self, data, period=14):
        atr = pd.concat([(data.high - data.low), abs(data.close.shift(1)-data.high), abs(data.close.shift(1)-data.low)],axis=1) \
                                .max(axis=1).dropna().rolling(period).mean()
        return atr
    
    def BB(self, data, period=20, multiplier=2, type='midline'):
        std = data.rolling(period).std()
        midline = data.rolling(period).mean()
        if type == 'midline':
            indicator = midline
        elif type == 'upper':
            indicator = midline + multiplier*std
        elif type == 'lower':
            indicator = midline - multiplier*std
        return indicator
    
    def update_indicators(self, old_series, new_series):
        return pd.concat([old_series.iloc[:-2], new_series.loc[old_series.index[-2]:]])