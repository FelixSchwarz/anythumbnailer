
from __future__ import absolute_import

import sys

from .thumbnail_ import create_thumbnail


__all__ = ['main']

def main():
    source_filename = sys.argv[1]
    output_filename = sys.argv[2] if len(sys.argv) >=3 else None
    thumbnail_fp = create_thumbnail(source_filename, output_format='jpg')
    if thumbnail_fp is None:
        sys.stderr.write('No suitable thumbnailer found.\n')
        sys.exit(10)
    if output_filename:
        file(output_filename, 'wb').write(thumbnail_fp.read())
    else:
        sys.stdout.write(thumbnail_fp.read())

