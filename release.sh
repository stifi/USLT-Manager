#!/bin/bash

pylupdate5 uslt_manager.pro 
/usr/lib/x86_64-linux-gnu/qt5/bin/linguist *.ts

pyrcc5 -o qrc_resources_rc.py uslt_manager.qrc

pep8 --max-line-length=100 uslt_manager.py  
pep8 --max-line-length=100 usltmodules/__init__.py
pep8 --max-line-length=100 usltmodules/dialogs.py
#pep8 --max-line-length=100 usltmodules/lngcodes.py 
pep8 --max-line-length=100 usltmodules/tagoperations.py
pep8 --max-line-length=100 usltmodules/tagwidget.py
pep8 --max-line-length=100 usltmodules/treeview.py
