import os
import shutil
import jinja2
import filecmp
import datetime
import json
from wkhtmltopdfwrapper import wkhtmltopdf
from . import views
from . import parser

import logging
logger = logging.getLogger(__name__)


def _spoof_url_for(path, filename=None):
    return filename


class HTMLRenderer(object):

    SONG_TEMPLATE = 'song.jinja2'
    INDEX_TEMPLATE = 'index.jinja2'
    OUTPUT_SUBDIR = 'html'

    def __init__(self, outputdir):
        logger.debug('initializing HTMLRenderer with outputdir: ' + outputdir)
        self.filepaths = []
        self.outputdir = os.path.join(outputdir, self.OUTPUT_SUBDIR)
        self.timestamp = datetime.datetime.now()

    def _prepare_output_directory(self):
        if not os.path.exists(self.outputdir):
            logger.debug('creating outputdir')
            os.makedirs(self.outputdir)
        fromdir = os.path.join(os.path.dirname(__file__), 'static')
        logged = False
        for filename in os.listdir(fromdir):
            if not filename.endswith('jinja2'):
                fromfile = os.path.join(fromdir, filename)
                tofile = os.path.join(self.outputdir, filename)
                if not os.path.exists(tofile) or not filecmp.cmp(fromfile, tofile):
                    if not logged:
                        logger.info('copying base files into outputdir')
                        logged = True
                    shutil.copy(fromfile, tofile)

    def _get_output_filename(self, song_title, suffix=None):
        ret = song_title.lower().replace(' ', '_')
        ret += '_' + suffix if suffix else ''
        return ret + '.html'

    def _render_template_to_file(self, template, outputfilename, template_data):
        self._prepare_output_directory()
        j2env = jinja2.Environment(loader=jinja2.PackageLoader('pyleadsheet', 'templates'))
        output = open(os.path.join(self.outputdir, outputfilename), 'w')
        output.write(j2env.get_template(template).render(**template_data))

    def _add_url_for_spoof(self, view_kwargs):
        view_kwargs.update({'url_for': _spoof_url_for})
        return view_kwargs

    def render_song(self, filepath, transpose_half_steps=None, transpose_to_root=None):
        self.filepaths.append(filepath)
        song_title = parser.get_title_from_song_file(filepath)
        logger.info('rendering song: ' + song_title)
        for song_view_type in views.SONG_VIEW_TYPES:
            view_kwargs = views.compose_song_kwargs(
                filepath,
                song_view_type,
                transpose_half_steps,
                transpose_to_root
            )
            view_kwargs.update({'url_for': _spoof_url_for})
            self._render_template_to_file(
                self.SONG_TEMPLATE,
                self._get_output_filename(song_title, song_view_type),
                self._add_url_for_spoof(view_kwargs)
            )

    def render_index(self):
        logger.info('rendering index')
        view_kwargs = views.compose_index_kwargs(self.filepaths)
        self._render_template_to_file(
            self.INDEX_TEMPLATE,
            'index.html',
            self._add_url_for_spoof(view_kwargs)
        )
        json.dump(
            view_kwargs['songs_by_first_letter'],
            open(os.path.join(self.outputdir, self.INDEX_JSON_FILE), 'w')
        )

    def render_book(self, no_index=False):
        logger.info('rendering HTML book')
        for filepath in self.filepaths:
            self.render_song(filepath)
        if not no_index:
            self.render_index()


class HTMLToPDFConverter(object):

    OUTPUT_SUBDIR = 'pdf'

    def __init__(self, outputdir, html_renderer=None):
        self.html_renderer = html_renderer
        self.inputdir = os.path.join(outputdir, HTMLRenderer.OUTPUT_SUBDIR)
        self.outputdir = os.path.join(outputdir, self.OUTPUT_SUBDIR)
        self.songs_by_first_letter = None

    def _find_sources(self):
        if not self.songs_by_first_letter:
            logger.debug('loading index from HTMLRenderer')
            json_file = os.path.join(self.inputdir, HTMLRenderer.INDEX_JSON_FILE)
            if not os.path.isfile(json_file):
                raise IOError('cannot find index file: ' + json_file)
            self.songs_by_first_letter = json.load(open(json_file, 'r'))

    def _prepare_output_directory(self):
        if not os.path.isdir(self.outputdir):
            logger.debug('creating outputdir: ' + self.outputdir)
            os.makedirs(self.outputdir)

    def _get_output_filename(self, input_filename):
        output_filename = None
        for extension in ('htm', 'html'):
            if input_filename.lower().endswith(extension):
                output_filename = input_filename.lower().replace(extension, 'pdf')
        if not output_filename:
            output_filename = input_filename.lower() + '.pdf'
        return output_filename

    def convert_songs(self):
        self._find_sources()
        self._prepare_output_directory()
        for songs in self.songs_by_first_letter.values():
            for song_data in songs:
                logger.info('converting song to pdf: ' + song_data['title'])
                for filename in song_data['filenames'].values():
                    wkhtmltopdf(
                        'file://{0}/{1}'.format(os.path.abspath(self.inputdir), filename),
                        os.path.join(self.outputdir, self._get_output_filename(filename))
                    )
