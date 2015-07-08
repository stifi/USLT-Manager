# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Stefan Gansinger
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

"""Small QDialogs."""

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from mutagen.id3 import Encoding

from .lngcodes import *


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
        super().__init__(parent)
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
        okButtonIcon = QIcon.fromTheme("dialog-ok", QIcon(":/icons/dialog-ok.svg"))
        self.okButton = QPushButton(QCoreApplication.translate('AddLyricsDialog', "Ok"))
        self.okButton.setIcon(okButtonIcon)
        cancelButtonIcon = QIcon.fromTheme("dialog-close", QIcon(":/icons/dialog-close.svg"))
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
        okButtonIcon = QIcon.fromTheme("dialog-error", QIcon(":/icons/dialog-error.svg"))
        self.okButton.setDisabled(True)
        self.okButton.setFlat(True)
        self.okButton.setText(QCoreApplication.translate('AddLyricsDialog',
                              "Only ASCII characters are allowed for description."))
        self.okButton.setIcon(okButtonIcon)

    def validDescription(self):
        """Notify user for valid only characters in description by changing the text and
        enabling the okButton.
        """
        okButtonIcon = QIcon.fromTheme("dialog-error", QIcon(":/icons/dialog-error.svg"))
        okButtonIcon = QIcon.fromTheme("dialog-ok", QIcon(":/icons/dialog-ok.svg"))
        self.okButton.setDisabled(False)
        self.okButton.setFlat(False)
        self.okButton.setText(QCoreApplication.translate('AddLyricsDialog', "Ok"))
        self.okButton.setIcon(okButtonIcon)


class SaveChangesDialog(QMessageBox):
    """Dialog to ask user if changes should be save into file.

    :param buttons: Which standard buttons should be available
    :return: value of pressed button
    """
    def __init__(self, buttons, parent=None):
        super().__init__(parent)
        self.setText(QCoreApplication.translate('TagWidget', "Lyrics have been modified."))
        self.setInformativeText(QCoreApplication.translate(
            'TagWidget', "Do you want to save your changes?"))
        self.setStandardButtons(buttons)
        self.setDefaultButton(QMessageBox.Save)

        # FIXME: Workaround for missing or at least not working translations QMessageBox
        #   buttons. It seems that the translations are stored in the context of QPlatformTheme
        if self.button(QMessageBox.Discard) is not None:
            self.button(QMessageBox.Discard). \
                setText(QCoreApplication.translate('QPlatformTheme', "Discard"))
        if self.button(QMessageBox.Cancel) is not None:
            self.button(QMessageBox.Cancel). \
                setText(QCoreApplication.translate('QPlatformTheme', "Cancel"))
        if self.button(QMessageBox.Save) is not None:
            self.button(QMessageBox.Save). \
                setText(QCoreApplication.translate('QPlatformTheme', "Save"))
