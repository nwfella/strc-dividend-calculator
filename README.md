# STRC Dividend Scenario Calculator

STRC (Strategy Inc, NASDAQ) preferred-stock dividend dashboard: historical price vs the $100 par peg, full dividend payment history, and bearish / neutral / bullish future scenarios — dividend income, yield-on-cost, and total return projections tied to your capital.

**Live:** https://nwfella.github.io/strc-dividend-calculator/

## Refresh the data

```bash
python scripts/update_data.py   # fetches price + dividend history from Yahoo Finance, merges, bakes into index.html
```

Data is baked into the page statically (no runtime API calls), so it works on any network. Add manual dividend/price corrections to `data/strc_data.json` — they survive refreshes (matched by date).

## Disclaimer

Scenario projections are modeled estimates, not forecasts or investment advice. STRC is a variable-rate preferred — future dividends are not guaranteed.
