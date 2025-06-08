

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import scipy
import math
import pandas_ta as ta
import os
from polygon import RESTClient


from datetime import datetime



def find_levels( 
        price: np.array, atr: float, # Log closing price, and log atr 
        first_w: float = 0.1, 
        atr_mult: float = 3.0, 
        prom_thresh: float = 0.1
):

    # Setup weights
    last_w = 1.0
    w_step = (last_w - first_w) / len(price)
    weights = first_w + np.arange(len(price)) * w_step
    weights[weights < 0] = 0.0

    # Get kernel of price. 
   
    kernal = scipy.stats.gaussian_kde(price, bw_method=atr*atr_mult, weights=weights)

    # Construct market profile
    min_v = np.min(price)
    max_v = np.max(price)
    step = (max_v - min_v) / 200
    price_range = np.arange(min_v, max_v, step)
    pdf = kernal(price_range) # Market profile

    # Find significant peaks in the market profile
    pdf_max = np.max(pdf)
    prom_min = pdf_max * prom_thresh

    peaks, props = scipy.signal.find_peaks(pdf, prominence=prom_min)
    levels = [] 
    for peak in peaks:
        levels.append(np.exp(price_range[peak]))

    return levels




def support_resistance_levels(
        data: pd.DataFrame, lookback: int, 
        first_w: float = 0.01, atr_mult:float=3.0, prom_thresh:float =0.25
):

    # Get log average true range, 
    atr = ta.atr(np.log(data['high']), np.log(data['low']), np.log(data['close']), lookback)

    all_levels = [None] * len(data)
    for i in range(lookback, len(data)):
        i_start  = i - lookback
        vals = np.log(data.iloc[i_start+1: i+1]['close'].to_numpy())
        levels, peaks, props, price_range, pdf, weights= find_levels(vals, atr.iloc[i], first_w, atr_mult, prom_thresh)
        all_levels[i] = levels
        
    return all_levels


def convert_agg_array_to_df(agg_array):
    data = {
        'timestamp': [pd.to_datetime(bar.timestamp, unit='ms') for bar in agg_array],
        'open': [bar.open for bar in agg_array],
        'high': [bar.high for bar in agg_array],
        'low': [bar.low for bar in agg_array],
        'close': [bar.close for bar in agg_array],
        'volume': [bar.volume for bar in agg_array],
        'vwap': [bar.vwap for bar in agg_array],  # optional
    }
    
    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    return df
def get_nearest_levels(levels, price):
    levels_below = [lvl for lvl in levels if lvl < price]
    levels_above = [lvl for lvl in levels if lvl > price]

    nearest_below = max(levels_below) if levels_below else None
    nearest_above = min(levels_above) if levels_above else None

    return nearest_below, nearest_above


start_date = datetime(2020,5,5)
end_date = datetime(2021,1,1) 

s = os.getenv('POLYGON_API_KEY')
client = RESTClient(str(s))

aggs = []
for a in client.list_aggs(
    "AAPL",
    1,
    "hour",
    "2025-01-05",
    "2025-04-10",
    adjusted="true",
    sort="asc",
    limit=3000,
):
    aggs.append(a)
data = convert_agg_array_to_df(aggs)

# print(np.log(data['high']))
# print()
# # levels = support_resistance_levels(data, 365, first_w=1.0, atr_mult=3.0)
# atr = ta.atr(np.log(data['high']), np.log(data['low']), np.log(data['close']))
# print(atr)
# vals = np.log(data['close'].to_numpy())
# levels = find_levels(vals,atr.iloc[-1]) # last row, then grab 'close'
# levelb,levela = get_nearest_levels(levels,210)
# print(levelb )
# print(levela)
# print(levels)