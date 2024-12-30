import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import pandas as pd
from utils.data_processing import get_segmented_data, sectors
import dash_bootstrap_components as dbc
import logging
import dash_table

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_heatmap(period="1mo"):
    """
    Creates a correlation heatmap for the given period using segmented stock data.

    Args:
        period (str): The time period for which to fetch the stock data (e.g., "1mo", "3mo").

    Returns:
        plotly.graph_objects.Figure: The generated heatmap figure.
    """
    logger.info(f"Creating heatmap for period: {period}")

    # Fetch segmented stock data for the specified period
    stock_data = get_segmented_data(period=period)
    
    if not stock_data:
        logger.warning("No stock data available for heatmap")
        return go.Figure()  # Return empty figure if no data
    
    # Initialize an empty DataFrame to hold percentage changes
    pct_change_df = pd.DataFrame()
    missing_symbols = []

    # Collect percentage changes for each stock symbol
    for symbol, data in stock_data.items():
        if not data.empty and 'Pct_Change' in data.columns:
            try:
                pct_change_df[symbol] = data['Pct_Change']
                logger.info(f"Added data for symbol: {symbol}")
            except Exception as e:
                logger.error(f"Error processing {symbol} for heatmap: {e}")
                missing_symbols.append(symbol)
        else:
            logger.warning(f"No data available for symbol: {symbol}")
            missing_symbols.append(symbol)

    # Log missing symbols
    if missing_symbols:
        logger.warning(f"Symbols missing data and excluded from heatmap: {missing_symbols}")

    if pct_change_df.empty:
        logger.warning("No percentage change data available for heatmap")
        return go.Figure()  # Return empty figure if no data

    logger.info(f"Total symbols included in heatmap: {len(pct_change_df.columns)}")

    # Reindex pct_change_df to include all symbols, filling missing with NaN
    all_symbols = [symbol for sector, symbols in sectors.items() for symbol in symbols]
    pct_change_df = pct_change_df.reindex(columns=all_symbols)
    
    # Log any symbols that were reindexed with NaN
    missing_in_pct_change = pct_change_df.columns[pct_change_df.isnull().all()].tolist()
    if missing_in_pct_change:
        logger.warning(f"Symbols with all NaN values and excluded from heatmap: {missing_in_pct_change}")
        pct_change_df = pct_change_df.drop(columns=missing_in_pct_change)

    # Calculate the correlation matrix
    correlation_matrix = pct_change_df.corr()
    logger.info("Correlation matrix calculated")

    # Create a heatmap to visualize the correlation matrix
    fig_corr = go.Figure(data=go.Heatmap(
        z=correlation_matrix.values,
        x=correlation_matrix.columns,
        y=correlation_matrix.columns,
        colorscale='Inferno',
        zmid=0,
        zsmooth='best'
    ))
    logger.info("Heatmap figure created")

    # Calculate sector boundaries for visual separation
    sector_boundaries = []
    current_position = 0
    sector_names = []
    for sector, tickers in sectors.items():
        current_position += len(tickers)
        sector_boundaries.append(current_position)
        sector_names.append(sector)
    logger.info("Sector boundaries calculated")

    # Add lines to plot sector divisions
    for boundary in sector_boundaries[:-1]:  # Exclude the last boundary
        # Vertical lines
        fig_corr.add_shape(
            type='line',
            x0=boundary - 0.5, y0=-0.5,
            x1=boundary - 0.5, y1=len(correlation_matrix.columns) - 0.5,
            line=dict(color='white', width=3)
        )

        # Horizontal lines
        fig_corr.add_shape(
            type='line',
            x0=-0.5, y0=boundary - 0.5,
            x1=len(correlation_matrix.columns) - 0.5, y1=boundary - 0.5,
            line=dict(color='white', width=3)
        )

    logger.info("Sector division lines added to heatmap")

    # Add a thick white diagonal line
    fig_corr.add_shape(
        type='line',
        x0=-0.5, y0=-0.5,
        x1=len(correlation_matrix.columns) - 0.5, y1=len(correlation_matrix.columns) - 0.5,
        line=dict(color='white', width=4)
    )
    logger.info("Diagonal line added to heatmap")

    # Add annotations for sector labels
    annotations = []
    start = 0
    for sector, tickers in sectors.items():
        end = start + len(tickers)
        annotations.append(dict(
            x=start + (end - start) / 2,
            y=-0.5,
            text=sector,
            showarrow=False,
            font=dict(size=10, color="white"),
            yshift=-50
        ))
        start = end

    fig_corr.update_layout(
        title=dict(
            text=f"Correlation Matrix of Daily Percentage Changes ({period})",
            font=dict(size=24, color="white")
        ),
        xaxis=dict(
            showgrid=False,
            range=[-0.5, len(correlation_matrix.columns) - 0.5],
            tickangle=45,
            tickfont=dict(color="white")
        ),
        yaxis=dict(
            showgrid=False,
            range=[-0.5, len(correlation_matrix.columns) - 0.5],
            tickfont=dict(color="white")
        ),
        plot_bgcolor='black',
        paper_bgcolor='black',
        margin=dict(l=0, r=50, t=50, b=100),
        annotations=annotations,
        height=800,
    )
    logger.info("Heatmap layout updated")

    return fig_corr

def create_data_availability_table(stock_data):
    """
    Creates a DataFrame indicating the availability of data for each symbol.

    Args:
        stock_data (dict): Dictionary containing stock data for each symbol.

    Returns:
        dash_table.DataTable: A Dash DataTable showing data availability.
    """
    availability = []
    for sector, symbols_list in sectors.items():
        for symbol in symbols_list:
            status = 'Available' if symbol in stock_data and not stock_data[symbol].empty else 'Missing'
            availability.append({'Sector': sector, 'Symbol': symbol, 'Data Status': status})
    
    df_availability = pd.DataFrame(availability)
    
    return dash_table.DataTable(
        id='data-availability-table',
        columns=[{"name": i, "id": i} for i in df_availability.columns],
        data=df_availability.to_dict('records'),
        style_cell={'textAlign': 'left', 'padding': '5px'},
        style_header={
            'backgroundColor': 'grey',
            'fontWeight': 'bold',
            'color': 'white'
        },
        style_data={
            'backgroundColor': 'black',
            'color': 'white'
        },
        style_data_conditional=[
            {
                'if': {
                    'filter_query': '{Data Status} = "Missing"',
                    'column_id': 'Data Status'
                },
                'backgroundColor': 'red',
                'color': 'white'
            },
            {
                'if': {
                    'filter_query': '{Data Status} = "Available"',
                    'column_id': 'Data Status'
                },
                'backgroundColor': 'green',
                'color': 'white'
            },
        ],
    )

# Define the layout for the Dashboard page
layout = html.Div([
    html.H1('Market Dashboard', style={'color': 'white', 'textAlign': 'center'}),
    
    # Correlation Heatmap Section
    html.Div([
        dcc.Dropdown(
            id='period-dropdown',
            options=[
                {'label': '1 Month', 'value': '1mo'},
                {'label': '3 Months', 'value': '3mo'},
                {'label': '6 Months', 'value': '6mo'},
                {'label': '1 Year', 'value': '1y'},
                {'label': '5 Years', 'value': '5y'},
                {'label': 'Max', 'value': 'max'}
            ],
            value='1mo',  # Default selection
            clearable=False
        ),
        dcc.Loading(
            id="loading-heatmap",
            type="default",
            children=dcc.Graph(
                id='correlation-heatmap',
                style={'marginBottom': '20px'}
            )
        ),
    ], style={'width': '80%', 'margin': 'auto'}),
    
    # Data Availability Table Section
    html.Div([
        html.H2('Data Availability', style={'color': 'white', 'textAlign': 'center'}),
        create_data_availability_table(get_segmented_data()),
    ], style={'width': '80%', 'margin': 'auto', 'paddingTop': '40px'}),
    
    # Add any additional dashboard components here
    
], style={'backgroundColor': 'black', 'minHeight': '100vh', 'padding': '20px'})

# Define callback to update the heatmap based on selected period
@dash.callback(
    Output('correlation-heatmap', 'figure'),
    [Input('period-dropdown', 'value')]
)
def update_heatmap(selected_period):
    """
    Updates the correlation heatmap based on the selected time period.

    Args:
        selected_period (str): The selected time period (e.g., "1mo", "3mo").

    Returns:
        plotly.graph_objects.Figure: The updated heatmap figure.
    """
    return create_heatmap(period=selected_period)