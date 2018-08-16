#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Eléments de visualisation (graphiques) appelés par app-irigo.py
"""
import dash
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html

import datetime as dt

import json

import math

import numpy as np

import pandas as pd

import plotly.graph_objs as go

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from textwrap import dedent as d

# Modules internes
from db import Session, Trajet, Etape, Ligne, Vehicule

from datavizelements import get_map_figure, get_barh, get_tsplot


def generate_table(dataframe, max_rows=10):
    return html.Table(
        # Header
        [html.Tr([html.Th(col) for col in dataframe.columns])]
        +
        # Body
        [
            html.Tr([html.Td(dataframe.iloc[i][col]) for col in dataframe.columns])
            for i in range(min(len(dataframe), max_rows))
        ]
    )


def get_dash():
    # Instanciation du Dash
    app = dash.Dash()

    # Ouverture d'une session vers la DB
    session = Session()

    # Récupération des trajets
    lastUts = (
        session.query(Etape.record_timestamp)
        .order_by(Etape.record_timestamp.desc())
        .first()[0]
    )
    results = (
        session.query(
            Etape.ecart,
            Trajet.latitude,
            Trajet.longitude,
            Trajet.destination,
            Trajet.id_trajet,
            Trajet.id_ligne,
            Ligne.nom_ligne,
        )
        .select_from(Etape)
        .join(Trajet)
        .join(Ligne)
        .filter(Etape.record_timestamp == lastUts)
    )

    session.close()

    # Contenu de l'app
    app.layout = html.Div(
        [
            html.H1("Irigo app", style={"text-align": "center"}),
            html.Div(
                children=[
                    html.Div(
                        [dcc.Graph(id="barh")],
                        style={"width": "50%", "display": "inline-block"},
                    ),
                    html.Div(
                        get_tsplot(), style={"width": "50%", "display": "inline-block"}
                    ),
                ],
                style={"width": "100%", "display": "inline-block"},
            ),
            html.Div(
                [
                    dcc.Dropdown(
                        id="select-ligne",
                        options=[
                            {"label": trajet.nom_ligne, "value": trajet.id_ligne}
                            for trajet in results
                        ],
                    )
                ]
            ),
            html.Div(dcc.Graph(id="map")),
            html.Div(
                [
                    dcc.Markdown(
                        d(
                            """
                **Données par point**

                Cliquez sur un point pour afficher les données relatives à celui-ci.
            """
                        )
                    ),
                    html.Table(id="click-data"),
                ],
                style={
                    "display": "inline-block",
                    "width": "100%",
                    "margin-left": "78px",
                },
            ),
        ]
    )

    @app.callback(Output("barh", "figure"), [Input("tsplot", "hoverData")])
    def plot_barh(hoverData):
        if not hoverData:
            return get_barh(lastUts)

        nb = len(hoverData["points"])
        if nb > 1:
            logging.warning("{} points hovered (should be 0 or 1).".format(nb))

        tt = dt.datetime.strptime(hoverData["points"][0]["x"], "%Y-%m-%d %H:%M")

        # bug des deux heures (lié à la timezone)
        tt -= dt.timedelta(hours=2)

        return get_barh(tt)

    @app.callback(
        dash.dependencies.Output("click-data", "children"),
        [dash.dependencies.Input("map", "clickData")],
    )
    def display_click_data(clickData):
        # nom de ligne
        # numéro de ligne
        # prochain arrêt
        # retard
        # Ouverture d'une session vers la DB
        session = Session()

        if clickData:
            query = (
                session.query(
                    Ligne.nom_ligne,
                    Ligne.num_ligne,
                    Vehicule.type_vehicule,
                    Vehicule.etat_vehicule,
                )
                .select_from(Trajet)
                .join(Ligne)
                .join(Vehicule)
                .filter(Trajet.id_trajet == clickData["points"][0]["customdata"])
            )
        else:
            query = (
                session.query(
                    Ligne.nom_ligne,
                    Ligne.num_ligne,
                    Vehicule.type_vehicule,
                    Vehicule.etat_vehicule,
                )
                .select_from(Trajet)
                .join(Ligne)
                .join(Vehicule)
            )

        df = pd.read_sql_query(query.statement, query.session.bind)

        session.close()

        return generate_table(df)

    @app.callback(
        Output("map", "figure"),
        [Input("select-ligne", "value"), Input("tsplot", "hoverData")],
    )
    def update_graph(value, hoverData):
        if not hoverData:
            return get_map_figure(lastUts, line=value)

        tt = dt.datetime.strptime(hoverData["points"][0]["x"], "%Y-%m-%d %H:%M")

        # bug des deux heures (lié à la timezone)
        tt -= dt.timedelta(hours=2)

        return get_map_figure(tt, line=value)

    app.css.append_css({"external_url": "https://codepen.io/chriddyp/pen/bWLwgP.css"})

    return app


def run_dash(docker=False):
    app = get_dash()
    if docker:
        app.run_server(host="0.0.0.0", port=8383)
    else:
        app.run_server(debug=True)


# Démarrage de l'app
if __name__ == "__main__":
    run_dash()
