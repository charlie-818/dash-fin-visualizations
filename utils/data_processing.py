from .data_manager import data_manager
import pandas as pd
import logging
import yfinance as yf
from typing import Dict, Optional
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger(__name__)

# Define all stock symbols by sector
sectors = {
    'Technology': ['AAPL', 'MSFT', 'NVDA', 'AVGO', 'CSCO'],
    'Healthcare': ['JNJ', 'UNH', 'PFE', 'MRK', 'ABT'],
    'Financials': ['JPM', 'BAC', 'WFC', 'GS', 'MS'],
    'Consumer Discretionary': ['AMZN', 'TSLA', 'HD', 'MCD', 'NKE'],
    'Consumer Staples': ['PG', 'KO', 'PEP', 'WMT', 'COST'],
    'Industrials': ['UPS', 'HON', 'CAT', 'BA', 'GE'],
    'Energy': ['XOM', 'CVX', 'COP', 'SLB', 'EOG'],
    'Utilities': ['NEE', 'DUK', 'SO', 'D', 'AEP'],
    'Materials': ['LIN', 'APD', 'ECL', 'DD', 'NEM'],
    'Real Estate': ['AMT', 'PLD', 'CCI', 'EQIX', 'PSA'],
    'Communication Services': ['GOOGL', 'META', 'NFLX', 'TMUS', 'VZ']
}

def get_all_symbols() -> list:
    """Get all unique symbols from sectors."""
    return list(set([symbol for symbols in sectors.values() for symbol in symbols]))

def get_segmented_data(period: str = "1mo") -> Dict[str, pd.DataFrame]:
    """Get stock data for all symbols, downloading if necessary."""
    try:
        # Get all symbols
        symbols = get_all_symbols()
        
        # Try to get data from cache first
        stock_data = data_manager.get_stock_data(symbols, period)
        
        # If no data in cache or cache is empty, download fresh data
        if not stock_data:
            logger.info("No cached data found. Downloading fresh data...")
            stock_data = download_fresh_data(symbols, period)
            
        return stock_data
    
    except Exception as e:
        logger.error(f"Error in get_segmented_data: {e}")
        return {}

def download_fresh_data(symbols: list, period: str = "1mo") -> Dict[str, pd.DataFrame]:
    """Download fresh stock data for given symbols."""
    try:
        all_data = {}
        for symbol in symbols:
            try:
                # Download data
                data = yf.download(symbol, period=period, progress=False)
                if not data.empty:
                    # Add symbol column
                    data['Symbol'] = symbol
                    # Calculate percentage change
                    data['Pct_Change'] = data['Adj Close'].pct_change()
                    # Reset index to make Date a column
                    data.reset_index(inplace=True)
                    all_data[symbol] = data
                    
            except Exception as e:
                logger.error(f"Error downloading data for {symbol}: {e}")
                continue
                
        # Cache the downloaded data
        if all_data:
            combined_data = pd.concat([df for df in all_data.values()], ignore_index=True)
            combined_data['timestamp'] = datetime.now()
            data_manager._data = combined_data
            data_manager._save_cache(combined_data)
            
        return all_data
    
    except Exception as e:
        logger.error(f"Error in download_fresh_data: {e}")
        return {}

def get_sector_data(period: str = "1mo") -> Dict[str, pd.DataFrame]:
    """Get aggregated sector data."""
    try:
        stock_data = get_segmented_data(period)
        if not stock_data:
            return {}
        
        sector_data = {}
        for sector, symbols in sectors.items():
            sector_returns = pd.DataFrame()
            for symbol in symbols:
                if symbol in stock_data:
                    data = stock_data[symbol]
                    if not data.empty and 'Pct_Change' in data.columns:
                        sector_returns[symbol] = data['Pct_Change']
            
            if not sector_returns.empty:
                # Calculate sector average
                sector_returns[sector] = sector_returns.mean(axis=1)
                sector_returns['Date'] = pd.to_datetime(data.index)
                sector_data[sector] = sector_returns
                
        return sector_data
    
    except Exception as e:
        logger.error(f"Error in get_sector_data: {e}")
        return {}

def calculate_sector_averages(sector_data):
    """
    Calculate average percentage changes for each sector.
    
    Args:
        sector_data (dict): Dictionary containing sector data
        
    Returns:
        pd.DataFrame: DataFrame with sector averages
    """
    try:
        averages = {}
        for sector, df in sector_data.items():
            if not df.empty and sector in df.columns:
                avg = df[sector].mean()
                averages[sector] = avg
                logger.info(f"Sector: {sector}, Average Pct Change: {avg}")
                
        return pd.DataFrame(list(averages.items()), columns=['Sector', 'Average_Change'])
        
    except Exception as e:
        logger.error(f"Error in calculate_sector_averages: {e}")
        return pd.DataFrame()