#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
##############################################################################
#   USLT Manager
#
#   Version: 0.1-alpha
#
#   last edit: 2015-06-14
#
#   Author: Stefan Gansinger <stefan.gansinger@posteo.at>
#
#   Description: Mangment for lyrics stored in the USLT frame of the ID3v2
#                tag of mp3 files
#
#   Thanks: o Michael Urman for Python-Mutagen and all people who contributed
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

from pathlib import Path

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import mutagen
from mutagen import version as mutagenVersion
from mutagen.id3 import ID3, USLT, Encoding

from lngcodes import *


class MainWindow(QMainWindow):
    def __init__(self, rootPath="/", parent=None, flags=Qt.WindowFlags(0)):
        super().__init__(parent, flags)

        self.showMaximized()

        self.centralWidget = self.CentralWidget(rootPath)
        self.setCentralWidget(self.centralWidget)

        mainIcon = QIcon("lyrics_id3_icon.svg")
        self.setWindowIcon(mainIcon)
        self.setWindowTitle("USLT Manager[*]")

        self.centralWidget.closeButton.clicked.connect(self.close)
        self.centralWidget.tagWidget.tagModified.connect(self.tagModified)

    def tagModified(self, modified):
        self.setWindowModified(modified)

    def closeEvent(self, event):
        if self.isWindowModified():
            ret = self.centralWidget.tagWidget.saveChangesDialog(QMessageBox.Save |
                                                                 QMessageBox.Discard |
                                                                 QMessageBox.Cancel)
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

    class CentralWidget(QWidget):
        def __init__(self, rootPath="/", parent=None):
            super().__init__(parent)

            mainLayout = QGridLayout()
            rightWidget = QWidget()
            rightLayout = QGridLayout()
            rightWidget.setLayout(rightLayout)

            fileTree = FileTree(rootPath)
            self.tagWidget = TagWidget()
            closeButtonIcon = QIcon.fromTheme("application-exit")
            self.closeButton = QPushButton(QCoreApplication.translate('MainWindow', "Exit"))
            self.closeButton.setIcon(closeButtonIcon)

            rightLayout.addWidget(self.tagWidget, 0, 0)
            rightLayout.addWidget(self.closeButton, 1, 0)

            splitter = QSplitter()
            splitter.addWidget(fileTree)
            splitter.addWidget(rightWidget)

            mainLayout.addWidget(splitter, 0, 0)

            self.setLayout(mainLayout)

            fileTree.mp3Selected.connect(self.tagWidget.loadAndShowTag)
            fileTree.nonmp3Selected.connect(self.tagWidget.unloadAndHideTag)


class TagWidget(QWidget):
    """Widget showing the most important ID3 tag values. Most importantly the lyrics.

    If the tag has been modified compared to the last savedd version tagModified(True) is emitted.
    If the ID3 tag matches the view elements tagModified(False) is emitted.
    """

    tagModified = pyqtSignal(bool)

    def __init__(self, parent=None):
        """Initialization of the widget. By default GUI element is disabled."""
        super().__init__(parent)

        mainLayout = QFormLayout()

        self.artistLineEdit = QLineEdit()
        self.artistLineEdit.setReadOnly(True)

        self.titleLineEdit = QLineEdit()
        self.titleLineEdit.setReadOnly(True)

        self.lyricsSelection = QComboBox()
        self.lyricsSelection.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.lyricsSelection.setDisabled(True)

        self.lyricsDisplay = QPlainTextEdit()
        self.lyricsDisplay.setReadOnly(True)
        # expand lyrics display to the bottom
        policy = self.lyricsDisplay.sizePolicy()
        policy.setVerticalStretch(1)
        self.lyricsDisplay.setSizePolicy(policy)

        spacer = QSpacerItem(0, 0, QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)

        addLyricsButtonIcon = QIcon.fromTheme("list-add")
        removeLyricsButtonIcon = QIcon.fromTheme("list-remove")
        editLyricsButtonIcon = QIcon.fromTheme("insert-text")
        searchLyricsButtonIcon = QIcon.fromTheme("system-search")
        saveTagButtonIcon = QIcon.fromTheme("document-save")
        reloadTagButtonIcon = QIcon.fromTheme("view-refresh")

        lyricsModifyToolbar = QToolBar()
        lyricsModifyToolbar.setFloatable(False)
        lyricsModifyToolbar.setMovable(False)

        self.editLyricsAction = lyricsModifyToolbar.addAction(
            editLyricsButtonIcon, QCoreApplication.translate('TagWidget', "Edit Lyrics"),
            self.editLyricsActionReceiver)
        self.addLyricsAction = lyricsModifyToolbar.addAction(
            addLyricsButtonIcon, QCoreApplication.translate('TagWidget', "Add Lyrics"),
            self.addLyricsActionReceiver)
        self.removeLyricsAction = lyricsModifyToolbar.addAction(
            removeLyricsButtonIcon, QCoreApplication.translate('TagWidget', "Remove Lyrics"),
            self.removeLyricsActionReceiver)
        self.searchLyricsAction = lyricsModifyToolbar.addAction(
            searchLyricsButtonIcon, QCoreApplication.translate('TagWidget', "Search for Lyrics"),
            self.searchLyricsActionReceiver)
        self.saveTagAction = lyricsModifyToolbar.addAction(
            saveTagButtonIcon, QCoreApplication.translate('TagWidget', "Save Tag"),
            self.saveTagActionReceiver)
        self.reloadTagAction = lyricsModifyToolbar.addAction(
            reloadTagButtonIcon, QCoreApplication.translate('TagWidget', "Reload Tag"),
            self.reloadTagActionReceiver)

        self.editLyricsAction.setShortcut(QKeySequence(Qt.CTRL + Qt.Key_E))
        self.addLyricsAction.setShortcut(QKeySequence(Qt.CTRL + Qt.Key_A))
        self.removeLyricsAction.setShortcut(QKeySequence(Qt.CTRL + Qt.Key_D))
        #self.searchLyricsAction.setShortcut(None)
        self.saveTagAction.setShortcut(QKeySequence(Qt.CTRL + Qt.Key_S))
        self.reloadTagAction.setShortcut(QKeySequence(Qt.CTRL + Qt.Key_R))

        lyricsModifyToolbar.insertSeparator(self.saveTagAction)
        self.editLyricsAction.setDisabled(True)
        self.addLyricsAction.setDisabled(True)
        self.removeLyricsAction.setDisabled(True)
        self.searchLyricsAction.setDisabled(True)
        self.saveTagAction.setDisabled(True)
        self.tagModified.emit(False)
        self.reloadTagAction.setDisabled(True)

        selectionGrid = QGridLayout()
        selectionGrid.addWidget(self.lyricsSelection, 0, 0, Qt.AlignLeft)
        selectionGrid.addItem(spacer, 0, 1, Qt.AlignLeft)
        selectionGrid.addWidget(lyricsModifyToolbar, 0, 2, Qt.AlignRight)

        mainLayout.addRow(QApplication.translate('TagWidget', "Artist"), self.artistLineEdit)
        mainLayout.addRow(QApplication.translate('TagWidget', "Title"), self.titleLineEdit)
        mainLayout.addRow(QApplication.translate('TagWidget', "Selection"), selectionGrid)
        mainLayout.addRow(QApplication.translate('TagWidget', "Lyrics"), self.lyricsDisplay)

        self.setLayout(mainLayout)
        self.setDisabled(True)

        # update lyrics if a different selection (language/description) is made
        self.lyricsSelection.currentIndexChanged.connect(self.showLyrics)

    def editLyricsActionReceiver(self):
        """Enable editing of lyrics in view."""
        self.lyricsDisplay.setReadOnly(False)
        self.editLyricsAction.setDisabled(True)
        self.addLyricsAction.setDisabled(True)
        self.removeLyricsAction.setDisabled(True)
        self.searchLyricsAction.setDisabled(False)
        self.lyricsSelection.setDisabled(True)
        self.saveTagAction.setDisabled(False)
        self.tagModified.emit(True)

    def addLyricsActionReceiver(self):
        """Initiates the AddLyricsDialog."""
        addLyricsDialog = AddLyricsDialog(self)
        if (addLyricsDialog.exec() == QDialog.Accepted):
            lng = addLyricsDialog.lngCodeComboBox.currentText()
            dsc = addLyricsDialog.descriptionLineEdit.text()
            enc = addLyricsDialog.encComboBox.currentData()
            lyr = addLyricsDialog.lyricsEdit.toPlainText()
            # add  lyrics to tag object
            self.tag.lyrics[(lng, dsc)] = [enc, lyr]
            # update lyrics in view
            self.setLyrics()
            # select currently added lyrics in view
            self.lyricsSelection.setCurrentText("/".join((lng, dsc)))
            self.saveTagAction.setDisabled(False)
            self.tagModified.emit(True)

        # save memory
        del addLyricsDialog

    def removeLyricsActionReceiver(self):
        """Delete lyrics from tag objects."""
        del self.tag.lyrics[self.lyricsSelection.currentData()]
        # update lyrics in view
        self.setLyrics()
        self.saveTagAction.setDisabled(False)
        self.tagModified.emit(True)

    def searchLyricsActionReceiver(self):
        """Search for lyrics in external browser."""
        QDesktopServices.openUrl(QUrl("https://www.google.com/search?as_q=\"lyrics\"+\"" +
                                      self.tag.artist + "\"+\"" + self.tag.title + "\"")
                        .adjusted(QUrl.FullyEncoded))

    def reloadTagActionReceiver(self):
        """Reload view by loading tag again from file."""
        # Ask user if modifcations needs to be saved (indicated by saveTagAction)
        #   but only if new file is loaded
        if (self.saveTagAction.isEnabled()):
            # No Cancel button is offered as a different file might be selected in tree view
            ret = self.saveChangesDialog(QMessageBox.Save | QMessageBox.Discard)
            if (ret == QMessageBox.Save):
                self.saveTagActionReceiver()
            self.saveTagAction.setDisabled(True)
            self.tagModified.emit(False)

        self.loadAndShowTag(self.tag.filePath)

    def saveTagActionReceiver(self):
        """Save lyrics to file."""
        # read back any modications in lyricsDisplay
        try:
            self.tag.lyrics[self.lyricsSelection.currentData()][1] = \
                self.lyricsDisplay.toPlainText()
        except KeyError:
            # No more lyrics left
            pass

        try:
            self.tag.save()
        except IOError as err:
            errorMessageDialog = QMessageBox()
            errorMessageDialog.setIcon(QMessageBox.Critical)
            errorMessageDialog.setInformativeText(QCoreApplication.translate(
                'TagWidget', "Could not write to file!"))
            errorMessageDialog.setText(str(err))
            errorMessageDialog.setStandardButtons(QMessageBox.Ok)
            errorMessageDialog.exec()
        else:
            self.saveTagAction.setDisabled(True)
            self.tagModified.emit(False)

    def saveChangesDialog(self, buttons):
        msgBox = QMessageBox()
        msgBox.setText(QCoreApplication.translate('TagWidget', "Lyrics have been modified."))
        msgBox.setInformativeText(QCoreApplication.translate(
            'TagWidget', "Do you want to save your changes?"))
        msgBox.setStandardButtons(buttons)
        msgBox.setDefaultButton(QMessageBox.Save)

        # FIXME: Workaround for missing or at least not working QMessageBox
        #   It seems that the translations are stored in the context of QPlatformTheme
        if msgBox.button(QMessageBox.Discard) is not None:
            msgBox.button(QMessageBox.Discard). \
                setText(QCoreApplication.translate('QPlatformTheme', "Discard"))
        if msgBox.button(QMessageBox.Cancel) is not None:
            msgBox.button(QMessageBox.Cancel). \
                setText(QCoreApplication.translate('QPlatformTheme', "Cancel"))
        if msgBox.button(QMessageBox.Save) is not None:
            msgBox.button(QMessageBox.Save). \
                setText(QCoreApplication.translate('QPlatformTheme', "Save"))

        return msgBox.exec()

    def loadAndShowTag(self, filePath):
        """Load tag, show tag values, and disable GUI elements."""
        # Ask user if modifcations needs to be saved (indicated by saveTagAction)
        #   but only if new file is loaded
        if (self.saveTagAction.isEnabled() and filePath != self.tag.filePath):
            # No Cancel button is offered as a different file might be selected in tree view
            ret = self.saveChangesDialog(QMessageBox.Save | QMessageBox.Discard)
            if (ret == QMessageBox.Save):
                self.saveTagActionReceiver()
            self.saveTagAction.setDisabled(True)
            self.tagModified.emit(False)

        # Tag might just be modified, so unload it to make sure
        self.unloadAndHideTag()
        self.tag = ID3Tag(filePath)
        self.setDisabled(False)
        self.reloadTagAction.setDisabled(False)
        self.setArtistName()
        self.setTitleName()
        self.setLyrics()

    def unloadAndHideTag(self):
        """Unload Tag and disable GUI elements."""
        # Ask user if modifcations needs to be saved (indicated by saveTagAction
        if (self.saveTagAction.isEnabled()):
            # No Cancel button is offered as a different file might be selected in tree view
            ret = self.saveChangesDialog(QMessageBox.Save | QMessageBox.Discard)
            if (ret == QMessageBox.Save):
                self.saveTagActionReceiver()
            self.saveTagAction.setDisabled(True)
            self.tagModified.emit(False)

        self.setDisabled(True)
        self.lyricsSelection.setDisabled(True)
        self.editLyricsAction.setDisabled(True)
        self.addLyricsAction.setDisabled(True)
        self.removeLyricsAction.setDisabled(True)
        self.searchLyricsAction.setDisabled(True)
        self.saveTagAction.setDisabled(True)
        self.tagModified.emit(False)
        self.reloadTagAction.setDisabled(True)
        self.lyricsDisplay.setReadOnly(True)
        self.unsetAll()
        try:
            del self.tag
        except AttributeError:
            pass

    def setArtistName(self):
        """Show the artist name."""
        self.artistLineEdit.setText(self.tag.artist)

    def setTitleName(self):
        """Show the title name."""
        self.titleLineEdit.setText(self.tag.title)

    def setLyrics(self):
        """Show lyrics and language/description keys."""
        self.lyricsSelection.clear()
        self.lyricsDisplay.clear()

        self.addLyricsAction.setDisabled(not self.tag.writeable)
        self.searchLyricsAction.setDisabled(False)

        if self.tag.lyrics:
            self.editLyricsAction.setDisabled(not self.tag.writeable)
            self.removeLyricsAction.setDisabled(not self.tag.writeable)
            self.lyricsSelection.setDisabled(False)
            for key, lyrics in self.tag.lyrics.items():
                self.lyricsSelection.addItem("/".join(key), userData=key)

            self.lyricsDisplay.setPlainText(self.tag.lyrics[self.lyricsSelection.currentData()][1])
        else:
            self.editLyricsAction.setDisabled(True)
            self.removeLyricsAction.setDisabled(True)
            self.lyricsSelection.setDisabled(True)

    def showLyrics(self, index):
        """Show lyrics depending on selected language/description key."""
        key = self.lyricsSelection.itemData(index)
        if key in self.tag.lyrics:
            self.lyricsDisplay.setPlainText(self.tag.lyrics[key][1])

    def unsetArtist(self):
        """Clear artist display."""
        self.artistLineEdit.clear()

    def unsetTitle(self):
        """Clear title display."""
        self.titleLineEdit.clear()

    def unsetLyrics(self):
        """Clear lyrics display."""
        self.lyricsSelection.clear()
        self.lyricsDisplay.clear()

    def unsetAll(self):
        """Clear every GUI elements holding tag values."""
        self.unsetArtist()
        self.unsetTitle()
        self.unsetLyrics()


class AddLyricsDialog(QDialog):
    """Dialog for editing lyrics to be stored in file"""

    class ASCIIValidator(QValidator):
        """Sub-class for validation of ASCII input"""
        inputValid = pyqtSignal()
        inputInvalid = pyqtSignal()

        def __init__(self, parent=None):
            super().__init__(parent)

        def validate(self, inp, pos):
            """return QValidator.Acceptable if entered string contains ASCII only.
            Otherwise, QValidator.Intermediate.
            """
            try:
                inp.encode('ascii')
            except UnicodeEncodeError:
                self.inputInvalid.emit()
                return (QValidator.Intermediate, inp, pos)
            else:
                self.inputValid.emit()
                return (QValidator.Acceptable, inp, pos)

        def fixup(self, input):
            return super().fixup(input)

    def __init__(self, parent):
        super().__init__(parent, Qt.WindowStaysOnTopHint)
        self.setModal(True)
        self.setWindowTitle(QCoreApplication.translate('AddLyricsDialog', "Add Lyrics"))

        mainLayout = QGridLayout()

        inputFieldsLayout = QFormLayout()
        #inputFieldsLayout.setRowWrapPolicy(QFormLayout.WrapAllRows)

        # Language settings
        lngCodeLayout = QBoxLayout(QBoxLayout.LeftToRight)
        self.lngCodeComboBox = QComboBox()
        self.lngCodeComboBox.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.lngCodeComboBox.addItems(sorted(ISO639_2_CODES.keys()))
        self.lngCodeLabel = QLabel()
        lngCodeLayout.addWidget(self.lngCodeComboBox)
        lngCodeLayout.addWidget(self.lngCodeLabel)
        self.lngCodeComboBox.setCurrentText("und")
        self.lngCodeLabel.setText(ISO639_2_CODES[self.lngCodeComboBox.currentText()])
        inputFieldsLayout.addRow(QCoreApplication.translate('AddLyricsDialog', "Language:"),
                                 lngCodeLayout)

        # Description settings
        self.descriptionLineEdit = QLineEdit()
        self.descriptionLineEdit.setText("USLT Manager")
        descriptionValidator = self.ASCIIValidator()
        self.descriptionLineEdit.setValidator(descriptionValidator)
        self.descriptionErrorLabel = QLabel()
        descriptionValidator.inputValid.connect(self.validDescription)
        descriptionValidator.inputInvalid.connect(self.invalidDescription)
        inputFieldsLayout.addRow(QCoreApplication.translate('AddLyricsDialog', "Description:"),
                                 self.descriptionLineEdit)

        # Encoding settings
        self.encComboBox = QComboBox()
        self.encComboBox.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.encComboBox.addItem("Latin-1", Encoding.LATIN1)
        self.encComboBox.addItem("UTF-16", Encoding.UTF16)
        self.encComboBox.addItem("UTF-16BE", Encoding.UTF16BE)
        self.encComboBox.addItem("UTF-8", Encoding.UTF8)
        self.encComboBox.setCurrentText("UTF-8")
        inputFieldsLayout.addRow(QCoreApplication.translate('AddLyricsDialog', "Encoding:"),
                                 self.encComboBox)

        # Lyrics
        self.lyricsEdit = QPlainTextEdit()
        ## expand lyrics display to the bottom
        policy = self.lyricsEdit.sizePolicy()
        policy.setVerticalStretch(1)
        self.lyricsEdit.setSizePolicy(policy)
        inputFieldsLayout.addRow(QCoreApplication.translate('AddLyricsDialog', "Lyrics:"),
                                 self.lyricsEdit)

        # Buttons
        okButtonIcon = QIcon.fromTheme("dialog-ok")
        self.okButton = QPushButton(QCoreApplication.translate('AddLyricsDialog', "Ok"))
        self.okButton.setIcon(okButtonIcon)
        cancelButtonIcon = QIcon.fromTheme("dialog-close")
        cancelButton = QPushButton(QCoreApplication.translate('AddLyricsDialog', "Cancel"))
        cancelButton.setIcon(cancelButtonIcon)

        mainLayout.addLayout(inputFieldsLayout, 0, 0, 1, 2)
        mainLayout.addWidget(self.okButton, 10, 0)
        mainLayout.addWidget(cancelButton, 10, 1)

        self.setLayout(mainLayout)

        self.lngCodeComboBox.currentIndexChanged.connect(self.updateCodeLabel)
        self.okButton.clicked.connect(self.accept)
        cancelButton.clicked.connect(self.reject)

    def updateCodeLabel(self):
        self.lngCodeLabel.setText(ISO639_2_CODES[self.lngCodeComboBox.currentText()])

    def invalidDescription(self):
        okButtonIcon = QIcon.fromTheme("dialog-error")
        self.okButton.setDisabled(True)
        self.okButton.setFlat(True)
        self.okButton.setText(QCoreApplication.translate('AddLyricsDialog',
                              "Only ASCII characters are allowed for description."))
        self.okButton.setIcon(okButtonIcon)

    def validDescription(self):
        okButtonIcon = QIcon.fromTheme("dialog-ok")
        self.okButton.setDisabled(False)
        self.okButton.setFlat(False)
        self.okButton.setText(QCoreApplication.translate('AddLyricsDialog', "Ok"))
        self.okButton.setIcon(okButtonIcon)


class ID3Tag():
    """Simple ID3 tag class holding the most important tag values.

    It uses the following format:
       ID3Tag['artist'] ... artist str of song (TPE1) [might be None]
       ID3Tag['title']  ... title str of song (TIT2) [might be None]
       ID3Tag['USLT'][(language,description)]   ... lyrics dict;
         the key is a tuple of language and description
         value is a list, while list[0] is the encoding coded as integer
         and list[1] are the lyrics str
    """
    def __init__(self, filePath):

        self._filePath = filePath

        self._writeable = os.access(self._filePath, os.W_OK)

        id3tag = ID3(self._filePath)

        self._tag = {}
        try:
            self._tag['artist'] = str(id3tag.getall('TPE1')[0])
        except IndexError:
            self._tag['artist'] = None

        try:
            self._tag['title'] = str(id3tag.getall('TIT2')[0])
        except IndexError:
            self._tag['title'] = None

        lyricsKeys = id3tag.getall('USLT')
        self._tag['USLT'] = {}
        for key in lyricsKeys:
            self._tag['USLT'][(key.lang, key.desc)] = [key.encoding, key.text]

        del id3tag
        #FIXME: If the file handle is closed, the file might be modified in the background.

    def save(self):
        """Store self._tag['USLT'] in file"""
        id3tag = ID3(self._filePath)

        lyricsKeys = id3tag.getall('USLT')
        for key in lyricsKeys:
            id3tag.delall('USLT:' + key.desc + ":" + key.lang)

        for key, lyrics in self._tag['USLT'].items():
            uslt = USLT(encoding=lyrics[0], lang=key[0], desc=key[1], text=lyrics[1])
            id3tag.add(uslt)

        id3tag.save()

    @property
    def filePath(self):
        """Return the file-path of the the tag."""
        return self._filePath

    @property
    def tag(self):
        """Return the tag as Dict."""
        return self._tag

    @property
    def artist(self):
        """Return artist string."""
        return self._tag['artist']

    @property
    def title(self):
        """Return title as string."""
        return self._tag['title']

    @property
    def lyrics(self):
        """Return lyrics as dict."""
        return self._tag['USLT']

    @property
    def writeable(self):
        """Retrun True if file is writeable"""
        return self._writeable


class FileTree(QWidget):
    """QTreeView enhanced by editable root, either by line edit or file dialog.
    A QFileSystemWatcher montiors visible files in the tree for changed. If a file
    is selected signal is emited. If its a MP3 file mp3Selected is emited.
    Otherwise, nonmp3Selected.
    """
    # Appropriate signal is emited if a file is selected
    mp3Selected = pyqtSignal(str)
    nonmp3Selected = pyqtSignal(str)

    class DirValidator(QValidator):
        """Sub-class for validation of root input. Validates if input is a valid directory."""
        def __init__(self, parent=None):
            super().__init__(parent)

        def validate(self, inp, pos):
            """return QValidator.Acceptable if entered directory is valid. Otherwise,
            QValidator.Intermediate.
            """
            if Path(inp).is_dir():
                return (QValidator.Acceptable, inp, pos)
            else:
                return (QValidator.Intermediate, inp, pos)

        def fixup(self, input):
            return super().fixup(input)

    def __init__(self, rootPath, parent=None):
        super().__init__(parent)

        self.rootPath = rootPath

        self.model = TagFileSystemModel()
        self.model.setRootPath(self.rootPath)

        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(self.rootPath))

         # Address line with address label, navigation icons and browser Icon
        openBrowserIcon = QIcon.fromTheme("folder")
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
        upButtonIcon = QIcon.fromTheme("go-up")
        upButton = QPushButton()
        upButton.setIcon(upButtonIcon)

        mainLayout = QGridLayout()
        mainLayout.addWidget(openBrowserButton, 0, 0)
        mainLayout.addWidget(self.addressLabel, 0, 1)
        mainLayout.addWidget(upButton, 0, 2)
        mainLayout.addWidget(self.tree, 1, 0, 1, 3)
        self.setLayout(mainLayout)

        # clear color cache of TagFileSystemModel if directories are expanded/collapsed
        self.tree.expanded.connect(self.model.clearFileInfoCache)
        self.tree.collapsed.connect(self.model.clearFileInfoCache)
        # Process newly selected files (e.g. emit mp3Selected)
        self.tree.selectionModel().selectionChanged.connect(self.selectionChanged)
        # Double clicked on selection
        self.tree.doubleClicked.connect(self.doubleClickEvent)
        # Notify for rootChanged() when new root have been entered
        #   (DirValidator prevents invalid directories)
        self.addressLabel.editingFinished.connect(self.rootChanged)
        # Open file dialog if button is clicked
        openBrowserButton.clicked.connect(self.fileDialog)
        # Go up in tree hierachy on button click
        upButton.clicked.connect(self.goUp)
        # force as this is the initialization
        self.rootChanged(force=True)

    def rootChanged(self, force=False):
        """Initialsize all required properties, if root has changed. To force
        initialization force must be True.
        """
        if self.rootPath != self.addressLabel.text() or force:
            self.rootPath = self.addressLabel.text()
            self.model.setRootPath(self.rootPath)
            self.tree.setRootIndex(self.model.index(self.rootPath))
            self.createFileSystemWatcher(self.rootPath)
            self.nonmp3Selected.emit(None)

    def createFileSystemWatcher(self, path):
        """Create a QFileSystemWatcher including all files and directories within path.
        Additionally, the necessary connections to the TagFileSystemModel are generated.
        """

        absolutePath = QDir(path).absolutePath()
        #FIXME: If file is not readable its not in the watchlist.
        #   Thus a toggling read flag is recognized.
        fileList = QDir(path).entryList(QDir.AllEntries | QDir.Readable |
                                        QDir.NoDotDot, QDir.DirsFirst)
        fileList = [absolutePath + "/" + s for s in fileList]

        try:
            del self.fileSystemWatcher
        except AttributeError:
            pass
        self.fileSystemWatcher = QFileSystemWatcher(fileList)
        #print("New watcher: " + ",".join(fileList))

        # clear color cache of TagFileSystemModel if watched directory or file changes
        self.fileSystemWatcher.directoryChanged.connect(self.model.clearFileInfoCache)
        self.fileSystemWatcher.fileChanged.connect(self.model.clearFileInfoCache)

        # If directory was changed, files might have been added
        #   --> add them to the QFileSystemWatcher
        self.fileSystemWatcher.directoryChanged.connect(self.modifyWatcher)

        # a watched file has changed --> react
        self.fileSystemWatcher.fileChanged.connect(self.fileChanged)

        # update QFileSystemWatcher on expanded/collapsed directories in QTreeView
        self.tree.expanded.connect(self.modifyWatcher)
        self.tree.collapsed.connect(self.modifyWatcher)

        #print("Watching" + str(self.fileSystemWatcher.files()))

    def doubleClickEvent(self):
        """Set root to the currently selected directory. (Should be called on doubleClickEvent)"""
        selectedPath = self.model.filePath(self.tree.selectionModel().selectedIndexes()[0])
        if Path(selectedPath).is_dir():
            self.addressLabel.setText(selectedPath)
            self.rootChanged()

    def goUp(self):
        """Go one hierachy up for the root"""
        actDir = QDir(self.addressLabel.text())
        if actDir.cdUp():
            self.addressLabel.setText(QDir.absolutePath(actDir))
            self.rootChanged()

    def fileDialog(self):
        """File dialog to set new root"""
        path = QFileDialog.getExistingDirectory(self, directory=self.rootPath)
        if path:
            self.addressLabel.setText(path)
            self.rootChanged()

    def modifyWatcher(self, index):
        """Add or remove files from the fileSystemWatcher.

        Depending if tree is expanded or collapsed files are removed or added.
        """
        # index should be of QModelIndexType. If its a str I assume its a path
        #   --> find index in model
        if type(index) is str:
            index = self.model.index(index)

        filePath = self.model.filePath(index)
        absolutePath = QDir(filePath).absolutePath()
        fileList = QDir(filePath).entryList(QDir.AllEntries | QDir.Readable |
                                            QDir.NoDotDot, QDir.DirsFirst)
        fileList = [absolutePath + "/" + s for s in fileList]

        if self.tree.isExpanded(index) or index == self.tree.rootIndex():
            #print("Adding: " + str(fileList))
            self.fileSystemWatcher.addPaths(fileList)
        else:
            #print("Removing: " + str(fileList))
            self.fileSystemWatcher.removePaths(fileList)

        #print("Watching" + str(self.fileSystemWatcher.files()))

    def selectionChanged(self, selected, deselected):
        """Emit mp3Selected or nonmp3Selected for the selected file.
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
        """Emit mp3Selected or nonmp3Selected for the selected file.
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
    """File system model to be used w/ QTreeView. It enhances the classical
    QFileSystemModel w/ ID3 tag handling. To speed up file handling important
    file parameters are cached in the object variable self.fileInfoCache.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # cache for file informations to speed-up painting
        self.fileInfoCache = {}

    def headerData(self, section, orientation, role):
        """Reimplemented to be able to add an addtional header for
        customly added columns.
        """
        if (section == self.columnCount() - 1):
            if (role == Qt.DisplayRole):
                return("ID3v2")

        return super().headerData(section, orientation, role)

    def data(self, index, role):
        """Reimplemented to enable coloring of lines depending on file type and if lyrics are
        availabe or not. Additionally, the ID3v2 column is generated.
        """
        # Add ID3v2 column and add version number into dedicated column. Version numbers
        #  of already displayed files are cached in fileInfoCache.
        if (index.column() == self.columnCount() - 1):
            if (role == Qt.DisplayRole):
                if (index, 'tagversion') not in self.fileInfoCache:
                    if self.fileInfo(index).isFile() and self.isMP3(self.filePath(index)):
                        self.fileInfoCache[index, 'tagversion'] = \
                            self.id3v2Version(self.filePath(index))
                    else:
                        self.fileInfoCache[index, 'tagversion'] = \
                            QApplication.translate('TagFileSystemModel', "N.A.")
                return self.fileInfoCache[index, 'tagversion']

        # paint rows in different colors depending if lyrics are availabe or not
        #  test for lyrics on every paint actions makes the program really slow, so
        #  the colors are cached in self.fileInfoCache. If the color is already cached,
        #  the file is not tested anymore
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

        return super().data(index, role)

    def columnCount(self, parent=None):
        """Reimplemented to be able to add an addtional header for
        customly added columns.

        Returns the number of colmuns including the customly
        added colmuns.
        """
        return super().columnCount()+1

    def isMP3(self, filePath):
        """Test if file is MP3 file by using Mutagen's MIME type evaluation."""
        try:
            return ((mutagen.File(filePath) is not None and
                    'audio/mp3' in mutagen.File(filePath).mime) or
                    False)
        except PermissionError:
            return False

    def id3v2Version(self, filePath):
        """Return the ID3v2 version number."""
        return ('.'.join(str(i) for i in ID3(filePath).version))

    def hasID3Lyrics(self, filePath):
        """Test if file has lyrics in ID3 tag by getting all USLT frames."""
        return (self.isMP3(filePath) and ID3(filePath).getall('USLT')) or False

    def clearFileInfoCache(self):
        """Clears the fileInfoCache."""
        self.fileInfoCache = {}

if __name__ == '__main__':
    import sys

    mutagenVersion = int("".join(map(str, mutagenVersion[:2])))

    if mutagenVersion >= 125:
        app = QApplication(sys.argv)

        locale = QLocale.system()
        usltTranslator = QTranslator()
        if usltTranslator.load(locale, "uslt-manager", "_"):
            app.installTranslator(usltTranslator)

        if len(sys.argv) > 1 and QDir(sys.argv[1]).isReadable():
            screen = MainWindow(sys.argv[1])
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
