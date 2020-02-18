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
    def x_round(self, x):
        mult = 1/self.tick_size
        return round(x*mult)/mult

    def trailing_stop(self, price_in, trailing, sl, order, type='traditional'):
        '''type = 'traditional' | 'staggered'
        '''
        new_sl = sl
        if trailing > 0:
            if self.position > 0:
                if type == 'traditional':
                    if self.data[-1].close - price_in >= trailing*self.tick_size:
                        if sl < self.data[-1].close - trailing*self.tick_size:
                            new_sl = round(self.data[-1].close - trailing*self.tick_size,self.digits)
                            order.auxPrice = new_sl
                            self.ib.placeOrder(self.contract,order)
                            print('=' * 55)
                            print('trailing stop from %5.5f to %5.5f'%(sl, new_sl))
                            print('=' * 55)
                else:
                    if self.data[-1].close - price_in >= trailing*self.tick_size and not self.first:
                        new_sl = round(price_in, self.digits)
                        order.auxPrice = new_sl
                        self.ib.placeOrder(self.contract,order)
                        self.first = True
                        print('=' * 55)
                        print('trailing stop from %5.5f to %5.5f'%(sl, new_sl))
                        print('=' * 55)
                    if self.data[-1].close - sl >= 2*trailing*self.tick_size and self.first:
                        new_sl = round(sl + trailing*self.tick_size,self.digits)
                        order.auxPrice = new_sl
                        self.ib.placeOrder(self.contract,order)
                        print('=' * 55)
                        print('trailing stop from %5.5f to %5.5f'%(sl, new_sl))
                        print('=' * 55)
            if self.position < 0:
                if type == 'traditional':
                    if price_in - self.data[-1].close >= trailing*self.tick_size:
                        if sl > self.data[-1].close + trailing*self.tick_size:
                            new_sl = round(self.data[-1].close + trailing*self.tick_size,self.digits)
                            order.auxPrice = new_sl
                            self.ib.placeOrder(self.contract,order)
                            print('=' * 55)
                            print('trailing stop from %5.5f to %5.5f'%(sl, new_sl))
                            print('=' * 55)
                else:
                    if price_in - self.data[-1].close >= trailing*self.tick_size and not self.first:
                        new_sl = round(price_in,self.digits)
                        order.auxPrice = new_sl
                        self.ib.placeOrder(self.contract,order)
                        self.first = True
                        print('=' * 55)
                        print('trailing stop from %5.5f to %5.5f'%(sl, new_sl))
                        print('=' * 55)
                    if sl - self.data[-1].close >= 2*trailing*self.tick_size and self.first:
                        new_sl = round(sl - trailing*self.tick_size,self.digits)
                        order.auxPrice = new_sl
                        self.ib.placeOrder(self.contract,order)
                        print('=' * 55)
                        print('trailing stop from %5.5f to %5.5f'%(sl, new_sl))
                        print('=' * 55)
        return self.x_round(new_sl)
    
    def run_strategy(self, initial_hour, final_hour, ticks_range, trades_per_day, minutes, target, trailing=0, trailing_type='traditional'):
        cancelled = False
        self.first = False
        trailing = self.x_round(trailing * target)
        
        while self.weekday < 5: #and pd.to_datetime(self.hour) < pd.to_datetime(final_hour)  
            self.ib.sleep(1)
            self.current_date()
            hour_range = pd.to_datetime(str(self.date)+' '+initial_hour) + timedelta(minutes = minutes)
            lots = 20000

            if pd.to_datetime(self.hour) >= hour_range:
                if pd.to_datetime(self.hour) == pd.to_datetime(hour_range):
                    cancelled = False
                    #=====Range Calculation=====
                    range_limit_hour = pd.to_datetime(str(self.date)+' '+initial_hour) + timedelta(minutes = minutes-1)
                    hist = util.df(self.data).set_index('date')
                    bars_range = hist.loc[str(self.date)+' '+initial_hour:str(range_limit_hour)]
                    maximum = round(bars_range['high'].max(),self.digits)
                    minimum = round(bars_range['low'].min(),self.digits)
                    #=====Calculate stop and target prices=====
                    price_buy_in = maximum + (ticks_range*self.tick_size)
                    sl_buy = minimum; tp_buy = price_buy_in + target
                    price_sell_in = minimum - (ticks_range*self.tick_size)
                    sl_sell = maximum; tp_sell = price_sell_in - target
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
                    self.trailing_stop(price_in=price_buy_in, trailing=trailing, sl=sl_buy, order=ord_buy_sl, type=trailing_type)
                    self.pending_check(ord_buy_sl)
                    self.pending_check(ord_buy_tp)
                    if pd.to_datetime(self.hour) == pd.to_datetime(final_hour):
                        self.ib.cancelOrder(ord_buy_sl)
                        self.order_send('SELL', lots)
                        print('=====Exit by time! Market SELL sent!=====')
                    if self.position == 0:
                        self.first = False
                ##=====Sells=====
                if self.position < 0:
                    self.trailing_stop(price_in=price_sell_in, trailing=trailing, sl=sl_sell, order=ord_sell_sl, type=trailing_type)
                    self.pending_check(ord_sell_sl)
                    self.pending_check(ord_sell_tp)
                    if pd.to_datetime(self.hour) == pd.to_datetime(final_hour):
                        self.ib.cancelOrder(ord_sell_sl)
                        self.order_send('BUY',lots)
                        print('=====Exit by time! Market BUY sent!=====')
                    if self.position == 0:
                        self.first = False
        self.ib.disconnect()

if __name__ == '__main__':
    #=====inputs=====
    '''symbol = input('\tsymbol: ')
    client = int(input('\tclient: '))
    minutes = int(input('\tminutes: '))
    target = float(input('\ttarget: '))
    trailing = float(input('\ttrailing: '))
    trailing_type = input('\ttrailing type(traditional, staggered): ')
    
    live_range = LiveRange(symbol=symbol, temp='1 min', client=client, verbose=True, notification=False)
    live_range.run_strategy(initial_hour='21:45:00', final_hour='21:48:00', ticks_range=1, trades_per_day=1, minutes=minutes, target=target,
                            trailing=trailing, trailing_type=trailing_type)'''

    symbol = 'EURUSD'
    live_range = LiveRange(symbol=symbol, temp='1 min', client=100, verbose=True, notification=True)
    live_range.run_strategy(initial_hour='14:18:00', final_hour='15:17:00', ticks_range=1, trades_per_day=1, minutes=1, target=0.00005,
                            trailing=0.2, trailing_type='traditional')