import os
os.environ["POLYGON_API_KEY"] = os.getenv('POLYGON_API_KEY')

from lumibot.strategies import Strategy
from lumibot.traders import Trader
from datetime import datetime
from datetime import timedelta
from lumibot.backtesting import BacktestingBroker,PolygonDataBacktesting  # Import Yahoo backtesting class
import yfinance as yf
import pandas as pd
import numpy as np

import pandas_ta as ta
from polygon import RESTClient
import requests
import Levels
# start_date = datetime(2025,2,19)
# end_date = datetime(2025,4,15) 

start_date = datetime(2022,1,1)
end_date = datetime(2022,2,16) 


# start_date = datetime(2021,12,31)
# end_date = datetime(2024,2,16) 

BASE_URL = 'https://paper-api.alpaca.markets/v2'

API_KEY = os.getenv('ALPACA_API_KEY')
API_SECRET = os.getenv('ALPACA_API_SECRET')


Alpaca_creds= {
    
    'API_KEY': API_KEY,
    'API_SECRET': API_SECRET,
    'PAPER' : True

}


class LevelsTrader(Strategy):
        

    

    #default initialization of values, runs 1 time when you start the program.
    #In theory this algo should short when we are under 200MA and the RSI is overbought, and buy when above 200MA and RSI Oversold, momentum trading essentially
    def initialize(self, symbol = "SPY", rsi_threshold_bull=30, rsi_threshold_bear=60,stop_loss_pct=0.005, ma_threshold_pct=0.001):
        self.symbol = symbol
        self.sleeptime = "1H"  # Check conditions every 1 hour
        self.levels = {}
        self.last_trade = ""
        self.stop_loss_pct = 0.02
        self.highest_price = None 
        self.lowest_price = None 
        
       
 
    #dynamic Position Sizing, assuming margin buying power 1:1.5 (50% margin)
    def position_sizing(self): 
        if(self.get_position(self.symbol) is not None):
             return abs(self.get_position(self.symbol).quantity)
        cash = self.get_cash() 
        last_price = self.get_last_price(self.symbol)
        marginbp = cash * 1
        if last_price is None or last_price == 0:
            print("No Stock Data")
            return 0

        quantity = round(marginbp * .98 / last_price,0)
        return quantity
    def get_nearest_levels(self):
        price = self.get_last_price(self.symbol)
        levels_below = [lvl for lvl in self.levels if lvl < price]
        levels_above = [lvl for lvl in self.levels if lvl > price]

        nearest_below = max(levels_below) if levels_below else None
        nearest_above = min(levels_above) if levels_above else None

        return nearest_below, nearest_above

    def before_market_opens(self):
        data = self.get_historical_prices(self.symbol, length=3000, timestep="60 minute")
        data = data.df
        if(data is None or data.empty):
            print("data empty")
            return
        
        
        atr = ta.atr(np.log(data['high']), np.log(data['low']), np.log(data['close']))
        if(atr is None):
            print("no atr")
            return
        vals = np.log(data['close'].to_numpy())
       
        self.levels = Levels.find_levels(vals,atr.iloc[-1]) 
    def custom_log(self, message):
        timestamp = self.get_datetime().strftime("%Y-%m-%d %H:%M:%S")
        with open("levelslog.txt", "a") as f:
            f.write(f"[{timestamp}] {message}\n")


    def on_trading_iteration(self):
        
        
        t1 = False
        t2 = False
        
        if(self.levels is None):
            print("no levels")
            return
        quantity = self.position_sizing()
        latestp = self.get_last_price(self.symbol)
        
       
        position = self.get_position(self.symbol)
       
        past_candle = self.get_historical_prices(self.symbol,length=2,timestep= "60 minute" )
        past_candle = past_candle.df
        if(past_candle is None or past_candle.empty):
            print("no past candles")
            
            return
       
        self.last_price = past_candle.iloc[0]["close"]
       
        self.custom_log(f"Latest price: {latestp}")
        self.custom_log(f"Last price: {self.last_price}")
        
        self.custom_log(f"Levels: {self.levels}")


        #  if self.last_price < lvl < latestp:
        
        #  if self.last_price > lvl > latestp:
        
        for lvl in self.levels:
            # Bullish breakout
            if self.last_price < lvl < latestp:
                if(position is not None and position.quantity> 0):
                    
                    return
                self.custom_log(f"Broke above level {lvl}, going long")
                if self.last_trade == "short":
                    self.sell_all()
                    self.custom_log(f"sold shorts")
                    
                order = self.create_order(self.symbol, quantity, "buy")
                self.submit_order(order)
                self.last_trade = "buy"
                self.custom_log(f"going long: {quantity}")
                self.last_level = lvl
                
                return  # Only one trade per bar

            # Bearish breakdown
            if self.last_price > lvl > latestp:
                if(position is not None and position.quantity < 0):
                    
                    return
                self.custom_log(f"Broke below level {lvl}, going short")
                if self.last_trade == "buy":
                    self.sell_all()
                    self.custom_log(f"sold longs")
                    
                order = self.create_order(self.symbol, quantity, "sell")
                self.submit_order(order)
                self.last_trade = "short"
                self.custom_log(f"going short {quantity}")
                self.last_level = lvl
                return
        if(self.last_trade == "buy"):
            if(self.last_level*.99 > latestp):
                self.sell_all()
                # order = self.create_order(self.symbol, quantity, "sell")
                # self.submit_order(order)
                # self.last_trade = "short"
        elif(self.last_trade == "sell"):
            if(self.last_level*1.01 < latestp):
                self.sell_all()
                # order = self.create_order(self.symbol, quantity, "buy")
                # self.submit_order(order)
                # self.last_trade = "buy"
        
    #    # Rejection logic
    #     last_high = past_candle.iloc[-2]["high"]
    #     last_low = past_candle.iloc[-2]["low"]

    #     for lvl in self.levels:
    #         # Bearish rejection from resistance
    #         if last_close < lvl and latestp < lvl and last_high >= lvl:
    #             self.custom_log(f"Rejected at resistance {lvl}, shorting")
    #             if self.last_trade == "buy":
    #                 self.sell_all()
    #             order = self.create_order(self.symbol, quantity, "sell")
    #             self.submit_order(order)
    #             self.last_trade = "short"
    #             return

    #         # Bullish rejection from support
    #         if last_close > lvl and latestp > lvl and last_low <= lvl:
    #             self.custom_log(f"Rejected at support {lvl}, going long")
    #             if self.last_trade == "short":
    #                 self.sell_all()
    #             order = self.create_order(self.symbol, quantity, "buy")
    #             self.submit_order(order)
    #             self.last_trade = "buy"
    #             return

      



        



#this is our "main" call api kees and initialize backtest


api_key = os.getenv('POLYGON_API_KEY')
LevelsTrader.run_backtest(
    PolygonDataBacktesting,
    start_date,
    end_date,
    parameters={},
    polygon_api_key= api_key
)


       



        
