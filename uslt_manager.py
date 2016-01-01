#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
##############################################################################
#   USLT Manager
#
#   Version: 1.1
#
#   Author: Stefan Gansinger <stefan.gansinger@posteo.at>
#
#   Description: Management for lyrics stored in the USLT frame of the ID3v2
#                tag of mp3 files
#
#   Thanks: o Michael Urman for Python-Mutagen and all people who contributed
#           o Breeze (Plasma Next Icons) project members and contributers
#           o The developers of Python, PyQt, and Qt
#
# Copyright (C) 2015-2016 Stefan Gansinger
#
##############################################################################
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import os
import sys

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from mutagen import version as mutagenVersion

from usltmodules import *
# qt resource file is created w/ pyrcc5 -o qrc_resources_rc.py uslt_manager.qrc
import qrc_resources_rc


class MainWindow(QMainWindow):
    """Main window of application

    :param rootPath: Path to root directory
    """
    class CentralWidget(QWidget):
        """The central widget combines the :class:`FileTree` and :class:`TagWidget`.

        :param rootPath: Path to root directory
        """
        def __init__(self, rootPath="/", parent=None):
            super().__init__(parent)

            mainLayout = QGridLayout()

            # file Tree at the left side
            fileTree = FileTree(rootPath)

            # TagWidget and Exit button on the right side
            self.tagWidget = TagWidget()
            exitButtonIcon = QIcon.fromTheme("application-exit", QIcon(":/icons/application-exit"))
            self.exitButton = QPushButton(QCoreApplication.translate('MainWindow', "Exit"))
            self.exitButton.setIcon(exitButtonIcon)
            rightWidget = QWidget()
            rightLayout = QGridLayout()
            rightWidget.setLayout(rightLayout)
            rightLayout.addWidget(self.tagWidget, 0, 0)
            rightLayout.addWidget(self.exitButton, 1, 0)

            # tooltips
            self.exitButton.setToolTip(QCoreApplication.translate('MainWindow',
                                                                  "Quits the application"))

            # combine left part and right part with QSplitter
            splitter = QSplitter()
            splitter.addWidget(fileTree)
            splitter.addWidget(rightWidget)

            mainLayout.addWidget(splitter, 0, 0)
            self.setLayout(mainLayout)

            # connections from FileTree to TagWidget
            fileTree.mp3Selected.connect(self.tagWidget.loadAndShowTag)
            fileTree.nonmp3Selected.connect(self.tagWidget.unloadAndHideTag)

    def __init__(self, rootPath="/", parent=None, flags=Qt.WindowFlags(0)):
        super().__init__(parent, flags)

        self.showMaximized()

        self.centralWidget = self.CentralWidget(rootPath)
        self.setCentralWidget(self.centralWidget)

        # Absolute path is required here.
        # However, QCoreApplication.applicationDirPath()) will not work since it will
        # return the path to the python executable. Thus qrc_resources_rc is used instead
        mainIcon = QIcon(":/icons/lyrics_id3_icon.svg")
        self.setWindowIcon(mainIcon)
        self.setWindowTitle("USLT Manager[*]")

        self.centralWidget.exitButton.clicked.connect(self.close)
        self.centralWidget.tagWidget.tagModified.connect(self.tagModified)

    def tagModified(self, modified):
        """Set or unset window to "modified"."""
        self.setWindowModified(modified)

    def closeEvent(self, event):
        """Actions to take when application is about to close."""
        if self.isWindowModified():
            ret = SaveChangesDialog(QMessageBox.Save | QMessageBox.Discard |
                                    QMessageBox.Cancel).exec()
            if (ret == QMessageBox.Save):
                self.centralWidget.tagWidget.saveTagActionReceiver()
                self.centralWidget.tagWidget.saveTagAction.setDisabled(True)
                self.centralWidget.tagWidget.tagModified.emit(False)
                event.accept()
            elif (ret == QMessageBox.Discard):
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


if __name__ == '__main__':
    # workaround to get CTRL+C working
    import signal
    # handle SIGINT w/ default function
    # must be installed before the Qt event loop
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    mutagenVersion = int("".join(map(str, mutagenVersion[:2])))

    if mutagenVersion >= 125:
        app = QApplication(sys.argv)

        locale = QLocale.system()
        usltTranslator = QTranslator()
        if usltTranslator.load(locale, ":/uslt_manager", "_"):
            app.installTranslator(usltTranslator)

        if len(sys.argv) > 1 and QDir(sys.argv[1]).isReadable():
            screen = MainWindow(QFileInfo(sys.argv[1]).canonicalFilePath())
        else:
            screen = MainWindow()

        screen.show()

        retval = app.exec_()
        # delete QApplication before Python does it on exit
        # Otherwise, a segmentation fault may occur
        del app

    else:
        print("Mutagen Version >= 1.25 required")
        retval = 1

    sys.exit(retval)
