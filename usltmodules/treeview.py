# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2017 Stefan Gansinger
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

"""QTreeView with attached QFileSystemModel."""

import os
import threading
from collections import defaultdict
from pathlib import Path
from shutil import which

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import mutagen

from .dialogs import addShortcutToToolTip
from .tagoperations import *


class FileTree(QWidget):
    """:class:`QWidget` showing a :class:`QTreeView` which root is editable either by
    line edit or file dialog.


    A :class:`QFileSystemWatcher` monitors visible files in the tree for changes.

    The `pyqtSignal` :data:`mp3Selected(filePath)` is emitted if a mp3 file is selected.
    The `pyqtSignal` :data:`nonmp3Selected(filePath)` is emitted if a non mp3 file is selected.
    The `pyqtSignal` :data:`nonmp3Selected(None)` is emitted when the root path was changed.

    :param rootPath: Path to root path of file tree
    """
    #: `pyqtSignal` emitted when an mp3 file is selected or changed.
    #: The file path is emitted as `str` parameter.
    mp3Selected = pyqtSignal(str)
    #: `pyqtSignal` emitted when a file is selected or changed which is not mp3.
    #: The file path is emitted as `str` parameter.
    nonmp3Selected = pyqtSignal(str)

    class DirValidator(QValidator):
        """Validation of root input. Validates if input is a readable directory."""
        def validate(self, inp, pos):
            """:returns: `QValidator.Acceptable` if entered directory is valid.
                         Otherwise, `QValidator.Intermediate`.

            :param inp: input string for validation
            """
            if Path(inp).is_dir():
                return (QValidator.Acceptable, inp, pos)
            else:
                return (QValidator.Intermediate, inp, pos)

    def __init__(self, rootPath, parent=None):
        super().__init__(parent)

        #: map parameter to object variable
        self.rootPath = rootPath

        # generate TagFileSystemModel
        self.model = TagFileSystemModel()
        self.model.setRootPath(self.rootPath)

        # tree view
        self.tree = QTreeView()
        # attach TagFileSystemModel
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(self.rootPath))
        # remove file type column
        self.tree.hideColumn(2)
        # remove last modified column
        self.tree.hideColumn(3)
        # fill available space with first column (Name) and adjust last column (ID3v2) to content
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        # custom context menu for QTreeView
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)

        # allow sorting
        self.tree.setSortingEnabled(True)
        self.model.sort(0, Qt.AscendingOrder)

        # Address line with address label, navigation icons and browser Icon
        openBrowserIcon = QIcon.fromTheme("folder", QIcon(":/icons/folder.svg"))
        openBrowserButton = QPushButton()
        openBrowserButton.setIcon(openBrowserIcon)
        self.addressLabel = QLineEdit(self.rootPath)
        addressValidator = self.DirValidator()
        self.addressLabel.setValidator(addressValidator)
        addressCompleter = QCompleter()
        addressCompleter.setModel(QDirModel(addressCompleter))
        self.addressLabel.setCompleter(addressCompleter)
        upButtonIcon = QIcon.fromTheme("go-up", QIcon(":/icons/go-up.svg"))
        upButton = QPushButton()
        upButton.setIcon(upButtonIcon)
        reloadButtonIcon = QIcon.fromTheme("view-refresh", QIcon(":/icons/view-refresh.svg"))
        reloadButton = QPushButton()
        reloadButton.setIcon(reloadButtonIcon)

        # options and progress bar at bottom
        checkDirsCheckBox = QCheckBox(
            QCoreApplication.translate('FileTree', "Check Directories"))
        self.progressBarDirCheck = QProgressBar()
        self.progressBarDirCheck.setMinimum(0)
        self.progressBarDirCheck.setMaximum(0)
        self.progressBarDirCheck.setVisible(False)

        bottomLineLayout = QBoxLayout(QBoxLayout.LeftToRight)
        bottomLineLayout.addWidget(checkDirsCheckBox)
        bottomLineLayout.addWidget(self.progressBarDirCheck)

        # shortcuts
        openBrowserButton.setShortcut(QKeySequence(Qt.CTRL + Qt.Key_O))
        reloadButton.setShortcut(QKeySequence(Qt.Key_F5))
        addressLabelShortcut = QShortcut(QKeySequence(Qt.CTRL + Qt.Key_L), self)
        addressLabelShortcut.activated.connect(self.addressLabel.selectAll)
        addressLabelShortcut.activated.connect(self.addressLabel.setFocus)

        # tooltips
        openBrowserButton.setToolTip(QCoreApplication.translate('FileTree', "Open in file browser"))
        upButton.setToolTip(QCoreApplication.translate('FileTree', "Up"))
        reloadButton.setToolTip(QCoreApplication.translate('FileTree', "Reload"))
        # <font> tag changes the string into "rich text" which is wrapped automatically
        checkDirsCheckBox.setToolTip(
            QCoreApplication.translate('FileTree',
                                       "<font>Check mp3 files in directory for lyrics. "
                                       "In case of missing lyrics the folder is marked. "
                                       "Subfolders are not checked!</font>"))
        addShortcutToToolTip(openBrowserButton)
        addShortcutToToolTip(reloadButton)

        # XXX: enables printing of cache values to stdout
        # debugCacheButtonIcon = QIcon.fromTheme("tools-report-bug")
        # debugCacheButton = QPushButton()
        # debugCacheButton.setIcon(debugCacheButtonIcon)
        # bottomLineLayout.addWidget(debugCacheButton)
        # debugCacheButton.clicked.connect(self._debugCache)

        # XXX: enables printing of fileSystemWatcher values to stdout
        # debugWatcherButtonIcon = QIcon.fromTheme("tools-report-bug")
        # debugWatcherButton = QPushButton()
        # debugWatcherButton.setIcon(debugWatcherButtonIcon)
        # bottomLineLayout.addWidget(debugWatcherButton)
        # debugWatcherButton.clicked.connect(self._debugWatcher)

        # main layout
        mainLayout = QGridLayout()
        mainLayout.addWidget(openBrowserButton, 0, 0)
        mainLayout.addWidget(self.addressLabel, 0, 1)
        mainLayout.addWidget(upButton, 0, 2)
        mainLayout.addWidget(reloadButton, 0, 3)
        mainLayout.addWidget(self.tree, 1, 0, 1, 4)
        mainLayout.addLayout(bottomLineLayout, 2, 0, 1, 3)
        self.setLayout(mainLayout)

        # clear color cache of TagFileSystemModel if directories are expanded/collapsed
        self.tree.collapsed.connect(self.model.removeFromFileInfoCache)
        # FIXME: temporarily disabled as cache cleaning might not be required on expansion t.b.v.
        # self.tree.expanded.connect(self.model.clearFileInfoCache)

        # process newly selected files (e.g. emit mp3Selected)
        self.tree.selectionModel().selectionChanged.connect(self.selectionChanged)
        # double click changes root to selected folder
        self.tree.doubleClicked.connect(self.changeRootToSelection)
        # notify for rootChanged() when new root have been entered
        #   (DirValidator prevents invalid directories)
        self.addressLabel.editingFinished.connect(self.rootChanged)
        # open file dialog if button is clicked
        openBrowserButton.clicked.connect(self.fileDialog)
        # go up in tree hierarchy on button click
        upButton.clicked.connect(self.goUp)
        # force reloading root
        reloadButton.clicked.connect(lambda: self.rootChanged(force=True))
        # checking directories is enabled or disabled
        checkDirsCheckBox.stateChanged.connect(self.checkDirsStateChanged)
        # show context menu
        self.tree.customContextMenuRequested.connect(self.treeContextMenu)
        # force as this is the initialization
        self.rootChanged(force=True)

    def _debugCache(self):
        """Print cache for debugging purposes."""
        print("______debugCache______")
        self.model.fileInfoCache.printCache()

    def _debugWatcher(self):
        """Print content of fileSystemWatcher for debugging purposes."""
        print("______debugWatch______")
        print("Directories" + "(" + str(len(self.fileSystemWatcher.directories())) + ")\n" +
              "\n".join(self.fileSystemWatcher.directories()))
        print("Files (" + str(len(self.fileSystemWatcher.files())) + ")\n" +
              "\n".join(self.fileSystemWatcher.files()))

    def keyPressEvent(self, event):
        """Handle key press events."""
        if event.key() == Qt.Key_Return:
            self.changeRootToSelection()
        elif event.key() == Qt.Key_Backspace:
            self.goUp()
        else:
            super().keyPressEvent(event)

    def treeContextMenu(self, pos):
        """Context menu."""
        menu = QMenu(self)

        # add "Open in kid3" to the context menu. Action is disabled if kid3 is not available
        kid3Action = menu.addAction(QCoreApplication.translate('FileTree', "Open in kid3"))
        if which("kid3"):
            kid3Action.triggered.connect(lambda: self.openKID3("kid3"))
            kid3Action.setEnabled(True)
        elif which("kid3-qt"):
            kid3Action.triggered.connect(lambda: self.openKID3("kid3-qt"))
            kid3Action.setEnabled(True)
        else:
            kid3Action.setEnabled(False)

        # add "Delete File" to context menu if a writable file is selected
        deleteFileAction = menu.addAction(QCoreApplication.translate('FileTree', "Delete File"))
        selectedFileInfo = self.model.fileInfo(self.tree.selectionModel().selectedIndexes()[0])
        if selectedFileInfo.isFile() and selectedFileInfo.isWritable():
            deleteFileAction.triggered.connect(
                lambda: self.deleteFile(selectedFileInfo.absoluteFilePath()))
            deleteFileAction.setEnabled(True)
        else:
            deleteFileAction.setEnabled(False)

        menu.exec(self.tree.mapToGlobal(pos))

    def openKID3(self, command):
        """Opens KID3 by :data:`command` with the current selection."""
        selection = self.model.filePath(self.tree.selectionModel().selectedIndexes()[0])
        if selection:
            QProcess.startDetached(command, [selection])

    def deleteFile(self, filePath):
        """Deletes the selected file."""
        msgBox = QMessageBox()
        msgBox.setText(QCoreApplication.translate('FileTree',
                                                  "Do you really want to delete the file?"))
        msgBox.setInformativeText(filePath)
        msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        # FIXME: Workaround for missing or at least not working translations QMessageBox
        #   buttons. It seems that the translations are stored in the context of QPlatformTheme
        msgBox.button(QMessageBox.Yes). \
            setText(QCoreApplication.translate('QPlatformTheme', "Yes"))
        msgBox.button(QMessageBox.No). \
            setText(QCoreApplication.translate('QPlatformTheme', "No"))
        if msgBox.exec() == QMessageBox.Yes:
            QFile(filePath).remove()

    def checkDirsStateChanged(self, state):
        """Enable directory check depending on :data:`state`."""
        if state == Qt.Checked:
            self.model.dirChecksEnable = True

            # Generates a timeout for the progress bar shown during directory checking
            # Every time a file is checked (in directory check mode) by the `TagFileSystemModel`
            # the signal `fileCheck` is emitted. The signal causes the progress bar to be shown
            # and the timeout to be set. After timeout the progress bar is hidden again.
            self.progressTimeoutTimer = QTimer()
            self.model.emitter.fileCheck.connect(self.showProgressBarDirCheck)
            # hide progress bar on timeout
            self.progressTimeoutTimer.timeout.connect(
                lambda: self.progressBarDirCheck.setVisible(False))
            # force progress bar to be shown
            self.showProgressBarDirCheck()

        else:
            self.model.dirChecksEnable = False
            self.progressBarDirCheck.setVisible(False)
            # destroy any remaining timeout timer
            try:
                del self.progressTimeoutTimer
            except AttributeError:
                pass

    def showProgressBarDirCheck(self):
        """Show progress bar and initialization of the timeout timer."""
        try:
            self.progressTimeoutTimer.start(500)
            self.progressBarDirCheck.setVisible(True)
        except AttributeError:
            # progressTimeoutTimer might already be removed
            # just to make sure: force progress bar to be invisible when no timer is available
            self.progressBarDirCheck.setVisible(False)

    def rootChanged(self, force=False):
        """Initializes all required properties but only if :data:`self.rootPath` has changed.
        The variable :data:`self.rootPath` is compared to :data:`self.addressLabel.text()` to
        identify root changes. So its important to call the :func:`self.addressLabel.setText()`
        before calling this method.

        :param force: Force initialization despite if :data:`self.rootPath` changed.
        """
        if self.rootPath != self.addressLabel.text() or force:
            self.rootPath = self.addressLabel.text()
            self.model.setRootPath(self.rootPath)
            self.tree.setRootIndex(self.model.index(self.rootPath))
            self.model.clearFileInfoCache()
            self.createFileSystemWatcher()
            # clearing selection is required if initialization is forced (at least)
            self.tree.clearSelection()
            # emit signal to notify for a root update. The parameter is set to None as no
            # file is selected if the root is changed.
            self.nonmp3Selected.emit(None)

    def createFileSystemWatcher(self):
        """Create a :class:`QFileSystemWatcher` including all files and directories
        within `self.rootPath`. All expanded indexes in the model are included as well.
        Additionally, the required connections to notify for file changes to the
        object of :class:`TagFileSystemModel` are generated.

        :param path: path which should be monitored
        """
        path = self.rootPath
        absolutePath = QDir(path).absolutePath()
        # FIXME: If file is not readable its not in the watch list.
        #   Thus a toggling read flag is recognized.
        fileList = QDir(path).entryList(QDir.AllEntries | QDir.Readable |
                                        QDir.NoDotDot, QDir.DirsFirst)
        fileList = [os.path.join(absolutePath, s) for s in fileList]

        # loop over all available indexes and add the to the watcher if it is expanded
        for index in self.model.persistentIndexList():
            if self.tree.isExpanded(index):
                path = self.model.filePath(index)
                absolutePath = QDir(path).absolutePath()
                expansionList = QDir(path).entryList(QDir.AllEntries | QDir.Readable |
                                                     QDir.NoDotDot, QDir.DirsFirst)
                expansionList = [os.path.join(absolutePath, s) for s in expansionList]
                fileList.extend(expansionList)

        try:
            del self.fileSystemWatcher
        except AttributeError:
            pass
        self.fileSystemWatcher = QFileSystemWatcher(fileList)
        # print("New watcher: " + "\n".join(fileList))

        # clear color cache of TagFileSystemModel if watched directory or file changes
        self.fileSystemWatcher.directoryChanged.connect(self.model.removeFromFileInfoCache)
        self.fileSystemWatcher.fileChanged.connect(self.model.removeFromFileInfoCache)

        # If directory was changed, files might have been added
        #   --> add them to the QFileSystemWatcher
        self.fileSystemWatcher.directoryChanged.connect(self.modifyWatcher)

        # a watched file has changed --> react
        self.fileSystemWatcher.fileChanged.connect(self.fileChanged)

        # update QFileSystemWatcher on expanded/collapsed directories in QTreeView
        self.tree.expanded.connect(self.modifyWatcher)
        self.tree.collapsed.connect(self.modifyWatcher)

        # print("Watching" + str(self.fileSystemWatcher.files()))

    def changeRootToSelection(self):
        """Set root to the currently selected directory. Should be called on `doubleClicked`."""
        try:
            selectedPath = self.model.filePath(self.tree.selectionModel().selectedIndexes()[0])
            if Path(selectedPath).is_dir():
                self.addressLabel.setText(selectedPath)
                self.rootChanged()
        except IndexError:
            # nothing selected
            pass

    def goUp(self):
        """Go one hierarchy up for the root."""
        actDir = QDir(self.addressLabel.text())
        if actDir.cdUp():
            self.addressLabel.setText(QDir.absolutePath(actDir))
            self.rootChanged()

    def fileDialog(self):
        """File dialog to set new root."""
        path = QFileDialog.getExistingDirectory(self, directory=self.rootPath)
        if path:
            self.addressLabel.setText(path)
            self.rootChanged()

    def modifyWatcher(self, index):
        """Add or remove files from the :data:`self.fileSystemWatcher`. Depending if
        tree is expanded or collapsed files are removed or added.

        :param index: index of changed path in tree.
        :type index: `QModelIndexType` or if `str` the index is looked up in tree
        """
        # index should be of QModelIndexType. If its a str its a path
        #   --> find index in model
        if type(index) is str:
            index = self.model.index(index)

        filePath = self.model.filePath(index)
        absolutePath = QDir(filePath).absolutePath()
        fileList = QDir(filePath).entryList(QDir.AllEntries | QDir.Readable |
                                            QDir.NoDotDot, QDir.DirsFirst)
        fileList = [os.path.join(absolutePath, s) for s in fileList]

        if self.tree.isExpanded(index) or index == self.tree.rootIndex():
            # print("Adding: " + str(fileList))
            self.fileSystemWatcher.addPaths(fileList)
        else:
            # print("Removing: " + str(fileList))
            # fileList might be empty (e.g. when a directory is deleted)
            if fileList:
                self.fileSystemWatcher.removePaths(fileList)
            # deleted files are removed automatically

        # print("Watching" + str(self.fileSystemWatcher.files()))

    def selectionChanged(self, selected, deselected):
        """Emit :data:`mp3Selected` or :data:`nonmp3Selected` for the selected file.
        To be called when a new file is selected.
        """
        if len(selected.indexes()) > 0:
            index = selected.indexes()[0]

            filePath = self.model.filePath(index)
            if self.model.fileInfo(index).isFile() and self.model.isMP3(filePath):
                self.mp3Selected.emit(filePath)
            else:
                self.nonmp3Selected.emit(filePath)

    def fileChanged(self, filePath):
        """Emit :data:`mp3Selected` or :data:`nonmp3Selected` for the selected file.
        To be called when the selected file changed.
        """
        index = self.model.index(filePath)
        if (len(self.tree.selectionModel().selectedIndexes()) > 0 and
                index == self.tree.selectionModel().selectedIndexes()[0]):
            if self.model.fileInfo(index).isFile() and self.model.isMP3(filePath):
                self.mp3Selected.emit(filePath)
            else:
                self.nonmp3Selected.emit(filePath)


class TagFileSystemModel(QFileSystemModel):
    """File system model to be used w/ :class:`QTreeView`.

    It enhances the classical :class:`QFileSystemModel` w/ ID3 tag handling. To speed up file
    handling important file parameters are cached in :data:`self.fileInfoCache`.
    A customized column provides information about the ID3 tag version.

    If file is an mp3 file it gets colored depending if lyrics are available or not.

    Additionally, the class provides a check for all files in a directory. To enable this check
    :data:`self.dirChecksEnable` must be `True`. Depending on the result of the check different
    folder icons are returned. The check is not recursive! When a file is checked in this mode
    the signal :data:`fileCheck` is emitted.
    """
    class Emitter(QObject):
        """Signals can only be emitted from classes derived from :class:`QOject`.
        As :class:`QFileIconProvider` is not derived from :class:`QOject` this nested
        class provides this feature.
        """
        fileCheck = pyqtSignal()

        def __init__(self):
            super().__init__()

    class FileInfoCache():
        """Provides a cache for file and directory informations."""
        def __init__(self):
            self._initCache()
            # inmutable tuple used as key (to make sure its not mixed with files)
            self._dirMarker = ('<dir>',)

        def _initCache(self):
            """Initializes an empty cache as object variable."""
            try:
                del self._trunk
            except AttributeError:
                pass
            # 3-dimensional defaultdict -- totally wired in my opinion
            self._trunk = defaultdict(lambda: defaultdict(defaultdict))

        def _splitFilePath(self, filePath):
            """Splits filePath into file name and path name.
            :returns: pathName, fileName
            """
            pathName = os.path.dirname(filePath)
            fileName = os.path.basename(filePath)
            return self._normPath(pathName), fileName

        def _normPath(self, pathName):
            """Normalize path, eliminating double slashes, etc."""
            return os.path.normpath(pathName)

        def insFileInfo(self, filePath, attribute, setting):
            """Inserts the `setting` of the `attribute` for the `file` at `path` into the cache."""
            pathName, fileName = self._splitFilePath(filePath)
            self._trunk[pathName][fileName][attribute] = setting

        def insertDirInfo(self, pathName, attribute, setting):
            """Inserts the `setting` of the `attribute` for the `pathName` into the cache."""
            pathName = self._normPath(pathName)
            self._trunk[pathName][self._dirMarker][attribute] = setting

        def getFileInfo(self, filePath, attribute):
            """Returns the `setting` of the `attribute` for the `file` at `path`.
            :return: `setting` or `None` if not available
            """
            pathName, fileName = self._splitFilePath(filePath)
            try:
                return self._trunk[pathName][fileName][attribute]
            except KeyError:
                return None

        def getDirInfo(self, pathName, attribute):
            """Returns the `setting` of the `attribute` for the `pathName`.
            :return: `setting` or `None` if not available
            """

            pathName = self._normPath(pathName)
            try:
                return self._trunk[pathName][self._dirMarker][attribute]
            except KeyError:
                return None

        def removeFileInfo(self, filePath):
            """Removes all cached attributes for the `file` at `path` from the cache."""
            pathName, fileName = self._splitFilePath(filePath)
            try:
                del self._trunk[pathName][fileName]
            except KeyError:
                pass
            try:
                # if no more attributes are stored, remove the whole entry
                if not self._trunk[pathName]:
                    del self._trunk[pathName]
            except KeyError:
                pass

        def removeDirInfo(self, pathName):
            try:
                del self._trunk[pathName][self._dirMarker]
            except KeyError:
                pass
            try:
                # if no more attributes are stored, remove the whole entry
                if not self._trunk[pathName]:
                    del self._trunk[pathName]
            except KeyError:
                pass

        def removeRecursively(self, pathName):
            """Removes all cached attributes for all files and paths starting with `pathName`."""
            for item in list(self._trunk):
                if pathName in item:
                    del self._trunk[item]

        def clearCache(self):
            """Deletes the whole cache by calling :func:`self._initCache()`."""
            self._initCache()

        def printCache(self):
            """Outputs the cache to stdout."""
            if not self._trunk:
                print("Cache is empty!")
            else:
                elements = 0
                for pathName in self._trunk.keys():
                    for fileName in self._trunk[pathName].keys():
                        for attribute in self._trunk[pathName][fileName].keys():
                            elements = elements + 1
                            print((pathName, fileName, attribute),
                                  self._trunk[pathName][fileName][attribute])
                print(elements, "elements in cache.\n")

    def __init__(self, parent=None):
        super().__init__(parent)
        #: cache for file informations to speed-up painting.
        #: QModelIndex is used is as key parameter
        self.fileInfoCache = self.FileInfoCache()
        #: enables directory checking
        self.dirChecksEnable = False
        #: List threads (identified by path) which are currently running
        self.threadList = []

        # preload icons for speed
        # fallback does not work in KDE due to Bug 342906
        self.redFolderIcon = QIcon.fromTheme("folder-red", QIcon(":/icons/folder-red.svg"))
        self.standardFolderIcon = QIcon.fromTheme("folder", QIcon(":/icons/folder.svg"))
        self.standardMP3Icon = QIcon.fromTheme("audio-x-generic", QIcon(":/icons/audio-mp3.svg"))
        self.standardFileIcon = QIcon.fromTheme("text-x-generic",
                                                QIcon(":/icons/text-x-generic.svg"))

        self.emitter = TagFileSystemModel.Emitter()

    def sort(self, column, order):
        # FIXME: sorting of custom columns is not working
        super().sort(column, order)

    def headerData(self, section, orientation, role):
        """Reimplemented to be able to add an additional header for
        customized columns.

        :returns: "ID3v2" or "Track" for the customized column, else super()
        """
        if (section == self.columnCount() - 2):
            if (role == Qt.DisplayRole):
                return(QCoreApplication.translate('FileTree', "Track"))
        if (section == self.columnCount() - 1):
            if (role == Qt.DisplayRole):
                return("ID3v2")

        return super().headerData(section, orientation, role)

    def data(self, index, role):
        """Reimplemented to enable coloring of lines depending on file type and if lyrics are
        available or not. Additionally, the Track and the ID3v2 column is generated.

        Before the file itself is analyzed the cached information is checked.

        If :data:`self.dirChecksEnable` is set to `True` the content of sub-directories is checked
        as well and the according icons are returned. Checking directories is done in a separate
        thread.
        """

        # add Track number into dedicated column.
        if ((role == Qt.DisplayRole)) and (index.column() == self.columnCount() - 2):
            filePath = self.filePath(index)
            if self.fileInfoCache.getFileInfo(filePath, 'track') is None:
                if self.fileInfo(index).isFile() and self.isMP3(self.filePath(index)):
                    self.fileInfoCache.insFileInfo(filePath, 'track',
                                                   self.ID3track(filePath))
                else:
                    self.fileInfoCache.insFileInfo(filePath, 'track',
                                                   QApplication.translate('TagFileSystemModel',
                                                                          "N.A."))
            return self.fileInfoCache.getFileInfo(filePath, 'track')

        # add ID3v2 version number into dedicated column.
        if ((role == Qt.DisplayRole)) and (index.column() == self.columnCount() - 1):
            filePath = self.filePath(index)
            if self.fileInfoCache.getFileInfo(filePath, 'tagversion') is None:
                if self.fileInfo(index).isFile() and self.isMP3(self.filePath(index)):
                    self.fileInfoCache.insFileInfo(filePath, 'tagversion',
                                                   self.id3v2Version(filePath))
                else:
                    self.fileInfoCache.insFileInfo(filePath, 'tagversion',
                                                   QApplication.translate('TagFileSystemModel',
                                                                          "N.A."))
            return self.fileInfoCache.getFileInfo(filePath, 'tagversion')

        # paint rows in different colors depending if lyrics are available or not
        if (role == Qt.ForegroundRole):
            filePath = self.filePath(index)
            if self.fileInfoCache.getFileInfo(filePath, 'color') is None:
                if self.fileInfo(index).isFile() and self.isMP3(self.filePath(index)):
                    if self.hasID3Lyrics(self.filePath(index)):
                        self.fileInfoCache.insFileInfo(filePath, 'color',
                                                       QVariant(QColor("green")))
                    else:
                        self.fileInfoCache.insFileInfo(filePath, 'color',
                                                       QVariant(QColor("red")))
                else:
                    self.fileInfoCache.insFileInfo(filePath, 'color', super().data(index, role))
            return self.fileInfoCache.getFileInfo(filePath, 'color')

        # XXX: QFileIconProvider is not working in Plasma 5 -> return symbol manually
        if (not self.dirChecksEnable and role == Qt.DecorationRole and index.column() == 0 and
                self.fileInfo(index).isDir()):
            return self.standardFolderIcon

        # XXX: QFileIconProvider is not working in Plasma 5 -> return symbol manually
        if (role == Qt.DecorationRole and index.column() == 0 and
                self.fileInfo(index).isFile()):
            if self.isMP3(self.filePath(index)):
                return self.standardMP3Icon
            else:
                return self.standardFileIcon

        # directory checks if requested
        if (self.dirChecksEnable and role == Qt.DecorationRole and index.column() == 0 and
                self.fileInfo(index).isDir()):
            pathName = self.filePath(index)
            if self.fileInfoCache.getDirInfo(pathName, 'icon') is None:
                path = self.fileInfo(index).absoluteFilePath()
                # if path is not already checked by a dedicated process start new process
                if path not in self.threadList:
                    self.threadList.append(path)
                    thread = threading.Thread(target=self.checkDirectory, args=(path,))
                    # FIXME: threads are NOT terminated gracefully on shutdown
                    thread.start()
                # Thread is still running as there is no icon in cache -> return intermediate icon
                return QIcon.fromTheme("folder-download", QIcon(":/icons/folder-download.svg"))
            return self.fileInfoCache.getDirInfo(pathName, 'icon')

        return super().data(index, role)

    def columnCount(self, parent=None):
        """Reimplemented to be able to add an header for customized columns.

        :returns: number of columns including the customized columns.
        """
        return super().columnCount()+2

    def isMP3(self, filePath):
        """Test if file is MP3 file by using Mutagen's MIME type evaluation.

        :returns: `True` if file is an MP3, else `False`.
        :rtype: boolean
        """
        try:
            return ((mutagen.File(filePath) is not None and
                    'audio/mp3' in mutagen.File(filePath).mime) or
                    False)
        except PermissionError:
            return False
        except mutagen.mp3.HeaderNotFoundError:
            return False
        except mutagen.id3._util.ID3NoHeaderError:
            return False
        except mutagen.mp4.MP4StreamInfoError:
            return False

    def id3v2Version(self, filePath):
        """ID3 tag version number. If ID3v1 and ID3v2 tags are located in the file. The version
        of ID3v2 is returned only.

        :return: version number
        :rtype: `str`
        """
        return ('.'.join(str(i) for i in ID3(filePath).version))

    def ID3track(self, filePath):
        """Returns track number

        :return: track number
        :rtype: `str`
        """
        return (self.isMP3(filePath) and ID3(filePath).track)

    def hasID3Lyrics(self, filePath):
        """Test if file has lyrics in ID3 tag by getting all USLT frames.

        :returns: `True` if lyrics are available, else `False`.
        :rtype: boolean
        """
        return (self.isMP3(filePath) and ID3(filePath).hasLyrics) or False

    def checkDirectory(self, path):
        """Saves :data:`self.standardFolderIcon` in :data:`self.fileInfoCache` if every mp3-file in
        `path` has embedded lyrics. Otherwise, `self.redFolderIcon`.
        Subdirectories are not checked!

        If checking is done, `path` is removed from :data:`self.threadList`.

        The `pyqtSignal` :data:`fileCheck` is emitted every time a file is checked.
        """
        fileList = QDir(path).entryList(QDir.Files | QDir.Readable | QDir.NoDotAndDotDot)
        fileList = [os.path.join(path, s) for s in fileList]

        allHaveLyrics = True
        allAreMP3 = True
        for filePath in fileList:
            self.emitter.fileCheck.emit()
            try:
                if ((mutagen.File(filePath) is not None) and
                        ('audio/mp3' in mutagen.File(filePath).mime)):
                    if not ID3(filePath).hasLyrics:
                        allHaveLyrics = False
                        break
                else:
                    allAreMP3 = False
            except PermissionError:
                pass
            except mutagen.id3._util.ID3NoHeaderError:
                allAreMP3 = False
            except mutagen.mp3.HeaderNotFoundError:
                # corrupt mp3
                allAreMP3 = False

        if not allHaveLyrics:
            self.fileInfoCache.insertDirInfo(path, 'icon', self.redFolderIcon)
        else:
            self.fileInfoCache.insertDirInfo(path, 'icon', self.standardFolderIcon)

        self.threadList.remove(path)

    def removeFromFileInfoCache(self, filePathOrIndex):
        """Removes specified files from :data:`self.fileInfoCache`.
        :param filePathOrIndex: model index or path
        """
        # if filePathOrIndex is not QModelIndex find index of corresponding path
        if type(filePathOrIndex) != QModelIndex:
            index = self.index(filePathOrIndex)
        else:
            index = filePathOrIndex

        filePath = self.fileInfo(index).filePath()

        if self.fileInfo(index).isDir():
            self.fileInfoCache.removeRecursively(filePath)
        else:
            self.fileInfoCache.removeFileInfo(filePath)

    def clearFileInfoCache(self):
        """Clears :data:`self.fileInfoCache`."""
        self.fileInfoCache.clearCache()
