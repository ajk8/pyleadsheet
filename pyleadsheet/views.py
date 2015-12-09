import os
import logging
from . import parser
from . import constants
from . import transposer

logger = logging.getLogger(__name__)

SONG_VIEW_TYPES = ['complete', 'leadsheet', 'lyrics']
MAX_MEASURES_PER_ROW = 4
DURATION_UNIT_MULTIPLIERS = {
    constants.DURATION_UNIT_MEASURE: 8,
    constants.DURATION_UNIT_BEAT: 2,
    constants.DURATION_UNIT_HALFBEAT: 1
}


def _get_sortable_title(title):
    if title.lower().startswith('the '):
        title = ' '.join(title.split()[1:])
    return title


def compose_index_kwargs(filepaths):
    songs_by_title = {}
    for path in filepaths:
        title = parser.get_title_from_song_file(path)
        sortable_title = _get_sortable_title(title)
        songs_by_title[title] = {
            'filepath': path,
            'display_title': title,
            'sortable_title': sortable_title
        }
    songs_by_first_letter = {}
    current_letter = None
    for song_data in sorted(songs_by_title.values(), key=lambda k: k['sortable_title']):
        if not current_letter or song_data['sortable_title'][0].upper() > current_letter:
            current_letter = song_data['sortable_title'][0].upper()
            songs_by_first_letter[current_letter] = []
        songs_by_first_letter[current_letter].append(song_data)
    view_kwargs = {
        'songs_by_first_letter': songs_by_first_letter,
        'song_view_types': SONG_VIEW_TYPES
    }
    return view_kwargs


def _calculate_max_measures_per_row(song_data):
    song_data['max_measures_per_row'] = MAX_MEASURES_PER_ROW
    if 'condense_measures' in song_data.keys() and song_data['condense_measures']:
        song_data['max_measures_per_row'] *= 2


def _calculate_multipliers(song_data):
    song_data['multipliers'] = DURATION_UNIT_MULTIPLIERS.copy()
    measure_mult_mult = 1.0 / (float(song_data['time']['unit']) / 8.0)
    song_data['multipliers'][constants.DURATION_UNIT_MEASURE] = \
        int(song_data['time']['count'] * measure_mult_mult)


def _calculate_transposition(song_data, transpose_half_steps, transpose_to_root):
    if transpose_half_steps:
        song_data['transpose'] = {
            'method': transposer.transpose_by_half_steps,
            'key': song_data['key'],
            'value': int(transpose_half_steps)
        }
    elif transpose_to_root:
        song_data['transpose'] = {
            'method': transposer.transpose_by_new_root,
            'key': song_data['key'],
            'value': transpose_to_root
        }
    else:
        song_data['transpose'] = None


def _clean_last_chord(measures):
    last_chord = measures[-1]['subdivisions'][-1]
    if last_chord == '':
        return
    last_last_chord = ''
    reverse_subdivision_i = -2
    reverse_measure_i = -1
    while last_last_chord == '' and abs(reverse_measure_i) <= len(measures):
        try:
            last_last_chord = measures[reverse_measure_i]['subdivisions'][reverse_subdivision_i]
        except IndexError:
            if reverse_subdivision_i == -1:
                break
            reverse_measure_i -= 1
            reverse_subdivision_i = -1
        reverse_subdivision_i -= 1
    if last_chord == last_last_chord:
        measures[-1]['subdivisions'][-1] = ''


def _convert_progression_data(progression_data, multipliers, transpose):
    measures = []
    cursor = 0
    for datum in progression_data:
        if 'arg' in datum.keys():
            if datum['arg'] == constants.ARG_ROW_BREAK:
                measures[-1]['args'].append(constants.ARG_ROW_BREAK)
        elif 'group' in datum.keys():
            group_measures = _convert_progression_data(datum['progression'], multipliers, transpose)
            if datum['group'] == 'repeat':
                group_measures[0]['start_bar'] = constants.BAR_REPEAT_OPEN
                group_measures[-1]['end_bar'] = constants.BAR_REPEAT_CLOSE
                group_measures[-1]['end_note'] = datum['note'] if datum['note'] else ''
            else:
                group_measures[0]['start_bar'] = constants.BAR_DOUBLE
                group_measures[0]['start_note'] = datum['note'] if datum['note'] else ''
            measures += group_measures
        elif 'chord' in datum.keys():
            if transpose:
                transpose['method'](datum['chord'], transpose['key'], transpose['value'])
            subdivisions = 0
            for duration_part in datum['duration']:
                subdivisions += duration_part['number'] * multipliers[duration_part['unit']]
            for i in range(subdivisions):
                if cursor % multipliers[constants.DURATION_UNIT_MEASURE] == 0:
                    measures.append({
                        'args': [],
                        'start_bar': constants.BAR_SINGLE,
                        'end_bar': constants.BAR_SINGLE,
                        'subdivisions': [datum['chord']]
                    })
                elif i == 0:
                    _clean_last_chord(measures)
                    measures[-1]['subdivisions'].append(datum['chord'])
                else:
                    measures[-1]['subdivisions'].append('')
                cursor += 1
    if measures[0]['start_bar'] < constants.BAR_SECTION_OPEN:
        measures[0]['start_bar'] = constants.BAR_SECTION_OPEN
    if measures[-1]['end_bar'] < constants.BAR_SECTION_CLOSE:
        measures[-1]['end_bar'] = constants.BAR_SECTION_CLOSE
    return measures


def _make_rows(progression_data, multipliers, max_measures, transpose):
    measures = _convert_progression_data(progression_data, multipliers, transpose)
    rows = []
    lastbreak = 0
    for i in range(len(measures)):
        if (
            i == 0 or
            i - lastbreak == max_measures or
            measures[i-1]['end_bar'] in (constants.BAR_REPEAT_CLOSE, constants.BAR_SECTION_CLOSE) or
            constants.ARG_ROW_BREAK in measures[i-1]['args']
        ):
            rows.append([])
            lastbreak = i
        rows[-1].append(measures[i])
    return rows


def _prepare_form_section_lyrics(form_section):
    if 'lyrics' not in form_section.keys():
        form_section['lyrics'] = form_section['lyrics_hint'] = ''
    else:
        lines = form_section['lyrics'].splitlines()
        form_section['lyrics'] = '<br />'.join(lines)
        form_section['lyrics_hint'] = (lines[0] if len(lines[0]) <= 50 else lines[0][0:50]) + '...'


def _get_sort_title(title):
    words = title.split()
    if len(words) > 1 and words[0].lower() == 'the':
        return ' '.join(words[1:])
    return title


def compose_song_kwargs(filepath, song_view_type, transpose_half_steps, transpose_to_root):
    if not os.path.isfile(filepath):
        raise IOError('input file does not exist: ' + filepath)
    if song_view_type not in SONG_VIEW_TYPES:
        raise ValueError('invalid song view type: ' + song_view_type)
    song_data = parser.parse_file(filepath)
    _calculate_multipliers(song_data)
    _calculate_max_measures_per_row(song_data)
    _calculate_transposition(song_data, transpose_half_steps, transpose_to_root)
    for progression in song_data['progressions']:
        progression['rows'] = _make_rows(
            progression['chords'],
            song_data['multipliers'],
            song_data['max_measures_per_row'],
            song_data['transpose']
        )
    for form_section in song_data['form']:
        _prepare_form_section_lyrics(form_section)
    song_data['sort_title'] = _get_sort_title(song_data['title'])
    return {
        'song': song_data,
        'num_subdivisions': song_data['multipliers'][constants.DURATION_UNIT_MEASURE],
        'render_leadsheet': song_view_type in ('complete', 'leadsheet'),
        'render_lyrics': song_view_type in ('complete', 'lyrics')
    }
