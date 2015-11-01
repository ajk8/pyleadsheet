"""
pyleadsheet -- convert a chordpro-like file into a pretty pdf leadsheet

Usage:
    pyleadsheet generate <inputfile> [options]
    pyleadsheet generate <inputdir> [options]
    pyleadsheet help

Options:
    -h             print this help screen
    --output=DIR   directory to place html files in (default: output)
    --pdf          convert html files to pdf after initial rendering
    --clean        start from a fresh output diretory
    --debug        use verbose logging
"""

import os
import sys
import docopt
import shutil
from .parser import parse_file
from .renderer import HTMLRenderer, HTMLToPDFConverter
import logging


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

    renderer = HTMLRenderer(outputdir)
    for yamlfile in inputfiles:
        song_data = parse_file(yamlfile)
        renderer.load_song(song_data)
    renderer.render_book()

    if args['--pdf']:
        converter = HTMLToPDFConverter(outputdir)
        converter.convert_songs()

    return 0


def main():
    args = docopt.docopt(__doc__)
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG if args['--debug'] else logging.INFO)

    if args['help']:
        print(__doc__)
        return 0

    elif args['generate']:
        return generate(args)
