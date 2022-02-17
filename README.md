# cad-viewer-widget

A Jupyter widget to view CAD objects

`cad-viewer-widgets` has its origin in [Jupyter-CadQuery](https://github.com/bernhard-42/jupyter-cadquery), which now
has been split into 3 layers. This repo being the middle layer:

1. **[three-cad-viewer](https://github.com/bernhard-42/three-cad-viewer)**
   This is the complete CAD viewer written in Javascript with _[threejs](https://github.com/mrdoob/three.js/)_ being the only dependency.

2. **cad-view-widget** (this repository)
   A thin layer on top of _cad-viewer-widget_ that wraps the CAD viewer into an [ipywidget](https://github.com/jupyter-widgets/ipywidgets). The API documentation can be found [here](https://bernhard-42.github.io/cad-viewer-widget/cad_viewer_widget/index.html)

3. **[Jupyter-CadQuery](https://github.com/bernhard-42/jupyter-cadquery)** A [CadQuery](https://github.com/CadQuery/cadquery) viewer, collecting and tessellating CadQuery objects, using cad-view-widget to visualize the objects

Click on the "launch binder" icon to start _cad-viewer-widget_ on binder:

[![Binder: Latest development version](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/bernhard-42/cad-viewer-widget/master?urlpath=lab&filepath=notebooks)

## Examples

- [Tests and demos](notebooks/Tests-and-demos.ipynb): Demonstrating the features using the sample tesssellations in [./examples](./examples)
- [Classic OCC Bottle](notebooks/Classic-OCC-Bottle.ipynb): A real CAD example based on [python-occ](https://github.com/tpaviot/pythonocc-core)

## Installation

To install use pip:

    $ pip install cad_viewer_widget

For a development installation (requires [Node.js](https://nodejs.org) and [Yarn version 1](https://classic.yarnpkg.com/)),

    $ git clone https://github.com/bernhard-42/cad-viewer-widget.git
    $ cd cad-viewer-widget
    $ pip install -e .
    $ jupyter nbextension install --py --symlink --overwrite --sys-prefix cad_viewer_widget
    $ jupyter nbextension enable --py --sys-prefix cad_viewer_widget

When actively developing your extension for JupyterLab, run the command:

    $ jupyter labextension develop --overwrite cad_viewer_widget

Then you need to rebuild the JS when you make a code change:

    $ cd js
    $ yarn run build

You then need to refresh the JupyterLab page when your javascript changes.
