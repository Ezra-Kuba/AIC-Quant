#This is the simple original version of the algorithm
#Feel free to analyze this before the up to date strategy


#Set API Key, this is how lumibot needs it above all imports
#Wasted 20 minutes figuring that out
#THIS FIRST ALWAYS!
import os
os.environ["POLYGON_API_KEY"] = os.getenv('POLYGON_API_KEY')




from lumibot.strategies import Strategy
from lumibot.traders import Trader
from datetime import datetime
from datetime import timedelta
from lumibot.backtesting import BacktestingBroker,PolygonDataBacktesting  # Import Yahoo backtesting class
import yfinance as yf
import pandas as pd

from polygon import RESTClient
import requests

start_date = datetime(2022,5,5)
end_date = datetime(2024,1,1) 

symbol = "SPY"
BASE_URL = 'https://paper-api.alpaca.markets/v2'

API_KEY = os.getenv('ALPACA_API_KEY') 
API_SECRET = os.getenv('ALPACA_API_SECRET')


Alpaca_creds= {
    
    'API_KEY': API_KEY,
    'API_SECRET': API_SECRET,
    'PAPER' : True

}

class DonchianAlgo(Strategy):
    def CalcDonchChannels(self, period=20):
        # Retrieve historical price data
        prices = self.get_historical_prices(asset="SPY", length=period, timestep="day")
        df = prices.df

        # Calculate Donchian Channel values
        min_price = df['close'].min()
        max_price = df['open'].max()
        mid_price = (min_price + max_price) / 2

        # Return the calculated values
        return [min_price, mid_price, max_price]

    def initialize(self, symbol="SPY"):
        self.symbol = symbol
        self.sleeptime = "1H"
        self.last_trade = None
        self.highest_price = None
        self.lowest_price = None
    
    def position_sizing(self): 
        cash = self.get_cash()
        last_price = self.get_last_price(self.symbol)
        marginbp = cash
        if last_price is None or last_price == 0:
            print("No Stock Data")
            return 0

        quantity = round(marginbp * .98 / last_price,0)
        return quantity

    def before_market_opens(self):
    # Call CalcDonchChannels method using self.
        channel_list = self.CalcDonchChannels()
        # Now you can use channel_list as needed
        self.lowest_price = channel_list[0]
        self.highest_price = channel_list[2]

    def on_trading_iteration(self):
        # Retrieve Donchian Channel values
        

        # Get the latest market data for the symbol
        current_price = self.get_last_price(self.symbol)

        # Check current position
        position = self.get_position(self.symbol)
        has_long_position = position is not None and position.quantity > 0
        has_short_position = position is not None and position.quantity < 0

        # Define the size of the order
        

        # if(self.get_cash() < order_quantity * self.get_last_price(self.symbol)):
        #     return

        # Long entry condition: Current price crosses above the upper band
        if current_price > self.highest_price and not has_long_position:
            if has_short_position:
                # Close the existing short position before going long
                self.sell_all()
                return
            order_quantity = self.position_sizing()
            # Create and submit a buy order to enter long position
            stopLoss = current_price - (current_price * .04)
            buy_order = self.create_order(self.symbol, order_quantity, 'buy', stop_loss_price= stopLoss)
            self.submit_order(buy_order)
            return

        # Short entry condition: Current price crosses below the lower band
        elif current_price < self.lowest_price and not has_short_position:
            if has_long_position:
                # Close the existing long position before going short
                self.sell_all()
                return
            # Create and submit a sell order to enter short position
            order_quantity = self.position_sizing()
            stopLoss = current_price + (current_price * .034)
            sell_order = self.create_order(self.symbol, order_quantity, 'sell', stop_loss_price= stopLoss)
            self.submit_order(sell_order)
            return

        # # Exit conditions: Close positions if price moves back within the channel
        # elif has_long_position and current_price < (middle_band * 0.9):
        #     self.sell_all()  # Close long position
        # elif has_short_position and current_price > (middle_band * 1.1):
        #     self.sell_all()  # Close short position


api_key = "wOPmrvJxYMnejK9h8bp82tgP5ZLxZxZ0"
DonchianAlgo.run_backtest(
    PolygonDataBacktesting,
    start_date,
    end_date,
    parameters={},
    polygon_api_key= api_key
)
