anythumbnailer
=======================

A CLI utility/Python library to create thumbnails for different file types
(including PDF, mp4 videos and Microsoft Office documents aka docx/xlsx/pptx).

All the heavy-lifting is done by commonly-used tools such as LibreOffice/unoconv,
ffmpeg, poppler and ImageMagick so format support is limited by what these tools
can process.

I built the library as I could not find a project which satisfied my needs
(as detailed in my question on StackOverflow [1]). However as I wrote something
from scratch the project has quite a few limitations:
- I'm using it only on Linux (Fedora, CentOS 6+7 to be exact). Paths to other
  programs are hard-coded.
- I never tried running this on any other system such as Windows or OS X.

Very likely you will have to tweak the code in case this project is useful for
anyone but me. That being said I'm interested in making the configuration less
hard-coded (e.g. by introducing a config file with sensible syntax) and
automated tests.


Installation / Usage
-----------------------

 $ python setup.py develop
 $ anythumbnail SOURCEFILE [OUTPUTFILE]


[1] http://stackoverflow.com/questions/21511974/is-there-a-python-library-to-create-thumbnails-for-various-document-file-formats
