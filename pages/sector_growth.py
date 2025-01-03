import dash
from dash import dcc, html, callback
from dash.dependencies import Input, Output
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import logging
import numpy as np
import yfinance as yf
from utils.data_processing import sectors

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Register the page
dash.register_page(__name__, path='/sector-growth', name='Sector Growth')

def fetch_and_process_data(symbols, period="5d"):
    """Fetches data for given symbols and calculates percentage change."""
    all_data = {}
    for symbol in symbols:
        try:
            data = yf.download(symbol, period=period, progress=False)
            if not data.empty:
                # Calculate percentage change immediately
                data['Pct_Change'] = data['Close'].pct_change() * 100
                all_data[symbol] = data
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
    return all_data

def calculate_sector_averages(stock_data, sectors):
    """Calculates average percentage change for each sector."""
    sector_avg_pct_change = {}
    for sector, sector_tickers in sectors.items():
        valid_changes = []
        for ticker in sector_tickers:
            if ticker in stock_data:
                # Use last valid mean, excluding NaN values
                mean_change = stock_data[ticker]['Pct_Change'].mean()
                if not np.isnan(mean_change):
                    valid_changes.append(mean_change)
        sector_avg_pct_change[sector] = np.mean(valid_changes) if valid_changes else np.nan
    return sector_avg_pct_change

def create_sector_growth_visualizations(period="5d"):
    """Creates both sector growth visualizations."""
    try:
        # Get all tickers
        all_tickers = [ticker for sector_tickers in sectors.values() for ticker in sector_tickers]
        
        # Fetch data with specified period
        stock_data = fetch_and_process_data(all_tickers, period=period)
        
        if not stock_data:
            logger.error("No stock data available")
            return go.Figure(), go.Figure()

        # Calculate sector averages
        sector_avg_pct_change = calculate_sector_averages(stock_data, sectors)

        # Create ranked sectors dataframe
        ranked_sectors = sorted(
            sector_avg_pct_change.items(), 
            key=lambda x: x[1] if not np.isnan(x[1]) else float('-inf'), 
            reverse=True
        )
        ranked_df = pd.DataFrame(ranked_sectors, columns=['Sector', 'Average Pct Change'])
        
        # Store numeric values for coloring
        ranked_df['Numeric_Value'] = ranked_df['Average Pct Change'].apply(
            lambda x: x if not np.isnan(x) else 0
        )
        
        # Format percentage changes for table
        ranked_df['Average Pct Change'] = ranked_df['Average Pct Change'].apply(
            lambda x: f"{x:.2f}%" if not np.isnan(x) else "N/A"
        )

        # Create table visualization with enhanced styling
        table_fig = go.Figure(data=[go.Table(
            header=dict(
                values=['<b>Sector</b>', '<b>Average % Change</b>'],
                fill_color='rgba(37, 37, 37, 1)',
                align='left',
                font=dict(size=14, color='white'),
                line_color='rgba(255, 255, 255, 0.2)',
                height=40
            ),
            cells=dict(
                values=[ranked_df.Sector, ranked_df['Average Pct Change']],
                fill_color=['rgba(50, 50, 50, 1)', 
                          ['rgba(50, 171, 96, 0.2)' if val > 0 else 'rgba(171, 50, 50, 0.2)' 
                           for val in ranked_df['Numeric_Value']]],
                align='left',
                font=dict(size=13, color='white'),
                line_color='rgba(255, 255, 255, 0.1)',
                height=35
            )
        )])
        
        table_fig.update_layout(
            
            height=len(ranked_sectors) * 35 + 100,
            margin=dict(l=20, r=20, t=80, b=20),
            template='plotly_dark',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white')
        )

        # Create sector performance subplots
        num_rows = (len(ranked_sectors) + 1) // 2
        performance_fig = make_subplots(
            rows=num_rows, 
            cols=2,
            subplot_titles=[sector[0] for sector in ranked_sectors],
            vertical_spacing=0.1
        )

        row = 1
        col = 1
        for sector, _ in ranked_sectors:
            sector_tickers = sectors.get(sector, [])
            for ticker in sector_tickers:
                if ticker in stock_data:
                    performance_fig.add_trace(
                        go.Scatter(
                            x=stock_data[ticker].index,
                            y=stock_data[ticker]['Pct_Change'],
                            mode='lines',
                            name=ticker,
                            showlegend=True,
                            line=dict(width=1)
                        ),
                        row=row, col=col
                    )
            col += 1
            if col > 2:
                col = 1
                row += 1

        performance_fig.update_layout(
            height=300 * num_rows,
            
            showlegend=True,
            template='plotly_dark',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white')
        )

        performance_fig.update_xaxes(
            title_text="Date",
            gridcolor='rgba(255, 255, 255, 0.1)',
            showgrid=True
        )
        
        performance_fig.update_yaxes(
            title_text="Percentage Change (%)",
            gridcolor='rgba(255, 255, 255, 0.1)',
            showgrid=True,
            zeroline=True,
            zerolinecolor='rgba(255, 255, 255, 0.2)'
        )

        return table_fig, performance_fig

    except Exception as e:
        logger.error(f"Error creating sector growth visualizations: {e}")
        return go.Figure(), go.Figure()

# Define the layout
layout = html.Div([
    # Period selector
    html.Div([
        dcc.Dropdown(
            id='sector-period-dropdown',
            options=[
                {'label': '1 Month', 'value': '1mo'},
                {'label': '3 Months', 'value': '3mo'},
                {'label': '6 Months', 'value': '6mo'},
                {'label': '1 Year', 'value': '1y'}
            ],
            value='1mo',
            style={
                'width': '200px',
                'color': 'black',
                'backgroundColor': 'rgba(255, 255, 255, 0.1)'
            }
        )
    ], style={'textAlign': 'center', 'marginBottom': '20px'}),
    
    # Sector Growth Table
    html.Div([
        dcc.Loading(
            id="loading-sector-table",
            type="default",
            children=dcc.Graph(
                id='sector-growth-table',
                config={'displayModeBar': False}
            )
        )
    ], style={'width': '80%', 'margin': 'auto', 'marginBottom': '40px'}),
    
    # Sector Performance Subplots
    html.Div([
        dcc.Loading(
            id="loading-sector-performance",
            type="default",
            children=dcc.Graph(
                id='sector-performance-subplots',
                config={'displayModeBar': False}
            )
        )
    ], style={'width': '95%', 'margin': 'auto'})
    
], style={'backgroundColor': '#1E1E1E', 'minHeight': '100vh', 'padding': '20px'})

# Callbacks
@callback(
    [Output('sector-growth-table', 'figure'),
     Output('sector-performance-subplots', 'figure')],
    [Input('sector-period-dropdown', 'value')]
)
def update_sector_growth(selected_period):
    """Updates sector growth visualizations based on the selected period."""
    try:
        table_fig, performance_fig = create_sector_growth_visualizations(period=selected_period)
        return table_fig, performance_fig
    except Exception as e:
        logger.error(f"Error updating sector growth visualizations: {e}")
        return go.Figure(), go.Figure()