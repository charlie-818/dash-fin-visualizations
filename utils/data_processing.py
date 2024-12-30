import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import os
import json
import logging
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create a data directory if it doesn't exist
DATA_DIR = "data"
CACHE_INFO_FILE = os.path.join(DATA_DIR, "cache_info.json")
os.makedirs(DATA_DIR, exist_ok=True)

# Define sectors and their corresponding stock symbols
sectors: Dict[str, List[str]] = {
    'Energy - Fossil Fuels': [
        'COP',  # ConocoPhillips
        'EOG',  # EOG Resources
        'FANG', # Diamondback Energy
        'HES',  # Hess Corporation
        'OXY',  # Occidental Petroleum
        'CNQ',  # Canadian Natural Resources
        'TPL',  # Texas Pacific Land
        'CEO'   # CNOOC Limited
    ],
    'Renewable Energy': [
        'NEE',  # NextEra Energy
        'FSLR', # First Solar
        'BEP',  # Brookfield Renewable Partners
        'ENPH', # Enphase Energy
        'CEG',  # Constellation Energy
        'CLNE', # Clean Energy Fuels
        'IBE',  # Iberdrola
        'ORA',  # Ormat Technologies
        'RNW',  # ReNew Energy Global
        'BEPC', # Brookfield Renewable Corporation
        'INE',  # Innergex Renewable Energy
        'PIF',  # Polaris Renewable Energy
        'ADNA', # Adani Green Energy
        'GAIL', # GAIL
        'NTPC', # NTPC
        'JSW'   # JSW Energy
    ],
    'Uranium': [
        'CCJ',  # Cameco Corporation
        'NXE',  # NexGen Energy
        'UEC',  # Uranium Energy Corp
        'DNN',  # Denison Mines
        'LEU',  # Centrus Energy
        'UUUU', # Energy Fuels
        'EU',   # enCore Energy
        'URG'   # Ur-Energy
    ],
    'Chemicals': [
        'DOW',  # Dow Inc
        'LYB',  # LyondellBasell
        'EMN',  # Eastman Chemical
        'CE',   # Celanese
        'BASFY', # BASF
        'DD',   # DuPont
        'HUN',  # Huntsman
        'TROX', # Tronox
        'BAK',  # Braskem
        'WLK',  # Westlake
        'APD'   # Air Products and Chemicals
    ],
    'Transportation': [
        'GE',   # General Electric
        'UNP',  # Union Pacific
        'UPS',  # United Parcel Service
        'CP',   # Canadian Pacific Kansas City
        'FDX',  # FedEx
        'CNI',  # Canadian National Railway
        'CSX',  # CSX
        'NSC',  # Norfolk Southern
        'DAL',  # Delta Air Lines
        'ODFL', # Old Dominion Freight
        'JBHT'  # J.B. Hunt Transport
    ],
    'Automobiles & Auto Parts': [
        'GPC',  # Genuine Parts Company
        'APTV', # Aptiv
        'MGA',  # Magna International
        'LKQ',  # LKQ Corporation
        'F',    # Ford Motor
        'HMC',  # Honda Motor
        'TM',   # Toyota Motor
        'TSLA', # Tesla
        'GM',   # General Motors
        'STLA'  # Stellantis
    ],
    'Healthcare Services': [
        'HCSG', # Healthcare Services Group
        'AMN',  # AMN Healthcare Services
        'HCA',  # HCA Healthcare
        'CVS'   # CVS Health Corporation
    ],
    'Software & IT Services': [
        'MSFT', # Microsoft
        'GOOGL', # Alphabet A
        'GOOG', # Alphabet C
        'META', # Meta Platforms
        'V',    # Visa A
        'MA',   # Mastercard
        'TCEHY', # Tencent ADR
        'ORCL', # Oracle
        'NFLX', # Netflix
        'CRM',  # Salesforce
        'SAP',  # SAP
        'NOW',  # ServiceNow
        'ACN',  # Accenture
        'IBM',  # IBM
        'BABA', # Alibaba ADR
        'ADBE', # Adobe
        'PLTR', # Palantir
        'SHOP', # Shopify
        'UBER', # Uber
        'PANW', # Palo Alto Networks
        'ADP'   # ADP
    ],
    'Telecommunications': [
        'T',    # AT&T
        'TMUS', # T-Mobile
        'VZ',   # Verizon
        'VOD',  # Vodafone
        'RCI',  # Rogers Communications
        'SFTBY', # SoftBank
        'CHL',  # China Mobile
        'CHT',  # Chunghwa Telecom
        'TLSYY' # Telstra Corporation
    ],
    'Utilities': [
        'AES',  # AES Corporation
        'LNT',  # Alliant Energy
        'AEE',  # Ameren Corporation
        'AEP',  # American Electric Power
        'D',    # Dominion Energy
        'ATO',  # Atmos Energy
        'CMS',  # CMS Energy
        'CNP',  # CenterPoint Energy
        'XEL'   # Xcel Energy
    ],
    'Real Estate': [
        'PLD',  # Prologis
        'AMT',  # American Tower
        'EQIX', # Equinix
        'WELL', # Welltower
        'SPG',  # Simon Property Group
        'DLR',  # Digital Realty Trust
        'AVB',  # AvalonBay Communities
        'CSGP', # CoStar Group
        'EQR',  # Equity Residential
        'VICI'  # VICI Properties
    ]
}

# Optionally, compile a list of all symbols for convenience
symbols: List[str] = [symbol for sector_symbols in sectors.values() for symbol in sector_symbols]

# Define maximum retry attempts for downloading missing tickers
MAX_RETRY_ATTEMPTS = 3

def get_cache_info() -> Dict[str, Any]:
    """Get information about cached data"""
    if os.path.exists(CACHE_INFO_FILE):
        with open(CACHE_INFO_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                logger.warning(f"{CACHE_INFO_FILE} is empty or contains invalid JSON. Recreating.")
                return {}
    return {}

def update_cache_info(period: str, last_updated: str) -> None:
    """Update the cache information"""
    cache_info = get_cache_info()
    cache_info[period] = last_updated
    with open(CACHE_INFO_FILE, 'w') as f:
        json.dump(cache_info, f)

def should_update_data(period: str) -> bool:
    """Check if data should be updated based on period"""
    cache_info = get_cache_info()
    if period not in cache_info:
        return True
    
    last_updated = datetime.strptime(cache_info[period], "%Y-%m-%d")
    current_time = datetime.now()
    
    # Define update frequencies based on period
    update_frequencies = {
        '1mo': timedelta(days=1),    # Update daily
        '3mo': timedelta(days=1),    # Update daily
        '6mo': timedelta(days=1),    # Update daily
        '1y': timedelta(days=1),     # Update daily
        '5y': timedelta(days=7),     # Update weekly
        'max': timedelta(days=30),   # Update monthly
    }
    
    return current_time - last_updated > update_frequencies.get(period, timedelta(days=1))

def get_csv_filename(symbol: str, period: str) -> str:
    """Generate CSV filename for a symbol and period"""
    safe_symbol = symbol.replace('/', '_')  # Ensure filename safety
    return os.path.join(DATA_DIR, f"{safe_symbol}_{period}.csv")

def download_ticker_data(symbol: str, period: str) -> pd.DataFrame:
    """
    Download data for a single ticker.

    Args:
        symbol (str): Stock symbol.
        period (str): Time period for data.

    Returns:
        pd.DataFrame: DataFrame containing ticker data.
    """
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        if df.empty:
            logger.warning(f"No data available for {symbol} during period {period}.")
            return pd.DataFrame()
        df['Pct_Change'] = df['Close'].pct_change() * 100
        logger.info(f"Successfully downloaded data for {symbol}.")
        return df
    except Exception as e:
        logger.error(f"Error downloading data for {symbol}: {e}")
        return pd.DataFrame()

def get_segmented_data(period: str = "1mo") -> Dict[str, pd.DataFrame]:
    """
    Get stock data with caching mechanism, including attempts to download missing tickers.

    Args:
        period (str, optional): The time period for which to fetch the stock data. Defaults to "1mo".

    Returns:
        Dict[str, pd.DataFrame]: Dictionary containing stock data for each symbol.
    """
    logger.info(f"Fetching data for period: {period}")

    all_data: Dict[str, pd.DataFrame] = {}
    update_needed = should_update_data(period)

    for sector, sector_symbols in sectors.items():
        for symbol in sector_symbols:
            csv_file = get_csv_filename(symbol, period)

            # Attempt to load from CSV first
            if os.path.exists(csv_file) and not update_needed:
                try:
                    df = pd.read_csv(csv_file)
                    df['Date'] = pd.to_datetime(df['Date'])
                    df.set_index('Date', inplace=True)
                    if 'Pct_Change' not in df.columns:
                        logger.warning(f"'Pct_Change' column missing in cached data for {symbol}. Recalculating.")
                        df['Pct_Change'] = df['Close'].pct_change() * 100
                        df.to_csv(csv_file)
                    all_data[symbol] = df
                    logger.info(f"Loaded cached data for {symbol}.")
                    continue
                except Exception as e:
                    logger.error(f"Error reading cached data for {symbol}: {e}")

            # If cache is not present or update is needed, attempt to download
            for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
                logger.info(f"Attempt {attempt} to download data for {symbol}.")
                df = download_ticker_data(symbol, period)
                if not df.empty:
                    # Save to CSV
                    try:
                        df.to_csv(csv_file)
                        all_data[symbol] = df
                        logger.info(f"Downloaded and cached data for {symbol} on attempt {attempt}.")
                        break  # Exit retry loop on success
                    except Exception as e:
                        logger.error(f"Error saving data for {symbol} to CSV: {e}")
                else:
                    logger.warning(f"Attempt {attempt} failed to download data for {symbol}.")

                if attempt == MAX_RETRY_ATTEMPTS:
                    logger.error(f"Failed to download data for {symbol} after {MAX_RETRY_ATTEMPTS} attempts.")
    
    if update_needed and all_data:
        update_cache_info(period, datetime.now().strftime("%Y-%m-%d"))
        logger.info(f"Updated cache for period: {period}.")
    elif not update_needed:
        logger.info(f"Using cached data for period: {period}.")
    else:
        logger.warning(f"No data was fetched or loaded for period: {period}.")

    return all_data