# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Stefan Gansinger
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

"""ID3v2 reading and writing."""

import os

from mutagen.id3 import ID3 as MutagenID3
from mutagen.id3 import USLT


class ID3(MutagenID3):
    """Extensions for the ID3 class from Mutagen."""

    @property
    def hasLyrics(self):
        """:returns: if tag has embedded lyrics"""
        for key in self.keys():
            if key.startswith('USLT:'):
                return True
        return False


class ID3Tag():
    """Simple ID3 tag class holding the most important tag values. The values are accessible as
    object properties. To save changes :func:`self.save()` is provided.

    :param filePath: filename and path to the mp3 file

    | :data:`filePath` filename and path to the mp3 file
    | :data:`artist` artist
    | :data:`title` title
    | :data:`lyrics` lyrics w/ encoding
    | :data:`writable` if tag can be written
    """
    def __init__(self, filePath):
        self._filePath = filePath
        self._writable = os.access(self._filePath, os.W_OK)
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

        # Handle is closed. File updates must be monitored elsewhere
        del id3tag

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
    def writable(self):
        """True if file is writable, else False."""
        return self._writable
