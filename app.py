# app.py
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc

# Initialize Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True, external_stylesheets=[dbc.themes.DARKLY])
app.title = "Financial Dashboard"

# Define the main layout with a navigation bar and page content
app.layout = html.Div([
    # URL Location component for routing
    dcc.Location(id='url', refresh=False),
    
    # Navigation Bar
    dbc.Navbar(
        dbc.Container([
            dbc.NavbarBrand("Financial Dashboard", href="/", className="ms-2"),
            dbc.Nav([
                dbc.NavLink("Dashboard", href="/", active="exact"),
                dbc.NavLink("Analysis", href="/analysis", active="exact"),
                dbc.NavLink("Sector Growth", href="/sector-growth", active="exact"),
            ], className="ms-auto", navbar=True)
        ]),
        color="dark",
        dark=True,
        fixed="top"
    ),
    
    # Page Content
    html.Div(id='page-content', style={'marginTop': '80px', 'backgroundColor': 'black', 'minHeight': '100vh', 'padding': '20px'})
], style={'backgroundColor': 'black'})

# Move this to the bottom after creating app instance
from pages import dashboard, analysis, sector_growth

# Callback for page routing
@app.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def display_page(pathname):
    if pathname == '/analysis':
        return analysis.layout
    elif pathname == '/sector-growth':
        return sector_growth.layout
    else:
        return dashboard.layout

# Run the app
if __name__ == "__main__":
    app.run_server(debug=True, port=8050)