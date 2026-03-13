#!/usr/bin/env python

from os import path, walk

import sys
from setuptools import setup, find_packages

NAME = 'Orange3-Ancient-Greek-Metrics'
DOCUMENTATION_NAME = 'Ancient Greek Metrics'

VERSION = "0.0.7"

DESCRIPTION = "Add-on for analyzing Ancient Greek metrics"
with open(path.join(path.dirname(__file__), 'README.md'), encoding='utf-8') as f:
    LONG_DESCRIPTION = f.read()
    
LICENSE = "BSD"

KEYWORDS = (
    # [PyPi](https://pypi.python.org) packages with keyword "orange3 add-on"
    # can be installed using the Orange Add-on Manager
    'orange3 add-on',
)

PACKAGES = find_packages()

PACKAGE_DATA = {
}

DATA_FILES = [
    # Data files that will be installed outside site-packages folder
]

INSTALL_REQUIRES = [
    'chardet>=3.0.2,<5.0.0',
    'Orange3 >= 3.38',
    'Orange3-Textable >= 3.2.7',
    'LTTL >= 2.1.0',
    'AnyQt',
    'PyQt6',
    'PyQt6-WebEngine',
]

ENTRY_POINTS = {
    # Entry points that marks this package as an orange add-on. If set, addon will
    # be shown in the add-ons manager even if not published on PyPi.
    'orange3.addon': (
        'ancient_greek_metrics = orangecontrib.ancient_greek_metrics',
    ),
    # Entry point used to specify packages containing tutorials accessible
    # from welcome screen. Tutorials are saved Orange Workflows (.ows files).
    'orange.widgets.tutorials': (
        # Syntax: any_text = path.to.package.containing.tutorials
        'ancient_greek_metrics_tutorials = orangecontrib.ancient_greek_metrics.tutorials',
    ),

    # Entry point used to specify packages containing widgets.
    'orange.widgets': (
        # Syntax: category name = path.to.package.containing.widgets
        # Widget category specification can be seen in
        #    orangecontrib/example/widgets/__init__.py
        'Ancient Greek Metrics = orangecontrib.ancient_greek_metrics.widgets',
    ),

    # Register widget help
    "orange.canvas.help": (
        'html-index = orangecontrib.ancient_greek_metrics.widgets:WIDGET_HELP_PATH',)
}

NAMESPACE_PACKAGES = ["orangecontrib"]

TEST_SUITE = "orangecontrib.ancient_greek_metrics.tests.suite"


def include_documentation(local_dir, install_dir):
    global DATA_FILES
    # On vérifie si le dossier existe, sinon on ignore silencieusement
    if not path.exists(local_dir):
        print(f"Warning: Directory '{local_dir}' not found. Skipping documentation.")
        return

    doc_files = []
    for dirpath, dirs, files in walk(local_dir):
        if files: # On n'ajoute que s'il y a des fichiers
            doc_files.append((dirpath.replace(local_dir, install_dir),
                              [path.join(dirpath, f) for f in files]))
    DATA_FILES.extend(doc_files)

if __name__ == '__main__':
    #include_documentation('doc/build/html', 'help/orange3-ancient-greek-metrics')
    setup(
        name=NAME,
        version=VERSION,
        description=DESCRIPTION,
        long_description=LONG_DESCRIPTION,
        long_description_content_type='text/markdown',
        license=LICENSE,
        packages=PACKAGES,
        package_data=PACKAGE_DATA,
        data_files=DATA_FILES,
        install_requires=INSTALL_REQUIRES,
        entry_points=ENTRY_POINTS,
        keywords=KEYWORDS,
        namespace_packages=NAMESPACE_PACKAGES,
        test_suite=TEST_SUITE,
        include_package_data=True,
        zip_safe=False,
    )
