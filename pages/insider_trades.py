import dash
from dash import dcc, html, callback
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import yfinance as yf
import logging
from datetime import datetime, timedelta
from utils.data_manager import data_manager
from utils.data_processing import sectors, get_all_symbols

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Register the page
dash.register_page(__name__, path='/insider-trades', name='Insider Trading')

def get_insider_trades(symbol: str) -> pd.DataFrame:
    """Fetch insider trading data for a given symbol."""
    try:
        stock = yf.Ticker(symbol)
        insider_trades = stock.insider_trades
        if insider_trades is not None:
            insider_trades['Symbol'] = symbol
            return insider_trades
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Error fetching insider trades for {symbol}: {e}")
        return pd.DataFrame()

def create_insider_table(df: pd.DataFrame) -> dbc.Table:
    """Create a formatted table for insider trades."""
    if df.empty:
        return html.Div("No insider trading data available", style={'color': 'white'})
    
    # Format the DataFrame
    df = df.copy()
    df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
    df['Value'] = df['Value'].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "")
    df['Shares'] = df['Shares'].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else "")
    
    return dbc.Table.from_dataframe(
        df,
        striped=True,
        bordered=True,
        hover=True,
        style={
            'color': 'white',
            'backgroundColor': '#383838'
        }
    )

# Layout
layout = html.Div([
    
    # Control Panel
    dbc.Card([
        dbc.CardBody([
            html.H4('Select Stock', className='card-title', style={'color': 'white'}),
            dcc.Dropdown(
                id='stock-selector',
                options=[{'label': symbol, 'value': symbol} for symbol in get_all_symbols()],
                value=None,
                placeholder='Select a stock symbol',
                style={
                    'color': 'black',
                    'backgroundColor': 'white',
                    'marginBottom': '10px'
                }
            ),
            dbc.Button(
                'Refresh Data',
                id='refresh-insider-data',
                color='primary',
                className='me-2'
            )
        ])
    ], style={'backgroundColor': '#383838', 'marginBottom': '20px'}),
    
    # Status Message
    dbc.Alert(id='insider-status', is_open=False, duration=4000),
    
    # Summary Card
    dbc.Card([
        dbc.CardBody([
            html.H4('Recent Insider Activity', className='card-title', style={'color': 'white'}),
            html.Div(id='insider-summary', style={'color': 'white'})
        ])
    ], style={'backgroundColor': '#383838', 'marginBottom': '20px'}),
    
    # Insider Trades Table
    dbc.Card([
        dbc.CardBody([
            html.H4('Detailed Insider Trades', className='card-title', style={'color': 'white'}),
            html.Div(id='insider-trades-table')
        ])
    ], style={'backgroundColor': '#383838'})
    
], style={'backgroundColor': '#2E2E2E', 'minHeight': '100vh', 'padding': '20px'})

@callback(
    [Output('insider-trades-table', 'children'),
     Output('insider-summary', 'children'),
     Output('insider-status', 'children'),
     Output('insider-status', 'is_open'),
     Output('insider-status', 'color')],
    [Input('stock-selector', 'value'),
     Input('refresh-insider-data', 'n_clicks')],
    prevent_initial_call=True
)
def update_insider_trades(symbol, n_clicks):
    """Update insider trading information."""
    if not symbol:
        return None, "", "", False, "primary"
    
    try:
        # Fetch insider trades
        trades_df = get_insider_trades(symbol)
        
        if trades_df.empty:
            return (
                html.Div("No insider trading data available", style={'color': 'white'}),
                "No recent insider activity to display",
                f"No insider trading data available for {symbol}",
                True,
                "warning"
            )
        
        # Create summary
        recent_trades = len(trades_df)
        total_value = trades_df['Value'].sum()
        latest_trade = trades_df['Date'].max()
        
        summary = f"""
        **Last 6 Months Summary:**
        - Total Transactions: {recent_trades}
        - Total Value: ${total_value:,.2f}
        - Latest Trade: {latest_trade.strftime('%Y-%m-%d')}
        """
        
        # Create table
        trades_table = create_insider_table(trades_df)
        
        return (
            trades_table,
            dcc.Markdown(summary),
            f"Successfully loaded insider trading data for {symbol}",
            True,
            "success"
        )
        
    except Exception as e:
        logger.error(f"Error updating insider trades: {e}")
        return (
            None,
            "",
            f"Error loading insider trading data: {str(e)}",
            True,
            "danger"
        )