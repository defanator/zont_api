"""
Zont API interface module
"""

__author__ = "Andrei Belov"
__license__ = "MIT"
__copyright__ = f"Copyright (c) {__author__}"

from .zont_api import ZontAPIException, ZontAPI, ZontDevice
from .version import __version__, __release__, __build__
