#
# Python Script with live trading 
# Range Strategy Class
#
# (c) Andres Estrada Cadavid
# QSociety

from Live_Class import Live
import pandas as pd

from datetime import timedelta
from ib_insync import util, Future, Stock, Forex

class LiveRange(Live):
    def run_strategy(self, initial_hour, final_hour, ticks_range, trades_per_day, minutes, target):
        cancelled = False
        
        while self.weekday < 5: #and pd.to_datetime(self.hour) < pd.to_datetime(final_hour)  
            self.ib.sleep(1)
            self.current_date()
            hour_range = pd.to_datetime(str(self.date)+' '+initial_hour) + timedelta(minutes = minutes)
            lots = 1

            if pd.to_datetime(self.hour) >= hour_range:
                if pd.to_datetime(self.hour) == pd.to_datetime(hour_range):
                    cancelled = False
                    #=====Range Calculation=====
                    range_limit_hour = pd.to_datetime(str(self.date)+' '+initial_hour) + timedelta(minutes = minutes-1)
                    hist = util.df(self.data).set_index('date')
                    bars_range = hist.loc[str(self.date)+' '+initial_hour:str(range_limit_hour)]
                    maximum = round(bars_range['high'].max(),self.digits)
                    minimum = round(bars_range['low'].min(),self.digits)
                    range_size = maximum - minimum
                    #=====Calculate stop and target prices=====
                    price_buy_in = maximum + (ticks_range*self.tick_size)
                    sl_buy = (lambda target,size: price_buy_in - target if target < size else minimum)(target,range_size)
                    tp_buy = price_buy_in + target
                    price_sell_in = minimum - (ticks_range*self.tick_size)
                    sl_sell = (lambda target,size: price_sell_in + target if target < size else maximum)(target,range_size)
                    tp_sell = price_sell_in - target
                    #=====Send bracket orders=====
                    ord_buy, ord_buy_tp, ord_buy_sl = self.bracket_stop_order('BUY', lots, price_buy_in, sl_buy, tp_buy)
                    ord_sell, ord_sell_tp, ord_sell_sl = self.bracket_stop_order('SELL', lots, price_sell_in, sl_sell, tp_sell)
                    print('=====Stop Orders sent succesfully!=====')
                
                #=====Cancel contrary order=====
                if not cancelled:
                    if self.pending_check(ord_buy):
                        self.ib.cancelOrder(ord_sell)
                        cancelled = True
                    if self.pending_check(ord_sell):
                        self.ib.cancelOrder(ord_buy)
                        cancelled = True
                
                #=====Cancel orders in case of not fill=====
                if not cancelled and pd.to_datetime(self.hour) == pd.to_datetime(final_hour):
                    self.ib.cancelOrder(ord_buy)
                    self.ib.cancelOrder(ord_sell)
                    print('=====Orders Cancelled. Not filled!=====')
                
                #=====Close by target or stop=====
                ##=====Buys=====
                if self.position > 0:
                    self.pending_check(ord_buy_sl)
                    self.pending_check(ord_buy_tp)
                    if pd.to_datetime(self.hour) == pd.to_datetime(final_hour):
                        self.ib.cancelOrder(ord_buy_sl)
                        self.order_send('SELL', lots)
                        print('=====Exit by time! Market SELL sent!=====')
                ##=====Sells=====
                if self.position < 0:
                    self.pending_check(ord_sell_sl)
                    self.pending_check(ord_sell_tp)
                    if pd.to_datetime(self.hour) == pd.to_datetime(final_hour):
                        self.ib.cancelOrder(ord_sell_sl)
                        self.order_send('BUY',lots)
                        print('=====Exit by time! Market BUY sent!=====')
        self.ib.disconnect()

if __name__ == '__main__':
    #=====inputs=====
    symbol = input('\tsymbol: ')
    client = int(input('\tclient: '))
    minutes = int(input('\tminutes: '))
    target = float(input('\ttarget: '))
    
    live_range = LiveRange(symbol=symbol, temp='1 min', client=client, verbose=True, notification=False)
    live_range.run_strategy(initial_hour='09:30:00', final_hour='15:45:00', ticks_range=1, trades_per_day=1, minutes=minutes, target=target)

    '''symbol = 'ES'
    live_range = LiveRange(symbol=symbol, temp='1 min', client=101, verbose=True, notification=False)
    live_range.run_strategy(initial_hour='16:15:00', final_hour='18:17:00', ticks_range=1, trades_per_day=1, minutes=1, target=1.0)'''