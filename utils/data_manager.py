import pandas as pd
import yfinance as yf
import logging
from datetime import datetime, timedelta
import os
from typing import Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataManager:
    def __init__(self, cache_file: str = 'assets/stock_data_cache.csv'):
        self.cache_file = cache_file
        self.cache_duration = timedelta(hours=24)
        self._data = None
        self.required_columns = [
            'Date',
            'Adj Close',
            'Close',
            'High',
            'Low',
            'Open',
            'Volume',
            'Symbol',
            'Pct_Change'
        ]
        
    def _process_stock_data(self, stock_data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Process individual stock data to ensure correct format."""
        try:
            # Reset index to make Date a column if it's in the index
            if isinstance(stock_data.index, pd.DatetimeIndex):
                stock_data = stock_data.reset_index()

            # Ensure all required columns exist
            stock_data['Symbol'] = symbol
            stock_data['Pct_Change'] = stock_data['Adj Close'].pct_change()

            # Select and order only the required columns
            processed_data = stock_data[self.required_columns].copy()
            
            # Ensure Date is datetime
            processed_data['Date'] = pd.to_datetime(processed_data['Date'])
            
            return processed_data

        except Exception as e:
            logger.error(f"Error processing data for {symbol}: {e}")
            return pd.DataFrame()

    def get_stock_data(self, symbols: list, period: str = '1y') -> Dict[str, pd.DataFrame]:
        """Get stock data either from cache or Yahoo Finance."""
        try:
            # Try to load cache if data is not already loaded
            if self._data is None:
                self._data = self._load_cache()
            
            # Check if cache is valid
            cache_is_valid = False
            if self._data is not None and not self._data.empty:
                if 'timestamp' in self._data.columns:
                    last_update = pd.to_datetime(self._data['timestamp'].iloc[0])
                    cache_is_valid = (datetime.now() - last_update) < self.cache_duration

            # Fetch new data if cache is invalid or empty
            if not cache_is_valid:
                logger.info("Fetching fresh data from Yahoo Finance")
                all_stock_data = []

                for symbol in symbols:
                    try:
                        stock = yf.download(symbol, period=period, progress=False)
                        if not stock.empty:
                            processed_stock = self._process_stock_data(stock, symbol)
                            if not processed_stock.empty:
                                all_stock_data.append(processed_stock)

                    except Exception as e:
                        logger.error(f"Error fetching data for {symbol}: {e}")
                        continue

                if all_stock_data:
                    combined_data = pd.concat(all_stock_data, ignore_index=True)
                    combined_data['timestamp'] = datetime.now()
                    self._data = combined_data
                    self._save_cache(combined_data)
                else:
                    logger.error("No data could be fetched")
                    return {}

            return self._process_data(self._data.copy(), symbols)

        except Exception as e:
            logger.error(f"Error in get_stock_data: {e}")
            return {}

    def _save_cache(self, data: pd.DataFrame):
        """Save data to cache file."""
        try:
            if data is not None:
                data.to_csv(self.cache_file, index=False)
        except Exception as e:
            logger.error(f"Error saving cache: {e}")

    def _load_cache(self) -> Optional[pd.DataFrame]:
        """Load data from cache file."""
        try:
            if os.path.exists(self.cache_file):
                df = pd.read_csv(self.cache_file, low_memory=False)
                df['Date'] = pd.to_datetime(df['Date'])
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                return df
            return None
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
            return None

    def _process_data(self, df: pd.DataFrame, symbols: list) -> Dict[str, pd.DataFrame]:
        """Process the data into individual symbol dataframes."""
        try:
            processed_data = {}
            for symbol in symbols:
                symbol_data = df[df['Symbol'] == symbol].copy()
                if not symbol_data.empty:
                    # Calculate percentage change for Adj Close only
                    symbol_data['Pct_Change'] = symbol_data['Adj Close'].pct_change()
                    
                    # Set the date as index
                    symbol_data.set_index('Date', inplace=True)
                    
                    processed_data[symbol] = symbol_data
                    
            return processed_data
            
        except Exception as e:
            logger.error(f"Error processing data: {e}")
            return {}

    def clear_cache(self):
        """Clear the cache file and memory cache."""
        try:
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
            self._data = None
            logger.info("Cache cleared successfully")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")

# Create a singleton instance
data_manager = DataManager()