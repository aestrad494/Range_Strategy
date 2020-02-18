#
# Python Script with Backtesting
# for Range Strategy
#
# (c) Andres Estrada Cadavid
# QSociety

import numpy as np
import pandas as pd
from itertools import product
from Backtesting_Class import Backtesting
from Backtesting_Range import BackRange

class OptimizationRange(BackRange):
    def run_optimizer(self):
        self.final_results = pd.DataFrame()
        self.select = True

        #Variables to optimize---------------
        ##Minutes
        min_list = [1, 2, 3, 4, 5, 6, 10, 15, 30]
        min_len = len(min_list)

        ##Target
        start = 8
        step = 4
        stop = 20
        target_list = np.round(list(np.arange(start,stop+step,step)),2)
        target_len = len(target_list)

        ##Range Size
        start = 20
        step = 10
        stop = 50
        size_list = list(np.arange(start,stop+step,step))
        size_len = len(size_list)

        ##ATR value
        start = 60
        step = 10
        stop = 80
        atr_list = list(np.arange(start,stop+step,step))
        atr_len = len(atr_list)

        #Number of iterations----------------
        number_iterations = min_len*target_len*size_len*atr_len
        combinations = list(product(min_list, target_list, size_list, atr_list))
        print('=' * 55)
        print('Total Combinations : %d' % number_iterations)
        print('=' * 55)

        iteration = 0
        for combination in combinations:
            #Initializing variables
            self.history = pd.DataFrame(columns=['date','type','lots','price','S/L','T/P','commission','comment','profit'])
            self.amount = self.initial_amount
            self.allow_margins = True

            minutes = float(combination[0])
            target = float(combination[1])
            range_size = float(combination[2])
            min_atr = float(combination[3])

            iteration += 1
            #self.printProgressBar(iteration, number_iterations, pref='Progress', suffix='Complete', length=80)
            print('Combination %d/%d' % (iteration, number_iterations))
            self.run_range_strategy(initial_hour='09:30:00', final_hour='15:45:00', ticks_r=1, trades_per_day=1, max_range_size=range_size, minutes=minutes, target=target, min_atr=min_atr)
            #self.calculate_metrics()
            print('Backtesting Metrics')
            print('='*55)
            print('\tTotal Profit(%%): %5.2f' % (self.total_profit*100/self.initial_amount))
            print('\tNet Profit(USD): %5.2f' % self.net_profit)
            print('\tMax. Drawdown(USD): %5.2f' % self.max_drawdown)
            print('\tPercent Profitable(%%): %5.2f' % (self.total_positive*100/self.total_trades))
            print('\tProfit Factor: %7.2f' % self.profit_factor)
            print('\tSharpe Ratio: %5.2f' % self.sharpe_ratio)
            print('='*55)

            partial_results = [int(minutes), float(target), int(range_size), int(min_atr), 
                                self.net_profit, self.max_drawdown, round(self.net_profit/self.max_drawdown,2), 
                                self.total_trades, round((self.total_positive/self.total_trades)*100,2), 
                                int(self.max_con_loss), round(self.sharpe_ratio,2)]
            partial_results = pd.DataFrame(partial_results).T
            self.final_results = pd.concat([self.final_results, partial_results])
        
        self.final_results.index = [i for i in range(1, len(self.final_results)+1)]
        self.final_results.index.names = ['combination']
        self.final_results.columns = ['minutes', 'target', 'range size', 'min atr', 
                                      'net profit', 'max drawdown', 'profit/dd', 'total trades', 
                                      'percent profitable', 'max con loss', 'sharpe ratio']
        
        self.final_results.to_csv('final_results_%s.csv' % self.symbol)

        if self.select:
            valid_combination = (self.final_results[(self.final_results['net profit'] > 0) & (self.final_results['sharpe ratio'] >= 1.5)])
            max_NP = valid_combination['net profit'].max()
            selected = valid_combination[valid_combination['net profit']==max_NP]

            if len(selected)>0:
                minutes = selected['minutes'].iloc[0]
                target = selected['target'].iloc[0]
                range_size = selected['range size'].iloc[0]
                min_atr = selected['min atr'].iloc[0]
                print('=' * 55)
                print('Selected Results:')
                print('minutes: %d | target: %5.2f | range size: %d | min atr: %d' 
                        % (minutes, target, range_size, min_atr))
                print('=' * 55)
            else:
                print('=' * 55)
                print('No Combination Selected')
                print('=' * 55)

if __name__ == '__main__':
    
    #inputs
    symbol = input('\tsymbol: ')
    start = input('\tstart date: ')
    end = input('\tend date: ')

    back = Backtesting(symbol=symbol, start=start, end=end, amount=10000)
    optimization = OptimizationRange(back)
    
    optimization.run_optimizer()