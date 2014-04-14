
from __future__ import absolute_import

from io import BytesIO
import os
import mimetypes
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


class Poppler(Thumbnailer):
    pdf_to_ppm = '/usr/bin/pdftoppm'
    executables = (pdf_to_ppm, ) + PNMToImage.executables

    def _args(self, dimensions=None, page=1):
        assert dimensions is None
        return (
            self.pdf_to_ppm,
                '-scale-to', str(2048),
                '-f', str(page),
                '-l', str(page)
        )

    def thumbnail(self, source_filename_or_fp, dimensions=None, page=1, output_format='jpg'):
        assert dimensions is None
        pdftoppm_args = self._args(dimensions=dimensions, page=page)
        pnm_converter_args = PNMToImage().pipe_args(dimensions=dimensions, output_format=output_format)
        thumbnail = pipe_with_input(source_filename_or_fp, pdftoppm_args, pnm_converter_args)
        return thumbnail


class Unoconv(Thumbnailer):
    executable = '/usr/bin/unoconv'

    def _args(self, source_filename):
        return (
            self.executable,
            '-f', 'pdf',
            '--stdout',
            source_filename
        )

    def thumbnail(self, source_filename, dimensions=None, page=1, output_format='jpg'):
        pdf_fp = run(self._args(source_filename))
        pdf_thumbnailer = thumbnailer_for('application/pdf')
        return pdf_thumbnailer.thumbnail(pdf_fp, dimensions=dimensions,
            page=page, output_format=output_format)


class MultifileOutputThumbnailer(Thumbnailer):
    output_pattern = None

    def _args(self, source_filename, output_filename):
        raise NotImplementedError()

    def _find_output_filename(self, temp_dir):
        # As a rough heuristic we'll pick the biggest one which probably
        # contains the most interesting data.
        pathname = lambda filename: os.path.join(temp_dir, filename)
        file_paths = map(pathname, os.listdir(temp_dir))
        if len(file_paths) == 0:
            return None
        files_with_size = [(os.stat(path).st_size, path) for path in file_paths]
        return sorted(files_with_size)[-1][1]

    def thumbnail(self, source_filename, dimensions=None, output_format='jpg'):
        try:
            temp_dir = tempfile.mkdtemp()
            temp_file = os.path.join(temp_dir, self.output_pattern+output_format)
            run(self._args(source_filename, temp_file))
            output_filename = self._find_output_filename(temp_dir)
            if output_filename is None:
                return None
            return BytesIO(file(output_filename, 'rb').read())
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class ImageMagick(MultifileOutputThumbnailer):
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


class ffmpeg(MultifileOutputThumbnailer):
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
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': Unoconv, # docx
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': Unoconv, # pptx
    'application/msword': Unoconv, # doc
    'application/vnd.ms-powerpoint': Unoconv, # ppt

    # xls(x/m)
    'application/vnd.ms-excel': Unoconv,
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': Unoconv,
    'application/vnd.ms-excel.sheet.macroEnabled.12': Unoconv, # with macros

    'image/vnd.adobe.photoshop': ImageMagick,
    'image/tiff': ImageMagick,

    # videos
    'video/mp4': ffmpeg, # mp4, m4v
    'video/webm': ffmpeg,
    'video/x-ms-wmv': ffmpeg, # wmv
}

def thumbnailer_for(mime_type):
    thumbnailer = thumbnailers.get(mime_type)
    if (thumbnailer is None) or (not thumbnailer().is_available()):
        return None
    return thumbnailer()

