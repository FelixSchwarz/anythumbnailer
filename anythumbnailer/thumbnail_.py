
from __future__ import absolute_import

from io import BytesIO
import mimetypes
import os
import re
import shutil
import tempfile

from .sh_utils import pipe_with_input, run

__all__ = ['create_thumbnail']


def create_thumbnail(source_filename, dimensions=None, **kwargs):
    assert dimensions is None
    mime_type, encoding = mimetypes.guess_type(source_filename, strict=False)
    thumbnailer = thumbnailer_for(mime_type)
    if thumbnailer is None:
        return None
    return thumbnailer.thumbnail(source_filename, dimensions, **kwargs)


class Thumbnailer(object):
    def is_available(self):
        if hasattr(self, 'executables'):
            executables = self.executables
        else:
            executables = (self.executable, )
        for command_path in executables:
            command = command_path.split(' ', 1)[0]
            if not os.path.exists(command):
                return False
        return True

    def thumbnail(self, source_filename_or_fp, **kwargs):
        raise NotImplementedError()


class PNMToImage(Thumbnailer):
    pnm_to_png = '/usr/bin/pnmtopng'
    pnm_to_jpg = '/usr/bin/pnmtojpeg'
    executables = (pnm_to_png, pnm_to_jpg)

    def pipe_args(self, dimensions=None, output_format='jpg'):
        assert dimensions is None
        executable = self.pnm_to_jpg if (output_format == 'jpg') else self.pnm_to_png
        return (
            executable,
        )

    def thumbnail(self, source_filename_or_fp, **kwargs):
        return run(self.pipe_args(**kwargs), input_=source_filename_or_fp)


# pdftoppm 0.12.4 (CentOS 6.5) bails out if the PDF contents are transferred
# via stdin. pdftoppm 0.24.3 (Fedora 20) works fine though...
class Poppler(Thumbnailer):
    pdf_to_ppm = '/usr/bin/pdftoppm'
    executables = (pdf_to_ppm, ) + PNMToImage.executables

    def _args(self, source_filename=None, dimensions=None, page=1):
        assert dimensions is None
        command = (
            self.pdf_to_ppm,
                '-scale-to', str(2048),
                '-f', str(page),
                '-l', str(page),
        )
        if source_filename is not None:
            command += (source_filename, )
        return command


    def thumbnail(self, source_filename_or_fp, dimensions=None, page=1, output_format='jpg'):
        assert dimensions is None
        temp_fp = None
        try:
            if not hasattr(source_filename_or_fp, 'read'):
                filename = source_filename_or_fp
            else:
                temp_fp = tempfile.NamedTemporaryFile(delete=True)
                temp_fp.write(source_filename_or_fp.read())
                temp_fp.flush()
                filename = temp_fp.name
            pdftoppm_args = self._args(source_filename=filename, dimensions=dimensions, page=page)
            pnm_fp = run(pdftoppm_args)
            pnm_converter_args = PNMToImage().pipe_args(dimensions=dimensions, output_format=output_format)
            return run(pnm_converter_args, input_=pnm_fp)
        finally:
            if temp_fp is not None:
                temp_fp.close()


class FileOutputThumbnailer(Thumbnailer):
    output_pattern = None

    def _args(self, source_filename, output_filename):
        raise NotImplementedError()

    def _find_output_filename(self, temp_dir, output_format):
        # As a rough heuristic we'll pick the biggest one which probably
        # contains the most interesting data.
        file_paths = []
        for filename in os.listdir(temp_dir):
            if filename.endswith('.'+output_format):
                file_paths.append(os.path.join(temp_dir, filename))
        if len(file_paths) == 0:
            return None
        files_with_size = [(os.stat(path).st_size, path) for path in file_paths]
        return sorted(files_with_size)[-1][1]

    def thumbnail(self, source_filename, dimensions=None, output_format='jpg'):
        try:
            temp_dir = tempfile.mkdtemp()
            temp_file = os.path.join(temp_dir, self.output_pattern+output_format)
            run(self._args(source_filename, temp_file))
            output_filename = self._find_output_filename(temp_dir, output_format)
            if output_filename is None:
                return None
            return BytesIO(file(output_filename, 'rb').read())
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class Unoconv(FileOutputThumbnailer):
    executable = '/usr/bin/unoconv'
    output_pattern = 'document.'

    def _args(self, source_filename, output_filename):
        return (
            self.executable,
            '-f', 'pdf',
            # it seems that LibreOffice 4.0/4.1 has a bug somewhere in pyuno
            # (or the LibreOffice core itself) when it should output to stdout:
            # https://github.com/dagwieers/unoconv/issues/66
            # http://thread.gmane.org/gmane.linux.debian.devel.bugs.general/1074109/focus=1074227
            # falling back to a temporary file which (strangely) works.
            # "--stdout" works fine in LibreOffice 4.2
            # '--stdout',
            '--output='+output_filename,
            source_filename,
        )

    def thumbnail(self, source_filename, dimensions=None, page=1, output_format='jpg'):
        pdf_fp = super(Unoconv, self).thumbnail(source_filename, dimensions=dimensions,
            output_format='pdf')
        pdf_thumbnailer = thumbnailer_for('application/pdf')
        return pdf_thumbnailer.thumbnail(pdf_fp, dimensions=dimensions,
            page=page, output_format=output_format)


class ImageMagick(FileOutputThumbnailer):
    # some image formats might contain multiple pages and/or layers and
    # ImageMagick will create multiple output files in that case.
    executable = '/usr/bin/convert'
    output_pattern = 'output.'

    def _args(self, source_filename, output_filename):
        return (
            self.executable,
            source_filename,
            output_filename,
        )


class ffmpeg(FileOutputThumbnailer):
    executable = '/usr/bin/ffmpeg'
    output_pattern = 'output%02d.'

    def _args(self, source_filename, output_filename):
        return (
            self.executable,
            '-ss', '3',
            '-i', source_filename,
            '-frames:v', '5',
            '-r', '1/10',
            '-vsync', 'vfr',
            output_filename,
        )


thumbnailers = {
    'image/x-portable-pixmap': PNMToImage,
    'application/pdf': Poppler,
    'application/msword': Unoconv, # doc
    re.compile('^'+re.escape('application/vnd.ms-')): Unoconv, # xls/ppt
    re.compile('^'+re.escape('application/vnd.openxmlformats-officedocument.')): Unoconv, # docx, pptx, xlsx
    'application/vnd.ms-excel.sheet.macroEnabled.12': Unoconv, # xlsm: xlsx with macros

    'image/vnd.adobe.photoshop': ImageMagick,
    'image/tiff': ImageMagick,

    re.compile('^video/'): ffmpeg, # videos
}

def thumbnailer_for(mime_type):
    thumbnailer = thumbnailers.get(mime_type)
    if thumbnailer is None:
        regex_thumbnailers = filter(lambda key: not isinstance(key, basestring), thumbnailers)
        for regex in regex_thumbnailers:
            if regex.match(mime_type):
                thumbnailer = thumbnailers[regex]
                break
        else:
            return None
    if not thumbnailer().is_available():
        return None
    return thumbnailer()

