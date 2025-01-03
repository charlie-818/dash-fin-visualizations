import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
import pandas as pd
import numpy as np
import logging
from typing import Dict, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Register the page
dash.register_page(__name__, path='/etf-analysis', name='ETF Analysis')

# Use the test_cases from the provided code as holdings_dict
holdings_dict = {
    'GDXJ': {
        'PAAS': 0.0713, 'AGI': 0.0645, 'EVN': 0.0640,
        'HMY': 0.0604, 'BTG': 0.0482, 'OR': 0.0225,
        'HL': 0.0215, 'EDV': 0.0209
    },
    'XRT': {
        'CVNA': 0.0229, 'WRBY': 0.0208, 'VSCO': 0.0196,
        'SFM': 0.0187, 'LAD': 0.0175, 'RVLV': 0.0172,
        'GME': 0.0168, 'DDS': 0.0162
    },
    'GDX': {
        'NEM': 0.1227, 'AEM': 0.1017, 'GOLD': 0.0769,
        'WPM': 0.0703, 'FNV': 0.0578
    },
    'SMH': {
        'NVDA': 0.2150, 'TSM': 0.1450, 'ASML': 0.1120,
        'AMD': 0.0950, 'AVGO': 0.0850
    },
    'XHB': {
        'DHI': 0.1250, 'LEN': 0.1150, 'PHM': 0.0950,
        'NVR': 0.0850, 'TOL': 0.0750
    },
    'XLK': {
        'AAPL': 0.2150, 'MSFT': 0.2050, 'NVDA': 0.1550,
        'AVGO': 0.0450, 'AMD': 0.0350
    },
    'IWM': {
        'CRGY': 0.0025, 'CELH': 0.0024, 'MEDP': 0.0023,
        'PODD': 0.0022, 'TECH': 0.0021
    }
}

def analyze_etf_divergence(
    etf_ticker: str,
    holdings: Dict[str, float],
    period: str = '1y',
    rolling_window: int = 20,
    min_days_between_signals: int = 10
) -> Tuple[go.Figure, dict]:
    try:
        # Validate weights
        total_weight = sum(holdings.values())
        if not 0.98 <= total_weight <= 1.02:
            logger.warning(f"Weights sum to {total_weight}, not 1.0. Normalizing weights.")
            holdings = {k: v/total_weight for k, v in holdings.items()}

        # Get ETF data
        etf = yf.Ticker(etf_ticker)
        etf_data = etf.history(period=period)['Close']

        # Get holdings data and calculate weighted average
        holdings_data = pd.DataFrame()
        for stock, weight in holdings.items():
            try:
                stock_data = yf.Ticker(stock).history(period=period)['Close']
                holdings_data[stock] = stock_data * weight
            except Exception as e:
                logger.error(f"Error fetching data for {stock}: {e}")
                continue

        if holdings_data.empty:
            logger.error("No holdings data available")
            return None, None

        holdings_avg = holdings_data.sum(axis=1)

        # Ensure both series have the same dates
        common_dates = etf_data.index.intersection(holdings_avg.index)
        if len(common_dates) == 0:
            logger.error("No common dates between ETF and holdings")
            return None, None

        etf_data = etf_data[common_dates]
        holdings_avg = holdings_avg[common_dates]

        # Normalize prices to starting point
        etf_normalized = etf_data / etf_data.iloc[0] * 100
        holdings_normalized = holdings_avg / holdings_avg.iloc[0] * 100

        # Calculate divergence and rolling statistics
        divergence = (etf_normalized - holdings_normalized)
        rolling_std = divergence.rolling(window=rolling_window).std()

        # Create figure
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # Add main price traces
        fig.add_trace(
            go.Scatter(x=etf_normalized.index, y=etf_normalized,
                      name=etf_ticker, line=dict(color="blue", width=2)),
            secondary_y=False
        )

        fig.add_trace(
            go.Scatter(x=holdings_normalized.index, y=holdings_normalized,
                      name="Holdings Average", line=dict(color="red", width=2)),
            secondary_y=False
        )

        # Add divergence trace
        fig.add_trace(
            go.Scatter(x=divergence.index, y=divergence,
                      name="Divergence", line=dict(color="orange", width=1)),
            secondary_y=True
        )

        # Find crossover points
        crossovers = []
        for i in range(1, len(divergence)):
            if (divergence.iloc[i-1] * divergence.iloc[i] <= 0):
                crossovers.append(i)

        # Calculate statistics
        stats = {
            'Max Divergence': divergence.max(),
            'Min Divergence': divergence.min(),
            'Mean Divergence': divergence.mean(),
            'Std Deviation': divergence.std(),
            'Current Divergence': divergence.iloc[-1],
            'Number of Crossovers': len(crossovers),
        }

        # Update layout
        fig.update_layout(
            title=f"{etf_ticker} vs Holdings Price Comparison",
            xaxis_title="Date",
            yaxis_title="Normalized Price (Base=100)",
            yaxis2_title="Divergence (%)",
            hovermode="x unified",
            width=1000,
            height=800,
            template="plotly_dark",
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.2,
                xanchor="center",
                x=0.5,
                bgcolor="rgba(0,0,0,0)",
                font=dict(color="white")
            )
        )

        return fig, stats

    except Exception as e:
        logger.error(f"Error in analyze_etf_divergence: {str(e)}")
        return None, None

# Layout
layout = html.Div([
    # Dropdown container
    html.Div([
        dcc.Dropdown(
            id='etf-dropdown',
            options=[
                {'label': f"{etf} - {etf} ETF", 'value': etf}
                for etf in holdings_dict.keys()
            ],
            value='GDXJ',
            style={
                'width': '200px',
                'color': 'black',
                'backgroundColor': 'rgba(255, 255, 255, 0.1)'
            }
        )
    ], style={'textAlign': 'center', 'marginBottom': '20px'}),
    
    # Container for graph and stats side by side
    html.Div([
        # Graph container
        html.Div([
            dcc.Loading(
                id="loading-etf-analysis",
                type="default",
                children=dcc.Graph(
                    id='etf-analysis-graph',
                    config={
                        'scrollZoom': True,
                        'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'drawclosedpath', 
                                              'drawcircle', 'drawrect', 'eraseshape']
                    },
                    style={
                        'height': '800px',
                        'width': '100%'  # Ensure graph uses full container width
                    }
                )
            )
        ], style={
            'width': '83%',
            'display': 'inline-block',
            'verticalAlign': 'top',
            'marginRight': '0',
            'padding': '0'  # Remove any padding
        }),
        
        # Stats container
        html.Div(
            id='etf-stats',
            style={
                'width': '17%',
                'display': 'inline-block',
                'verticalAlign': 'top',
                'padding': '20px',
                'backgroundColor': '#2E2E2E',
                'borderRadius': '15px',
                'color': 'white',
                'height': '800px',
                'overflowY': 'auto',
                'boxShadow': '0 4px 8px rgba(0, 0, 0, 0.2)'
            }
        )
    ], style={
        'width': '100%',
        'margin': '0',  # Remove margin
        'padding': '0',  # Remove padding
        'display': 'flex',
        'justifyContent': 'space-between',
        'alignItems': 'flex-start',
        'gap': '0'  # Remove gap
    }),
    
], style={'backgroundColor': '#1E1E1E', 'minHeight': '100vh', 'padding': '30px'})

@dash.callback(
    [Output('etf-analysis-graph', 'figure'),
     Output('etf-stats', 'children')],
    [Input('etf-dropdown', 'value')]
)
def update_etf_analysis(selected_etf):
    try:
        holdings = holdings_dict.get(selected_etf, {})
        if not holdings:
            return go.Figure(), "No holdings data available."
            
        fig, stats = analyze_etf_divergence(selected_etf, holdings)
        
        if fig is None or stats is None:
            return go.Figure(), "Analysis failed. Please try again."
        
        # Update figure layout with proper margins and bottom legend
        fig.update_layout(
            margin=dict(l=50, r=20, t=30, b=150),  # Adjusted margins, increased bottom for legend
            autosize=True,
            height=800,
            template="plotly_dark",
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.35,  # Moved legend further down
                xanchor="center",
                x=0.5,
                bgcolor="rgba(0,0,0,0)",
                font=dict(color="white")
            ),
            xaxis=dict(
                rangeslider=dict(visible=True),
                type="date"
            ),
            title=dict(
                text=f"{selected_etf} vs Holdings Price Comparison",
                x=0.5,
                y=0.95
            )
        )
            
        # Format statistics for display
        stats_components = [
            html.Div([
                html.H3("ETF Analysis Statistics", 
                    style={
                        'borderBottom': '2px solid #666',
                        'paddingBottom': '10px',
                        'marginBottom': '20px',
                        'textAlign': 'center'
                    }
                ),
                *[html.Div([
                    html.Strong(f"{key}: ", style={
                        'color': '#ADD8E6',
                        'fontSize': '14px'
                    }),
                    html.Span(
                        f"{value:.2f}" if isinstance(value, float) else str(value),
                        style={
                            'color': '#FFF',
                            'fontSize': '14px'
                        }
                    )
                ], style={
                    'marginBottom': '15px',
                    'padding': '10px',
                    'backgroundColor': 'rgba(255, 255, 255, 0.05)',
                    'borderRadius': '8px'
                }) for key, value in stats.items()]
            ])
        ]
        
        return fig, stats_components
        
    except Exception as e:
        logger.error(f"Error in callback: {e}")
        return go.Figure(), f"An error occurred during analysis: {str(e)}"
