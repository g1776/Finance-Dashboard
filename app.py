# Import packages
from dash import Dash, html, dash_table, dcc, callback, Output, Input
import pandas as pd
import plotly.express as px
import dash_mantine_components as dmc


def load_data():
    df = pd.read_csv(r"C:\Users\grego\Downloads\Checking1.csv", header=None)

    # give the columns names, and drop the columns we don't need
    df.columns = ["Date", "Amount", "DROP", "DROP2", "Description"]
    df.drop(["DROP", "DROP2"], axis=1, inplace=True)

    # convert the date column to datetime
    df["Date"] = pd.to_datetime(df["Date"])

    # sort the dataframe by date
    df.sort_values(by="Date", inplace=True)

    return df


def clean_description(df):
    """Call this function to clean the description column of the dataframe."""

    descr_clean = df.copy()

    # remove all of these patterns from the description column
    patterns = [
        r"PURCHASE AUTHORIZED ON \d{2}/\d{2}",
        r"\b\w{16}\sCARD\s\d{4}\b",
        r"PURCHASE INTL AUTHORIZED ON \d{2}/\d{2}",
    ]
    for pattern in patterns:
        descr_clean["Description"] = (
            descr_clean["Description"].str.replace(pattern, "", regex=True).str.strip()
        )

    return descr_clean


def transactions_over_time(df):
    """Call this function to plot the transactions over time."""

    # clean the description column
    to_plot = clean_description(df)

    # Assign colors based on transaction values
    to_plot["Color"] = to_plot["Amount"].apply(lambda x: "green" if x >= 0 else "red")

    fig = px.bar(
        to_plot,
        x="Date",
        y="Amount",
        color="Color",
        title="Transactions Over Time",
        hover_data=["Description"],
        color_discrete_map={"green": "green", "red": "red"},
    )

    # make hover only show the description
    fig.update_traces(
        hovertemplate="<br>".join(["Date: %{x}", "Amount: %{y}", "Description: %{customdata[0]}"])
    )

    # remove the legend
    fig.update_layout(showlegend=False)

    return fig


def description_pie_chart(df, type="+", legend=False):
    """Call this function to plot the description pie chart, with the option to filter by type."""

    # clean the description column
    to_plot = clean_description(df)

    if type == "+":
        to_plot = to_plot[to_plot["Amount"] >= 0]
        title = "Top 10 Positive Transaction Types"
    elif type == "-":
        to_plot = to_plot[to_plot["Amount"] < 0]
        title = "Top 10 Negative Transaction Types"

    # get the top 10 descriptions
    to_plot = (
        to_plot.groupby(["Description"])["Description"]
        .count()
        .reset_index(name="Frequency")
        .sort_values(["Frequency"], ascending=False)
        .head(10)
    )

    fig = px.pie(
        to_plot, values="Frequency", names="Description", title=title, hover_data=["Description"]
    )

    # make hover only show the description
    fig.update_traces(hovertemplate="<br>".join(["Description: %{label}", "Frequency: %{value}"]))

    # toggle legend
    fig.update_layout(showlegend=legend)

    return dcc.Graph(figure=fig, id=f"{type}-pie-chart")


def create_table(df):
    columns, values = df.columns, df.values
    header = [html.Tr([html.Th(col) for col in columns])]
    rows = [
        html.Tr(
            [html.Td(cell) for cell in row],
            style={"background-color": "white" if i % 2 == 0 else "lightgray"},
        )
        for i, row in enumerate(values)
    ]
    table = [html.Thead(header), html.Tbody(rows)]

    table = html.Table(table)

    return table


df = load_data()

# Initialize the app - incorporate css
external_stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]
app = Dash(__name__, external_stylesheets=external_stylesheets)

# App layout
app.layout = dmc.Container(
    [
        dmc.Title("Transactions Dashboard", color="blue", size="h1", style={"margin-bottom": 20}),
        dmc.Title("Data snapshot", size="h3"),
        create_table(df.head(5)),
        dmc.Grid(
            [
                dmc.Col(
                    [dcc.Graph(figure=transactions_over_time(df), id="graph-placeholder")], span=12
                ),
                dmc.Col([description_pie_chart(df, type="+", legend=False)], span=6),
                dmc.Col([description_pie_chart(df, type="-", legend=True)], span=6),
            ]
        ),
    ],
    fluid=True,
)


# # Add controls to build the interaction
# @callback(
#     Output(component_id="controls-and-graph", component_property="figure"),
#     Input(component_id="controls-and-radio-item", component_property="value"),
# )
# def update_graph(col_chosen):
#     fig = px.histogram(df, x="continent", y=col_chosen, histfunc="avg")
#     return fig


# Run the app
if __name__ == "__main__":
    app.run_server(debug=True, dev_tools_hot_reload=True)
