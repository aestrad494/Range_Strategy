#
# Python Script with live trading Class
#
# (c) Andres Estrada Cadavid
# QSociety

import pandas as pd
from ib_insync import IB, util, MarketOrder, Future, Stock, Forex
from datetime import datetime
from nested_lookup import nested_lookup
import requests
from os import path

class Live(IB):
    def __init__(self, symbol, temp, client, verbose=False, notification=False):
        self.symbol = symbol
        instruments = pd.read_csv('instruments.csv').set_index('symbol')
        params = instruments.loc[self.symbol]
        self.market = str(params.market)
        self.exchange = str(params.exchange)
        self.temp = temp
        self.tick_size = float(params.tick_size)
        self.digits = int(params.digits)
        self.leverage = int(params.leverage)
        self.client = client
        self.verbose = verbose
        self.notification = notification
        self.ib = IB()
        print(self.ib.connect('127.0.0.1',7497, client))
        self.get_contract()
        self.data = self.download_data(tempo=self.temp, duration='1 D')
        self.current_date()
        self.pool = pd.DataFrame(columns=['date','id','type','lots','price','S/L','T/P','commission','comment','profit'])
        self.history = pd.DataFrame(columns=['date','id','type','lots','price','S/L','T/P','commission','comment','profit'])
        self.pending = pd.DataFrame(columns=['date','id','type','lots','price','S/L','T/P','commission','comment','profit'])
        self.position = 0
        self.number = 0

    def get_contract(self):
        if self.market == 'futures':
            expiration = self.ib.reqContractDetails(Future(self.symbol,self.exchange))[0].contract.lastTradeDateOrContractMonth 
            self.contract = Future(symbol=self.symbol, exchange=self.exchange, lastTradeDateOrContractMonth=expiration)
        elif self.market == 'forex':
            self.contract = Forex(self.symbol)
        elif self.market == 'stocks':
            self.contract = Stock(symbol=self.symbol, exchange=self.exchange, currency='USD')

    def download_data(self,tempo, duration):
        pr = (lambda mark:'TRADES' if mark=='futures' else ('TRADES' if mark=='stocks' else 'MIDPOINT'))(self.market)
        historical = self.ib.reqHistoricalData(self.contract, endDateTime='', durationStr=duration,
                        barSizeSetting=tempo, whatToShow=pr, useRTH=True, keepUpToDate=True)
        return historical
    
    def data_to_df(self, data):
        df = util.df(data)[['date','open','high','low','close','volume']].set_index('date')
        df.index = pd.to_datetime(df.index)
        return df
    
    def send_telegram_message(self, msg):
        '''Sends a telegram message
        '''
        requests.post('https://api.telegram.org/bot804823606:AAFq-YMKr4hIjQ4N5M8GYCGa5w9JJ1kIunk/sendMessage',
                      data={'chat_id': '@ranguito_channel', 'text': msg})

    def current_date(self):
        self.date = datetime.now().strftime('%Y-%m-%d')
        self.weekday = datetime.now().weekday()
        self.hour = datetime.now().strftime('%H:%M:%S')
    
    def pool_check(self):
        '''Check pool trades'''
        if self.position == 0:
            self.pool = pd.DataFrame(columns=['date','type','lots','price','S/L','T/P','commission','comment','profit'])

    def calculate_profit(self, type, price, lots):
        '''Calculates profit'''
        if type == 'BUY':
            profit = (lambda pos: 0 if pos>=0 else (self.pool[self.pool.type == 'SELL'])['price'].iloc[0] - price)(self.position)
        else:
            profit = (lambda pos: 0 if pos<=0 else price - (self.pool[self.pool.type == 'BUY'])['price'].iloc[0])(self.position)
        return profit*self.leverage*lots

    def order_values(self, order_id):
        price = 0
        commission = 0
        if len(self.ib.fills()) > 0:
            for trade in util.tree(self.ib.fills()):
                if ('OrderId' and 'clientId') in trade[1]['Execution']:
                    if ((nested_lookup('orderId',trade)[0] == order_id) and (nested_lookup('clientId',trade)[0] == self.client)):
                        commission = nested_lookup('commission',trade)[0]
                        price = nested_lookup('price',trade)[0]
        return (price, commission)
    
    def order_send(self, type, lots, sl=0, tp=0, comment=''):
        market_order = MarketOrder(type, lots)
        #initial_margin, maintenance_margin = self.get_margins(market_order)
        self.ib.placeOrder(self.contract, market_order)
        id = market_order.orderId
        
        self.number += 1
        price = 0
        while price == 0:
            self.ib.sleep(1)
            price, commission = self.order_values(id)
        profit = self.calculate_profit(type, price, lots)
        trade = {'date':str(self.date)+' '+str(self.hour), 'id':id, 'type':type, 'lots':lots, 'price':price, 
                 'S/L':sl, 'T/P':tp, 'commission':commission, 'comment':comment, 'profit':profit}
        self.save_trade(trade)
        self.pool = pd.concat([self.pool,pd.DataFrame(trade,index=[self.number])], sort=False)
        self.history = pd.concat([self.history,pd.DataFrame(trade,index=[self.number])], sort=False)
        mult = (lambda dir: 1 if dir == 'BUY' else -1)(type)
        self.position += (mult*lots)
        self.pool_check()
        if self.verbose:
            print('%s %s | %sING %d units at %5.2f in %s' % (str(self.date), str(self.hour), type, lots, price, self.symbol))
        if self.notification:
            if self.position != 0:
                self.send_message_in(type, price, sl, tp, lots)
            else:
                self.send_message_out(type, price, lots, profit, commission, commission)
    
    def bracket_stop_order(self, type, lots, entry_price, sl=0, tp=0, comment=''):
        bracket_order = self.ib.bracketStopOrder(type, lots, entry_price, tp, sl)
        #initial_margin, maintenance_margin = self.get_margins(bracket_order[0])
        for order in bracket_order:
            self.ib.placeOrder(self.contract, order)
        id_entry = bracket_order[0].orderId
        id_tp = bracket_order[1].orderId
        id_sl = bracket_order[2].orderId

        trade = {'date':str(self.date)+' '+str(self.hour), 'id':id_entry, 'type':bracket_order[0].action, 'lots':lots, 
                 'price':entry_price, 'S/L':sl, 'T/P':tp, 'commission':0, 'comment':comment, 'profit':0}
        self.pending = pd.concat([self.pending,pd.DataFrame(trade,index=[id_entry])], sort=False)
        trade = {'date':str(self.date)+' '+str(self.hour), 'id':id_tp, 'type':bracket_order[1].action, 'lots':lots, 
                 'price':tp, 'S/L':0, 'T/P':0, 'commission':0, 'comment':comment, 'profit':0}
        self.pending = pd.concat([self.pending,pd.DataFrame(trade,index=[id_entry])], sort=False)
        trade = {'date':str(self.date)+' '+str(self.hour), 'id':id_sl, 'type':bracket_order[2].action, 'lots':lots, 
                 'price':sl, 'S/L':0, 'T/P':0, 'commission':0, 'comment':comment, 'profit':0}
        self.pending = pd.concat([self.pending,pd.DataFrame(trade,index=[id_entry])], sort=False)
        return (bracket_order[0], bracket_order[1], bracket_order[2])

    def pending_check(self, order):
        id = order.orderId
        if len(self.pending) > 0:
            price, commission = self.order_values(id)
            if price > 0:
                self.number += 1
                order_select = self.pending[self.pending.id == id]
                profit = self.calculate_profit(order_select.type.iloc[0], price, order_select.lots.iloc[0])
                trade = {'date':str(self.date)+' '+str(self.hour), 'id':id, 'type':order_select.type.iloc[0], 'lots':order_select.lots.iloc[0], 'price':price, 
                         'S/L':order_select['S/L'].iloc[0], 'T/P':order_select['T/P'].iloc[0], 'commission':commission, 'comment':'', 'profit':profit}
                self.save_trade(trade)
                self.pool = pd.concat([self.pool,pd.DataFrame(trade,index=[self.number])], sort=False)
                self.history = pd.concat([self.history,pd.DataFrame(trade,index=[self.number])], sort=False)
                mult = (lambda dir: 1 if dir == 'BUY' else -1)(order_select.type.iloc[0])
                self.position += (mult*order_select.lots.iloc[0])
                self.pool_check()
                if self.verbose:
                    print('%s %s | %sING %d units at %5.2f in %s' % (str(self.date), str(self.hour), order_select.type.iloc[0], order_select.lots.iloc[0], price, self.symbol))
                if self.notification:
                    if self.position != 0:
                        self.send_message_in(order_select.type.iloc[0], price, order_select['S/L'].iloc[0], order_select['T/P'].iloc[0], order_select.lots.iloc[0])
                    else:
                        self.send_message_out(order_select.type.iloc[0], price, order_select.lots.iloc[0], profit, commission, commission)
                return True
            else:
                return False

    def get_margins(self, order):
        init_margin = float(self.ib.whatIfOrder(self.contract,order).initMarginChange)
        maint_margin = float(self.ib.whatIfOrder(self.contract,order).maintMarginChange)
        return(init_margin, maint_margin)
    
    def send_message_in(self, type, price_in, sl, tp, lots):
        msg_in = '%s Opened in %s \nPrice: %5.2f \nS/L: %5.2f \nT/P: %5.2f \nLots: %d \nAt: %s' % (type, self.symbol, price_in, sl, tp, lots, self.hour)
        self.send_telegram_message(msg_in)
    
    def send_message_out(self, type, price_out, lots, profit, comm_in, comm_out):
        msg_out = '%s Closed in %s \nPrice: %5.2f \nProfit(USD): %5.2f \nCommissions(USD): %5.2f \nAt: %s' % \
                    (type, self.symbol, price_out, profit, (comm_in+comm_out),self.hour)
        self.send_telegram_message(msg_out)

    def save_trade(self, trade):
        if not path.exists('history_trades_%s.csv'%self.symbol):
            initial = pd.DataFrame(columns=['date','id','type','lots','price','S/L','T/P','commission','comment','profit']).set_index('date')
            initial.to_csv('history_trades_%s.csv'%self.symbol)
        history = pd.read_csv('history_trades_%s.csv'%self.symbol)
        trade = pd.DataFrame(trade, index=[0])
        history = pd.concat([history, trade], sort=False)
        history['net profit'] = history['profit'] - history['commission']
        history['accumulated profit'] = history['net profit'].cumsum()
        history['max profit'] = history['accumulated profit'].cummax()
        history.set_index('date').to_csv('history_trades_%s.csv'%self.symbol)

if __name__ == '__main__':
    '''symbol = 'ES'
    live = Live(symbol='ES', tempo='1 min', client=100, verbose=False, notification=False)'''

    symbol = 'EURUSD'
    live = Live(symbol=symbol, temp='1 min', client=100, verbose=False, notification=False)