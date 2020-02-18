#
# Python Script with live trading 
# Range Strategy Class
#
# (c) Andres Estrada Cadavid
# QSociety

from Live_Class import Live
from Indicators import Indicators
import pandas as pd
from datetime import timedelta
from ib_insync import util, Future, Stock, Forex

class LiveRange(Live, Indicators):        
    def run_strategy(self, initial_hour, final_hour, ticks_range, minutes, target, max_range_size, min_atr_value=0):
        cancelled = False
        #===== Data in DataFrame and ATR initial calculation =====
        period_ATR = 14
        self.data_df = self.data_to_df(data=self.data)
        ATR = self.ATR(data=self.data_df, period=period_ATR)
        #===== Daily Data =====
        data_1h = self.download_data(tempo='1 hour', duration='20 D')
        data_1h_df = self.data_to_df(data=data_1h)
        data_1D_df = self.convert_data(data=data_1h_df, tempo='1D')
        #data_1D = self.download_data(tempo='1 day', duration='20 D')
        #data_1D_df = self.data_to_df(data=data_1D)
        ATR_1D = self.ATR(data=data_1D_df)
        
        while self.weekday < 5: #and pd.to_datetime(self.hour) < pd.to_datetime(final_hour)
            #===== Continuous DataFrame =====
            self.data_df = self.df_continuous(df=self.data_df)
            #===== Update indicators =====
            if self.second == 0:
                new_ATR = self.ATR(self.data_df.iloc[-(period_ATR+2):])
                ATR = self.update_indicators(old_series=ATR, new_series=new_ATR)
                #print('last ATR: %5.2f at %s' % (ATR[-2], ATR.index[-2]))

            self.ib.sleep(1)
            self.current_date()
            hour_range = pd.to_datetime(str(self.date)+' '+initial_hour) + timedelta(minutes = minutes)
            lots = 1
            
            if pd.to_datetime(self.hour) >= hour_range:
                if pd.to_datetime(self.hour) == pd.to_datetime(hour_range):
                    cancelled = False
                    #===== Range Calculation =====
                    range_limit_hour = pd.to_datetime(str(self.date)+' '+initial_hour) + timedelta(minutes = minutes-1)
                    hist = util.df(self.data).set_index('date')
                    bars_range = hist.loc[str(self.date)+' '+initial_hour:str(range_limit_hour)]
                    maximum = round(bars_range['high'].max(),self.digits)
                    minimum = round(bars_range['low'].min(),self.digits)
                    range_size = maximum - minimum
                    print('range size: %5.2f' % range_size)
                    #===== Calculate Stop and Target prices =====
                    price_buy_in = maximum + (ticks_range*self.tick_size)
                    sl_buy = minimum; tp_buy = price_buy_in + target
                    price_sell_in = minimum - (ticks_range*self.tick_size)
                    sl_sell = maximum; tp_sell = price_sell_in - target
                    #===== ATR restriction =====
                    days = (lambda day:3 if day==0 else 1)(self.weekday)
                    date_atr = pd.to_datetime(self.date) - timedelta(days=days)
                    daily_atr = ATR_1D.loc[date_atr]
                    print('Last Day ATR: %5.3f' % daily_atr)
                    #===== Send Bracket Orders =====
                    if range_size < max_range_size and daily_atr > min_atr_value:
                        ord_buy, ord_buy_tp, ord_buy_sl = self.bracket_stop_order('BUY', lots, price_buy_in, sl_buy, tp_buy)
                        ord_sell, ord_sell_tp, ord_sell_sl = self.bracket_stop_order('SELL', lots, price_sell_in, sl_sell, tp_sell)
                        print('===== Stop Orders sent succesfully! =====')
                    else:
                        print('===== No Conditions Fulfilled =====')
                
                if range_size < max_range_size and daily_atr > min_atr_value:
                    #===== Cancel contrary order =====
                    if not cancelled:
                        if self.pending_check(ord_buy):
                            self.ib.cancelOrder(ord_sell)
                            cancelled = True
                        if self.pending_check(ord_sell):
                            self.ib.cancelOrder(ord_buy)
                            cancelled = True
                    
                    #===== Cancel orders in case of not fill =====
                    if not cancelled and pd.to_datetime(self.hour) == pd.to_datetime(final_hour):
                        self.ib.cancelOrder(ord_buy)
                        self.ib.cancelOrder(ord_sell)
                        print('===== Orders Cancelled. Not filled! =====')
                    
                    #=====Close by target or stop=====
                    ##=====Buys=====
                    if self.position > 0:
                        self.pending_check(ord_buy_sl)
                        self.pending_check(ord_buy_tp)
                        if pd.to_datetime(self.hour) == pd.to_datetime(final_hour):
                            self.ib.cancelOrder(ord_buy_sl)
                            self.order_send('SELL', lots)
                            print('===== Exit by time! Market SELL sent! =====')
                    ##=====Sells=====
                    if self.position < 0:
                        self.pending_check(ord_sell_sl)
                        self.pending_check(ord_sell_tp)
                        if pd.to_datetime(self.hour) == pd.to_datetime(final_hour):
                            self.ib.cancelOrder(ord_sell_sl)
                            self.order_send('BUY',lots)
                            print('===== Exit by time! Market BUY sent! =====')
        self.ib.disconnect()

if __name__ == '__main__':
    #===== inputs =====
    symbol = input('\tsymbol: ')
    client = int(input('\tclient: '))
    minutes = int(input('\tminutes: '))
    target = float(input('\ttarget: '))
    atr_value = float(input('\tatr value: '))
    range_size = float(input('\trange size: '))
    
    live_range = LiveRange(symbol=symbol, temp='1 min', client=client, verbose=True, notification=False)
    live_range.run_strategy(initial_hour='12:23:00', final_hour='12:26:00', ticks_range=1, minutes=minutes, target=target,
                            max_range_size=range_size, min_atr_value=atr_value)
    
    '''live_range = LiveRange(symbol='ES', temp='1 min', client=50, verbose=True, notification=True)
    live_range.run_strategy(initial_hour='15:15:00', final_hour='20:27:00', ticks_range=1, minutes=1, target=1.5, max_range_size=5, 
                            min_atr_value=20)'''