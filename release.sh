#!/bin/bash

pylupdate5 uslt_manager.pro 
/usr/lib/x86_64-linux-gnu/qt5/bin/linguist *.ts

pyrcc5 -o qrc_resources_rc.py uslt_manager.qrc

python3 /usr/lib/python3/dist-packages/pep8.py --max-line-length=100 uslt_manager.py  
python3 /usr/lib/python3/dist-packages/pep8.py --max-line-length=100 usltmodules/__init__.py
python3 /usr/lib/python3/dist-packages/pep8.py --max-line-length=100 usltmodules/dialogs.py
#python3 /usr/lib/python3/dist-packages/pep8.py --max-line-length=100 usltmodules/lngcodes.py 
python3 /usr/lib/python3/dist-packages/pep8.py --max-line-length=100 usltmodules/tagoperations.py
python3 /usr/lib/python3/dist-packages/pep8.py --max-line-length=100 usltmodules/tagwidget.py
python3 /usr/lib/python3/dist-packages/pep8.py --max-line-length=100 usltmodules/treeview.py
