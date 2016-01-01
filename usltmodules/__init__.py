# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Stefan Gansinger
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

"""Modules for the USLT manager."""

from .tagoperations import *
from .lngcodes import *
from .treeview import *
from .dialogs import *
from .tagwidget import *

__all__ = ['ID3', 'ID3Tag', 'ISO639_2_CODES', 'FileTree', 'TagFileSystemModel',
           'AddLyricsDialog', 'SaveChangesDialog', 'TagWidget']
