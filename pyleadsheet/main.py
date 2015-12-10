"""
pyleadsheet -- convert a chordpro-like file into a pretty pdf leadsheet

Usage:
    pyleadsheet generate <inputfile> [options]
    pyleadsheet generate <inputdir> [options]
    pyleadsheet runserver <inputdir> [--debug]
    pyleadsheet help

Options:
    -h, --help                  print this help screen
    --output=DIR                directory to place html files in
                                (default: output)
    --no-index                  don't (re)generate an index
    --pdf                       convert html files to pdf after initial
                                rendering
    --transpose-half-steps=INT  transpose song +/- INT half steps
    --transpose-to-root=ROOT    transpose song to be rooted at ROOT
    --clean                     start from a fresh output diretory
    --debug                     use verbose logging
"""

import os
import sys
import docopt
import shutil
from . import server
from . import renderer
import logging
logger = logging.getLogger(__name__)


def runserver(args):
    if not os.path.isdir(args['<inputdir>']):
        logger.error('tried to start server with invalid input dir: ' + args['<inputdir>'])
        return 1
    return server.run(args['<inputdir>'], debug=args['--debug'])


def generate(args):

    inputfiles = []
    if os.path.isfile(args['<inputfile>']):
        inputfiles.append(args['<inputfile>'])
    elif os.path.isdir(args['<inputfile>']):
        for filename in os.listdir(args['<inputfile>']):
            if filename.lower().endswith('.yaml') or filename.lower().endswith('.yml'):
                inputfiles.append(os.path.join(args['<inputfile>'], filename))

    if not inputfiles:
        raise IOError('could not find input: ' + args['<inputfile>'])

    outputdir = args['--output'] or 'output'
    if args['--clean'] and os.path.isdir(outputdir):
        shutil.rmtree(outputdir)

    html_renderer = renderer.HTMLRenderer(outputdir)
    for yamlfile in inputfiles:
        html_renderer.render_song(
            yamlfile,
            transpose_half_steps=args['--transpose-half-steps'],
            transpose_to_root=args['--transpose-to-root']
        )
    if not args['--no-index']:
        html_renderer.render_index

    if args['--pdf']:
        pdf_converter = renderer.HTMLToPDFConverter(outputdir)
        pdf_converter.convert_songs()

    return 0


def main():
    args = docopt.docopt(__doc__)
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.DEBUG if args['--debug'] else logging.INFO
    )

    if args['help']:
        print(__doc__)
        return 0

    elif args['runserver']:
        return runserver(args)

    elif args['generate']:
        return generate(args)
