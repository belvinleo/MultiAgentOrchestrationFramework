"""
finance_api.py
--------------
Real market data tool for the Finance Department.
Uses yfinance for NSE/BSE/global stocks — completely free, no API key needed.
"""

import yfinance as yf
from datetime import datetime


class FinanceAPI:
    """
    Fetches live and historical market data.
    NSE stocks use the suffix .NS (e.g., RELIANCE.NS)
    BSE stocks use the suffix .BO (e.g., RELIANCE.BO)
    Global stocks use plain ticker (e.g., AAPL, TSLA)
    """

    def get_stock_price(self, ticker: str) -> dict:
        """
        Get current price and basic info for a stock.

        Parameters:
            ticker : e.g. 'RELIANCE.NS', 'TCS.NS', 'AAPL'

        Returns:
            dict with price, change, volume, market cap
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            # Extract key fields safely
            current_price = (
                info.get("currentPrice")
                or info.get("regularMarketPrice")
                or info.get("navPrice")
            )

            previous_close = info.get("previousClose") or info.get("regularMarketPreviousClose")
            change = None
            change_pct = None

            if current_price and previous_close:
                change = round(current_price - previous_close, 2)
                change_pct = round((change / previous_close) * 100, 2)

            return {
                "ticker": ticker,
                "name": info.get("longName") or info.get("shortName", ticker),
                "current_price": current_price,
                "previous_close": previous_close,
                "change": change,
                "change_pct": change_pct,
                "volume": info.get("volume"),
                "market_cap": info.get("marketCap"),
                "currency": info.get("currency", "INR"),
                "sector": info.get("sector", "N/A"),
                "timestamp": str(datetime.now()),
            }
        except Exception as e:
            return {"ticker": ticker, "error": str(e)}

    def get_index(self, index: str = "nifty") -> dict:
        """
        Get current value of major indices.

        Supported: 'nifty', 'sensex', 'banknifty', 'sp500', 'nasdaq'
        """
        index_map = {
            "nifty":     "^NSEI",
            "sensex":    "^BSESN",
            "banknifty": "^NSEBANK",
            "sp500":     "^GSPC",
            "nasdaq":    "^IXIC",
            "dowjones":  "^DJI",
        }

        ticker = index_map.get(index.lower(), index)
        return self.get_stock_price(ticker)

    def get_multiple_stocks(self, tickers: list) -> list:
        """
        Fetch data for multiple stocks at once.

        Parameters:
            tickers : list of ticker strings
        """
        return [self.get_stock_price(t) for t in tickers]

    def get_top_gainers_losers(self) -> dict:
        """
        Returns a curated snapshot of key Indian market movers.
        Uses a fixed watchlist of major NSE stocks.
        """
        watchlist = [
            "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS",
            "INFY.NS", "ICICIBANK.NS", "SBIN.NS",
            "BHARTIARTL.NS", "WIPRO.NS", "LT.NS", "AXISBANK.NS"
        ]

        results = self.get_multiple_stocks(watchlist)
        valid = [r for r in results if "error" not in r and r.get("change_pct") is not None]

        gainers = sorted(valid, key=lambda x: x["change_pct"], reverse=True)[:3]
        losers = sorted(valid, key=lambda x: x["change_pct"])[:3]

        return {"gainers": gainers, "losers": losers}

    def get_portfolio_summary(self, holdings: dict) -> dict:
        """
        Calculate portfolio value from holdings.

        Parameters:
            holdings : dict of {ticker: quantity}
            e.g. {"RELIANCE.NS": 10, "TCS.NS": 5}

        Returns:
            dict with total value and per-stock breakdown
        """
        breakdown = []
        total_value = 0

        for ticker, qty in holdings.items():
            data = self.get_stock_price(ticker)
            if "error" not in data and data.get("current_price"):
                value = data["current_price"] * qty
                total_value += value
                breakdown.append({
                    "ticker": ticker,
                    "name": data["name"],
                    "qty": qty,
                    "price": data["current_price"],
                    "value": round(value, 2),
                    "change_pct": data.get("change_pct"),
                })

        return {
            "total_value": round(total_value, 2),
            "currency": "INR",
            "holdings": breakdown,
            "timestamp": str(datetime.now()),
        }

    def format_for_agent(self, data: dict) -> str:
        """
        Convert raw market data into clean text an agent can use.
        """
        if "error" in data:
            return f"Could not fetch data for {data['ticker']}: {data['error']}"

        lines = []
        name = data.get("name", data["ticker"])
        price = data.get("current_price")
        change = data.get("change")
        change_pct = data.get("change_pct")
        currency = data.get("currency", "INR")

        if price:
            direction = "▲" if (change or 0) >= 0 else "▼"
            lines.append(f"{name} ({data['ticker']})")
            lines.append(f"Price: {currency} {price:,.2f}")
            if change is not None:
                lines.append(f"Change: {direction} {abs(change):,.2f} ({change_pct:+.2f}%)")

        return "\n".join(lines)