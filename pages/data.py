import dash
from dash import dcc, html, callback
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
from utils.data_manager import data_manager
from utils.data_processing import sectors, get_all_symbols
import pandas as pd
import logging
from datetime import datetime, timedelta
import plotly.graph_objects as go

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Register the page
dash.register_page(__name__, path='/data', name='Data Management')

def create_data_summary():
    """Creates a summary of the loaded data."""
    try:
        if data_manager._data is None:
            data_manager._data = data_manager._load_cache()
            
        if data_manager._data is None:
            return "No cached data available", []
            
        # Get basic statistics
        total_symbols = data_manager._data['Symbol'].nunique()
        earliest_date = pd.to_datetime(data_manager._data['Date']).min()
        latest_date = pd.to_datetime(data_manager._data['Date']).max()
        total_data_points = len(data_manager._data)
        
        # Handle timestamp column safely
        if 'timestamp' in data_manager._data.columns:
            cache_age = datetime.now() - pd.to_datetime(data_manager._data['timestamp'].iloc[0])
        else:
            cache_age = timedelta(0)  # Default to 0 if no timestamp
        
        summary_text = f"""
        **Cache Statistics:**
        - Total Symbols: {total_symbols}
        - Date Range: {earliest_date.strftime('%Y-%m-%d')} to {latest_date.strftime('%Y-%m-%d')}
        - Total Data Points: {total_data_points:,}
        - Cache Age: {cache_age.days} days, {cache_age.seconds//3600} hours
        """
        
        # Create coverage table
        coverage_data = []
        for sector, symbols in sectors.items():
            available_symbols = [s for s in symbols if s in data_manager._data['Symbol'].unique()]
            coverage_data.append({
                'Sector': sector,
                'Total Symbols': len(symbols),
                'Available Symbols': len(available_symbols),
                'Coverage': f"{(len(available_symbols)/len(symbols))*100:.1f}%"
            })
            
        return summary_text, coverage_data
        
    except Exception as e:
        logger.error(f"Error creating data summary: {e}")
        return "Error loading data summary", []

# Layout
layout = html.Div([
 
    # Control Panel
    dbc.Card([
        dbc.CardBody([
            html.H4('Data Controls', className='card-title', style={'color': 'white'}),
            html.Div([
                dbc.Button(
                    'Clear Cache',
                    id='clear-cache-button',
                    color='danger',
                    className='me-2'
                ),
                dbc.Button(
                    'Refresh Data',
                    id='refresh-data-button',
                    color='primary',
                    className='me-2'
                ),
                dcc.Dropdown(
                    id='data-period-dropdown',
                    options=[
                        {'label': '1 Month', 'value': '1mo'},
                        {'label': '3 Months', 'value': '3mo'},
                        {'label': '6 Months', 'value': '6mo'},
                        {'label': '1 Year', 'value': '1y'},
                        {'label': '2 Years', 'value': '2y'},
                        {'label': '5 Years', 'value': '5y'}
                    ],
                    value='1y',
                    placeholder='Select Period',
                    style={
                        'width': '200px',
                        'color': 'black',
                        'marginTop': '10px',
                        'backgroundColor': 'white'
                    }
                )
            ], style={'marginBottom': '20px'})
        ])
    ], style={'backgroundColor': '#383838', 'marginBottom': '20px'}),
    
    # Status Messages
    dbc.Alert(id='status-message', is_open=False, duration=4000),
    
    # Data Summary
    dbc.Card([
        dbc.CardBody([
            html.H4('Data Summary', className='card-title', style={'color': 'white'}),
            dcc.Markdown(id='data-summary', style={'color': 'white'})
        ])
    ], style={'backgroundColor': '#383838', 'marginBottom': '20px'}),
    
    # Sector Coverage Table
    dbc.Card([
        dbc.CardBody([
            html.H4('Sector Coverage', className='card-title', style={'color': 'white'}),
            html.Div(id='sector-coverage-table')
        ])
    ], style={'backgroundColor': '#383838'})
    
], style={'backgroundColor': '#2E2E2E', 'minHeight': '100vh', 'padding': '20px'})

@callback(
    [Output('status-message', 'children'),
     Output('status-message', 'is_open'),
     Output('status-message', 'color'),
     Output('data-summary', 'children'),
     Output('sector-coverage-table', 'children')],
    [Input('clear-cache-button', 'n_clicks'),
     Input('refresh-data-button', 'n_clicks'),
     Input('data-period-dropdown', 'value')],
    prevent_initial_call=False
)
def handle_data_controls(clear_clicks, refresh_clicks, period):
    """Handles data management control actions."""
    ctx = dash.callback_context
    
    try:
        if not ctx.triggered:
            # Initial load - try to load from cache first
            data_manager._data = data_manager._load_cache()
            if data_manager._data is None or data_manager._data.empty:
                # If no cache exists, fetch fresh data
                symbols = get_all_symbols()
                data_manager.get_stock_data(symbols, period)
            
            summary_text, coverage_data = create_data_summary()
            return "", False, "primary", summary_text, create_coverage_table(coverage_data)
        
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if button_id == 'clear-cache-button':
            data_manager.clear_cache()
            return "Cache cleared successfully", True, "success", "No cached data available", None
            
        elif button_id == 'refresh-data-button' or button_id == 'data-period-dropdown':
            # Force refresh for button click
            if button_id == 'refresh-data-button':
                data_manager.clear_cache()
            
            # Get all symbols and fetch new data
            symbols = get_all_symbols()
            data_manager.get_stock_data(symbols, period)
            
            summary_text, coverage_data = create_data_summary()
            coverage_table = create_coverage_table(coverage_data)
            
            message = "Data refreshed successfully" if button_id == 'refresh-data-button' else ""
            color = "success" if button_id == 'refresh-data-button' else "primary"
            
            return message, bool(message), color, summary_text, coverage_table
            
    except Exception as e:
        logger.error(f"Error in handle_data_controls: {e}")
        return str(e), True, "danger", "", None

def create_coverage_table(coverage_data):
    """Creates a formatted coverage table."""
    return dbc.Table.from_dataframe(
        pd.DataFrame(coverage_data),
        striped=True,
        bordered=True,
        hover=True,
        style={
            'color': 'white',
            'backgroundColor': '#383838'
        }
    )