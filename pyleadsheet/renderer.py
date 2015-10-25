import os
import shutil
import jinja2
import filecmp
import datetime
import json
from wkhtmltopdfwrapper import wkhtmltopdf
from .constants import DURATION_UNIT_MEASURE, DURATION_UNIT_BEAT, DURATION_UNIT_HALFBEAT
from .constants import BAR_SINGLE, BAR_REPEAT_OPEN, BAR_REPEAT_CLOSE
from .constants import ARG_ROW_BREAK
from .constants import FILENAME_SUFFIX_COMBINED, FILENAME_SUFFIX_NO_LYRICS, FILENAME_SUFFIX_LYRICS_ONLY

import logging
logger = logging.getLogger(__name__)


class HTMLRenderer(object):

    SONG_TEMPLATE = 'song.jinja2'
    INDEX_TEMPLATE = 'index.jinja2'
    OUTPUT_SUBDIR = 'html'
    INDEX_JSON_FILE = '.index.json'
    DURATION_UNIT_MULTIPLIERS = {DURATION_UNIT_MEASURE: 8, DURATION_UNIT_BEAT: 2, DURATION_UNIT_HALFBEAT: 1}

    MODES = {
        'no_lyrics': {'filename_suffix': FILENAME_SUFFIX_NO_LYRICS, 'display_name': 'Lead Sheet', 'display_order': 1},
        'lyrics_only': {'filename_suffix': FILENAME_SUFFIX_LYRICS_ONLY, 'display_name': 'Lyrics', 'display_order': 2},
        'combined': {'filename_suffix': FILENAME_SUFFIX_COMBINED, 'display_name': 'Combined', 'display_order': 3},
    }

    def __init__(self, outputdir, combined=False, no_lyrics=False, lyrics_only=False):
        logger.debug('initializing HTMLRenderer with outputdir: ' + outputdir)
        self.songs_data = {}
        self.outputdir = os.path.join(outputdir, self.OUTPUT_SUBDIR)
        self.mode_flags = {'combined': combined, 'no_lyrics': no_lyrics, 'lyrics_only': lyrics_only}
        self.timestamp = datetime.datetime.now()

    def _prepare_output_directory(self):
        if not os.path.exists(self.outputdir):
            logger.debug('creating outputdir')
            os.makedirs(self.outputdir)
        fromfile = os.path.join(os.path.dirname(__file__), 'templates', 'pyleadsheet.css')
        tofile = os.path.join(self.outputdir, 'pyleadsheet.css')
        if not os.path.exists(tofile) or not filecmp.cmp(fromfile, tofile):
            logger.info('copying base files into outputdir')
            shutil.copy(fromfile, tofile)

    def _convert_progression_data(self, progression_data):
        bars = []
        measures = []
        cur = 0
        for datum in progression_data:
            if 'arg' in datum.keys():
                pass
            elif 'group' in datum.keys():
                group_bars, group_measures = self._convert_progression_data(datum['progression'])
                if datum['group'] == 'repeat':
                    group_bars[0] = BAR_REPEAT_OPEN
                group_bars[-1] = BAR_REPEAT_CLOSE
                bars += group_bars
                measures += group_measures
            elif 'chord' in datum.keys():
                subdivisions = 0
                for duration_part in datum['duration']:
                    subdivisions += duration_part['number'] * self.DURATION_UNIT_MULTIPLIERS[duration_part['unit']]
                for i in range(subdivisions):
                    if cur % 8 == 0:
                        measures.append([datum['chord']])
                        if len(bars) < len(measures):
                            bars.append(BAR_SINGLE)
                    elif i == 0:
                        measures[-1].append(datum['chord'])
                    else:
                        measures[-1].append('')
                    cur += 1
        if len(measures) == len(bars):
            bars.append(BAR_SINGLE)
        return bars, measures

    def _make_rows(self, progression_data):
        bars, measures = self._convert_progression_data(progression_data)

        # for now, all rows are divided into 4 measures
        rows = []
        lastbreak = 0
        for i in range(len(measures)):
            if i == 0 or i - lastbreak == 4 or bars[i] == BAR_REPEAT_CLOSE:
                rows.append({'bars': [], 'measures': []})
                rows[-1]['bars'].append(BAR_SINGLE if bars[i] == BAR_REPEAT_CLOSE else bars[i])
                lastbreak = i
            rows[-1]['measures'].append(measures[i])
            rows[-1]['bars'].append(BAR_SINGLE if bars[i+1] == BAR_REPEAT_OPEN else bars[i+1])
        from pprint import pformat
        print pformat(rows)
        return rows

    def _prepare_form_section_lyrics(self, form_section):
        if 'lyrics' not in form_section.keys():
            form_section['lyrics'] = form_section['lyrics_hint'] = ''
        else:
            lines = form_section['lyrics'].splitlines()
            form_section['lyrics'] = '<br />'.join(lines)
            form_section['lyrics_hint'] = (lines[0] if len(lines[0]) <= 50 else lines[0][0:50]) + '...'

    def load_song(self, song_data):
        for i in range(len(song_data['progressions'])):
            progression_name = song_data['progressions'][i].keys()[0]
            song_data['progressions'][i] = {
                'name': progression_name,
                'rows': self._make_rows(song_data['progressions'][i][progression_name])
            }
        for form_section in song_data['form']:
            self._prepare_form_section_lyrics(form_section)
        self.songs_data[song_data['title']] = song_data

    def _get_output_filename(self, song_title, suffix=None):
        ret = song_title.lower().replace(' ', '_')
        ret += '_' + suffix if suffix else ''
        return ret + '.html'

    def _update_template_data(self, template_data):
        template_data.update({
            'timestamp': self.timestamp,
            'modes': self.MODES,
            'mode_keys': sorted(self.MODES.keys(), key=lambda(k): self.MODES[k]['display_order']),
            'mode_flags': self.mode_flags
        })

    def _render_template_to_file(self, template, outputfilename, template_data):
        self._prepare_output_directory()
        self._update_template_data(template_data)
        j2env = jinja2.Environment(loader=jinja2.PackageLoader('pyleadsheet', 'templates'))
        output = open(os.path.join(self.outputdir, outputfilename), 'w')
        output.write(j2env.get_template(template).render(**template_data))

    def render_song(self, song_title):
        logger.info('rendering song: ' + song_title)
        if self.mode_flags['combined']:
            self._render_template_to_file(
                self.SONG_TEMPLATE,
                self._get_output_filename(song_title, self.MODES['combined']['filename_suffix']),
                {'song': self.songs_data[song_title], 'render_leadsheet': True, 'render_lyrics': True}
            )
        if self.mode_flags['no_lyrics']:
            self._render_template_to_file(
                self.SONG_TEMPLATE,
                self._get_output_filename(song_title, self.MODES['no_lyrics']['filename_suffix']),
                {'song': self.songs_data[song_title], 'render_leadsheet': True, 'render_lyrics': False}
            )
        if self.mode_flags['lyrics_only']:
            self._render_template_to_file(
                self.SONG_TEMPLATE,
                self._get_output_filename(song_title, self.MODES['lyrics_only']['filename_suffix']),
                {'song': self.songs_data[song_title], 'render_leadsheet': False, 'render_lyrics': True}
            )

    def render_index(self):
        logger.info('rendering index')
        songs_by_first_letter = {}
        current_letter = None
        for title in sorted(self.songs_data.keys()):
            if not current_letter or title[0].upper() > current_letter:
                current_letter = title[0].upper()
                songs_by_first_letter[current_letter] = []
            songs_by_first_letter[current_letter].append(
                {'title': title, 'filenames': {}}
            )
            for mode in self.MODES.keys():
                songs_by_first_letter[current_letter][-1]['filenames'][mode] = \
                        self._get_output_filename(title, self.MODES[mode]['filename_suffix'])
        self._render_template_to_file(
            self.INDEX_TEMPLATE,
            'index.html',
            {'songs_by_first_letter': songs_by_first_letter, 'sorted_letters': sorted(songs_by_first_letter.keys())}
        )
        json.dump(songs_by_first_letter, open(os.path.join(self.outputdir, self.INDEX_JSON_FILE), 'w'))

    def render_book(self):
        logger.info('rendering HTML book')
        for song_title in self.songs_data.keys():
            self.render_song(song_title)
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
                wkhtmltopdf(
                    'file://{0}/{1}'.format(os.path.abspath(self.inputdir), song_data['filenames']['no_lyrics']),
                    os.path.join(self.outputdir, self._get_output_filename(song_data['filenames']['no_lyrics']))
                )
                wkhtmltopdf(
                    'file://{0}/{1}'.format(os.path.abspath(self.inputdir), song_data['filenames']['lyrics_only']),
                    os.path.join(self.outputdir, self._get_output_filename(song_data['filenames']['lyrics_only']))
                )
