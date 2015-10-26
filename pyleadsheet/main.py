"""
pyleadsheet -- convert a chordpro-like file into a pretty pdf leadsheet

Usage:
    pyleadsheet generate <inputfile> [options]
    pyleadsheet generate <inputdir> [options]
    pyleadsheet help

Options:
    -h             print this help screen
    --output=DIR   directory to place html files in (default: output)
    --format=EXT   right now only html is supported, pdf in the future (default: html)
    --clean        start from a fresh output diretory (default: False)
    --all          include all of the following 3 types of output (default: True)
    --combined     include leadsheet and lyrics inline on each page (default: False)
    --no-lyrics    exclude lyrics from all pages (default: False)
    --lyrics-only  limit output to lyrics onlye (default: False)
"""

import os
import sys
import docopt
import shutil
from .parser import parse_file
from .renderer import HTMLRenderer, HTMLToPDFConverter
import logging
logging.basicConfig(stream=sys.stderr, level=logging.INFO)


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

    # set modes
    combined = no_lyrics = lyrics_only = True
    if args['--all']:
        combined = no_lyrics = lyrics_only = True
    elif args['--combined']:
        combined = True
    elif args['--no-lyrics']:
        no_lyrics = True
    elif args['--lyrics-only']:
        lyrics_only = True

    renderer = HTMLRenderer(
        outputdir,
        combined=combined,
        no_lyrics=no_lyrics,
        lyrics_only=lyrics_only
    )
    for yamlfile in inputfiles:
        song_data = parse_file(yamlfile)
        renderer.load_song(song_data)
    renderer.render_book()

    if args['--format'] and args['--format'].lower() == 'pdf':
        converter = HTMLToPDFConverter(outputdir)
        converter.convert_songs()

    return 0


def main():
    args = docopt.docopt(__doc__)

    if args['help']:
        print(__doc__)
        return 0

    elif args['generate']:
        return generate(args)
