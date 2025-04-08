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
or for a specific node `$NODE` and `$URL` (`http://host:port`):
```
poetry run visual_octopoes/visual_octopoes.py $NODE $URL
```
Node and URL can be additionally be supplied as a parameter in the total URL as such http://127.0.0.1:8050/?node=0&url=http://localhost:3000.

### Configuration
VisualOctopoesStudio takes the following URL parameters:
| Parameter name | Description                              | Values     | Default               | Example                   |
|:---------------|:-----------------------------------------|:-----------|:----------------------|:--------------------------|
|`node`          |XTDB Node                                 | string     |`0`                    |`node=0`                   |
|`node`          |XTDB URL                                  | string     |`http://localhost:3000`|`url=http://localhost:3000`|
|`nonull`        |Hide NULL node                            | `1` or `0` |`0`                    |`nonull=0`                 |
|`nofakes`       |Hide fake (implied but not present) nodes | `1` or `0` |`0`                    |`nofakes=0`                |
|`norefs`        |Hide OOI references                       | `1` or `0` |`0`                    |`norefs=0`                 |
|`noorigins`     |Hide Origins                              | `1` or `0` |`0`                    |`noorigins=0`              |
