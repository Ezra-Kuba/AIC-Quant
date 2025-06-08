import pandas as pd
from pytrends.request import TrendReq
import time
import numpy as np
import os
import warnings
warnings.filterwarnings("ignore")  # Ignore warnings for cleaner output

csv_path = 'STAD_algo/trends_data.csv'

def load_and_filter_companies(file_path='STAD_algo\iShares-Russell-3000-ETF_fund.csv',
                              market_cap_threshold_billion=100, # data is in thousands ($)
                              exclude_tickers=None):
    """
    Loads company data and filters out large/excluded companies.
        basically just removes the big tech companies that already have hype
        and are not suitable for the STAD algorithm.
        
    """
    df = pd.read_csv(file_path)

    # Convert Market Cap to numeric, handling potential errors
    #remove commas and dollar signs, convert to numeric
    df['Market Value'] = df['Market Value'].replace({'\$': '', ',': ''}, regex=True)

    #convert from thousands to billions
    df['Market Value'] = df['Market Value'].astype(float) / 1000000
    #print("Market Value in billions:", df['Market Value'].head())


    df['Market Value'] = pd.to_numeric(
        df['Market Value'], errors='coerce'
    )

    # Filter by market capitalization
    small_to_mid_cap_companies = df[
        df['Market Value'] < market_cap_threshold_billion
    ].copy()

    # make sure to only include companies with 'consumer discretionary' sector 
    # (this is the sector that the STAD algorithm is designed for) like fashion, retail, etc.
    small_to_mid_cap_companies = small_to_mid_cap_companies[
        small_to_mid_cap_companies['Sector'] == 'Consumer Discretionary'
    ]

    # clean up the DataFrame by removing unnecessary columns
    columns_to_keep = ['Ticker', 'Name', 'Market Value', 'Sector']
    small_to_mid_cap_companies = small_to_mid_cap_companies[columns_to_keep]

    # clean up the Names by removing keywords that are not useful for searching
    # e.g. 'Inc.', 'Corp.', 'LLC', etc.
    list_of_keywords_to_remove = ['Inc.','CORP','Corp.', 'LLC', 'Ltd.', 'Group', 'Company', 'COMPANIES', 'INC', 'CLASS A', 'CLASS B', 'CLASS C', 'HOLDINGS', 'HOLDING', 'LTD',' PLC', 'GMBH', 'S.A.', 'S.A']
    for keyword in list_of_keywords_to_remove:
        small_to_mid_cap_companies['Name'] = small_to_mid_cap_companies['Name'].str.replace(keyword, '', regex=False)

    # Remove any leading/trailing whitespace from the 'Name' column
    small_to_mid_cap_companies['Name'] = small_to_mid_cap_companies['Name'].str.strip()

    # Exclude specific companies or tickers if provided to optimize
    if os.path.exists(csv_path):
        existing_df = pd.read_csv(csv_path, index_col=0)
        already_queried_companies = list(existing_df.columns)
        # Filter out companies that are already in the trends_data.csv
        small_to_mid_cap_companies = small_to_mid_cap_companies[
            ~small_to_mid_cap_companies['Name'].isin(already_queried_companies)
        ]
        print("Companies already in trends_data.csv:", already_queried_companies)
    else:
        already_queried_companies = []
        print("No existing trends_data.csv found.")


    if exclude_tickers:
        small_to_mid_cap_companies = small_to_mid_cap_companies[
            ~small_to_mid_cap_companies['Ticker'].isin(exclude_tickers)
        ]
    # Reset index for the filtered DataFrame
    small_to_mid_cap_companies.reset_index(drop=True, inplace=True)

    print(f"Loaded {len(df)} companies. Filtered down to {len(small_to_mid_cap_companies)} smaller companies.")
    return small_to_mid_cap_companies



def fetch_google_trends_data(keywords, timeframe='today 12-m', geo='US'):
    """
    Fetches Google Trends 'interest over time' data for given keywords.

    """
    pytrend = TrendReq(hl='en-US', tz=360) # tz is timezone offset in minutes (e.g., 360 for CST)

    # Pytrends has a limit of 5 keywords per request. We'll fetch one by one.
    # For large lists, you might need to manage rate limits more carefully.
    all_trends_data = {}
    ct = len(keywords)
    print(f"Total keywords to fetch: {ct}, estimated time: {ct * 2} seconds")
    for keyword in keywords:
        try:
            pytrend.build_payload(kw_list=[keyword], cat=0, timeframe=timeframe, geo=geo)
            data = pytrend.interest_over_time()
            if not data.empty:
                all_trends_data[keyword] = data[keyword]
            time.sleep(2) # to be respectful of google's servers lol
            print(f"Fetched data for {keyword}...")
        except Exception as e:
            print(f"Could not fetch data for {keyword}: {e}")
            time.sleep(5) # Longer pause on error

    return pd.DataFrame(all_trends_data)





# Load and Filter Companies
# Define big tech and other hype tickers to exclude
## add excludes for hyped companies or ones that already have data for in trends_data.csv
EXCLUDE_TICKERS = ['AAPL', 'MSFT', 'GOOG', 'AMZN', 'TSLA', 'NVDA', 'HOOD', 'PLTR', 'AMC', 'GME', 'META', 'NFLX', 'BABA', 'UBER', 'LYFT']
SMALL_CAP_THRESHOLD = 100 # Billions USD

filtered_companies_df = load_and_filter_companies(
    'STAD_algo\iShares-Russell-3000-ETF_fund.csv',
    market_cap_threshold_billion=SMALL_CAP_THRESHOLD,
    exclude_tickers=EXCLUDE_TICKERS
)
print("\nFiltered Companies for Analysis:")
print(filtered_companies_df.head())


company_names_to_search = filtered_companies_df['Name'].tolist()
# to test this just limit the number of companies to search
test_keywords = company_names_to_search[:] # Adjust this for real runs
print(test_keywords)

print(f"\nFetching Google Trends data for {len(test_keywords)} companies...")
trends_df = fetch_google_trends_data(test_keywords, timeframe='today 12-m')
print("\nTrends Data Sample:")
print(trends_df.head())
# output the trends data to a csv file

# Check if the CSV already exists if so load it and append new data
if os.path.exists(csv_path):
    existing_df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
    # Align indices if needed
    trends_df.index = pd.to_datetime(trends_df.index)
    existing_df.index = pd.to_datetime(existing_df.index)
    # Only add columns that are not already in the file
    new_cols = [col for col in trends_df.columns if col not in existing_df.columns]
    if new_cols:
        combined_df = pd.concat([existing_df, trends_df[new_cols]], axis=1)
        combined_df.to_csv(csv_path, index=True)
    else:
        print("No new columns to append.")
else:
    # If file doesn't exist, just save the new DataFrame
    trends_df.to_csv(csv_path, index=True)