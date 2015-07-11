# USLT Manager

>***Management for lyrics stored in the USLT frame of the ID3v2 tag of mp3 files.***

**Requirements:**
* Python 3
* Python Mutagen (>= 1.25): https://mutagen.readthedocs.org
* PyQt5: https://pypi.python.org/pypi/PyQt5

### Description
The ID3 tag used to store some informations on a song directly into mp3 file supports saving the lyrics as well. Various mp3 playing programs support showing the embedded lyrics or even provide an interface to add or modify the lyrics.

This programs focuses on the management of these lyrics. Files or even directories are checked for embedded lyrics. Lyrics can be added, modified, or deleted. The program supports editing multiple lyrics in one file as defined by the [ID3v2.4 standard](http://id3.org/id3v2.4.0-frames).

Be aware that files are directly modified. As this program is in an early development phase, make a backup before saving your modifications.^
