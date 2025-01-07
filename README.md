# Visual Octopoes Studio

A graphical browser interface for Octopoes

## Install
```
poetry install
```

## Run
```
poetry run visual_octopoes/visual_octopoes.py
```
or for a specific node `$NODE`:
```
poetry run visual_octopoes/visual_octopoes.py $NODE
```
Nodes can be additionally be supplied as a parameter in the URL as such http://127.0.0.1:8050/?node=0.
The NULL node, and fake nodes can be suppressed by setting `nonull=1` or `nofakes=1` as a URL parameter.

VisualOctopoesStudio takes the following URL parameters:
| Parameter name | Description                              | Values     | Default | Example   |
|:---------------|:-----------------------------------------|:-----------|:--------|:----------|
|`node`          |XTDB Node                                 | string     |`0`      |`node=0`   |
|`nonull`        |Hide NULL node                            | `1` or `0` |`0`      |`nonull=0` |
|`nofakes`       |Hide fake (implied but not present) nodes | `1` or `0` |`0`      |`nofakes=0`|
|`norefs`        |Hide OOI references                       | `1` or `0` |`0`      |`norefs=0`|
