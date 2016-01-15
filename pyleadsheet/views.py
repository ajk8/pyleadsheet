import os
import logging
import datetime
import funcy
from . import parser
from . import constants
from . import models
from . import transposer

logger = logging.getLogger(__name__)

SONG_VIEW_TYPES = ['complete', 'leadsheet', 'lyrics']
DEFAULT_MEASURES_PER_ROW = 4
DURATION_UNIT_MULTIPLIERS = {
    constants.DURATION_UNIT_MEASURE: 8,
    constants.DURATION_UNIT_BEAT: 2,
    constants.DURATION_UNIT_HALFBEAT: 1
}


@funcy.memoize
def _get_display_timestamp():
    """ Get a timestamp which is formatted for display.  Memoize for reuse

    .. doctests ::

        >>> ts_str = _get_display_timestamp()
        >>> ts_dt = datetime.datetime.strptime(ts_str, '%c')
        >>> type(ts_dt) == type(datetime.datetime.now())
        True

    :rtype: string
    """
    return datetime.datetime.now().strftime('%c')


def _with_universal_view_kwargs(view_kwargs):
    """ Supplement view_kwargs with items that are required in all views

    .. doctests ::

        >>> vk = _with_universal_view_kwargs({})
        >>> 'timestamp' in vk.keys()
        True

    :param view_kwargs: dict of objects which are needed to render a view
    :rtype: dict
    """
    view_kwargs.update({
        'timestamp': _get_display_timestamp()
    })
    return view_kwargs


def _get_sortable_title(title):
    """ Get a version of a song title which fits it in a sort function (eg. ignore "the")

    .. doctests ::

        >>> _get_sortable_title('Homeward Bound')
        'Homeward Bound'
        >>> _get_sortable_title('The Onion Strikes Again')
        'Onion Strikes Again'
        >>> _get_sortable_title('the lowercase')
        'lowercase'
        >>> _get_sortable_title('THE')
        'THE'
        >>> _get_sortable_title('Theoretically True')
        'Theoretically True'

    :param title: title to convert
    :rtype: string
    """
    if title.lower().startswith('the '):
        title = ' '.join(title.split()[1:])
    return title


def compose_index_kwargs(filepaths):
    """ Get a dict of objects needed to render a table of contents

    :param filepaths:
    :rtype: dict
    """
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
    return _with_universal_view_kwargs(view_kwargs)


def _calculate_max_measures_per_row(condense_measures):
    """ Figure out how many measures will fit on displayed row given a "condense" directive

    .. doctests ::

        >>> _calculate_max_measures_per_row(False)
        4
        >>> _calculate_max_measures_per_row(True)
        8

    :param condense_measures: boolean directive to cut the measure width in half
    :rtype: int
    """
    max_measures_per_row = DEFAULT_MEASURES_PER_ROW
    if condense_measures:
        max_measures_per_row *= 2
    return max_measures_per_row


def _add_max_measures_per_row_to_song_data(song_data):
    condense_measures = 'condense_measures' in song_data.keys() and song_data['condense_measures']
    song_data['max_measures_per_row'] = _calculate_max_measures_per_row(condense_measures)


def _calculate_duration_unit_measure(time_signature):
    """ Figure out how many available "nodes" there are in every measure given an instance
        of objects.TimeSignature

    .. doctests ::

        >>> from .models import TimeSignature
        >>> _calculate_duration_unit_measure(TimeSignature(4, 4))
        8
        >>> _calculate_duration_unit_measure(TimeSignature(7, 4))
        14
        >>> _calculate_duration_unit_measure(TimeSignature(3, 4))
        6
        >>> _calculate_duration_unit_measure(TimeSignature(6, 8))
        6

    :param time_signature: instance of objects.TimeSignature
    :rtype: int
    """
    default_units_per_measure = DURATION_UNIT_MULTIPLIERS[constants.DURATION_UNIT_MEASURE]
    new_unit_multiplier = 1.0 / (float(time_signature.unit) / default_units_per_measure)
    return int(time_signature.count * new_unit_multiplier)


def _add_multipliers_to_song_data(song_data):
    dum = _calculate_duration_unit_measure(song_data['time'])
    song_data['multipliers'] = DURATION_UNIT_MULTIPLIERS.copy()
    song_data['multipliers'][constants.DURATION_UNIT_MEASURE] = dum


def _clean_last_chord(measures):
    last_chord = measures[-1][-1]
    if last_chord == '':
        return
    last_last_chord = ''
    reverse_subdivision_i = -2
    reverse_measure_i = -1
    while last_last_chord == '' and abs(reverse_measure_i) <= len(measures):
        try:
            last_last_chord = measures[reverse_measure_i][reverse_subdivision_i]
        except IndexError:
            if reverse_subdivision_i == -1:
                break
            reverse_measure_i -= 1
            reverse_subdivision_i = -1
        reverse_subdivision_i -= 1
    if last_chord == last_last_chord:
        measures[-1][-1] = ''


def _convert_progression_data(progression_data, multipliers):
    measures = []
    cursor = 0
    for datum in progression_data:
        if 'arg' in datum.keys():
            if datum['arg'] == constants.ARG_ROW_BREAK:
                measures[-1].args.append(constants.ARG_ROW_BREAK)
        elif 'group' in datum.keys():
            group_measures = _convert_progression_data(
                datum['progression'],
                multipliers
            )
            if datum['group'] == 'repeat':
                group_measures[0].start_bar = constants.BAR_REPEAT_OPEN
                group_measures[-1].end_bar = constants.BAR_REPEAT_CLOSE
                group_measures[-1].end_note = datum['note'] if datum['note'] else ''
            else:
                group_measures[0].start_bar = constants.BAR_DOUBLE
                group_measures[0].start_note = datum['note'] if datum['note'] else ''
            measures += group_measures
        elif 'chord' in datum.keys():
            subdivisions = 0
            for duration_part in datum['duration']:
                subdivisions += duration_part.count * multipliers[duration_part.unit]
            for i in range(subdivisions):
                if cursor % multipliers[constants.DURATION_UNIT_MEASURE] == 0:
                    measures.append(models.Measure(
                        multipliers[constants.DURATION_UNIT_MEASURE],
                        datum['chord']
                    ))
                elif i == 0:
                    _clean_last_chord(measures)
                    measures[-1].set_next_subdivision(datum['chord'])
                else:
                    measures[-1].set_next_subdivision('')
                cursor += 1
    if measures[0].start_bar < constants.BAR_SECTION_OPEN:
        measures[0].start_bar = constants.BAR_SECTION_OPEN
    if measures[-1].end_bar < constants.BAR_SECTION_CLOSE:
        measures[-1].end_bar = constants.BAR_SECTION_CLOSE
    return measures


def _make_rows(progression_data, multipliers, max_measures):
    measures = _convert_progression_data(progression_data, multipliers)
    rows = []
    lastbreak = 0
    for i in range(len(measures)):
        if (
            i == 0 or
            i - lastbreak == max_measures or
            measures[i-1].end_bar in (
                constants.BAR_REPEAT_CLOSE,
                constants.BAR_SECTION_CLOSE
            ) or
            constants.ARG_ROW_BREAK in measures[i-1].args
        ):
            rows.append([])
            lastbreak = i
        rows[-1].append(measures[i])
    return rows


def _convert_linebreaks_to_html(text_snippet):
    """ Take a text snippet and turn all line breaks into <br /> tags

    .. doctests ::

        >>> _convert_linebreaks_to_html('i am a single line string')
        'i am a single line string'
        >>> _convert_linebreaks_to_html('''i am a
        ... multiline
        ...
        ... string''')
        'i am a<br />multiline<br /><br />string'
    """
    lines = text_snippet.splitlines()
    return '<br />'.join(lines)


def _generate_text_snippet_hint(text_snippet):
    """ Take a text snippet and generate a string of length <52 as a hint

    .. doctests ::

        >>> _generate_text_snippet_hint('i am a short snippet')
        'i am a short snippet'
        >>> _generate_text_snippet_hint('''i am a series
        ... of short
        ... lines''')
        'i am a series...'
        >>> _generate_text_snippet_hint('i am a very long line, rather longer than ' + \
                                        'i might need to be -- so long, in fact, ' + \
                                        'that i need to be split to not trip pep8')
        'i am a very long line, rather longer than i might...'
    """
    lines = text_snippet.splitlines()
    if len(lines) == 1 and len(lines[0]) < 50:
        return lines[0]
    elif len(lines) > 1:
        return lines[0] + '...'
    else:
        return lines[0][0:49] + '...'


def _prepare_form_section_lyrics(form_section):
    if 'lyrics' not in form_section.keys():
        form_section['lyrics'] = form_section['lyrics_hint'] = ''
    else:
        form_section['lyrics_hint'] = _generate_text_snippet_hint(form_section['lyrics'])
        form_section['lyrics'] = _convert_linebreaks_to_html(form_section['lyrics'])


def _prepend_global_comments(song_data):
    """ Take any comments defined as part of a progression, and prepend them
        to the comments of all form sections which refer to that progression

    .. doctests ::

        >>> song_data = {'progressions': [], 'form': []}
        >>> song_data['progressions'].append({'name': 'a'})
        >>> song_data['form'].append({'progression': 'a'})
        >>> _prepend_global_comments(song_data)
        >>> song_data['form'][0]['comment']  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        KeyError: 'comment'
        >>> song_data['progressions'][0]['comment'] = 'global'
        >>> _prepend_global_comments(song_data)
        >>> song_data['form'][0]['comment']
        ['global']
        >>> song_data['form'][0]['comment'] = ['local']
        >>> _prepend_global_comments(song_data)
        >>> song_data['form'][0]['comment']
        ['global', ' -- ', 'local']
    """
    for progression in song_data['progressions']:
        if 'comment' in progression.keys():
            for section in song_data['form']:
                if section['progression'] == progression['name']:
                    logger.debug('prepending progression comment')
                    comment = [progression['comment']]
                    if 'comment' in section.keys():
                        comment += [' -- '] + section['comment']
                    section['comment'] = comment


def _prepend_continuation_comments(form_data):
    """ Take any form sections which are marked as continuations and make
        a note of it in the comment

    .. doctests ::

        >>> form_data = [{'progression': 'a'}, {}]
        >>> _prepend_continuation_comments(form_data)
        >>> form_data
        [{'progression': 'a'}, {}]
        >>> form_data[-1]['continuation'] = True
        >>> _prepend_continuation_comments(form_data)
        >>> form_data[-1]['comment']
        ['continuation of a']
        >>> form_data[-1]['comment'] = ['comment']
        >>> _prepend_continuation_comments(form_data)
        >>> form_data[-1]['comment']
        ['continuation of a', ' -- ', 'comment']
    """
    for i in range(len(form_data)):
        if 'continuation' in form_data[i].keys():
            comment = ['continuation of ' + form_data[i-1]['progression']]
            if 'comment' in form_data[i].keys():
                comment += [' -- '] + form_data[i]['comment']
            form_data[i]['comment'] = comment


def compose_song_kwargs(filepath, song_view_type, transpose_to_root=None):
    if not os.path.isfile(filepath):
        raise IOError('input file does not exist: ' + filepath)
    if song_view_type not in SONG_VIEW_TYPES:
        raise ValueError('invalid song view type: ' + song_view_type)
    song_data = parser.parse_file(filepath)
    if transpose_to_root:
        transposer.transpose_song_data_by_new_root(song_data, transpose_to_root)
    _add_multipliers_to_song_data(song_data)
    _add_max_measures_per_row_to_song_data(song_data)
    for progression in song_data['progressions']:
        progression['rows'] = _make_rows(
            progression['chords'],
            song_data['multipliers'],
            song_data['max_measures_per_row']
        )
    for form_section in song_data['form']:
        _prepare_form_section_lyrics(form_section)
    _prepend_global_comments(song_data)
    _prepend_continuation_comments(song_data['form'])
    return _with_universal_view_kwargs({
        'song': song_data,
        'num_subdivisions': song_data['multipliers'][constants.DURATION_UNIT_MEASURE],
        'render_leadsheet': song_view_type in ('complete', 'leadsheet'),
        'render_lyrics': song_view_type in ('complete', 'lyrics'),
        'transpose_roots': song_data['key'].transposable_roots
    })
