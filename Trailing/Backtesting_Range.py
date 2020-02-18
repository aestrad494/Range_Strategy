#
# Python Script with Backtesting
# for Range Strategy
#
# (c) Andres Estrada Cadavid
# QSociety

import pandas as pd
from datetime import timedelta
from Backtesting_Class import Backtesting

class BackRange(Backtesting):
    def x_round(self, x):
        mult = 1/self.tick_size
        return round(x*mult)/mult
    
    def trailing_stop(self, bar, price_in, trailing, sl, type = 'traditional'):
        '''type = 'traditional' | 'staggered'
        '''
        new_sl = sl
        if trailing > 0:
            if self.position > 0:
                if type == 'traditional':
                    if self.data['high'][bar] - price_in >= trailing:
                        if sl < self.data['high'][bar] - trailing:
                            new_sl = self.data['high'][bar] - trailing
                            print('stop modified from %5.2f to %5.2f' % (sl, new_sl))
                else:
                    if self.data['high'][bar] - price_in >= trailing and not self.first:
                        new_sl = price_in
                        self.first = True
                        print('stop modified from %5.2f to %5.2f (BE)' % (sl, new_sl))
                    if self.first and self.data['high'][bar] - new_sl >= 2*trailing:
                        new_sl = sl + trailing
                        print('stop modified from %5.2f to %5.2f' % (sl, new_sl))
            if self.position < 0:
                if type == 'traditional':
                    if price_in - self.data['low'][bar] >= trailing:
                        if sl > self.data['low'][bar] + trailing:
                            new_sl = self.data['low'][bar] + trailing
                            print('stop modified from %5.2f to %5.2f' % (sl, new_sl))
                else:
                    if price_in - self.data['low'][bar] >= trailing and not self.first:
                        new_sl = price_in
                        self.first = True
                        print('stop modified from %5.2f to %5.2f (BE)' % (sl, new_sl))
                    if self.first and new_sl - self.data['low'][bar] >= 2*trailing:
                        new_sl = sl - trailing
                        print('stop modified from %5.2f to %5.2f' % (sl, new_sl))
        return self.x_round(new_sl)
    
    def run_range_strategy(self, initial_hour, final_hour, ticks_r, trades_per_day, minutes, target, trailing=0, trailing_type='traditional'):
        print('=' * 55)
        print('Running Range Strategy in %s | minutes = %d & target = %2.2f & trailing = %2.2f & type = %s' % (self.symbol, minutes, target, trailing, trailing_type))
        print('=' * 55)

        self.initial_hour = pd.to_datetime(initial_hour).time()
        self.final_hour = pd.to_datetime(final_hour).time()
        range_calculation = False
        current_trades = 0
        self.first = False
        trailing = self.x_round(trailing * target)

        for bar in range(len(self.data)):
            self.current_date(bar)
            last_weekday = (lambda bar : self.weekday if (bar == 0) else self.data.index[bar-1].weekday())(bar)
            
            if self.weekday != last_weekday or bar == 0:
                hour_range = pd.to_datetime(str(self.date)+' '+initial_hour) + timedelta(minutes = minutes)
                current_trades = 0
                range_calculation = False
            
            if self.weekday < 5 and self.final_hour >= self.hour >= hour_range.time():
                if self.data.index[bar] >= hour_range and not range_calculation:
                    bars_range = (self.data.loc[str(self.date)+' '+initial_hour:str(hour_range)])
                    if bars_range.index[-1].minute == hour_range.minute:
                        bars_range = (self.data.loc[str(self.date)+' '+initial_hour:str(hour_range)]).iloc[:-1]
                    maximum = round(bars_range['high'].max(),2)
                    minimum = round(bars_range['low'].min(),2)
                    price_buy_in = maximum + (ticks_r*self.tick_size)
                    sl_buy = minimum; tp_buy = price_buy_in + target
                    price_sell_in = minimum - (ticks_r*self.tick_size)
                    sl_sell = maximum; tp_sell = price_sell_in - target
                    range_calculation = True
                    lots = 1

                #Entries---------------------------------
                if self.position == 0 and current_trades < trades_per_day:
                    if self.allow_margins:
                        ##Buys
                        if self.data.high[bar] >= price_buy_in:
                            self.order_send('Buy', lots, price=price_buy_in, sl=sl_buy, tp=tp_buy, comment='entry_buy')
                            current_trades += 1
                        ##Sells
                        if self.data.low[bar] <= price_sell_in:
                            self.order_send('Sell', lots, price=price_sell_in, sl=sl_sell, tp=tp_sell, comment='entry_sell')
                            current_trades += 1
                    else:
                        break
                
                #Current Profit--------------------------
                if self.position != 0:
                    self.get_current_profit(bar, lots)

                #Exits----------------------------------- 
                ## Buys        
                if self.position > 0:
                    sl_buy = self.trailing_stop(bar=bar, price_in=price_buy_in, trailing=trailing, sl=sl_buy, type=trailing_type)
                    if self.data.low[bar] <= sl_buy:
                        price_buy_out = sl_buy
                        self.order_send('Sell', lots, price=price_buy_out, sl=sl_buy, tp=tp_buy, comment='stop loss')
                    if self.data.high[bar] >= tp_buy:
                        price_buy_out = tp_buy
                        self.order_send('Sell', lots, price=price_buy_out, sl=sl_buy, tp=tp_buy, comment='take profit')
                    if self.hour == self.final_hour:
                        self.order_send('Sell', lots, bar=bar, sl=sl_buy, tp=tp_buy, comment='time exit')
                    if self.floating_amount < self.maintenance_margin:
                        self.order_send('Sell', lots, bar=bar, sl=sl_buy, tp=tp_buy, comment='margin call'); break
                    if self.position == 0 and trailing_type == 'staggered':
                        self.first = False

                ## Sells
                if self.position < 0:
                    sl_sell = self.trailing_stop(bar=bar, price_in=price_sell_in, trailing=trailing, sl=sl_sell, type=trailing_type)
                    if self.data.high[bar] >= sl_sell:
                        price_sell_out = sl_sell
                        self.order_send('Buy', lots, price=price_sell_out, sl=sl_sell, tp=tp_sell, comment='stop loss')
                    if self.data.low[bar] <= tp_sell:
                        price_sell_out = tp_sell
                        self.order_send('Buy', lots, price=price_sell_out, sl=sl_sell, tp=tp_sell, comment='take profit')
                    if self.hour == self.final_hour:
                        self.order_send('Buy', lots, bar=bar, sl=sl_sell, tp=tp_sell, comment='time exit')
                    if self.floating_amount < self.maintenance_margin:
                        self.order_send('Sell', lots, bar=bar, sl=sl_buy, tp=tp_buy, comment='margin call'); break
                    if self.position == 0 and trailing_type == 'staggered':
                        self.first = False
        
        if len(self.history) > 0:
            self.history.set_index('date',inplace=True)
            self.history['net profit'] = self.history['profit'] - self.history['commission']
            self.history['accumulated profit'] = self.history['net profit'].cumsum() + self.initial_amount
            self.history['max profit'] = self.history['accumulated profit'].cummax()

            self.history.to_csv('history_trades/history_trades_%s.csv' % self.symbol)
            #print(self.history)
            self.calculate_metrics()
            #self.print_metrics()
            if self.verbose:
                self.print_metrics()

if __name__ == '__main__':
    range_back = BackRange(symbol='RTY', start='2019-01-31', end='2020-01-31', amount=10000, verbose=True)
    range_back.run_range_strategy(initial_hour='09:30:00', final_hour='15:45:00', ticks_r=1, trades_per_day=1, minutes=2, target=12, trailing=0.8, 
                                  trailing_type='staggered')