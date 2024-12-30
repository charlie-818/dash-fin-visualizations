import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import dash_bootstrap_components as dbc

from utils.data_processing import get_segmented_data, sectors
from app import app

# Define TIME_PERIODS dictionary
TIME_PERIODS = {
    '1 Month': '1mo',
    '3 Months': '3mo',
    '6 Months': '6mo',
    '1 Year': '1y',
    '5 Years': '5y',
    'Max': 'max'
}

def calculate_sector_averages(stock_data, sectors):
    sector_avg_pct_change = {}
    sector_stats = {}  # Add more detailed statistics
    
    for sector, tickers in sectors.items():
        sector_changes = []
        valid_tickers = []  # Track which tickers have valid data
        
        for ticker in tickers:
            if ticker in stock_data and not stock_data[ticker].empty:
                try:
                    # Calculate the percentage change from first to last day
                    first_price = float(stock_data[ticker]['Close'].iloc[0])
                    last_price = float(stock_data[ticker]['Close'].iloc[-1])
                    pct_change = ((last_price - first_price) / first_price) * 100
                    sector_changes.append(pct_change)
                    valid_tickers.append(ticker)
                except (IndexError, ValueError, TypeError) as e:
                    print(f"Error processing {ticker}: {e}")
                    continue
        
        if sector_changes:
            sector_avg_pct_change[sector] = sum(sector_changes) / len(sector_changes)
            sector_stats[sector] = {
                'average': sector_avg_pct_change[sector],
                'count': len(sector_changes),
                'tickers': valid_tickers,
                'max_change': max(sector_changes),
                'min_change': min(sector_changes)
            }
        else:
            print(f"No valid data for sector: {sector}")
            sector_avg_pct_change[sector] = 0
            sector_stats[sector] = {
                'average': 0,
                'count': 0,
                'tickers': [],
                'max_change': 0,
                'min_change': 0
            }
    
    return sector_avg_pct_change, sector_stats

def create_heatmap(period="1mo"):
    # Function reused from dashboard.py if needed
    pass  # Placeholder if needed

def create_sector_growth_analysis(stock_data=None, period="1mo"):
    if stock_data is None:
        stock_data = get_segmented_data(period=period)
    
    if not stock_data:
        print("No stock data available for sector growth analysis")
        return go.Figure(), go.Figure()

    # Calculate sector averages and stats
    sector_avg_pct_change, sector_stats = calculate_sector_averages(stock_data, sectors)

    # Create enhanced table figure
    table_data = []
    for sector in sector_stats:
        stats = sector_stats[sector]
        table_data.append([
            sector,
            f"{stats['average']:.2f}%",
            f"{stats['count']}/{len(sectors[sector])}",  # Show coverage
            f"{stats['max_change']:.2f}%",
            f"{stats['min_change']:.2f}%"
        ])

    table_df = pd.DataFrame(
        table_data,
        columns=['Sector', 'Avg Growth', 'Coverage', 'Best Performer', 'Worst Performer']
    )
    table_df = table_df.sort_values(by='Avg Growth', ascending=False)

    table_fig = go.Figure(data=[go.Table(
        header=dict(
            values=list(table_df.columns),
            fill_color='#2c3e50',
            align='left',
            font=dict(color='white', size=16)
        ),
        cells=dict(
            values=[table_df[col] for col in table_df.columns],
            fill_color='#1a1a1a',
            align='left',
            font=dict(color='white', size=14)
        )
    )])

    table_fig.update_layout(
        title=dict(
            text=f"Sector Performance Summary ({period})",
            font=dict(size=24, color="white")
        ),
        plot_bgcolor='black',
        paper_bgcolor='black',
        margin=dict(l=0, r=0, t=50, b=0),
        height=400
    )

    # Create sector performance subplots
    subplot_fig = make_subplots(
        rows=len(sectors),
        cols=1,
        subplot_titles=[f"{sector} Daily Returns" for sector in sectors.keys()],
        vertical_spacing=0.03
    )

    # Color palette for lines
    colors = px.colors.qualitative.Set3

    for i, (sector, tickers) in enumerate(sectors.items(), 1):
        for j, ticker in enumerate(tickers):
            if ticker in stock_data and not stock_data[ticker].empty:
                try:
                    # Calculate daily percentage change
                    daily_returns = stock_data[ticker]['Pct_Change']
                    
                    subplot_fig.add_trace(
                        go.Scatter(
                            x=stock_data[ticker].index,
                            y=daily_returns,
                            name=ticker,
                            mode='lines',
                            opacity=0.7,
                            line=dict(
                                width=1.5,
                                color=colors[j % len(colors)]
                            ),
                            showlegend=True,
                            legendgroup=sector,
                            legendgrouptitle_text=sector
                        ),
                        row=i,
                        col=1
                    )

                    # Add a horizontal line at y=0 for reference
                    subplot_fig.add_hline(
                        y=0,
                        line=dict(color='white', width=1, dash='dash'),
                        row=i,
                        col=1
                    )

                except Exception as e:
                    print(f"Error plotting {ticker}: {e}")
                    continue

        # Update y-axis title for each subplot
        subplot_fig.update_yaxes(
            title_text="Daily Return (%)",
            title_font=dict(color='white', size=10),
            tickfont=dict(color='white'),
            gridcolor='rgba(255,255,255,0.1)',
            zeroline=True,
            zerolinecolor='white',
            zerolinewidth=1,
            row=i,
            col=1
        )

    # Update layout for better visualization
    subplot_fig.update_layout(
        title=dict(
            text=f"Sector Daily Returns ({period})",
            font=dict(size=24, color="white"),
            y=0.99
        ),
        showlegend=True,
        plot_bgcolor='black',
        paper_bgcolor='black',
        height=250 * len(sectors),  # Adjust height based on number of sectors
        margin=dict(l=50, r=50, t=100, b=50),
        legend=dict(
            font=dict(color='white'),
            bgcolor='rgba(0,0,0,0.5)',
            bordercolor='white',
            borderwidth=1,
            groupclick="toggleitem"
        )
    )

    # Update x-axes
    subplot_fig.update_xaxes(
        showgrid=True,
        gridcolor='rgba(255,255,255,0.1)',
        tickfont=dict(color='white'),
        showline=True,
        linecolor='white'
    )

    return table_fig, subplot_fig

# Define the layout for the Sector Growth Analysis page
layout = html.Div([
    html.H1('Sector Growth Analysis', style={'color': 'white', 'textAlign': 'center'}),
    
    # Add time period selector
    html.Div([
        html.Label('Select Time Period:', style={'color': 'white', 'marginRight': '10px'}),
        dcc.Dropdown(
            id='time-period-selector',
            options=[{'label': k, 'value': v} for k, v in TIME_PERIODS.items()],
            value='1mo',  # Default value
            style={'width': '200px', 'backgroundColor': '#1a1a1a', 'color': 'black'},
            clearable=False
        )
    ], style={'marginBottom': '20px', 'display': 'flex', 'alignItems': 'center'}),
    
    # Table showing sector rankings
    dcc.Graph(id='sector-rankings-table'),
    
    # Detailed sector performance plots
    dcc.Graph(id='sector-performance-plots')
], style={'backgroundColor': 'black', 'minHeight': '100vh', 'padding': '20px'})

# Callback for updating sector growth figures
@app.callback(
    [Output('sector-rankings-table', 'figure'),
     Output('sector-performance-plots', 'figure')],
    [Input('time-period-selector', 'value')]
)
def update_sector_growth_figures(time_period):
    try:
        # Fetch and cache data for the selected time period
        stock_data = get_segmented_data(period=time_period)
        
        if not stock_data:
            # Return empty figures with error message
            empty_fig = go.Figure()
            empty_fig.add_annotation(
                text="No data available for selected time period",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(color="white", size=16)
            )
            empty_fig.update_layout(
                plot_bgcolor='black',
                paper_bgcolor='black'
            )
            return empty_fig, empty_fig
            
        return create_sector_growth_analysis(stock_data=stock_data, period=time_period)
    except Exception as e:
        print(f"Error updating sector growth figures: {e}")
        # Return empty figures with error message
        error_fig = go.Figure()
        error_fig.add_annotation(
            text=f"Error loading data: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(color="white", size=16)
        )
        error_fig.update_layout(
            plot_bgcolor='black',
            paper_bgcolor='black'
        )
        return error_fig, error_fig