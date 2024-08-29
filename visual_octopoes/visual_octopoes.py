import json
import os
import urllib.parse
from itertools import chain

import dash_cytoscape as cyto
from dash import Dash, dcc, html, no_update
from dash.dependencies import Input, Output
from xtdb_client import XTDBClient

cyto.load_extra_layouts()
os.environ["PYTHONHASHSEED"] = "2084"


def colorize(a: str) -> str:
    h = hash(a)
    return f"#{(h & 0xFF0000) >> 16:02x}{(h & 0x00FF00) >> 8:02x}{(h & 0x0000FF):02x}"


class XTDBSession:
    def __init__(selfless, xtdb_node: str):
        selfless.connect(xtdb_node)

    def connect(selfless, xtdb_node: str):
        selfless.node = xtdb_node
        selfless.client = XTDBClient("http://localhost:3000", xtdb_node, 7200)

    @property
    def nodes(selfless):
        oois = list(
            chain.from_iterable(
                selfless.client.query(
                    "{:query {:find [(pull ?var [*])] :where [[?var :object_type]]}}"
                )
            )
        )
        return [
            {
                "data": {"id": ooi["xt/id"], "label": ooi["object_type"], "info": ooi},
                "style": {"background-color": colorize(ooi["object_type"])},
            }
            for ooi in oois
        ]

    @property
    def edges(selfless):
        origins = list(
            chain.from_iterable(
                selfless.client.query(
                    '{:query {:find [(pull ?var [*])] :where [[?var :type "Origin"]]}}'
                )
            )
        )
        connectors = list(
            chain.from_iterable(
                [
                    zip(
                        [origin["source"]] * len(origin["result"]),
                        origin["result"],
                        [origin] * len(origin["result"]),
                        [origin["origin_type"]] * len(origin["result"]),
                    )
                    for origin in origins
                    if len(origin["result"]) > 0
                ]
            )
        )
        return [
            {
                "data": {
                    "source": source,
                    "target": target,
                    "info": info,
                    "kind": kind,
                },
                "style": {
                    "line-color": colorize(kind),
                    "target-arrow-color": colorize(kind),
                },
            }
            for source, target, info, kind in connectors
        ]


app = Dash(__name__)

session = XTDBSession("0")
base_elements = session.nodes + session.edges


default_stylesheet = [
    {
        "selector": "node",
        "style": {"background-color": "#BFD7B5", "label": "data(label)"},
    },
    {
        "selector": "edge",
        "style": {
            "curve-style": "bezier",
            "label": "data(kind)",
            "line-color": "#A3C4BC",
            "target-arrow-color": "#A3C4BC",
            "target-arrow-shape": "triangle",
            "text-rotation": "autorotate",
        },
    },
]

app.layout = html.Div(
    [
        dcc.Interval(
            id="updater",
            interval=1913,
        ),
        dcc.Location(id="url", refresh=False),
        cyto.Cytoscape(
            id="cytoscape",
            layout={
                "name": "dagre",
                "nodeDimensionsIncludeLabels": True,
                "rankSep": 500,
            },
            elements=base_elements,
            stylesheet=default_stylesheet,
            style={
                "width": "100%",
                "height": "100vh",
                "z-index": "0",
            },
            zoom=1.0,
            minZoom=60.0**-1,
            maxZoom=60.0,
        ),
        html.Pre(
            id="info",
            contentEditable="true",
            style={
                "background": "rgba(255, 255, 255, 0.5)",
                "border": "1px solid rgba(0, 0, 0, 0.5)",
                "border-radius": "10px",
                "left": "10px",
                "padding": "10px",
                "position": "absolute",
                "top": "10px",
                "white-space": "pre-wrap",
                "z-index": 1,
            },
        ),
    ]
)


@app.callback(
    Output("cytoscape", "elements"),
    Input("updater", "n_intervals"),
    Input("url", "search"),
)
def update_graph(_, search):
    params = urllib.parse.parse_qs(search.lstrip("?"))
    xtdb_node = params.get("node", "0")[0]
    if xtdb_node != session.node:
        session.connect(xtdb_node)
    global base_elements
    new_elements = session.nodes + session.edges
    if [element for element in new_elements if element not in base_elements]:
        base_elements = new_elements
        return new_elements
    else:
        return no_update


@app.callback(
    Output("info", "children"),
    Input("cytoscape", "selectedNodeData"),
    Input("cytoscape", "selectedEdgeData"),
)
def display_info(node_info, edge_info):
    if node_info:
        return json.dumps(node_info[0]["info"], sort_keys=True, indent=2)

    if edge_info:
        return json.dumps(edge_info[0]["info"], sort_keys=True, indent=2)

    return "Press a node or edge for content info"


if __name__ == "__main__":
    app.run(debug=True)
