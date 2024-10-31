#!/usr/bin/env python

import hashlib
import json
import sys
import urllib.parse
from copy import deepcopy
from datetime import datetime, timezone
from itertools import chain

import dash_cytoscape as cyto
from dash import Dash, dcc, html
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
        windows95,
        xtdb_node: str = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_XTDB_NODE,
    ):
        windows95.connect(xtdb_node)
        windows95.valid_time: datetime = datetime.now(timezone.utc)

    def connect(
        windows95,
        xtdb_node: str,
    ) -> None:
        windows95.node: str = xtdb_node
        windows95.client: XTDBClient = XTDBClient(
            "http://localhost:3000",
            xtdb_node,
            7200,
        )

    def elements(
        windows95,
        add_fakes: bool = True,
        add_fake_null: bool = True,
    ) -> list[dict]:
        try:
            status = windows95.client.status()
        except Exception as e:
            status = {"error": str(e)}
        if isinstance(status, dict) and "error" in status:
            return [
                {
                    "data": {
                        "id": "error",
                        "label": "Error",
                        "info": status
                        | {
                            "node": windows95.node,
                            "default_node": DEFAULT_XTDB_NODE,
                            "xt/id": "error",
                        },
                        "profile": "undifined",
                    },
                    "style": {"background-color": colorize("error")},
                }
            ]
        else:
            oois = list(
                chain.from_iterable(
                    windows95.client.query(
                        "{:query {:find [(pull ?var [*])] :where [[?var :object_type]]}}",
                        valid_time=windows95.valid_time,
                    )
                )
            )
            origins = list(
                chain.from_iterable(
                    windows95.client.query(
                        '{:query {:find [(pull ?var [*])] :where [[?var :type "Origin"]]}}',
                        valid_time=windows95.valid_time,
                    )
                )
            )
            origin_parameters = list(
                chain.from_iterable(
                    windows95.client.query(
                        '{:query {:find [(pull ?var [*])] :where [[?var :type "OriginParameter"]]}}',
                        valid_time=windows95.valid_time,
                    )
                )
            )
            scan_profiles = list(
                chain.from_iterable(
                    windows95.client.query(
                        '{:query {:find [(pull ?var [*])] :where [[?var :type "ScanProfile"]]}}',
                        valid_time=windows95.valid_time,
                    )
                )
            )
            xtids = list(map(lambda ooi: ooi["xt/id"], oois))
            fake_null = False
            for origin in origins:
                if not origin["result"] and add_fake_null:
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
                            [origin["xt/id"]] * len(origin["result"]),
                        )
                        for origin in origins
                    ]
                )
            )
            parameters = {op["origin_id"]: op for op in origin_parameters}
            profiles = {sp["reference"]: sp for sp in scan_profiles}
            profile_borders = {
                "declared": "solid",
                "inherited": "dashed",
                "empty": "none",
            }
            fakes = (
                [
                    {
                        "data": {
                            "id": fake,
                            "label": "Fake",
                            "info": {
                                "error": "ooi not present in xtdb but found in origin",
                                "xt/id": fake,
                            },
                            "profile": "undefined",
                        },
                        "style": {"background-color": "red"},
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
                if add_fakes
                else []
            )
            if fake_null:
                fakes.append(
                    {
                        "data": {
                            "id": "fake_null",
                            "label": "Null",
                            "info": {
                                "error": "the origin pointing to this node has no result",
                                "xt/id": "fake_null",
                            },
                            "profile": "undefined",
                        },
                        "style": {"background-color": "red"},
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
                        "parameter": parameters[id] if id in parameters else None
                    },
                    "style": {
                        "line-color": colorize(kind),
                        "target-arrow-color": colorize(kind),
                    },
                }
                for source, target, info, kind, id in connectors
            ]
            nodes = [
                {
                    "data": {
                        "id": ooi["xt/id"],
                        "label": ooi["object_type"],
                        "info": ooi,
                        "profile": (
                            profiles[ooi["xt/id"]] if ooi["xt/id"] in profiles else None
                        ),
                    },
                    "style": {
                        "background-color": colorize(ooi["object_type"]),
                        "border-width": (
                            f"{2 * int(profiles[ooi["xt/id"]]["level"])}px"
                            if ooi["xt/id"] in profiles
                            else "10px"
                        ),
                        "border-color": "black" if ooi["xt/id"] in profiles else "red",
                        "border-style": (
                            profile_borders[profiles[ooi["xt/id"]]["scan_profile_type"]]
                            if ooi["xt/id"] in profiles
                            and profiles[ooi["xt/id"]]["scan_profile_type"]
                            in profile_borders
                            else "double"
                        ),
                    },
                }
                for ooi in oois
            ]
            return nodes + fakes + edges


app = Dash(__name__, title="VisualOctopoesStudio", update_title=None)
session = XTDBSession()
base_elements = [
    {
        "data": {
            "id": "init",
            "label": "Initializing...",
            "info": {
                "current_node": session.node,
                "default_node": DEFAULT_XTDB_NODE,
                "xt/id": "init",
            },
            "profile": "undefined",
        },
        "style": {"background-color": colorize("error")},
    }
]

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
            interval=257,
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
                "max-height": "80vh",
                "max-width": "70vw",
                "overflow-wrap": "break-word",
                "overflow-y": "auto",
                "padding": "10px",
                "position": "absolute",
                "top": "10px",
                "white-space": "pre-wrap",
                "word-break": "break-all",
                "z-index": 1,
            },
        ),
        html.Pre(
            id="profile",
            contentEditable="true",
            style={
                "background": "rgba(255, 255, 255, 0.5)",
                "border": "1px solid rgba(0, 0, 0, 0.5)",
                "border-radius": "10px",
                "right": "10px",
                "max-height": "90vh",
                "max-width": "20vw",
                "overflow-wrap": "break-word",
                "overflow-y": "auto",
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
                    placeholder=datetime.now(timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%S"
                    ),
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


ELEMENT_CACHE = []


@app.callback(
    Output("cytoscape", "elements"),
    Output("datetime", "placeholder"),
    Input("updater", "n_intervals"),
    Input("url", "search"),
    Input("datetime", "value"),
    Input("cytoscape", "elements"),
)
def update_graph(_, search, value, current_elements):
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
    add_fakes = False if params.get("nofakes", "0")[0] == "1" else True
    add_fake_null = False if params.get("nonull", "0")[0] == "1" else True
    if session.node != xtdb_node:
        session.connect(xtdb_node)
    new_elements = session.elements(add_fakes, add_fake_null)
    curdict = {
        element["data"]["info"]["xt/id"]: element for element in current_elements
    }
    update_elements = sorted(
        [
            (
                {
                    **element,
                    "position": curdict[element["data"]["info"]["xt/id"]]["position"],
                }
                if element["data"]["info"]["xt/id"] in curdict
                and "position" in curdict[element["data"]["info"]["xt/id"]]
                else element
            )
            for element in new_elements
        ],
        key=lambda element: element["data"]["info"]["xt/id"],
    )
    global ELEMENT_CACHE
    if len(current_elements) <= 1:
        return update_elements, session.valid_time
    elif update_elements != ELEMENT_CACHE:
        ELEMENT_CACHE = deepcopy(update_elements)
        return update_elements, session.valid_time
    else:
        return current_elements, session.valid_time


REGISTER = "Press a node or edge for content info"


@app.callback(
    Output("info", "children"),
    Output("profile", "children"),
    Output("profile", "style"),
    Input("cytoscape", "selectedNodeData"),
    Input("cytoscape", "selectedEdgeData"),
    Input("profile", "style"),
)
def display_info(node_info, edge_info, profile_style):
    global REGISTER
    global session
    retval1 = "Press a node or edge for content info"
    retval2 = None
    retval3 = {**profile_style, "display": "none"}

    if node_info:
        if "display" in retval3:
            retval3.pop("display")
        retval1 = json.dumps(node_info[0]["info"], sort_keys=True, indent=2)
        retval2 = "\n" + json.dumps(node_info[0]["profile"], sort_keys=True, indent=2)
        if retval1 == REGISTER:
            data = session.client.history(node_info[0]["id"], True, True)
            retval1 = json.dumps(data, sort_keys=True, indent=2)
            profile = session.client.history(
                node_info[0]["profile"]["xt/id"], True, True
            )
            retval2 = "\n" + json.dumps(profile, sort_keys=True, indent=2)

    if edge_info:
        retval1 = json.dumps(edge_info[0]["info"], sort_keys=True, indent=2)
        if edge_info[0]["parameter"]:
            if "display" in retval3:
                retval3.pop("display")
            retval2 = "\n" + json.dumps(edge_info[0]["parameter"], sort_keys=True, indent=2)
        if retval1 == REGISTER:
            data = session.client.history(edge_info[0]["info"]["xt/id"], True, True)
            retval1 = json.dumps(data, sort_keys=True, indent=2)
            if edge_info[0]["parameter"]:
                if "display" in retval3:
                    retval3.pop("display")
                data = session.client.history(edge_info[0]["parameter"]["xt/id"], True, True)
                retval2 = "\n" + json.dumps(data, sort_keys=True, indent=2)

    REGISTER = retval1
    return retval1, retval2, retval3


if __name__ == "__main__":
    app.run(debug=True)
