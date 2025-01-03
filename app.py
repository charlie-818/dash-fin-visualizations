# app.py
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

# Initialize the Dash app with Dash Pages enabled
app = dash.Dash(
    __name__,
    use_pages=True,  # Enable Dash Pages
    suppress_callback_exceptions=True,
    external_stylesheets=[dbc.themes.DARKLY]
)
app.title = "Financial Dashboard"

# Import pages AFTER app initialization
from pages import dashboard, research, sector_growth, etf

# Define the navigation bar with logo using Dash Bootstrap Components
navbar = dbc.NavbarSimple(
    children=[
        dbc.NavItem(dcc.Link("Heatmap", href="/", className="nav-link")),
        dbc.NavItem(dcc.Link("Sector Growth", href="/sector-growth", className="nav-link")),
        dbc.NavItem(dcc.Link("ETF Analysis", href="/etf-analysis", className="nav-link")),
        dbc.NavItem(dcc.Link("Research", href="/research", className="nav-link")),
        dbc.NavItem(dcc.Link("Financials", href="/financials", className="nav-link")),
        dbc.NavItem(dcc.Link("Insider Trading", href="/insider-trades", className="nav-link")),
        dbc.NavItem(dcc.Link("Data", href="/data", className="nav-link")),
    ],
    brand=[
        html.Img(
            src="/assets/logo.png",
            height="120px",
            style={
                'marginRight': '10px',
                'objectFit': 'contain',
                'padding': '5px'
            }
        ),
        "Financial Dashboard"
    ],
    brand_href="/",
    color="#2E2E2E",
    dark=True,
    fluid=True,
    style={
        'padding': '10px',
        'height': '90px'
    }
)

# Define the overall app layout
app.layout = html.Div([
    navbar,
    dash.page_container  # Automatically handles page rendering
], style={'backgroundColor': '#2E2E2E'})

server = app.server  # Expose the server variable for deployments

if __name__ == "__main__":
    app.run_server(debug=True, port=8050)