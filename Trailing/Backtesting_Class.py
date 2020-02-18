#
# Python Script with Base Class
# for Event-based Backtesting
#
# (c) Andres Estrada Cadavid
# QSociety

import pandas as pd
from math import sqrt
from itertools import groupby

class Backtesting():
    def __init__(self, symbol, start, end, amount, verbose=False):
        self.symbol = symbol
        instruments = pd.read_csv('instruments.csv').set_index('symbol')
        params = instruments.loc[self.symbol]
        self.market = str(params.market)
        self.init_margin = float(params.init_margin)
        self.maint_margin = float(params.maint_margin)
        self.leverage = int(params.leverage)
        self.tick_size = float(params.tick_size)
        self.comm_value = float(params.comm_value)
        self.slippage = int(params.slippage)
        self.start = start
        self.end = end
        self.amount = amount
        self.initial_amount = amount
        self.verbose = verbose
        self.position = 0
        self.number = 0
        self.allow_margins = True
        self.pool = pd.DataFrame(columns=['date','type','lots','price','S/L','T/P','commission','comment','profit'])
        self.history = pd.DataFrame(columns=['date','type','lots','price','S/L','T/P','commission','comment','profit'])
        self.get_data()

    def printProgressBar (self, iteration, total, pref = '', suffix = '', decimals = 2, length = 100, fill = '#'):
        percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
        filledLength = int(length * iteration // total)
        bar = fill * filledLength + '-' * (length - filledLength)
        print('\r%s |%s| %s%% %s' % (pref, bar, percent, suffix), end = '\r')
        # Print New Line on Complete
        if iteration == total: 
            print()

    def get_data(self):
        '''Retrieves and prepares the data'''
        print('Loading Data...')
        data = pd.read_csv('D:/futuro/Algorithmics/Data/Futures/1sec/'+self.symbol+'_1sec.csv', index_col=0, parse_dates=True).dropna()
        self.data = data.loc[self.start:self.end]
        print('Data Loaded!')
    
    def current_date(self,bar):
        '''Retrieves current date, weekday & hour'''
        self.date = self.data.index[bar].date()
        self.weekday = self.date.weekday()
        self.hour = self.data.index[bar].time()
    
    def calculate_commission(self, lots, price=0):
        '''Retrieves commission'''
        if self.market == 'futures':
            commission = lots * self.comm_value
        elif self.market == 'stocks':
            commission = ((lambda lot,pr: 1 if (lot*0.005 < 1 or lot*pr*0.01<1) else(lot*pr*0.01 if lot*0.005 > lot*pr*0.01 else lots*0.005))
                         (lots,price))
        return commission

    def calculate_profit(self, type, price, lots):
        '''Calculates profit'''
        if type == 'Buy':
            profit = (lambda pos: 0 if pos>=0 else (self.pool[self.pool.type == 'Sell'])['price'].iloc[0] - price)(self.position)
        else:
            profit = (lambda pos: 0 if pos<=0 else price - (self.pool[self.pool.type == 'Buy'])['price'].iloc[0])(self.position)
        return profit*self.leverage*lots
    
    def pool_check(self):
        '''Check pool trades'''
        if self.position == 0:
            self.pool = pd.DataFrame(columns=['date','type','lots','price','S/L','T/P','commission','comment','profit'])
    
    def calculate_margins(self, initial=0, maintenance=0, price=0, lots=0):
        '''Calculates according to market, the initial and maintenance margins'''
        if self.market == 'futures':
            self.initial_margin = initial * lots
            self.maintenance_margin = maintenance * lots
        elif self.market == 'stocks':
            self.initial_margin=self.maintenance_margin=price*lots*(lambda pos : 0.25 if pos>0 else 0.3)(self.position)

    def order_send(self, type, lots, price=0, bar=0, sl=0, tp=0, comment=''):
        '''Open a market or pending order'''
        self.calculate_margins(lots=lots, initial=self.init_margin, maintenance=self.maint_margin)
        if self.amount > self.initial_margin or (self.amount < self.initial_margin and self.position != 0):
            self.allow_margins = True
            if price == 0:
                price = (lambda pr : pr-(self.slippage*self.tick_size) if type == 'Buy' else pr+(self.slippage*self.tick_size))(self.data.close.iloc[bar])
            commission = self.calculate_commission(lots, price)
            profit = self.calculate_profit(type, price, lots)
            self.amount += (-commission + profit)
            self.number += 1
            self.trade = {'date':str(self.date)+' '+str(self.hour), 'type':type, 'lots':lots, 'price':price, 'S/L':sl, 'T/P':tp, 
                        'commission':commission, 'comment':comment, 'profit':profit}
            self.pool = pd.concat([self.pool,pd.DataFrame(self.trade,index=[self.number])], sort=False)
            self.history = pd.concat([self.history,pd.DataFrame(self.trade,index=[self.number])], sort=False)
            mult = (lambda dir: 1 if dir == 'Buy' else -1)(type)
            self.position += (mult*lots)
            self.pool_check()
            if self.verbose:
                print('%s | %sing %d units at %5.2f in %s' % (str(self.date)[:10], type, lots, price, self.symbol))
                print('%s | current cash balance %7.2f' % (str(self.date)[:10], self.amount))
        else:
            self.allow_margins = False
            print('Initial margin is not enough...')
    
    def get_current_profit(self, bar, lots):
        '''current profit'''
        mult = (lambda pos:1 if pos>0 else(-1 if pos<0 else 0))(self.position)
        self.current_profit = (self.data.close[bar] - self.pool.price.iloc[-1])*lots*self.leverage*mult
        self.floating_amount = self.amount + self.current_profit
        if self.floating_amount < self.maintenance_margin:
            print('Margin Call!')
    
    def calculate_metrics(self):
        '''Calculate backtesting metrics
        '''
        df = self.history
        df.index = pd.to_datetime(df.index)
        #Total Profit
        self.total_profit = round((df['profit']).sum(),2)
        #Total Commissions cost
        self.total_commissions = round(df['commission'].sum(),2)
        #Net Profit
        self.net_profit = self.total_profit - self.total_commissions
        #Gross Profit and Loss
        self.gross_profit = round((df['profit'][df['profit']>0]).sum(),2)
        self.gross_loss = round((df['profit'][df['profit']<0]).sum(),2)
        #Profit Factor
        self.profit_factor = (lambda prof,loss:abs(prof/loss) if loss != 0 else 0)(self.gross_profit,self.gross_loss)
        #Maximum Drawdown value and date
        self.max_drawdown = (df['max profit'] - df['accumulated profit']).max()
        self.max_drawdown_date = df.index[(df['max profit'] - df['accumulated profit']).values.argmax()]
        #Relative Drawdown
        self.relative_drawdown = (self.max_drawdown/self.initial_amount)*100
        #Absolute Drawdown
        self.absolute_drawdown = (lambda account : account - df['accumulated profit'].min() 
                                  if (df['accumulated profit'].min() < account) else 0)(self.initial_amount)
        #Total Transactions, Positive and Negative
        self.total_trades = (df['profit']!=0).sum()
        self.total_positive = (df['profit']>0).sum()
        self.total_negative = self.total_trades - self.total_positive
        #Short Transactions, Positive and Negative
        self.short_trades = len(df[(df['profit'] == 0) & (df['type'] == 'Sell')])
        self.short_pos = len(df[(df['profit']>0) & (df['type'] == 'Buy')])
        self.short_neg = len(df[(df['profit']<0) & (df['type'] == 'Buy')])
        #Long Transactions, Positive and Negative
        self.long_trades = len(df[(df['profit'] == 0) & (df['type'] == 'Buy')])
        self.long_pos = len(df[(df['profit']>0) & (df['type'] == 'Sell')])
        self.long_neg = len(df[(df['profit']<0) & (df['type'] == 'Sell')])
        #Expected Payoff
        self.expected_payoff = self.net_profit/self.total_trades
        #Greater Transactions
        self.greater_profitable = (df['profit'][df['profit']!=0]).max()
        self.greater_non_profitable = (df['profit'][df['profit']!=0]).min()
        #Average Transactions
        self.average_profitable = (df['profit'][df['profit']>0]).mean()
        self.average_non_profitable = (df['profit'][df['profit']<0]).mean()
        #Max Consecutive Win and Loss
        if True in ((df['profit'][df['profit']!=0])>0).values:
            self.max_con_win = max([len(list(g[1])) for g in groupby((df['profit'][df['profit']!=0])>0) if g[0]==1])
        else: self.max_con_win = 0
        if False in ((df['profit'][df['profit']!=0])>0).values:
            self.max_con_loss = max([len(list(g[1])) for g in groupby((df['profit'][df['profit']!=0])>0) if g[0]==0])
        else: self.max_con_loss = 0
        #Sharpe Ratio
        self.sharpe_ratio = (((df['profit'][df['profit']!=0]).mean()*len(set(df.index.date)))/
                      ((df['profit'][df['profit']!=0]).std()*sqrt(len(set(df.index.date)))))
    
    def print_metrics(self):
        print('='*55)
        print('Backtesting Metrics %s' % self.symbol)
        print('='*55)
        print('Total Profit(USD):  %7.2f' % self.total_profit)
        print('Total Profit(%%): %5.2f' % (self.total_profit*100/self.initial_amount))
        print('Total Commissions (USD): %7.2f' % self.total_commissions)
        print('Net Profit(USD): %7.2f' % self.net_profit)
        print('Gross Profit(USD): %7.2f Gross Loss (USD): %7.2f' % (self.gross_profit, self.gross_loss))
        print('Profit Factor: %7.2f' % self.profit_factor)
        print('Maximal Drawdown(usd): %7.2f date: %s' % (self.max_drawdown, self.max_drawdown_date))
        print('Relative Drawdown(%%): %7.2f' % self.relative_drawdown)
        print('Absolute Drawdown(usd): %7.2f' % self.absolute_drawdown)
        print('Total Trades: %d Positive Trades: %d Negative Trades: %d' % (self.total_trades,self.total_positive,self.total_negative))
        print('Total Sell Trades: %d Positive Shorts: %d Negative Shorts: %d' % (self.short_trades,self.short_pos,self.short_neg))
        print('Total Buy Trades: %d Positive longs: %d Negative Longs: %d' % (self.long_trades,self.long_pos,self.long_neg))
        print('Percent Profitable(%%): %7.2f' % (self.total_positive*100/self.total_trades))
        print('Expected Payoff: %7.2f' % self.expected_payoff)
        print('Greater Profitable Transaction: %7.2f' % self.greater_profitable)
        print('Greater non Profitable Transaction: %7.2f' % self.greater_non_profitable)
        print('Average Profitable Transaction: %7.2f' % self.average_profitable)
        print('Average non Profitable Transaction: %7.2f' % self.average_non_profitable)
        print('Max Consecutive Loss: %d Max Consecutive Win: %d' % (self.max_con_loss, self.max_con_win))
        print('Sharpe Ratio: %7.2f' % self.sharpe_ratio)

if __name__ == '__main__':
    back = Backtesting(symbol='ES', start='2019-09-25', end='2019-10-21', amount=10000, verbose=False)
    print(back.data.info())
    print(back.data.head())
    print(back.data.tail())