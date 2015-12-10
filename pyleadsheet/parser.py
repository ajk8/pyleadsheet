import os
import yaml
import funcy
from .constants import DURATION_UNIT_MEASURE, DURATION_UNIT_BEAT, DURATION_UNIT_HALFBEAT
from .constants import ARG_ROW_BREAK, REST, RIFF

import logging
logger = logging.getLogger(__name__)

YAML_SCHEMA = {
    'title': str,
    'key': str,
    'time': str,
    'feel': str,
    'condense_measures': bool,
    'progressions': [
        {
            'name': str,
            'chords': str,
            'comment': str
        }
    ],
    'form': [
        {
            'progression': str,
            'reps': (str, int, float),
            'comment': str,
            'lyrics': str,
            'continuation': bool
        }
    ]
}


def _self_or_type(value):
    if isinstance(value, type):
        return value
    return type(value)


def _validate_schema(song_data):
    for key, value in song_data.items():
        if key not in YAML_SCHEMA.keys():
            raise KeyError('invalid key found in yaml data: {0} (valid keys are {1})'.format(
                key, YAML_SCHEMA.keys()
            ))
        elif not isinstance(value, _self_or_type(YAML_SCHEMA[key])):
            raise TypeError('invalid value found in yaml data: {0}={1} (expecting {2})'.format(
                key, value, _self_or_type(YAML_SCHEMA[key])
            ))
        elif isinstance(value, list):
            for i in range(len(value)):
                if not isinstance(value[i], _self_or_type(YAML_SCHEMA[key][0])):
                    raise TypeError(
                        'invalid value found in yaml data: {0}[{1}]={2} (expecting {3})'.format(
                            key, i, value, _self_or_type(YAML_SCHEMA[key][0])
                        )
                    )
                for subkey, subvalue in value[i].items():
                    if subkey not in YAML_SCHEMA[key][0].keys():
                        raise KeyError(
                            'invalid key found in yaml data: '
                            '{0}[{1}][{2}] (valid keys are {3})'.format(
                                key, i, subkey, YAML_SCHEMA[key][0].keys()
                            )
                        )
                    elif not isinstance(subvalue, YAML_SCHEMA[key][0][subkey]):
                        raise TypeError(
                            'invalid value found in yaml data: '
                            '{0}[{1}][{2}]={3} (expecting {4})'.format(
                                key, i, subkey, subvalue, YAML_SCHEMA[key][0][subkey]
                            )
                        )


CHORD_MARKUP = {'open_char': '[', 'close_char': ']', 'separator': ':'}
PROGRESSION_GROUPS = {
    'repeat': {'open_char': '{', 'close_char': '}'},
    'suffix': {'open_char': '(', 'close_char': ')'}
}


def _find_i(progression_substr, close_char):
    end_i = progression_substr.find(close_char)
    if end_i == -1:
        raise ValueError('reached end of string looking for "{0}"'.format(close_char))
    return end_i


def _parse_chord(progression_substr):
    end_i = _find_i(progression_substr, CHORD_MARKUP['close_char'])
    tokens = progression_substr[:end_i].split(CHORD_MARKUP['separator'])
    if tokens[0] == 'rest':
        chord_parts = (None, REST, None, None)
    elif tokens[0] == 'riff':
        chord_parts = (None, RIFF, None, None)
    else:
        chord_parts = funcy.re_find(r'(\??)([A-Gb#]{1,2})([^/]+)?(/[A-Gb#]{1,2})?', tokens[0])
    chord_def = {
        'chord': {'root': chord_parts[1], 'optional': True if chord_parts[0] else False},
        'duration': []
    }
    if chord_parts[2]:
        chord_def['chord']['spec'] = chord_parts[2]
    if chord_parts[3]:
        chord_def['chord']['base'] = chord_parts[3][1:]
    if len(tokens) == 1:
        chord_def['duration'].append({'number': 1, 'unit': DURATION_UNIT_MEASURE})
    else:
        for number, unit in funcy.re_all(r'([\d\.]+)([{0}{1}{2}])'.format(
            DURATION_UNIT_MEASURE, DURATION_UNIT_BEAT, DURATION_UNIT_HALFBEAT
        ), tokens[1]):
            chord_def['duration'].append({'number': int(number), 'unit': unit})
    return chord_def, end_i


def _all_open_chars():
    ret = [CHORD_MARKUP['open_char']]
    ret += [pg['open_char'] for pg in PROGRESSION_GROUPS.values()]
    return ret


def _parse_group(progression_substr, group_type):
    close_char = PROGRESSION_GROUPS[group_type]['close_char']
    end_i = _find_i(progression_substr, close_char)
    ret = {'group': group_type}
    first_directive_open_i = 9999
    for open_char in _all_open_chars():
        try:
            open_i = _find_i(progression_substr, open_char)
        except ValueError:
            continue
        if open_i < first_directive_open_i:
            first_directive_open_i = open_i
    ret['note'] = progression_substr[:first_directive_open_i] \
        if first_directive_open_i > 0 else None
    ret['progression'] = _parse_progression(progression_substr[first_directive_open_i:end_i])
    return ret, end_i


def _parse_progression(progression_str):
    ret = []
    i = 0
    while i < len(progression_str):
        offset = 0
        progression_char = progression_str[i]
        flag = False
        for group_type in PROGRESSION_GROUPS.keys():
            if progression_char == PROGRESSION_GROUPS[group_type]['open_char']:
                group_def, offset = _parse_group(progression_str[i+1:], group_type)
                ret.append(group_def)
                flag = True
        if not flag:
            if progression_char == CHORD_MARKUP['open_char']:
                chord_def, offset = _parse_chord(progression_str[i+1:])
                ret.append(chord_def)
            elif progression_char == ARG_ROW_BREAK:
                ret.append({'arg': ARG_ROW_BREAK})
        i += offset + 1
    return ret


def _process_progression_chords(song_data):
    for progression in song_data['progressions']:
        logger.debug('parsing chords for progression: ' + progression['name'])
        progression['chords'] = _parse_progression(progression['chords'])


def _process_comments(song_data):
    for progression in song_data['progressions']:
        if 'comment' in progression.keys():
            for section in song_data['form']:
                if section['progression'] == progression['name']:
                    logger.debug('prepending progression comment')
                    comment = progression['comment']
                    if 'comment' in section.keys():
                        comment += ' -- ' + section['comment']
                    section['comment'] = comment
    for i in range(len(song_data['form'])):
        if 'continuation' in song_data['form'][i].keys():
            comment = 'continuation of ' + song_data['form'][i-1]['progression']
            if 'comment' in song_data['form'][i].keys():
                comment += ' -- ' + song_data['form'][i]['comment']
            song_data['form'][i]['comment'] = comment


def _process_time_signature(song_data):
    if song_data['time']:
        tokens = funcy.re_find(r'(\d+)/([48])', song_data['time'])
        if tokens is None:
            raise ValueError('bad time signature, must be of the form int/int, with ' +
                             'only 4 and 8 supported as units')
        song_data['time'] = {'count': int(tokens[0]), 'unit': int(tokens[1])}


def parse(yaml_str):
    song_data = yaml.load(yaml_str)
    logger.debug('parsing input for song: ' + song_data['title'])
    _validate_schema(song_data)
    _process_progression_chords(song_data)
    _process_comments(song_data)
    _process_time_signature(song_data)
    return song_data


def _get_content_from_song_file(filepath):
    if not os.path.isfile(filepath):
        raise IOError('could not find any file at {0}'.format(filepath))
    content = open(filepath, 'r').read()
    return content


def parse_file(filepath):
    content = _get_content_from_song_file(filepath)
    return parse(content)


def get_title_from_song_file(filepath):
    content = _get_content_from_song_file(filepath)
    song_data = yaml.load(content)
    return song_data['title']
