# Import packages
from dash import Dash, html, dash_table, dcc, callback, Output, Input
import pandas as pd
import plotly.express as px
import dash_mantine_components as dmc
import json


# load the dashboard
SETTINGS = json.load(open("settings.json", "r"))


def load_data(account_settings):
    # TODO: We should really only be looking at expenses from checkings, and additionally load in the savings account for income
    df = pd.read_csv(account_settings["filePath"], header=None)

    # give the columns names, and drop the columns we don't need (any that start with DROP)
    df.columns = account_settings["columns"]
    to_drop = [col for col in df.columns if col.startswith("DROP")]
    df.drop(to_drop, axis=1, inplace=True)

    if "Date" in df.columns:
        # convert the date column to datetime
        df["Date"] = pd.to_datetime(df["Date"])

        # sort the dataframe by date
        df.sort_values(by="Date", inplace=True)
    else:
        print("Expected a Date column, but none was found.")

    return df


def clean_description(df, account_type):
    """
    Call this function to clean the description column of the dataframe.

    account_type can be "savings" or "checking"
    """

    if "Description" not in df.columns:
        print("Expected a Description column, but none was found.")
        return df

    descr_clean = df.copy()

    # remove all of these patterns from the description column
    patterns = SETTINGS[account_type]["patterns"]
    for pattern in patterns:
        print(pattern)
        descr_clean["Description"] = (
            descr_clean["Description"].str.replace(pattern, "", regex=True).str.strip()
        )

    custom_categories = SETTINGS[account_type]["customCategories"]

    # replace the custom categories
    for custom_category in custom_categories:
        # if the custom category is in the description, replace it
        descr_clean.loc[
            descr_clean["Description"].str.contains(custom_category), "Description"
        ] = custom_categories[custom_category]

    # if the description is over 30 characters, cut it off and add ...
    descr_clean["Description"] = descr_clean["Description"].apply(
        lambda x: x[:30] + "..." if len(x) > 30 else x
    )

    return descr_clean


def transactions_over_time(checking, savings):
    """Call this function to plot the transactions over time."""

    # clean the description column
    c_clean = clean_description(checking, "checking")
    c_clean["account"] = "checking"
    s_clean = clean_description(savings, "savings")
    s_clean["account"] = "savings"

    # join checking and savings, ignoring transfers between accounts
    # - income comes from positive savings transactions
    # - expenses come from negative checking transactions
    to_plot = pd.concat(
        [
            c_clean[c_clean["Amount"] < 0],  # grab expenses from checking
            s_clean[s_clean["Amount"] > 0],  # grab income from savings
        ]
    )

    # Assign colors based on transaction values
    to_plot["Color"] = to_plot["Amount"].apply(lambda x: "green" if x >= 0 else "red")

    # sort by date
    to_plot.sort_values(by="Date", inplace=True)

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
    if type == "+":
        to_plot = clean_description(df, "savings")
        to_plot = to_plot[to_plot["Amount"] > 0]
        title = "Income by Category"
    elif type == "-":
        to_plot = clean_description(df, "checking")
        to_plot = to_plot[to_plot["Amount"] < 0]
        to_plot["Amount"] *= -1
        title = "Expenses by Category"

    # get the top 10 descriptions by total value
    to_plot = (
        to_plot.groupby("Description")
        .sum("Amount")
        .reset_index()
        .rename(columns={"Amount": "Total Amount"})
        .sort_values(by="Total Amount", ascending=False)
        .head(10)
    )

    fig = px.pie(
        to_plot,
        values="Total Amount",
        names="Description",
        title=title,
        hover_data=["Description"],
    )

    # make hover only show the description
    fig.update_traces(
        hovertemplate="<br>".join(["Description: %{label}", "Total Amount: %{value}"])
    )

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


checking = load_data(SETTINGS["checking"])
savings = load_data(SETTINGS["savings"])

# Initialize the app - incorporate css
external_stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]
app = Dash(__name__, external_stylesheets=external_stylesheets)

# App layout
app.layout = dmc.Container(
    [
        dmc.Title("Transactions Dashboard", color="blue", size="h1", style={"margin-bottom": 20}),
        dmc.Title("Data snapshot", size="h3"),
        dmc.Grid(
            [
                dmc.Col(
                    [
                        dmc.Title("Checking", size="h4"),
                        create_table(checking.head(5)),
                    ],
                    span=6,
                ),
                dmc.Col(
                    [
                        dmc.Title("Savings", size="h4"),
                        create_table(savings.head(5)),
                    ],
                    span=6,
                ),
            ]
        ),
        dmc.Grid(
            [
                dmc.Col(
                    [
                        dcc.Graph(
                            figure=transactions_over_time(checking, savings),
                            id="graph-placeholder",
                        )
                    ],
                    span=12,
                ),
                dmc.Col([description_pie_chart(savings, type="+", legend=True)], span=6),
                dmc.Col([description_pie_chart(checking, type="-", legend=True)], span=6),
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
