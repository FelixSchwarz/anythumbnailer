
from __future__ import absolute_import

import mimetypes

from .sh_utils import pipe_with_input, run

__all__ = ['create_thumbnail']

def create_thumbnail(source_filename, dimensions=None, **kwargs):
    assert dimensions is None
    mime_type, encoding = mimetypes.guess_type(source_filename, strict=False)
    thumbnailer = thumbnailers.get(mime_type)
    if thumbnailers[mime_type] is None:
        return None
    return thumbnailer(source_filename, dimensions, **kwargs)

def poppler_thumbnail(source_filename_or_fp, dimensions=None, page=1, output_format='jpg'):
    assert dimensions is None
    
    pdftoppm_args = (
        '/usr/bin/pdftoppm',
            '-scale-to', str(2048),
            '-f', str(page),
            '-l', str(page))
    pnm_converter = pnm_converters[output_format]
    pnm_converter_args = (pnm_converter, )
    thumbnail = pipe_with_input(source_filename_or_fp, pdftoppm_args, pnm_converter_args)
    return thumbnail

def unoconv_thumbnail(source_filename, dimensions=None, output_format='jpg'):
    assert dimensions is None
    args = (
        '/usr/bin/unoconv',
        '-f', 'pdf',
        '--stdout',
        source_filename
    )
    pdf_fp = run(args)
    pdf_thumbnailer = thumbnailers['application/pdf']
    return pdf_thumbnailer(pdf_fp, dimensions=dimensions, output_format=output_format)

pnm_converters = {
    'jpg': '/usr/bin/pnmtojpeg',
    'png': '/usr/bin/pnmtopng',
}

thumbnailers = {
    'application/pdf': poppler_thumbnail,
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': unoconv_thumbnail, # docx
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': unoconv_thumbnail, # pptx
    'application/msword': unoconv_thumbnail, # doc
    'application/vnd.ms-powerpoint': unoconv_thumbnail, # ppt
}
