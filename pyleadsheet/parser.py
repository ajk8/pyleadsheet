import os
import yaml
import funcy
from .constants import DURATION_UNIT_MEASURE, DURATION_UNIT_BEAT, DURATION_UNIT_HALFBEAT
from .constants import BAR_REPEAT_OPEN, BAR_REPEAT_CLOSE


def _parse_chord(progression_str, start_i):
    end_i = start_i + progression_str[start_i:].find(']')
    if end_i == -1:
        raise ValueError('reached end of string looking for "]"')
    tokens = progression_str[start_i:end_i].split(':')
    chord_def = {'chord': tokens[0], 'duration': []}
    if len(tokens) == 1:
        chord_def['duration'].append({'number': 1, 'unit': DURATION_UNIT_MEASURE})
    else:
        for number, unit in funcy.re_all(r'([\d\.]+)([{0}{1}{2}])'.format(
            DURATION_UNIT_MEASURE, DURATION_UNIT_BEAT, DURATION_UNIT_HALFBEAT
        ), tokens[1]):
            chord_def['duration'].append({'number': int(number), 'unit': unit})
    return chord_def, end_i


def _parse_progression(progression_str):
    ret = []
    repeat_open = False
    for i in range(len(progression_str)):
        progression_char = progression_str[i]
        if progression_char == '{':
            if repeat_open:
                raise ValueError('found "{" in open repeating section')
            repeat_open = True
            ret.append({'bar': BAR_REPEAT_OPEN})
        elif progression_char == '}':
            if not repeat_open:
                raise ValueError('found "}" outside of repeating section')
            repeat_open = False
            ret.append({'bar': BAR_REPEAT_CLOSE})
        elif progression_char == '[':
            chord_def, i = _parse_chord(progression_str, i+1)
            ret.append(chord_def)
    if repeat_open:
        raise ValueError('reached end of string looking for "}"')
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
