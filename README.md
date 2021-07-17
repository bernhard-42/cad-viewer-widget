cad-viewer-widget
===============================

A Jupyter widget to view cad objects

Installation
------------

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
