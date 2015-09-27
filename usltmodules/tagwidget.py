# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Stefan Gansinger
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

"""Widget showing the most important ID3 tag values. Most importantly the lyrics."""

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from mutagen.id3 import Encoding

from .tagoperations import ID3Tag
from .dialogs import AddLyricsDialog, SaveChangesDialog, addShortcutToToolTip


class TagWidget(QWidget):
    """Widget showing the most important ID3 tag values. Most importantly the lyrics.

    By default all GUI elements are disabled. They are enabled when a mp3 file is loaded
    using :func:`loadAndShowTag()`.

    The `pyqtSignal` :data:`tagModified` is used to notify for changes
    """

    #: emitted with the parameter True when tag has been modified
    #: emitted with the parameter False when view elements match the tag content
    #: i.e. when tag has been saved or tag is reloaded
    tagModified = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        #: encodings available for USLT and defined in mutagen
        self.encoding = {}
        self.encoding[Encoding.LATIN1] = "Latin-1"
        self.encoding[Encoding.UTF16] = "UTF-16"
        self.encoding[Encoding.UTF16BE] = "UTF-16BE"
        self.encoding[Encoding.UTF8] = "UTF-8"

        mainLayout = QFormLayout()

        # artist
        self.artistLineEdit = QLineEdit()
        self.artistLineEdit.setReadOnly(True)

        # title
        self.titleLineEdit = QLineEdit()
        self.titleLineEdit.setReadOnly(True)

        # lyrics selection (language and description)
        self.lyricsSelection = QComboBox()
        self.lyricsSelection.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.lyricsSelection.setDisabled(True)

        # encoding
        self.lyricsEncoding = QLabel()
        self.lyricsEncoding.setDisabled(True)
        # XXX: Label is hidden as most users don't care about encodings
        self.lyricsEncoding.setVisible(False)

        # lyrics
        self.lyricsDisplay = QPlainTextEdit()
        self.lyricsDisplay.setReadOnly(True)
        # expand lyrics display to the bottom
        policy = self.lyricsDisplay.sizePolicy()
        policy.setVerticalStretch(1)
        self.lyricsDisplay.setSizePolicy(policy)

        # spacer between id3 elements and toolbar
        spacer = QSpacerItem(0, 0, QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)

        # toolbar
        lyricsModifyToolbar = QToolBar()
        lyricsModifyToolbar.setFloatable(False)
        lyricsModifyToolbar.setMovable(False)

        addLyricsButtonIcon = QIcon.fromTheme("list-add",
                                              QIcon(":/icons/list-add.svg"))
        removeLyricsButtonIcon = QIcon.fromTheme("list-remove",
                                                 QIcon(":/icons/list-remove.svg"))
        editLyricsButtonIcon = QIcon.fromTheme("insert-text",
                                               QIcon(":/icons/insert-text.svg"))
        searchLyricsButtonIcon = QIcon.fromTheme("system-search",
                                                 QIcon(":/icons/system-search.svg"))
        saveTagButtonIcon = QIcon.fromTheme("document-save",
                                            QIcon(":/icons/document-save.svg"))
        reloadTagButtonIcon = QIcon.fromTheme("view-refresh",
                                              QIcon(":/icons/view-refresh.svg"))

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

        # shortcuts for toolbar
        self.editLyricsAction.setShortcut(QKeySequence(Qt.CTRL + Qt.Key_E))
        self.addLyricsAction.setShortcut(QKeySequence(Qt.CTRL + Qt.Key_Plus))
        self.removeLyricsAction.setShortcut(QKeySequence(Qt.CTRL + Qt.Key_D))
        # self.searchLyricsAction.setShortcut(None)
        self.saveTagAction.setShortcut(QKeySequence(Qt.CTRL + Qt.Key_S))
        self.reloadTagAction.setShortcut(QKeySequence(Qt.CTRL + Qt.Key_R))

        addShortcutToToolTip(self.editLyricsAction)
        addShortcutToToolTip(self.addLyricsAction)
        addShortcutToToolTip(self.removeLyricsAction)
        addShortcutToToolTip(self.searchLyricsAction)
        addShortcutToToolTip(self.saveTagAction)
        addShortcutToToolTip(self.reloadTagAction)

        # separator for save button
        lyricsModifyToolbar.insertSeparator(self.saveTagAction)

        # disable all buttons
        self.editLyricsAction.setDisabled(True)
        self.addLyricsAction.setDisabled(True)
        self.removeLyricsAction.setDisabled(True)
        self.searchLyricsAction.setDisabled(True)
        #: The state of the button (disabled/enabled) is used as indicator as well
        #: if the tag content has been modified compared to the saved tag version
        self.saveTagAction.setDisabled(True)
        self.reloadTagAction.setDisabled(True)

        # layouts
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

        # disable everything
        self.setDisabled(True)

        # update lyrics if a different selection (language/description) is made
        self.lyricsSelection.currentIndexChanged.connect(self.showLyrics)

        # notify for matching elements with tag content
        self.tagModified.emit(False)

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
        # tag and GUI elements do not match anymore
        self.tagModified.emit(True)

    def addLyricsActionReceiver(self):
        """Initiate the AddLyricsDialog."""
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
            # tag and GUI elements do not match anymore
            self.tagModified.emit(True)

    def removeLyricsActionReceiver(self):
        """Delete current shown lyrics from tag."""
        del self.tag.lyrics[self.lyricsSelection.currentData()]
        # update lyrics in view
        self.setLyrics()
        self.saveTagAction.setDisabled(False)
        # tag and GUI elements do not match anymore
        self.tagModified.emit(True)

    def searchLyricsActionReceiver(self):
        """Search for lyrics in external browser."""
        queryUrl = QUrlQuery()

        def toStr(s): return (s or "")

        queryUrl.addQueryItem("as_q",
                              '"lyrics"+"' + toStr(self.tag.artist) +
                              '"+"' + toStr(self.tag.title) + '"')
        finalUrl = QUrl("https://www.google.com/search")
        finalUrl.setQuery(queryUrl)

        QDesktopServices.openUrl(finalUrl)

    def reloadTagActionReceiver(self):
        """Reload view by loading tag from file again."""
        # ask user if modifications needs to be saved (indicated by saveTagAction)
        #   but only if new file is loaded
        if (self.saveTagAction.isEnabled()):
            # No Cancel button is offered as a different file might be selected in tree view already
            ret = SaveChangesDialog(QMessageBox.Save | QMessageBox.Discard).exec()
            if (ret == QMessageBox.Save):
                self.saveTagActionReceiver()
            self.saveTagAction.setDisabled(True)
            # tag and GUI elements match
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
            # FIXME: Workaround for missing or at least not working translations QMessageBox
            #   buttons. It seems that the translations are stored in the context of QPlatformTheme
            errorMessageDialog.button(QMessageBox.Ok). \
                setText(QCoreApplication.translate('QPlatformTheme', "Ok"))
            errorMessageDialog.exec()
        else:
            self.saveTagAction.setDisabled(True)
            # tag and GUI elements match
            self.tagModified.emit(False)

    def loadAndShowTag(self, filePath):
        """Load tag, show tag values, and enable GUI elements."""
        # ask user if modifications needs to be saved (indicated by saveTagAction)
        #   but only if new file is loaded
        if (self.saveTagAction.isEnabled() and filePath != self.tag.filePath):
            # no Cancel button is offered as a different file might be selected in tree view already
            ret = SaveChangesDialog(QMessageBox.Save | QMessageBox.Discard).exec()
            if (ret == QMessageBox.Save):
                self.saveTagActionReceiver()
            self.saveTagAction.setDisabled(True)

        # Tag might be modified, so unload it first to make sure elements are up-to-date
        self.unloadAndHideTag()
        self.tag = ID3Tag(filePath)
        self.setDisabled(False)
        self.reloadTagAction.setDisabled(False)
        self.setArtistName()
        self.setTitleName()
        self.setLyrics()
        # tag and GUI elements match
        self.tagModified.emit(False)

    def unloadAndHideTag(self):
        """Unload Tag and disable GUI elements."""
        # ask user if modifications needs to be saved (indicated by saveTagAction)
        if (self.saveTagAction.isEnabled()):
            # no Cancel button is offered as a different file might be selected in tree view already
            ret = SaveChangesDialog(QMessageBox.Save | QMessageBox.Discard).exec()
            if (ret == QMessageBox.Save):
                self.saveTagActionReceiver()
            self.saveTagAction.setDisabled(True)

        self.setDisabled(True)
        self.lyricsSelection.setDisabled(True)
        self.lyricsEncoding.setDisabled(True)
        self.editLyricsAction.setDisabled(True)
        self.addLyricsAction.setDisabled(True)
        self.removeLyricsAction.setDisabled(True)
        self.searchLyricsAction.setDisabled(True)
        self.saveTagAction.setDisabled(True)
        # tag and GUI elements match
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
        """Load language/description keys and show selected lyrics."""
        self.lyricsSelection.clear()
        self.lyricsDisplay.clear()
        self.addLyricsAction.setDisabled(not self.tag.writable)
        self.searchLyricsAction.setDisabled(False)

        if self.tag.lyrics:
            self.editLyricsAction.setDisabled(not self.tag.writable)
            self.removeLyricsAction.setDisabled(not self.tag.writable)
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
        """Clear each GUI elements holding tag values."""
        self.unsetArtist()
        self.unsetTitle()
        self.unsetLyrics()
