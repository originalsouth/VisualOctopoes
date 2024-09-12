import hashlib
import json
import sys
import urllib.parse
from datetime import datetime, timezone
from itertools import chain

import dash_cytoscape as cyto
from dash import Dash, dcc, html, no_update
from dash.dependencies import Input, Output
from xtdb_client import XTDBClient

cyto.load_extra_layouts()


DEFAULT_XTDB_NODE = "0"


def colorize(a: str) -> str:
    seed = "137"
    h = int(hashlib.sha512((seed + a + seed).encode()).hexdigest(), 16)
    return f"#{(h & 0xFF0000) >> 16:02x}{(h & 0x00FF00) >> 8:02x}{(h & 0x0000FF):02x}"


class XTDBSession:
    def __init__(
        selfless,
        xtdb_node: str = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_XTDB_NODE,
    ):
        selfless.connect(xtdb_node)
        selfless.valid_time: datetime = datetime.now(timezone.utc)

    def connect(selfless, xtdb_node: str):
        selfless.node: str = xtdb_node
        selfless.client: XTDBClient = XTDBClient(
            "http://localhost:3000",
            xtdb_node,
            7200,
        )

    @property
    def elements(selfless):
        try:
            status = selfless.client.status()
        except Exception as e:
            status = {"error": str(e)}
        if "error" in status:
            return [
                {
                    "data": {
                        "id": "error",
                        "label": "Error",
                        "info": status | {"node": selfless.node, "default_node": DEFAULT_XTDB_NODE},
                    },
                    "style": {"background-color": colorize("error")},
                }
            ]
        else:
            oois = list(
                chain.from_iterable(
                    selfless.client.query(
                        "{:query {:find [(pull ?var [*])] :where [[?var :object_type]]}}",
                        valid_time=selfless.valid_time,
                    )
                )
            )
            origins = list(
                chain.from_iterable(
                    selfless.client.query(
                        '{:query {:find [(pull ?var [*])] :where [[?var :type "Origin"]]}}',
                        valid_time=selfless.valid_time,
                    )
                )
            )
            xtids = list(map(lambda ooi: ooi["xt/id"], oois))
            fake_null = False
            for origin in origins:
                if not origin["result"]:
                    origin["result"].append("fake_null")
                    fake_null = True
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
                    ]
                )
            )
            fakes = [
                {
                    "data": {
                        "id": fake,
                        "label": "Fake",
                        "info": {"error": "ooi not present in xtdb but found in origin", "xt/id": fake},
                    },
                    "style": {"background-color": "#FF0000"},
                }
                for fake in [
                    connector[0]
                    for connector in connectors
                    if connector[0] not in xtids
                ]
                + [
                    connector[1]
                    for connector in connectors
                    for connector in connectors
                    if connector[1] != "fake_null" and connector[1] not in xtids
                ]
            ]
            if fake_null:
                fakes.append(
                    {
                        "data": {
                            "id": "fake_null",
                            "label": "Null",
                            "info": {"error": "the origin pointing to this node has no result"},
                        },
                        "style": {"background-color": "#FF0000"},
                    }
                )
            for origin in origins:
                if "fake_null" in origin["result"]:
                    origin["result"].remove("fake_null")
            edges = [
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
            nodes = [
                {
                    "data": {
                        "id": ooi["xt/id"],
                        "label": ooi["object_type"],
                        "info": ooi,
                    },
                    "style": {"background-color": colorize(ooi["object_type"])},
                }
                for ooi in oois
            ]
            return nodes + fakes + edges


app = Dash(__name__, title="VisualOctopoesStudio", update_title=None)
session = XTDBSession()
base_elements = session.elements

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
            interval=997,
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
                "max-width": "calc(100vw - 230px)",
                "overflow-wrap": "break-word",
                "padding": "10px",
                "position": "absolute",
                "top": "10px",
                "white-space": "pre-wrap",
                "word-break": "break-all",
                "z-index": 1,
            },
        ),
        html.Div(
            [
                dcc.Input(
                    id="datetime",
                    type="text",
                    placeholder=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
                    style={
                        "background": "rgba(255, 255, 255, 0.5)",
                        "border": "1px solid rgba(0, 0, 0, 0.5)",
                        "border-radius": "10px",
                        "padding": "10px",
                        "width": "130px",
                        "z-index": "1",
                    },
                )
            ],
            style={
                "position": "absolute",
                "right": "10px",
                "top": "22px",
            },
        ),
    ]
)


@app.callback(
    Output("cytoscape", "elements"),
    Output("datetime", "placeholder"),
    Input("updater", "n_intervals"),
    Input("url", "search"),
    Input("datetime", "value"),
)
def update_graph(_, search, value):
    global session
    session.valid_time = datetime.now(timezone.utc)
    if value:
        try:
            new_time = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            new_time = datetime.now(timezone.utc)
        if session.valid_time != new_time:
            session.valid_time = new_time
    params = urllib.parse.parse_qs(search.lstrip("?"))
    xtdb_node = params.get("node", session.node)[0]
    if xtdb_node != session.node:
        session.connect(xtdb_node)
    global base_elements
    new_elements = session.elements
    if not new_elements:
        base_elements = new_elements
        return new_elements, session.valid_time
    elif any(element for element in new_elements if element not in base_elements):
        base_elements = new_elements
        return new_elements, session.valid_time
    else:
        return no_update, session.valid_time


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
