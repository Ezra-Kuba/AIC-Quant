
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

start_date = datetime(2020,5,5)
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


class bTestClass(Strategy):
        

    

    #default initialization of values, runs 1 time when you start the program.
    #In theory this algo should short when we are under 200MA and the RSI is overbought, and buy when above 200MA and RSI Oversold, momentum trading essentially
    def initialize(self, symbol = "SPY", rsi_threshold_bull=30, rsi_threshold_bear=60,stop_loss_pct=0.005, ma_threshold_pct=0.001):
        self.symbol = symbol
        self.rsi_threshold_bull = rsi_threshold_bull 
        self.rsi_threshold_bear = rsi_threshold_bear
        self.stop_loss_pct = stop_loss_pct 
        self.ma_threshold_pct = ma_threshold_pct  # Must be at least 0.10% below 200-SMA to trigger trade
        self.sleeptime = "1H"  # Check conditions every 1 hour
        self.last_trade = None 
        self.highest_price = None 
        self.lowest_price = None 
        
        self.ma_df = self.fetch_polygon_sma_series(symbol = self.symbol)

        if self.ma_df is None:
            print("Could not fetch SMA series.")
            
       
    def fetch_polygon_sma_series( self, symbol, window=200, timespan="day"):
        client = RESTClient("wOPmrvJxYMnejK9h8bp82tgP5ZLxZxZ0")
        
        sma = client.get_sma(
            ticker=symbol,
            timespan=timespan,
            adjusted="true",
            window="200",
            series_type="close",
            order="desc",
            timestamp_gte=start_date.strftime("%Y-%m-%d"),
            timestamp_lte=end_date.strftime("%Y-%m-%d"),
            limit= 5000
        )
        # print(sma)
        values = sma.values  
        df = pd.DataFrame(values)
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms").dt.date
        df = df[["datetime", "value"]].rename(columns={"value": "sma"})

        # O(1) LOOKUP META
        sma_df = df.set_index("datetime")
    
        return sma_df
    
    def get_smas_for_date(self,dt):
        #IN O(1) TIME GOOGLE HIRE ME
        if isinstance(dt, datetime):
            dt = dt.date()
        return self.ma_df.loc[dt, "sma"] if dt in self.ma_df.index else None

        
    #dynamic Position Sizing, assuming margin buying power 1:1.5 (50% margin)
    def position_sizing(self): 
        cash = self.get_cash() 
        last_price = self.get_last_price(self.symbol)
        marginbp = cash * 1.5
        if last_price is None or last_price == 0:
            print("No Stock Data")
            return 0

        quantity = round(marginbp * .98 / last_price,0)
        return quantity

   
    def calculate_rsi(self, symbol, length=14, timeframe="60 minute"):
        prices = self.get_historical_prices(symbol, timestep=timeframe, length=length + 1)
        if len(prices) < length + 1:
            return None
        
        delta = prices["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(length).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(length).mean()
        rs = gain / (loss + 1e-6)
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]


  


    #this runs once every sleeptime inverval, currently that is 1H so once every hour.
    def on_trading_iteration(self):
        quantity = self.position_sizing() 

       


        # print("trading Iteration")
        # Log the latest SMA value
        daily_200_sma = self.get_smas_for_date(self.get_datetime())
        if(daily_200_sma is None):
            return
        position = self.get_position(self.symbol)
        
        current_price = self.get_last_price(self.symbol)
        #Position Manager
        # print("debating Position")

        #I simulated rollingstop loss order (prob works maybe) and some other stuff
        if position is not None:
            # print("we took trade")
            #We are long boner time
            if(position.quantity > 0):
                #if within +- .10% of MA cut short
                if abs(current_price - daily_200_sma) / daily_200_sma <= 0.001:
                        self.sell_all()         
                        self.lowest_price = None  # Reset for next trade
                          
                        return
                    

                    # Update lowest price reached since entry
                if self.highest_price is None or current_price > self.highest_price:
                        self.highest_price = current_price

                    # Calculate the rolling stop price (0.5% below lowest price reached)
                rolling_stop_price = self.highest_price * (1 - self.stop_loss_pct)

                    # Exit trade if price falls below the rolling stop
                if current_price <= rolling_stop_price:
                        self.sell_all()
                       
                        self.highest_price = None  # Reset for next trade
                        return
                return
                    
            #we are currently short
            if(position.quantity < 0):
                #if within +- .10% of MA cut short
                if abs(current_price - daily_200_sma) / daily_200_sma <= 0.001:
                    self.sell_all()
                    
                    self.lowest_price = None  # Reset for next trade
                    return
                

                   

                #rolling stop functionality
                current_price = self.get_last_price(self.symbol)

                # Update lowest price reached since entry
                if self.lowest_price is None or current_price < self.lowest_price:
                    self.lowest_price = current_price

                # Calculate the rolling stop price (0.5% above lowest price reached)
                rolling_stop_price = self.lowest_price * (1 + self.stop_loss_pct)

                # Exit trade if price rises above the rolling stop
                if current_price >= rolling_stop_price:
                    self.sell_all()
                    self.lowest_price = None  # Reset for next trade
                    return
                return
            

        if(position is not None):
            return
        #If we here we not in trade lets look for a new trade
        #Lets see if Bear or Bull case activates
        if (current_price >= daily_200_sma * (1 - self.ma_threshold_pct)):
            # print("calculating trade strategies")
            #Bull Case was activated
            #hourly prices only accepts time in terms of days or mins, this took about 2 hours to figure out. Not in the instructions anywhere tf
            hourly_prices = self.get_historical_prices(self.symbol, length=14, timestep="60 minute")

            if(hourly_prices is None):
                print("Bro aint got no hour data")

            hourly_prices = hourly_prices.df

            if len(hourly_prices) < 14:
                return  # Not enough data
            
            

            # Calculate RSI
            delta = hourly_prices["close"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / (loss + 1e-6)
            rsi = 100 - (100 / (1 + rs))

            latest_rsi = rsi.iloc[-1]

             # Check if RSI  30 or less
        

            if latest_rsi <= self.rsi_threshold_bull and position is None:
                #we need to buy here
                
                #buy order
                order = self.create_order(
                    self.symbol, 
                    quantity, 
                    "buy", 
                    
                )


                #supposedly trailing stop orders do not work during backtesting. I took some random reddit thread's word but would be optimal here

                # Trailing stop
                # trailingstop = self.create_order(
                #     self.symbol,
                #     quantity,
                #     "sell",
                #     type= "trailing_stop",
                #     trail_percent= .5


                # )
                self.submit_order(order)
                # self.submit_order(trailingstop)
                return

        elif(current_price <= daily_200_sma * (1 - self.ma_threshold_pct)):
            #Bear Case market cooked 
            # Get hourly historical prices for RSI calculation
            hourly_prices = self.get_historical_prices(self.symbol, length=14, timestep="60 minute")
            if(hourly_prices is None):
                #print("Bro aint got no hour data")
                return
            hourly_prices = hourly_prices.df
            if len(hourly_prices) < 14:
                return  # Not enough data

            # Calculate RSI
            delta = hourly_prices["close"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / (loss + 1e-6)
            rsi = 100 - (100 / (1 + rs))

            latest_rsi = rsi.iloc[-1]

            # Check if RSI > 60
            

            if latest_rsi >= self.rsi_threshold_bear and position is None:
                  #sell order
                order = self.create_order(
                    self.symbol, 
                    quantity, 
                    "sell", 
                   
                )
                # Trailing stop
                # trailingstop = self.create_order(
                #     self.symbol,
                #     quantity,
                #     "buy",
                #     type= "trailing_stop",
                #     trail_percent= .5


                # )
                self.submit_order(order)
                # self.submit_order(trailingstop)
                return
        



#this is our "main" call api kees and initialize backtest


api_key = "wOPmrvJxYMnejK9h8bp82tgP5ZLxZxZ0"
bTestClass.run_backtest(
    PolygonDataBacktesting,
    start_date,
    end_date,
    parameters={},
    polygon_api_key= api_key
)


       



        
