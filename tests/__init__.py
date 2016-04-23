# -*- coding: utf-8 -*-


import os
import sys

base = os.path.normpath(os.path.join(os.path.abspath(__file__), "../.."))
sys.path.append(base)

from .spec import *
from .rpc import *
