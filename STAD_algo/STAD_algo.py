import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

def detect_anomalies(trends_df, window_size=7, spike_threshold_percent=50, ma_deviation_threshold=2):
    """
    Detects search traffic anomalies (spikes or rapid increases) ONLY if the value is >=80 in the last 2 weeks.

    Args:
        trends_df (pandas.DataFrame): DataFrame of Google Trends data.
        window_size (int): Window for moving average (e.g., 7 for weekly average).
        spike_threshold_percent (int): Percentage increase to consider a spike.
        ma_deviation_threshold (int): How many standard deviations above the MA to consider an anomaly.

    Returns:
        dict: A dictionary where keys are company names and values are detected anomaly details.
    """
    anomalies = {}
    cutoff_date = datetime.now() - timedelta(days=14)

    for company in trends_df.columns:
        series = trends_df[company].dropna()
        if series.empty or len(series) < window_size + 1:
            continue # Not enough data

        # Calculate daily percentage change
        daily_change = series.pct_change() * 100

        # Calculate moving average and standard deviation
        moving_avg = series.rolling(window=window_size).mean()
        moving_std = series.rolling(window=window_size).std()

        # Iterate through the series to find anomalies
        for i in range(window_size, len(series)):
            current_value = series.iloc[i]
            previous_value = series.iloc[i-1]
            current_date = series.index[i]
            # Only consider anomalies in the last 2 weeks and value >= 80
            if current_date < cutoff_date or current_value < 80:
                continue

            date_str = current_date.strftime('%Y-%m-%d')

            # Anomaly 1: Sudden Spike (large percentage increase)
            if not np.isnan(daily_change.iloc[i]) and daily_change.iloc[i] > spike_threshold_percent:
                if previous_value == 0:
                    window_vals = series.iloc[i-window_size:i]
                    nonzero_window_vals = window_vals[window_vals != 0]
                    if len(nonzero_window_vals) > 0:
                        denom = nonzero_window_vals.mean()
                    else:
                        denom = 1
                else:
                    denom = previous_value

                change_percent = ((current_value - previous_value) / denom) * 100

                anomalies.setdefault(company, []).append({
                    'date': date_str,
                    'type': 'Sudden Spike (Percent Change)',
                    'current_value': current_value,
                    'previous_value': previous_value,
                    'change_percent': change_percent
                })

            # Anomaly 2: Rapidly Increasing (above moving average + std dev)
            if not np.isnan(moving_avg.iloc[i]) and not np.isnan(moving_std.iloc[i]):
                if moving_std.iloc[i] > 0:
                    if (current_value - moving_avg.iloc[i]) / moving_std.iloc[i] > ma_deviation_threshold:
                        anomalies.setdefault(company, []).append({
                            'date': date_str,
                            'type': 'Rapidly Increasing (MA Deviation)',
                            'current_value': current_value,
                            'moving_average': moving_avg.iloc[i],
                            'deviation': f"{(current_value - moving_avg.iloc[i]) / moving_std.iloc[i]:.2f} std dev"
                        })
    return anomalies

# import trends data
def load_trends_data(csv_path):
    """
    Load Google Trends data from a CSV file.

    Args:
        csv_path (str): Path to the CSV file containing trends data.

    Returns:
        pandas.DataFrame: DataFrame containing the trends data.
    """
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
        return df
    else:
        raise FileNotFoundError(f"CSV file not found at {csv_path}")

trends_data = load_trends_data('STAD_algo/trends_data.csv')
# Detect anomalies in the trends data
anomalies = detect_anomalies(trends_data, window_size=7, spike_threshold_percent=50, ma_deviation_threshold=2)
# Print detected anomalies from the last 2 weeks only
print("Anomaly Detection Results:")
print("=====================================")
print(f"Total anomalies Analyzed: {len(anomalies.keys())}")
if anomalies:
    cutoff_date = datetime.now() - timedelta(days=14)
    for company, alerts in anomalies.items():
        # Filter alerts for the last 2 weeks
        recent_alerts = [
            alert for alert in alerts
            if datetime.strptime(alert['date'], "%Y-%m-%d") >= cutoff_date
        ]
        if recent_alerts:
            print(f"Detected anomalies for {company}:")
            for alert in recent_alerts:
                msg = f" - {alert['date']}: {alert['type']} (Current: {alert['current_value']}"
                if 'previous_value' in alert:
                    msg += f", Previous: {alert['previous_value']}"
                if 'change_percent' in alert:
                    msg += f", Change: {alert['change_percent']}"
                if 'moving_average' in alert:
                    msg += f", MA: {alert['moving_average']:.2f}"
                if 'deviation' in alert:
                    msg += f", Deviation: {alert['deviation']}"
                msg += ")"
                print(msg)
else:
    print("No anomalies detected in the trends data.")