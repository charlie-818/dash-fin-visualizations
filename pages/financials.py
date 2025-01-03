import dash
from dash import dcc, html, callback
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import yfinance as yf
import logging
from datetime import datetime
from utils.data_processing import get_all_symbols

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Register the page
dash.register_page(__name__, path='/financials', name='Financial Statements')

def get_financial_data(symbol: str, statement_type: str) -> pd.DataFrame:
    """
    Fetch financial statement data for a given symbol.
    statement_type can be: 'income', 'balance', 'cash'
    """
    try:
        stock = yf.Ticker(symbol)
        if statement_type == 'income':
            return stock.income_stmt
        elif statement_type == 'balance':
            return stock.balance_sheet
        elif statement_type == 'cash':
            return stock.cashflow
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Error fetching {statement_type} statement for {symbol}: {e}")
        return pd.DataFrame()

def format_financial_value(value):
    """Format financial values for display."""
    if pd.isna(value):
        return "-"
    
    if not isinstance(value, (int, float)):
        return str(value)
    
    abs_value = abs(value)
    if abs_value >= 1e9:
        return f"{'$' if value >= 0 else '-$'}{abs_value/1e9:.2f}B"
    elif abs_value >= 1e6:
        return f"{'$' if value >= 0 else '-$'}{abs_value/1e6:.2f}M"
    elif abs_value >= 1e3:
        return f"{'$' if value >= 0 else '-$'}{abs_value/1e3:.2f}K"
    else:
        return f"{'$' if value >= 0 else '-$'}{abs_value:.2f}"

def create_financial_table(df: pd.DataFrame) -> dbc.Table:
    """Create a formatted table for financial statements."""
    if df.empty:
        return html.Div("No financial data available", style={'color': 'white'})
    
    # Format the DataFrame
    df = df.copy()
    
    # Convert column dates to formatted strings and create index
    formatted_dates = [d.strftime('%Y-%m-%d') if isinstance(d, pd.Timestamp) else str(d) for d in df.columns]
    df.columns = formatted_dates
    
    # Format all numeric values
    for col in df.columns:
        df[col] = df[col].apply(format_financial_value)
    
    # Reset index to make metrics names a column
    df = df.reset_index()
    df = df.rename(columns={'index': 'Metric'})
    
    return dbc.Table.from_dataframe(
        df,
        striped=True,
        bordered=True,
        hover=True,
        style={
            'color': 'white',
            'backgroundColor': '#383838',
            'overflowX': 'auto'
        }
    )

def create_key_metrics(symbol: str) -> html.Div:
    """Create a summary of key financial metrics."""
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        
        metrics = [
            ('Market Cap', info.get('marketCap', 'N/A')),
            ('P/E Ratio', info.get('trailingPE', 'N/A')),
            ('EPS (TTM)', info.get('trailingEps', 'N/A')),
            ('Revenue (TTM)', info.get('totalRevenue', 'N/A')),
            ('Profit Margin', info.get('profitMargins', 'N/A')),
            ('Operating Margin', info.get('operatingMargins', 'N/A')),
            ('ROE', info.get('returnOnEquity', 'N/A')),
            ('ROA', info.get('returnOnAssets', 'N/A')),
            ('Debt to Equity', info.get('debtToEquity', 'N/A')),
            ('Current Ratio', info.get('currentRatio', 'N/A'))
        ]
        
        return html.Div([
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6(metric, style={'color': 'white'}),
                            html.P(format_financial_value(value) if isinstance(value, (int, float)) 
                                  else str(value), style={'color': 'white'})
                        ])
                    ], style={'backgroundColor': '#383838', 'margin': '5px'})
                ], width=3) for metric, value in metrics
            ], className='g-0')
        ])
        
    except Exception as e:
        logger.error(f"Error creating key metrics for {symbol}: {e}")
        return html.Div("Error loading key metrics", style={'color': 'white'})

# Layout
layout = html.Div([
    # Control Panel
    dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.H4('Select Stock', style={'color': 'white'}),
                    dcc.Dropdown(
                        id='stock-selector-financials',
                        options=[{'label': symbol, 'value': symbol} for symbol in get_all_symbols()],
                        value=None,
                        placeholder='Select a stock symbol',
                        style={'color': 'black', 'backgroundColor': 'white'}
                    )
                ], width=6),
                dbc.Col([
                    html.H4('Statement Type', style={'color': 'white'}),
                    dcc.Dropdown(
                        id='statement-type',
                        options=[
                            {'label': 'Income Statement', 'value': 'income'},
                            {'label': 'Balance Sheet', 'value': 'balance'},
                            {'label': 'Cash Flow', 'value': 'cash'}
                        ],
                        value='income',
                        style={'color': 'black', 'backgroundColor': 'white'}
                    )
                ], width=6)
            ]),
            html.Div([
                dbc.Button(
                    'Refresh Data',
                    id='refresh-financials',
                    color='primary',
                    className='mt-3'
                )
            ])
        ])
    ], style={'backgroundColor': '#383838', 'marginBottom': '20px'}),
    
    # Status Message
    dbc.Alert(id='financials-status', is_open=False, duration=4000),
    
    # Key Metrics
    dbc.Card([
        dbc.CardBody([
            html.H4('Key Metrics', className='card-title', style={'color': 'white'}),
            html.Div(id='key-metrics')
        ])
    ], style={'backgroundColor': '#383838', 'marginBottom': '20px'}),
    
    # Financial Statements
    dbc.Card([
        dbc.CardBody([
            html.H4('Financial Statement', className='card-title', style={'color': 'white'}),
            html.Div(id='financial-statement-table', style={'overflowX': 'auto'})
        ])
    ], style={'backgroundColor': '#383838'})
    
], style={'backgroundColor': '#2E2E2E', 'minHeight': '100vh', 'padding': '20px'})

@callback(
    [Output('financial-statement-table', 'children'),
     Output('key-metrics', 'children'),
     Output('financials-status', 'children'),
     Output('financials-status', 'is_open'),
     Output('financials-status', 'color')],
    [Input('stock-selector-financials', 'value'),
     Input('statement-type', 'value'),
     Input('refresh-financials', 'n_clicks')],
    prevent_initial_call=True
)
def update_financials(symbol, statement_type, n_clicks):
    """Update financial statement information."""
    if not symbol or not statement_type:
        return None, None, "", False, "primary"
    
    try:
        # Fetch financial data
        financial_df = get_financial_data(symbol, statement_type)
        
        if financial_df.empty:
            return (
                html.Div("No financial data available", style={'color': 'white'}),
                None,
                f"No financial data available for {symbol}",
                True,
                "warning"
            )
        
        # Create financial table
        financial_table = create_financial_table(financial_df)
        
        # Create key metrics
        metrics = create_key_metrics(symbol)
        
        return (
            financial_table,
            metrics,
            f"Successfully loaded financial data for {symbol}",
            True,
            "success"
        )
        
    except Exception as e:
        logger.error(f"Error updating financials: {e}")
        return (
            None,
            None,
            f"Error loading financial data: {str(e)}",
            True,
            "danger"
        )