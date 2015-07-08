# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Stefan Gansinger
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

"""QTreeView with attached QFileSystemModel."""

import os
from pathlib import Path

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import mutagen

from .tagoperations import *


class FileTree(QWidget):
    """QWidget having QTreeView which root is editable either by line edit or file dialog.


    A `QFileSystemWatcher` monitors visible files in the tree for changes. If a mp3 file
    is selected or modified :data:`mp3Selected` signal with filePath as parameter is emitted.
    Otherwise, :data:`nonmp3Selected` with filePath is emitted.

    If the root path is changed :data:`nonmp3Selected`  with parameter None is emitted.

    :param rootPath: Path to root path of file tree
    """
    #: `pyqtSignal` emitted when an mp3 file is selected or changed.
    #: The file path is emitted as str parameter.
    mp3Selected = pyqtSignal(str)
    #: `pyqtSignal` emitted when a file is selected or changed which is not mp3.
    #: The file path is emitted as str parameter.
    nonmp3Selected = pyqtSignal(str)

    class DirValidator(QValidator):
        """Sub-class for validation of root input. Validates if input is an existing directory."""
        def __init__(self, parent=None):
            super().__init__(parent)

        def validate(self, inp, pos):
            """:returns: `QValidator.Acceptable` if entered directory is valid.
                         Otherwise, `QValidator.Intermediate`.

            :param inp: input string for validation
            """
            if Path(inp).is_dir():
                return (QValidator.Acceptable, inp, pos)
            else:
                return (QValidator.Intermediate, inp, pos)

        def fixup(self, input):
            return super().fixup(input)

    def __init__(self, rootPath, parent=None):
        super().__init__(parent)

        #: map parameter to object variable
        self.rootPath = rootPath

        self.model = TagFileSystemModel()
        self.model.setRootPath(self.rootPath)

        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(self.rootPath))
        # remove file type column
        self.tree.hideColumn(2)
        # fill available space with first column (Name) and adjust last column (ID3v2) to content
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        # create a custom context menu for QTreeView
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.treeContextMenu)

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
        addressLabelShortcut = QShortcut(QKeySequence(Qt.CTRL + Qt.Key_L), self)
        addressLabelShortcut.activated.connect(self.addressLabel.selectAll)
        addressLabelShortcut.activated.connect(self.addressLabel.setFocus)
        upButtonIcon = QIcon.fromTheme("go-up", QIcon(":/icons/go-up.svg"))
        upButton = QPushButton()
        upButton.setIcon(upButtonIcon)
        reloadButtonIcon = QIcon.fromTheme("view-refresh", QIcon(":/icons/view-refresh.svg"))
        reloadButton = QPushButton()
        reloadButton.setIcon(reloadButtonIcon)

        # Options at bottom
        checkDirsCheckBox = QCheckBox(
            QCoreApplication.translate('FileTree',
                                       "Check Directories" +
                                       " (experimental)"))
        self.progressBarDirCheck = QProgressBar()
        self.progressBarDirCheck.setMinimum(0)
        self.progressBarDirCheck.setMaximum(0)
        self.progressBarDirCheck.setVisible(False)

        bottomLineLayout = QBoxLayout(QBoxLayout.LeftToRight)
        bottomLineLayout.addWidget(checkDirsCheckBox)
        bottomLineLayout.addWidget(self.progressBarDirCheck)

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

        # Process newly selected files (e.g. emit mp3Selected)
        self.tree.selectionModel().selectionChanged.connect(self.selectionChanged)
        # Double clicked on selection
        self.tree.doubleClicked.connect(self.changeRootToSelection)
        # Notify for rootChanged() when new root have been entered
        #   (DirValidator prevents invalid directories)
        self.addressLabel.editingFinished.connect(self.rootChanged)
        # Open file dialog if button is clicked
        openBrowserButton.clicked.connect(self.fileDialog)
        # Go up in tree hierarchy on button click
        upButton.clicked.connect(self.goUp)
        # Force reloading root
        reloadButton.clicked.connect(lambda: self.rootChanged(force=True))
        #
        checkDirsCheckBox.stateChanged.connect(self.checkDirsStateChanged)

        # force as this is the initialization
        self.rootChanged(force=True)

    def showProgressBarDirCheck(self):
        """Show progress bar and initialization of the timeout timer."""
        self.progressTimeoutTimer.start(500)
        self.progressBarDirCheck.setVisible(True)

    def treeContextMenu(self, pos):
        """Adds context menu."""
        menu = QMenu(self)

        # Adds "Open in kid3" to the context menu. Action is disabled if kid3 is not available
        kid3Action = menu.addAction(QCoreApplication.translate('FileTree', "Open in kid3"))
        if which("kid3"):
            kid3Action.triggered.connect(lambda: self.openKID3("kid3"))
            kid3Action.setEnabled(True)
        elif which("kid3-qt"):
            kid3Action.triggered.connect(lambda: self.openKID3("kid3-qt"))
            kid3Action.setEnabled(True)
        else:
            kid3Action.setEnabled(False)

        # Adds "Delete File" to context menu if a writable file is selected
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
        """Opens KID3 using `command`."""
        selection = self.model.filePath(self.tree.selectionModel().selectedIndexes()[0])

        if selection:
            QProcess.startDetached("kid3", [selection])

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
        """Depending on `state` directory checking is enabled or nor."""
        if state == Qt.Checked:
            self.model.dirChecksEnable = True

            # Generates a timeout for the progress bar shown during directory checking
            # Every time a file is checked (in directory check mode) by the TagFileSystemModel
            # the signal fileCheck is emitted. The signal causes the progress bar to be shown
            # and the timeout to be set. After timeout the progress bar is hidden again.
            self.progressTimeoutTimer = QTimer()
            self.model.emitter.fileCheck.connect(self.showProgressBarDirCheck)
            self.progressTimeoutTimer.timeout.connect(
                lambda: self.progressBarDirCheck.setVisible(False))
            self.showProgressBarDirCheck()

        else:
            self.model.dirChecksEnable = False
            self.progressBarDirCheck.setVisible(False)
            try:
                del self.progressTimeoutTimer
            except AttributeError:
                pass

    def rootChanged(self, force=False):
        """Initializes all required properties but only if `rootPath` has really changed.
        The object variable `rootPath` to the `addressLabel` to find out if it was changed.
        So its important to change the `addressLabel` manually before calling this method.

        :param force: Force initialization despite if `rootPath` changed.
        """
        if self.rootPath != self.addressLabel.text() or force:
            self.rootPath = self.addressLabel.text()
            self.model.setRootPath(self.rootPath)
            self.tree.setRootIndex(self.model.index(self.rootPath))
            self.model.clearFileInfoCache()
            self.createFileSystemWatcher(self.rootPath)
            # clearing selection is required if initialization is forced (at least)
            self.tree.clearSelection()
            # Emit signal to notify for a root update. The parameter is set to None as no
            # file is selected if the root is changed.
            self.nonmp3Selected.emit(None)

    def createFileSystemWatcher(self, path):
        """Create a QFileSystemWatcher including all files and directories within the watched path.
        Additionally, the required connections to notify file for file changes to the
        object of :class:`TagFileSystemModel` are generated.

        :param path: path which should be monitored.
        """

        absolutePath = QDir(path).absolutePath()
        #FIXME: If file is not readable its not in the watch list.
        #   Thus a toggling read flag is recognized.
        fileList = QDir(path).entryList(QDir.AllEntries | QDir.Readable |
                                        QDir.NoDotDot, QDir.DirsFirst)
        fileList = [os.path.join(absolutePath, s) for s in fileList]

        try:
            del self.fileSystemWatcher
        except AttributeError:
            pass
        self.fileSystemWatcher = QFileSystemWatcher(fileList)
        #print("New watcher: " + ",".join(fileList))

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

        #print("Watching" + str(self.fileSystemWatcher.files()))

    def changeRootToSelection(self):
        """Set root to the currently selected directory. Should be called on `doubleClicked`."""
        selectedPath = self.model.filePath(self.tree.selectionModel().selectedIndexes()[0])
        if Path(selectedPath).is_dir():
            self.addressLabel.setText(selectedPath)
            self.rootChanged()

    def goUp(self):
        """Go one hierarchy up for the root."""
        actDir = QDir(self.addressLabel.text())
        if actDir.cdUp():
            self.addressLabel.setText(QDir.absolutePath(actDir))
            self.rootChanged()

    def fileDialog(self):
        """File dialog to sets new root."""
        path = QFileDialog.getExistingDirectory(self, directory=self.rootPath)
        if path:
            self.addressLabel.setText(path)
            self.rootChanged()

    def modifyWatcher(self, index):
        """Add or remove files from the `fileSystemWatcher`. Depending if tree is expanded or
        collapsed files are removed or added.

        :param index: index of changed path in tree.
        :type index: QModelIndexType or if str the index is looked up in tree
        """
        # index should be of QModelIndexType. If its a str I assume its a path
        #   --> find index in model
        if type(index) is str:
            index = self.model.index(index)

        filePath = self.model.filePath(index)
        absolutePath = QDir(filePath).absolutePath()
        fileList = QDir(filePath).entryList(QDir.AllEntries | QDir.Readable |
                                            QDir.NoDotDot, QDir.DirsFirst)
        fileList = [os.path.join(absolutePath, s) for s in fileList]

        if self.tree.isExpanded(index) or index == self.tree.rootIndex():
            #print("Adding: " + str(fileList))
            self.fileSystemWatcher.addPaths(fileList)
        else:
            #print("Removing: " + str(fileList))
            # fileList might be empty (e.g. when a directory is deleted)
            # QFileSystemWatcher removes deleted files automatically
            if fileList:
                self.fileSystemWatcher.removePaths(fileList)

        #print("Watching" + str(self.fileSystemWatcher.files()))

    def selectionChanged(self, selected, deselected):
        """Emit `mp3Selected` or `nonmp3Selected` for the selected file.
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
        """Emit `mp3Selected` or `nonmp3Selected` for the selected file.
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
    """File system model to be used w/ QTreeView.

    It enhances the classical QFileSystemModel w/ ID3 tag handling. To speed up file
    handling important file parameters are cached. A customized column provides information
    about the ID3 tag version.

    If file is an mp3 file it gets colored depending if lyrics are available or not.

    Additionally, the class provides a check for all files in a directory. To enable this check
    `self.dirChecksEnable` must be `True`. Depending of the result of the check different folder
    icons are returned. The check is not recursive! When if file is checked in this mode the signal
    `fileCheck` is emitted.
    """
    class Emitter(QObject):
        """Signals can only be emitted from classes derived from QOject. As QFileIconProvider
        is not derived from QOject this nested class provides this feature."""
        fileCheck = pyqtSignal()

        def __init__(self):
            super().__init__()

    def __init__(self, parent=None):
        super().__init__(parent)
        #: cache for file informations to speed-up painting.
        #: QModelIndex is used is as key parameter
        self.fileInfoCache = {}
        #: enables directory checking
        self.dirChecksEnable = False
        # preload icons for speed
        # fallback does not work in KDE due to Bug 342906
        self.redFolderIcon = QIcon.fromTheme("folder-red", QIcon(":/icons/folder-red.svg"))
        self.standardFolderIcon = QIcon.fromTheme("folder", QIcon(":/icons/folder.svg"))

        self.emitter = TagFileSystemModel.Emitter()

    def headerData(self, section, orientation, role):
        """Reimplemented to be able to add an additional header for
        customized columns.

        :returns: "ID3v2" for the customized column, else super()
        """
        if (section == self.columnCount() - 1):
            if (role == Qt.DisplayRole):
                return("ID3v2")

        return super().headerData(section, orientation, role)

    def data(self, index, role):
        """Reimplemented to enable coloring of lines depending on file type and if lyrics are
        available or not. Additionally, the ID3v2 column is generated.

        Before the file itself is analyzed the cached information is checked.

        If `self.dirChecksEnable` is set to `True` the content of sub-directories is checked
        as well.
        """
        # add ID3v2 version number into dedicated column.
        if ((role == Qt.DisplayRole)) and (index.column() == self.columnCount() - 1):
            if (index, 'tagversion') not in self.fileInfoCache:
                if self.fileInfo(index).isFile() and self.isMP3(self.filePath(index)):
                    self.fileInfoCache[index, 'tagversion'] = \
                        self.id3v2Version(self.filePath(index))
                else:
                    self.fileInfoCache[index, 'tagversion'] = \
                        QApplication.translate('TagFileSystemModel', "N.A.")
            return self.fileInfoCache[index, 'tagversion']

        # paint rows in different colors depending if lyrics are available or not
        if (role == Qt.ForegroundRole):
            if (index, 'color') not in self.fileInfoCache:
                if self.fileInfo(index).isFile() and self.isMP3(self.filePath(index)):
                    if self.hasID3Lyrics(self.filePath(index)):
                        self.fileInfoCache[index, 'color'] = QVariant(QColor("green"))
                    else:
                        self.fileInfoCache[index, 'color'] = QVariant(QColor("red"))
                else:
                    self.fileInfoCache[index, 'color'] = super().data(index, role)
            return self.fileInfoCache[index, 'color']

        # directory checks if requested
        if (self.dirChecksEnable and
                role == Qt.DecorationRole and
                index.column() == 0 and
                self.fileInfo(index).isDir()):
            if (index, 'icon') not in self.fileInfoCache:
                if not self.checkDirectory(self.fileInfo(index).absoluteFilePath()):
                    self.fileInfoCache[index, 'icon'] = self.redFolderIcon
                else:
                    self.fileInfoCache[index, 'icon'] = self.standardFolderIcon

            return self.fileInfoCache[index, 'icon']

        return super().data(index, role)

    def columnCount(self, parent=None):
        """Reimplemented to be able to add an header for customized columns.

        :returns: number of columns including the customized columns.
        """
        return super().columnCount()+1

    def isMP3(self, filePath):
        """Test if file is MP3 file by using Mutagen's MIME type evaluation.

        :returns: True if file is an MP3, False else.
        :rtype: boolean
        """
        try:
            return ((mutagen.File(filePath) is not None and
                    'audio/mp3' in mutagen.File(filePath).mime) or
                    False)
        except PermissionError:
            return False

    def id3v2Version(self, filePath):
        """ID3 tag version number. If ID3v1 and ID3v2 tags are located in the file. The version
        of ID3v2 is returned only.

        :return: version number
        :rtype: str
        """
        return ('.'.join(str(i) for i in ID3(filePath).version))

    def hasID3Lyrics(self, filePath):
        """Test if file has lyrics in ID3 tag by getting all USLT frames.

        :returns: True if lyrics are available, False else.
        :rtype: boolean
        """
        return (self.isMP3(filePath) and ID3(filePath).hasLyrics) or False

    def checkDirectory(self, path):
        """Return True if every mp3-file in `path` have embedded lyrics. Otherwise, False.
        Subdirectories are not checked!

        The pyqtSignal `fileCheck` is emitted every time a file is checked.

        :return: if all mp3 files have lyrics
        :rtype: boolean
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

        return allHaveLyrics

    def removeFromFileInfoCache(self, filePathOrIndex):
        """Removes specified files from fileInfoCache."""
        # If filePathOrIndex is not QModelIndex find index of corresponding path
        if type(filePathOrIndex) != QModelIndex:
            index = self.index(filePathOrIndex)
        else:
            index = filePathOrIndex

        filePath = self.fileInfo(index).filePath()
        # loop over all columns in model and deleted cached values
        for col in range(0, self.columnCount()):
            idx = self.index(filePath, col)
            self._delFromFileInfoCache(idx)

        # If its a directory remove the containing files as well
        if self.fileInfo(index).isDir():
            # dirIterator contains all files and directories recursively
            dirIterator = QDirIterator(self.fileInfo(index).filePath(),
                                       QDir.AllEntries | QDir.Readable | QDir.NoDotAndDotDot,
                                       QDirIterator.Subdirectories)

            while dirIterator.hasNext():
                f = (dirIterator.next())
                for col in range(0, self.columnCount()):
                    self._delFromFileInfoCache(self.index(f, col))

    def _delFromFileInfoCache(self, partialKey):
        """Removes all elements from cache having `partialKey` in key."""
        # keys() will not work in Python 3 because an iterator is returned
        for item in list(self.fileInfoCache):
            if partialKey in item:
                #print("R ", self.fileInfo(item[0]).filePath())
                del self.fileInfoCache[item]

    def clearFileInfoCache(self):
        """Clears self.fileInfoCache."""
        self.fileInfoCache = {}
