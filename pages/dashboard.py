import dash
from dash import dcc, html, callback
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import pandas as pd
import logging
import numpy as np
import yfinance as yf

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Register the page
dash.register_page(__name__, path='/', name='Dashboard')

# Define sectors
sectors = {
    "Technology": [
        "AAPL", "MSFT", "GOOG", "AMZN", "TSLA", "NVDA", "INTC", "CRM",
        "ADBE", "ORCL", "CSCO", "IBM", "HPQ", "AVGO", "AMD", "TXN", "QCOM"
    ],
    "Healthcare": [
        "JNJ", "UNH", "PFE", "MRK", "ABBV", "LLY", "AMGN", "BMY",
        "GILD", "TMO", "MDT", "DHR", "ISRG", "ABT", "CVS", "CI"
    ],
    "Financials": [
        "JPM", "BAC", "WFC", "C", "GS", "MS", "AXP", "V",
        "MA", "BLK", "BRK-B", "SCHW", "SPGI", "COF", "USB", "PNC", "AIG"
    ],
    "Consumer Discretionary": [
        "AMZN", "HD", "MCD", "NKE", "SBUX", "TGT", "LOW", "DIS",
        "CMG", "TJX", "ROST", "BKNG", "EBAY", "LVS", "MAR", "DG", "AZO"
    ],
    "Consumer Staples": [
        "PG", "KO", "PEP", "WMT", "COST", "MDLZ", "KHC", "CL",
        "GIS", "EL", "WBA", "SYY", "TAP", "K", "KR", "ADM", "HSY"
    ],
    "Industrials": [
        "BA", "UNP", "CAT", "HON", "GE", "RTX", "MMM", "UPS",
        "FDX", "LMT", "DE", "EMR", "GD", "ITW", "NOC", "CSX", "ETN"
    ],
    "Energy": [
        "XOM", "CVX", "COP", "EOG", "SLB", "KMI", "WMB", "PSX",
        "VLO", "HAL", "MPC", "OKE", "BKR", "FANG", "HES", "DVN"
    ],
    "Utilities": [
        "NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL",
        "ED", "EIX", "AWK", "ES", "PEG", "WEC", "DTE", "PPL", "ATO"
    ],
    "Materials": [
        "LIN", "APD", "SHW", "ECL", "NEM", "FCX", "LYB", "PPG",
        "CE", "DD", "DOW", "EMN", "IP", "NUE", "VMC", "MLM", "ALB"
    ],
    "Real Estate": [
        "AMT", "PLD", "CCI", "EQIX", "SPG", "PSA", "AVB", "WELL",
        "O", "VTR", "DLR", "EXR", "ESS", "EQR", "BXP", "HST", "ARE"
    ],
    "Communication Services": [
        "META", "TMUS", "CMCSA", "CHTR", "NFLX", "VZ", "T", "EA",
        "LYV", "FOXA", "WBD", "OMC", "TTWO", "GOOGL"
    ],
}

# Global variables to store data
stock_data = {}
correlation_matrix = None
transformed_mask = None
sector_correlation_matrix = None
sector_transformed_mask = None

def download_data(period="5d"):
    """Downloads data for the specified period and stores it in global variables."""
    global stock_data, correlation_matrix, transformed_mask, sector_correlation_matrix, sector_transformed_mask
    
    logger.info(f"Downloading fresh data for period: {period}")
    all_tickers = [ticker for sector_tickers in sectors.values() for ticker in sector_tickers]
    
    stock_data = {}
    for symbol in all_tickers:
        try:
            data = yf.download(symbol, period=period, progress=False)
            if not data.empty:
                stock_data[symbol] = data
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            continue

    if not stock_data:
        logger.error("No stock data was downloaded.")
        return

    # Calculate daily percentage changes
    pct_change_df = pd.DataFrame()
    for symbol, data in stock_data.items():
        data['Pct_Change'] = data['Close'].pct_change() * 100
        pct_change_df[symbol] = data['Pct_Change']

    # Calculate stock correlation matrix without masking
    correlation_matrix = pct_change_df.corr()
    transformed_mask = correlation_matrix  # No masking, show all correlations
    
    # Calculate sector returns
    sector_returns = pd.DataFrame()
    for sector, tickers in sectors.items():
        valid_tickers = [t for t in tickers if t in stock_data]
        if not valid_tickers:
            continue
            
        sector_data = pd.DataFrame()
        for ticker in valid_tickers:
            returns = stock_data[ticker]['Close'].pct_change() * 100
            sector_data[ticker] = returns
        
        sector_returns[sector] = sector_data.mean(axis=1)
    
    # Calculate sector correlation matrix without masking
    sector_correlation_matrix = sector_returns.corr()
    sector_transformed_mask = sector_correlation_matrix  # No masking, show all correlations
    
    logger.info("Data download and processing completed.")

def create_stock_heatmap():
    """Creates a correlation heatmap using stored data."""
    global correlation_matrix, transformed_mask
    
    if correlation_matrix is None:
        download_data()
    
    if correlation_matrix is None:
        # Data download failed
        fig = go.Figure()
        fig.update_layout(
            title="Stock Correlation Matrix - Data Not Available",
            template='plotly_dark',
            plot_bgcolor='#1E1E1E',
            paper_bgcolor='#1E1E1E',
            font=dict(color='white')
        )
        return fig
    
    fig = go.Figure(data=go.Heatmap(
        z=transformed_mask,
        x=correlation_matrix.columns,
        y=correlation_matrix.columns,
        colorscale='RdBu',
        zmid=0,
        zmin=-1,
        zmax=1,
        zsmooth="best",
        hoverongaps=False,
        hovertemplate='%{x} & %{y}<br>Correlation: %{z:.2f}<extra></extra>'  # Show values on hover only
    ))

    # Add sector divisions
    sector_boundaries = []
    current_position = 0
    for sector, tickers in sectors.items():
        current_position += len(tickers)
        sector_boundaries.append(current_position)

    for boundary in sector_boundaries[:-1]:
        fig.add_shape(
            type='line',
            x0=boundary - 0.5, y0=-0.5,
            x1=boundary - 0.5, y1=len(correlation_matrix.columns) - 0.5,
            line=dict(color='rgba(255, 255, 255, 0.5)', width=2, dash='dot')
        )
        fig.add_shape(
            type='line',
            x0=-0.5, y0=boundary - 0.5,
            x1=len(correlation_matrix.columns) - 0.5, y1=boundary - 0.5,
            line=dict(color='rgba(255, 255, 255, 0.5)', width=2, dash='dot')
        )

    # Add diagonal line
    fig.add_shape(
        type='line',
        x0=-0.5, y0=-0.5,
        x1=len(correlation_matrix.columns) - 0.5,
        y1=len(correlation_matrix.columns) - 0.5,
        line=dict(color='white', width=3)
    )

    # Add sector labels
    annotations = []
    start = 0
    for sector, tickers in sectors.items():
        end = start + len(tickers)
        annotations.append(dict(
            x=start + (end - start) / 2,
            y=-0.5,
            text=sector,
            showarrow=False,
            font=dict(size=12, color="white", family="Arial Black"),
            yshift=-50,
            bgcolor='rgba(0,0,0,0.5)',
            borderpad=4
        ))
        start = end

    # Update layout with consistent formatting
    update_figure_layout(fig, "", len(correlation_matrix.columns))
    return fig

def create_sector_heatmap():
    """Creates a correlation heatmap for sectors."""
    global sector_correlation_matrix, sector_transformed_mask
    
    if sector_correlation_matrix is None:
        download_data()
    
    if sector_correlation_matrix is None:
        # Data download failed
        fig = go.Figure()
        fig.update_layout(
            title="Sector Correlation Matrix - Data Not Available",
            template='plotly_dark',
            plot_bgcolor='#1E1E1E',
            paper_bgcolor='#1E1E1E',
            font=dict(color='white')
        )
        return fig
    
    fig = go.Figure(data=go.Heatmap(
        z=sector_transformed_mask,
        x=sector_correlation_matrix.columns,
        y=sector_correlation_matrix.columns,
        colorscale='RdBu',  # Changed to RdBu for better correlation visualization
        zmid=0,
        zmin=-1,
        zmax=1,
        zsmooth="best",
        text=np.round(sector_transformed_mask, 2),  # Add correlation values as text
        texttemplate='%{text}',  # Show the text for all cells
        textfont={"size": 10},  # Slightly larger font for sector heatmap
        hoverongaps=False
    ))
    
    # Add diagonal line
    fig.add_shape(
        type='line',
        x0=-0.5, y0=-0.5,
        x1=len(sector_correlation_matrix.columns) - 0.5,
        y1=len(sector_correlation_matrix.columns) - 0.5,
        line=dict(color='white', width=3)
    )
    
    # Update layout with consistent formatting
    update_figure_layout(fig, "", len(sector_correlation_matrix.columns))
    return fig

def update_figure_layout(fig, title, matrix_len):
    """Updates figure layout with consistent formatting."""
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=24, color='white', family="Arial Black"),
            y=0.95
        ),
        xaxis=dict(
            showgrid=False,
            range=[-0.5, matrix_len - 0.5],
            tickangle=45,
            tickfont=dict(size=12, color='white', family="Arial"),
            showline=True,
            linewidth=2,
            linecolor='rgba(255,255,255,0.3)'
        ),
        yaxis=dict(
            showgrid=False,
            range=[-0.5, matrix_len - 0.5],
            tickfont=dict(size=12, color='white', family="Arial"),
            showline=True,
            linewidth=2,
            linecolor='rgba(255,255,255,0.3)'
        ),
        margin=dict(l=50, r=50, t=100, b=100),
        height=800,
        template='plotly_dark',
        plot_bgcolor='#1E1E1E',
        paper_bgcolor='#1E1E1E',
        font=dict(color='white', family="Arial")
    )

# Initial Data Download
download_data()

# Layout
layout = html.Div([
    # Period selector
    html.Div([
        dcc.Dropdown(
            id='correlation-period-dropdown',
            options=[
                {'label': '5 Days', 'value': '5d'},
                {'label': '1 Month', 'value': '1mo'},
                {'label': '3 Months', 'value': '3mo'},
                {'label': '6 Months', 'value': '6mo'},
                {'label': '1 Year', 'value': '1y'}
            ],
            value='5d',
            style={
                'width': '200px',
                'color': 'black',
                'backgroundColor': 'rgba(255, 255, 255, 0.1)'
            }
        )
    ], style={'textAlign': 'center', 'marginBottom': '20px'}),
    
    # Stock Correlation Heatmap
    html.Div([
        dcc.Loading(
            id="loading-stock-heatmap",
            type="default",
            children=dcc.Graph(
                id='stock-correlation-heatmap',
                config={
                    'displayModeBar': True,
                    'modeBarButtonsToRemove': [
                        'zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d',
                        'autoScale2d', 'resetScale2d', 'toggleSpikelines',
                        'hoverClosestCartesian', 'hoverCompareCartesian'
                    ]
                }
            )
        )
    ], style={'width': '95%', 'margin': 'auto', 'marginBottom': '50px'}),
    
    # Sector Correlation Heatmap
    html.Div([
        dcc.Loading(
            id="loading-sector-heatmap",
            type="default",
            children=dcc.Graph(
                id='sector-correlation-heatmap',
                config={
                    'displayModeBar': True,
                    'modeBarButtonsToRemove': [
                        'zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d',
                        'autoScale2d', 'resetScale2d', 'toggleSpikelines',
                        'hoverClosestCartesian', 'hoverCompareCartesian'
                    ]
                }
            )
        )
    ], style={'width': '95%', 'margin': 'auto', 'marginBottom': '50px'})
], style={'backgroundColor': '#1E1E1E', 'minHeight': '100vh', 'padding': '30px'})

# Callback
@callback(
    [Output('stock-correlation-heatmap', 'figure'),
     Output('sector-correlation-heatmap', 'figure')],
    [Input('correlation-period-dropdown', 'value')]
)
def display_heatmaps(selected_period):
    """Display both heatmaps based on the selected period."""
    # Download fresh data for the selected period
    download_data(selected_period)
    return create_stock_heatmap(), create_sector_heatmap()