
from __future__ import absolute_import

import os
import mimetypes

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

    def thumbnail(self, source_filename_or_fp, dimensions=None, page=1, output_format='jpg'):
        pdf_fp = run(self._args(source_filename_or_fp))
        pdf_thumbnailer = thumbnailer_for('application/pdf')
        return pdf_thumbnailer.thumbnail(pdf_fp, dimensions=dimensions,
            page=page, output_format=output_format)


thumbnailers = {
    'image/x-portable-pixmap': PNMToImage,
    'application/pdf': Poppler,
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': Unoconv, # docx
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': Unoconv, # pptx
    'application/msword': Unoconv, # doc
    'application/vnd.ms-powerpoint': Unoconv, # ppt
}

def thumbnailer_for(mime_type):
    thumbnailer = thumbnailers.get(mime_type)
    if (thumbnailer is None) or (not thumbnailer().is_available()):
        return None
    return thumbnailer()

