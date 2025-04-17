# Trend Strategy Using ADX and Donchian Channels

## Summary

This strategy uses two indicators — **ADX** and **Donchian Channels** — to identify trends in the market.

### Donchian Channels

The Donchian Channel is a simple technical indicator. It creates two bands:

- **Upper Band**: highest high over a lookback period  
- **Lower Band**: lowest low over a lookback period  

If the stock trades outside these bands, it signals a possible trend.
But this is clearly not enough on its own.

### ADX (Average Directional Index)

The ADX measures the **strength** of a trend (not the direction). It uses recent price data and gives values:

- **ADX > 25**: a strong trend is likely forming

---

## Strategy Logic

- **Buy** when:
  - Price > Upper Donchian Band  
  - ADX > 25  

- **Short** when:
  - Price < Lower Donchian Band  
  - ADX > 25  

- **Otherwise**:  
  Stay out of the market and invest in the **S&P 500**, to match our baseline's performance.

---

## Contact

For any further questions, contact me:  
📧 `ezra_k234@tamu.edu`
