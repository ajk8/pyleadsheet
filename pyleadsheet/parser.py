import os
import yaml
import funcy
from .constants import DURATION_UNIT_MEASURE, DURATION_UNIT_BEAT, DURATION_UNIT_HALFBEAT
from .constants import ARG_ROW_BREAK, REST

CHORD_MARKUP = {
    'open_char': '[',
    'close_char': ']',
    'separator': ':'
}
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
        chord_parts = (REST, None, None)
    else:
        chord_parts = funcy.re_find(r'([A-Gb#]{1,2})([^/]+)?(/[A-Gb#]{1,2})?', tokens[0])
    chord_def = {'chord': {'root': chord_parts[0]}, 'duration': []}
    if chord_parts[1]:
        chord_def['chord']['spec'] = chord_parts[1]
    if chord_parts[2]:
        chord_def['chord']['base'] = chord_parts[2][1:]
    if len(tokens) == 1:
        chord_def['duration'].append({'number': 1, 'unit': DURATION_UNIT_MEASURE})
    else:
        for number, unit in funcy.re_all(r'([\d\.]+)([{0}{1}{2}])'.format(
            DURATION_UNIT_MEASURE, DURATION_UNIT_BEAT, DURATION_UNIT_HALFBEAT
        ), tokens[1]):
            chord_def['duration'].append({'number': int(number), 'unit': unit})
    return chord_def, end_i


def _parse_group(progression_substr, group_type):
    close_char = PROGRESSION_GROUPS[group_type]['close_char']
    end_i = _find_i(progression_substr, close_char)
    ret = {'group': group_type}
    first_chord_open_i = _find_i(progression_substr, CHORD_MARKUP['open_char'])
    ret['name'] = progression_substr[:first_chord_open_i] if first_chord_open_i > 0 else None
    ret['progression'] = _parse_progression(progression_substr[first_chord_open_i:end_i])
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


def parse(yaml_str):
    pls_data = yaml.load(yaml_str)
    for i in range(len(pls_data['progressions'])):
        progression_name = pls_data['progressions'][i].keys()[0]
        pls_data['progressions'][i][progression_name] = _parse_progression(
            pls_data['progressions'][i][progression_name]
        )
    return pls_data


def parse_file(filepath):
    if not os.path.isfile(filepath):
        raise IOError('could not find any file at {0}'.format(filepath))
    contents = open(filepath, 'r').read()
    return parse(contents)
