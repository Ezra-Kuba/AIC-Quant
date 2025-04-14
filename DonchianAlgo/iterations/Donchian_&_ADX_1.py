#Set API Key, this is how lumibot needs it above all imports
#Wasted 20 minutes figuring that out
#THIS FIRST ALWAYS!
import os
os.environ["POLYGON_API_KEY"] = "wOPmrvJxYMnejK9h8bp82tgP5ZLxZxZ0"




from lumibot.strategies import Strategy
from lumibot.traders import Trader
from datetime import datetime
from datetime import timedelta
from lumibot.backtesting import BacktestingBroker,PolygonDataBacktesting  # Import Yahoo backtesting class
import yfinance as yf
import pandas as pd

from polygon import RESTClient
import requests

start_date = datetime(2020,5,5)
end_date = datetime(2024,1,1) 

symbol = "SPY"
BASE_URL = 'https://paper-api.alpaca.markets/v2'

API_KEY = 'PKHU42ZDVTSNKQY264DS'
API_SECRET = 'a233CXw0ti4Pda7XaHXCqy6P8erGeCeRXzWkHbUj'


Alpaca_creds= {
    
    'API_KEY': API_KEY,
    'API_SECRET': API_SECRET,
    'PAPER' : True

}

class DonchianAlgo_48hr(Strategy):
    def calculate_adx(self, df, period=11):
        # Step 1: Calculate price differences
        df['up_move'] = df['high'].diff()
        df['down_move'] = -df['low'].diff() # negate so its prev - curr

        # Step 2: Calculate +DM and -DM
        df['+DM'] = ((df['up_move'] > df['down_move']) & (df['up_move'] > 0)) * df['up_move']
        df['-DM'] = ((df['down_move'] > df['up_move']) & (df['down_move'] > 0)) * df['down_move']

        # Step 3: Calculate True Range (TR)
        #df['TR'] = df[['high', 'low', 'close']].copy().shift(1)
        df['TR'] = df[['high', 'low', 'close']].apply(
            lambda row: max(row['high'] - row['low'], abs(row['high'] - row['close']), abs(row['low'] - row['close'])),
            axis=1
        )

        # Step 4: Smooth TR, +DM, and -DM using Wilder’s smoothing (EMA with alpha = 1/period)
        df['TR_smooth'] = df['TR'].rolling(window=period).sum()
        df['+DM_smooth'] = df['+DM'].rolling(window=period).sum()
        df['-DM_smooth'] = df['-DM'].rolling(window=period).sum()

        # Step 5: Calculate +DI and -DI
        df['+DI'] = 100 * (df['+DM_smooth'] / df['TR_smooth'])
        df['-DI'] = 100 * (df['-DM_smooth'] / df['TR_smooth'])

        # Step 6: Calculate DX
        df['DX'] = 100 * (abs(df['+DI'] - df['-DI']) / (df['+DI'] + df['-DI']))

        # Step 7: Calculate ADX (smooth DX)
        df['ADX'] = df['DX'].rolling(window=period).mean()

        return df[['+DI', '-DI', 'ADX']]

    def CalcDonchChannels(self, df, period= 36):
        # Retrieve historical price data
        

        # Calculate Donchian Channel values
        min_price = df['close'].min()
        max_price = df['close'].max()
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
        marginbp = cash * 1.2
        if last_price is None or last_price == 0:
            #print("No Stock Data")
            return 0

        quantity = round(marginbp * .98 / last_price,0)
        return quantity

    def before_market_opens(self):
    # Call CalcDonchChannels method using self.
        prices = self.get_historical_prices(asset="SPY", length=36, timestep="60 minute")
        df = prices.df
        self.ADX_df = self.calculate_adx(df)
        channel_list = self.CalcDonchChannels(df)
        # Now you can use channel_list as needed
        self.lowest_price = channel_list[0]
        self.highest_price = channel_list[2]

    def on_trading_iteration(self):
        # Check if ADX_df is empty or invalid
        if self.ADX_df is None or self.ADX_df.empty:
            print("ADX DataFrame is empty. Skipping iteration.")
            return

        # Check if ADX column has enough data
        if 'ADX' not in self.ADX_df.columns or self.ADX_df['ADX'].isna().all():
            print("ADX data is missing or NaN. Skipping iteration.")
            return

        # Safely access the latest ADX value
        try:
            latest_adx = self.ADX_df['ADX'].iloc[-1]
        except IndexError:
            #print("Not enough ADX data to calculate. Skipping iteration.")
            return

        current_price = self.get_last_price(self.symbol)
        if current_price is None or pd.isna(current_price):
            #print(f"Error getting last price for {self.symbol}: price is NaN. Skipping iteration.")
            return

        position = self.get_position(self.symbol)
        has_long_position = position is not None and position.quantity > 0
        has_short_position = position is not None and position.quantity < 0

        # Rolling stop-loss logic for long positions
        if has_long_position:
            if self.highest_price is None or current_price >= self.highest_price:
                self.highest_price = current_price
                self.long_stop_loss_price = self.highest_price * 0.96  # Adjust stop-loss to 4% below the highest price

            if current_price < self.long_stop_loss_price:
                #print(f"Long position stop-loss triggered at {current_price}. Selling all.")
                self.sell_all()
                return

        # Rolling stop-loss logic for short positions
        elif has_short_position:
            if self.lowest_price is None or current_price <= self.lowest_price:
                self.lowest_price = current_price
                self.short_stop_loss_price = self.lowest_price * 1.03  # Adjust stop-loss to 3% above the lowest price

            if current_price > self.short_stop_loss_price:
                #print(f"Short position stop-loss triggered at {current_price}. Selling all.")
                self.sell_all()
                return

        # Entry logic based on ADX and price levels
        if latest_adx > 25:
            if current_price > self.highest_price and not has_long_position:
                if has_short_position:
                    self.sell_all()
                    return
                order_quantity = self.position_sizing()
                self.long_stop_loss_price = current_price * 0.96  # Initial stop-loss for long position
                self.highest_price = current_price  # Initialize highest price
                buy_order = self.create_order(
                    self.symbol,
                    order_quantity,
                    'buy',
                    type='stop',
                    stop_price=self.long_stop_loss_price
                )
                self.submit_order(buy_order)
                return

            elif current_price < self.lowest_price and not has_short_position:
                if has_long_position:
                    self.sell_all()
                    return
                order_quantity = self.position_sizing()
                self.short_stop_loss_price = current_price * 1.03  # Initial stop-loss for short position
                self.lowest_price = current_price  # Initialize lowest price
                sell_order = self.create_order(
                    self.symbol,
                    order_quantity,
                    'sell',
                    type='stop',
                    stop_price=self.short_stop_loss_price
                )
                self.submit_order(sell_order)
                return


api_key = "wOPmrvJxYMnejK9h8bp82tgP5ZLxZxZ0"
DonchianAlgo_48hr.run_backtest(
    PolygonDataBacktesting,
    start_date,
    end_date,
    parameters={},
    polygon_api_key= api_key
)
