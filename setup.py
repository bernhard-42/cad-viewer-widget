from __future__ import print_function
from setuptools import setup, find_packages
import os
import sys
from os.path import join as pjoin
from distutils import log

from jupyter_packaging import (
    create_cmdclass,
    install_npm,
    ensure_targets,
    combine_commands,
)


here = os.path.dirname(os.path.abspath(__file__))

# log.set_verbosity(log.DEBUG)
# log.info('setup.py entered')
# log.info('$PATH=%s' % os.environ['PATH'])

name = "cad_viewer_widget"
LONG_DESCRIPTION = "A Jupyter widget to view cad objects"

js_dir = pjoin(here, "js")

# Representative files that should exist after a successful build
jstargets = [
    pjoin(js_dir, "dist", "index.js"),
]

data_files_spec = [
    ("share/jupyter/nbextensions/cad-viewer-widget", "cad_viewer_widget/nbextension", "*.*"),
    ("share/jupyter/labextensions/cad-viewer-widget", "cad_viewer_widget/labextension", "**"),
    ("share/jupyter/labextensions/cad-viewer-widget", ".", "install.json"),
    ("etc/jupyter/nbconfig/notebook.d", ".", "cad-viewer-widget.json"),
]

cmdclass = create_cmdclass("jsdeps", data_files_spec=data_files_spec)
cmdclass["jsdeps"] = combine_commands(
    install_npm(js_dir, npm=["yarn"], build_cmd="build:prod"),
    ensure_targets(jstargets),
)

# Get cad_viewer_widget version
sys.path.insert(0, "./cad_viewer_widget")
from _version import __version__

setup_args = dict(
    name=name,
    version=__version__,
    description="A Jupyter widget to view cad objects",
    long_description=LONG_DESCRIPTION,
    include_package_data=True,
    install_requires=["ipywidgets>=7.6.0"],
    extras_require={"dev": ["twine", "bumpversion", "pydoc3"]},
    packages=find_packages(),
    zip_safe=False,
    cmdclass=cmdclass,
    author="Bernhard Walter",
    author_email="b_walter@arcor.de",
    url="https://github.com/bernhard-42/cad-viewer-widget",
    keywords=[
        "ipython",
        "jupyter",
        "widgets",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Framework :: IPython",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Multimedia :: Graphics",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
)

setup(**setup_args)
