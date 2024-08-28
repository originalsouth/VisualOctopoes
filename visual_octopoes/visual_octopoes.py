import json
from itertools import chain

import dash_cytoscape as cyto
from dash import Dash, html
from dash.dependencies import Input, Output
from xtdb_client import XTDBClient

cyto.load_extra_layouts()


class XTDBSession:
    def __init__(selfless, xtdb_node: str):
        selfless.node = xtdb_node
        selfless.connect(selfless.node)

    def connect(selfless, xtdb_node: str):
        selfless.client = XTDBClient("http://localhost:3000", xtdb_node, 7200)

    @property
    def oois(selfless):
        return list(
            chain.from_iterable(
                selfless.client.query("{:query {:find [(pull ?var [*])] :where [[?var :object_type]]}}")
            )
        )

    @property
    def origins(selfless):
        return list(
            chain.from_iterable(
                selfless.client.query(
                    '{:query {:find [(pull ?var [*])] :where [[?var :type "Origin"]]}}'
                )
            )
        )

    @property
    def connectors(selfless):
        return list(
            chain.from_iterable(
                [
                    zip(
                        [origin["source"]] * len(origin["result"]),
                        origin["result"],
                        [origin] * len(origin["result"]),
                        [origin["origin_type"]] * len(origin["result"]),
                    )
                    for origin in selfless.origins
                    if len(origin["result"]) > 0
                ]
            )
        )

    @property
    def nodes(selfless):
        return [
            {"data": {"id": ooi["xt/id"], "label": ooi["object_type"], "info": ooi}}
            for ooi in selfless.oois
        ]

    @property
    def edges(selfless):
        return [
            {"data": {"source": source, "target": target, "info": info, "kind": kind}}
            for source, target, info, kind in selfless.connectors
        ]


app = Dash(__name__)

session = XTDBSession("0")

default_stylesheet = [
    {
        "selector": "node",
        "style": {
            "background-color": "#BFD7B5",
            "label": "data(label)"
        },
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
        cyto.Cytoscape(
            id="cytoscape",
            layout={
                "name": "dagre",
                "nodeDimensionsIncludeLabels": True,
                "rankSep": 500,
            },
            elements=session.nodes + session.edges,
            stylesheet=default_stylesheet,
            style={"width": "100%", "height": "100vh", "z-index": "0"},
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
