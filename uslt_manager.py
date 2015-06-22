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
#   Description: Management for lyrics stored in the USLT frame of the ID3v2
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

# qt resource file created w/ pyrcc5 -o qrc_resources_rc.py uslt_manager.qrc
import qrc_resources_rc


class MainWindow(QMainWindow):
    """Main window of application

    :param rootPath: Path to root directory
    """
    def __init__(self, rootPath="/", parent=None, flags=Qt.WindowFlags(0)):
        super().__init__(parent, flags)

        self.showMaximized()

        self.centralWidget = self.CentralWidget(rootPath)
        self.setCentralWidget(self.centralWidget)

        # Absolute path is required here.
        # However, QCoreApplication.applicationDirPath()) will not work since it will
        # return the path to the python executable. Thus qrc_resources_rc is used instead
        mainIcon = QIcon(":/lyrics_id3_icon.svg")
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

    By default all GUI elements are disabled. They are enabled when a mp3 file is loaded
    using :func:`loadAndShowTag()`.

    The `pyqtSignal` :data:`tagModified` is used to notify if changes have been made
    """

    #: emitted with the parameter True when tag has been modified
    #: emitted with the parameter False when view elements match the tag content
    #: i.e. when tag has been saved or tag is reloaded
    tagModified = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        #: Encodings available for USLT and defined in mutagen
        self.encoding = {}
        self.encoding[Encoding.LATIN1] = "Latin-1"
        self.encoding[Encoding.UTF16] = "UTF-16"
        self.encoding[Encoding.UTF16BE] = "UTF-16BE"
        self.encoding[Encoding.UTF8] = "UTF-8"

        mainLayout = QFormLayout()

        self.artistLineEdit = QLineEdit()
        self.artistLineEdit.setReadOnly(True)

        self.titleLineEdit = QLineEdit()
        self.titleLineEdit.setReadOnly(True)

        self.lyricsSelection = QComboBox()
        self.lyricsSelection.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.lyricsSelection.setDisabled(True)

        self.lyricsEncoding = QLabel()
        self.lyricsEncoding.setDisabled(True)
        # XXX: Label is hidden as most users don't care about encodings
        self.lyricsEncoding.setVisible(False)

        self.lyricsDisplay = QPlainTextEdit()
        self.lyricsDisplay.setReadOnly(True)
        # expand lyrics display to the bottom
        policy = self.lyricsDisplay.sizePolicy()
        policy.setVerticalStretch(1)
        self.lyricsDisplay.setSizePolicy(policy)

        spacer = QSpacerItem(0, 0, QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)

        lyricsModifyToolbar = QToolBar()
        lyricsModifyToolbar.setFloatable(False)
        lyricsModifyToolbar.setMovable(False)

        addLyricsButtonIcon = QIcon.fromTheme("list-add")
        removeLyricsButtonIcon = QIcon.fromTheme("list-remove")
        editLyricsButtonIcon = QIcon.fromTheme("insert-text")
        searchLyricsButtonIcon = QIcon.fromTheme("system-search")
        saveTagButtonIcon = QIcon.fromTheme("document-save")
        reloadTagButtonIcon = QIcon.fromTheme("view-refresh")

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
        #: The state of the button (disabled/enabled) is used as indicator as well
        #: if the tag content has been modified compared to the saved tag version
        self.saveTagAction.setDisabled(True)
        self.tagModified.emit(False)
        self.reloadTagAction.setDisabled(True)

        selectionGrid = QGridLayout()
        selectionGrid.addWidget(self.lyricsSelection, 0, 0, Qt.AlignLeft)
        selectionGrid.addWidget(self.lyricsEncoding, 0, 1, Qt.AlignLeft)
        selectionGrid.addItem(spacer, 0, 2, Qt.AlignLeft)
        selectionGrid.addWidget(lyricsModifyToolbar, 0, 3, Qt.AlignRight)

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
        self.lyricsEncoding.setDisabled(True)
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
        """Delete lyrics from tag."""
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
        """Reload view by loading tag from file again."""
        # Ask user if modifications needs to be saved (indicated by saveTagAction)
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
        # read back any modifications in lyricsDisplay
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
            # FIXME: Workaround for missing or at least not working QMessageBox
            #   It seems that the translations are stored in the context of QPlatformTheme
            errorMessageDialog.button(QMessageBox.Ok). \
                setText(QCoreApplication.translate('QPlatformTheme', "Ok"))

            errorMessageDialog.exec()
        else:
            self.saveTagAction.setDisabled(True)
            self.tagModified.emit(False)

    def saveChangesDialog(self, buttons):
        """Dialog to ask user if changes should be save into file."""
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
        """Load tag, show tag values, and enable GUI elements."""
        # Ask user if modifications needs to be saved (indicated by saveTagAction)
        #   but only if new file is loaded
        if (self.saveTagAction.isEnabled() and filePath != self.tag.filePath):
            # No Cancel button is offered as a different file might be selected in tree view
            ret = self.saveChangesDialog(QMessageBox.Save | QMessageBox.Discard)
            if (ret == QMessageBox.Save):
                self.saveTagActionReceiver()
            self.saveTagAction.setDisabled(True)
            self.tagModified.emit(False)

        # Tag might be modified, so unload it first to make sure elements are up-to-date
        self.unloadAndHideTag()
        self.tag = ID3Tag(filePath)
        self.setDisabled(False)
        self.reloadTagAction.setDisabled(False)
        self.setArtistName()
        self.setTitleName()
        self.setLyrics()

    def unloadAndHideTag(self):
        """Unload Tag and disable GUI elements."""
        # Ask user if modifications needs to be saved (indicated by saveTagAction
        if (self.saveTagAction.isEnabled()):
            # No Cancel button is offered as a different file might be selected in tree view
            ret = self.saveChangesDialog(QMessageBox.Save | QMessageBox.Discard)
            if (ret == QMessageBox.Save):
                self.saveTagActionReceiver()
            self.saveTagAction.setDisabled(True)
            self.tagModified.emit(False)

        self.setDisabled(True)
        self.lyricsSelection.setDisabled(True)
        self.lyricsEncoding.setDisabled(True)
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
        """Load language/description keys and show one selected lyrics."""
        self.lyricsSelection.clear()
        self.lyricsDisplay.clear()

        self.addLyricsAction.setDisabled(not self.tag.writeable)
        self.searchLyricsAction.setDisabled(False)

        if self.tag.lyrics:
            self.editLyricsAction.setDisabled(not self.tag.writeable)
            self.removeLyricsAction.setDisabled(not self.tag.writeable)
            self.lyricsSelection.setDisabled(False)
            self.lyricsEncoding.setDisabled(False)
            for key, lyrics in self.tag.lyrics.items():
                self.lyricsSelection.addItem("/".join(key), userData=key)

            self.lyricsDisplay.setPlainText(self.tag.lyrics[self.lyricsSelection.currentData()][1])
            self.lyricsEncoding.setText(
                self.encoding[self.tag.lyrics[self.lyricsSelection.currentData()][0]])
        else:
            self.editLyricsAction.setDisabled(True)
            self.removeLyricsAction.setDisabled(True)
            self.lyricsSelection.setDisabled(True)
            self.lyricsEncoding.setDisabled(True)

    def showLyrics(self, index):
        """Show lyrics depending on selected language/description key."""
        key = self.lyricsSelection.itemData(index)
        if key in self.tag.lyrics:
            self.lyricsDisplay.setPlainText(self.tag.lyrics[key][1])
            self.lyricsEncoding.setText(self.encoding[self.tag.lyrics[key][0]])

    def unsetArtist(self):
        """Clear artist display."""
        self.artistLineEdit.clear()

    def unsetTitle(self):
        """Clear title display."""
        self.titleLineEdit.clear()

    def unsetLyrics(self):
        """Clear lyrics display."""
        self.lyricsSelection.clear()
        self.lyricsEncoding.clear()
        self.lyricsDisplay.clear()

    def unsetAll(self):
        """Clear every GUI elements holding tag values."""
        self.unsetArtist()
        self.unsetTitle()
        self.unsetLyrics()


class AddLyricsDialog(QDialog):
    """Dialog for editing lyrics to be stored in file."""

    class ASCIIValidator(QValidator):
        """Sub-class for validation of ASCII input."""
        #: `pyqtSignal` emitted when input contains ASCII only
        inputValid = pyqtSignal()
        #: `pyqtSignal` emitted when input does not contain ASCII only
        inputInvalid = pyqtSignal()

        def __init__(self, parent=None):
            super().__init__(parent)

        def validate(self, inp, pos):
            """Emitts `inputInvalid` or `inputInvalid` depending if input string contains
            ASCII only.

            :returns: `QValidator.Acceptable` if entered input string contains ASCII only.
                         Otherwise, `QValidator.Intermediate`.

            :param inp: input string for validation
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
        ## descriptionValidator emits inputValid or inputInvalid which is used to highlight
        ## invalid input (e.g. changing the okay button)
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

        # change description of language if a different language code is selected
        self.lngCodeComboBox.currentIndexChanged.connect(self.updateLngCodeLabel)

        # emit accept or reject depending which button was selected
        self.okButton.clicked.connect(self.accept)
        cancelButton.clicked.connect(self.reject)

    def updateLngCodeLabel(self):
        """Change description of language depending on selected language code."""
        self.lngCodeLabel.setText(ISO639_2_CODES[self.lngCodeComboBox.currentText()])

    def invalidDescription(self):
        """Notify user for invalid characters in description by changing the text and
        disabling the okButton.
        """
        okButtonIcon = QIcon.fromTheme("dialog-error")
        self.okButton.setDisabled(True)
        self.okButton.setFlat(True)
        self.okButton.setText(QCoreApplication.translate('AddLyricsDialog',
                              "Only ASCII characters are allowed for description."))
        self.okButton.setIcon(okButtonIcon)

    def validDescription(self):
        """Notify user for valid only characters in description by changing the text and
        enabling the okButton.
        """
        okButtonIcon = QIcon.fromTheme("dialog-error")
        okButtonIcon = QIcon.fromTheme("dialog-ok")
        self.okButton.setDisabled(False)
        self.okButton.setFlat(False)
        self.okButton.setText(QCoreApplication.translate('AddLyricsDialog', "Ok"))
        self.okButton.setIcon(okButtonIcon)


class ID3Tag():
    """Simple ID3 tag class holding the most important tag values. The values are accessible as
    object properties.

    :param filePath: filename and path to the mp3 file holding the tag

    Internally the class uses the following dict

    ID3Tag['artist']
        artist str of song (TPE1) [might be None]
    ID3Tag['title']
        title str of song (TIT2) [might be None]
    ID3Tag['USLT'][(language,description)]
        | the key is a tuple of language and description
        | value[0] = encoding
        | value[1] = lyrics
    ID3Tag['filePath']
        filename and path
    ID3Tag['writeable']
        if file can be written
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
        """Save self._tag['USLT'] to file"""
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
        """file-path of tag."""
        return self._filePath

    @property
    def artist(self):
        """artist string."""
        return self._tag['artist']

    @property
    def title(self):
        """title string."""
        return self._tag['title']

    @property
    def lyrics(self):
        """| lyrics dict
           |  key = (language, description)
           |  value[0] = encoding
           |  value[1] = lyrics
        """
        return self._tag['USLT']

    @property
    def writeable(self):
        """True if file is writeable, else False."""
        return self._writeable


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
        reloadButtonIcon = QIcon.fromTheme("view-refresh")
        reloadButton = QPushButton()
        reloadButton.setIcon(reloadButtonIcon)

        mainLayout = QGridLayout()
        mainLayout.addWidget(openBrowserButton, 0, 0)
        mainLayout.addWidget(self.addressLabel, 0, 1)
        mainLayout.addWidget(upButton, 0, 2)
        mainLayout.addWidget(reloadButton, 0, 3)
        mainLayout.addWidget(self.tree, 1, 0, 1, 4)
        self.setLayout(mainLayout)

        # clear color cache of TagFileSystemModel if directories are expanded/collapsed
        self.tree.expanded.connect(self.model.clearFileInfoCache)
        self.tree.collapsed.connect(self.model.clearFileInfoCache)
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

        # force as this is the initialization
        self.rootChanged(force=True)

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
            self.createFileSystemWatcher(self.rootPath)
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
    """

    class IconProvider(QFileIconProvider):
        """FIXME: The idea of this class is to provide different icons depending if all
        files, some files, or no files in a directory have lyrics embedded. However,
        its unclear how subdirectories should be handled.
        """
        def __init__(self):
            super().__init__()
            self.dirInfoCache = {}

        def icon(self, info):
            if type(info) == QFileInfo and info.isDir():
                # FIXME: custom icons could be returned here
                return super().icon(info)
            else:
                return super().icon(info)

    def __init__(self, parent=None):
        super().__init__(parent)
        #: cache for file informations to speed-up painting.
        #: QModelIndex is used is as key parameter
        self.fileInfoCache = {}
        self.setIconProvider(self.IconProvider())

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
        return (self.isMP3(filePath) and ID3(filePath).getall('USLT')) or False

    def clearFileInfoCache(self):
        """Clears self.fileInfoCache."""
        self.fileInfoCache = {}

if __name__ == '__main__':
    import sys

    mutagenVersion = int("".join(map(str, mutagenVersion[:2])))

    if mutagenVersion >= 125:
        app = QApplication(sys.argv)

        locale = QLocale.system()
        usltTranslator = QTranslator()
        if usltTranslator.load(locale, ":/uslt_manager", "_"):
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
