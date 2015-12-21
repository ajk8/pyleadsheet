import os
import yaml
import funcy
import re
from . import objects
from . import constants

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
    """ If value is a type, then return it, otherwise return the type of value

    .. doctests ::

        >>> _self_or_type(str) == str
        True
        >>> _self_or_type(None) == type(None)
        True
        >>> _self_or_type(['a', 'b']) == list
        True

    :param value: value to check
    :rtype: type
    """
    if isinstance(value, type):
        return value
    return type(value)


def _validate_schema(song_data):
    """ Validate a dict of song data against the YAML_SCHEMA

    .. doctests ::

        >>> _validate_schema({})
        >>> _validate_schema({'notathing': 'value'})  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        KeyError: "invalid key found...
        >>> _validate_schema({'title': []})  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        TypeError: invalid value found...
        >>> _validate_schema({'form': ['invalid']})  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        TypeError: invalid value found...
        >>> _validate_schema({'form': [{'badkey': 'value'}]})  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        KeyError: "invalid key found...
        >>> _validate_schema({'form': [{'reps': None}]})  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        TypeError: invalid value found...

    :param song_data: dict representation of a song
    :raises: KeyError, TypeError
    """
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
    """ Return the index of close_char, otherwise raise an exception

    .. doctests ::

        >>> _find_i('somestring', ':')  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        ValueError: reached end of string...
        >>> _find_i('got/slash?', '/')
        3

    :param progression_substr: string to search through
    :param close_char: char to search for
    :rtype: int
    :raises: ValueError
    """
    end_i = progression_substr.find(close_char)
    if end_i == -1:
        raise ValueError('reached end of string looking for "{0}"'.format(close_char))
    return end_i


def _parse_chord(progression_substr):
    """ Parse a progression_substr for a chord directive, returning both the chord
        definition and the index where it ended

    .. doctests ::

        >>> _parse_chord('C#-')  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        ValueError: reached end of string...
        >>> parsed, end_i = _parse_chord('C#-]')
        >>> parsed['chord']
        Chord(C#-)
        >>> len(parsed['duration'])
        1
        >>> parsed['duration'][0].count
        1
        >>> parsed['duration'][0].unit == constants.DURATION_UNIT_MEASURE
        True
        >>> end_i
        3
        >>> parsed, end_i = _parse_chord('rest]')
        >>> parsed['chord'] == constants.REST
        True
        >>> parsed, end_i = _parse_chord('riff]')
        >>> parsed['chord'] == constants.RIFF
        True
        >>> parsed, end_i = _parse_chord('?G:1m1b]')
        >>> parsed['optional']
        True
        >>> len(parsed['duration'])
        2

    :param progression_substr: part of a progression string
    :rtype: tuple
    """
    end_i = _find_i(progression_substr, CHORD_MARKUP['close_char'])
    tokens = progression_substr[:end_i].split(CHORD_MARKUP['separator'])
    chord_def = {
        'chord': None,
        'duration': []
    }
    chord_content = tokens[0]
    if chord_content == 'rest':
        chord_def['chord'] = constants.REST
    elif chord_content == 'riff':
        chord_def['chord'] = constants.RIFF
    else:
        if chord_content.startswith('?'):
            chord_def['optional'] = True
            chord_content = chord_content[1:]
        chord_def['chord'] = objects.Chord(chord_content)
    if len(tokens) == 1:
        chord_def['duration'].append(objects.ChordDuration(1, constants.DURATION_UNIT_MEASURE))
    else:
        for number, unit in funcy.re_all(r'([\d\.]+)([{0}{1}{2}])'.format(
            constants.DURATION_UNIT_MEASURE,
            constants.DURATION_UNIT_BEAT,
            constants.DURATION_UNIT_HALFBEAT
        ), tokens[1]):
            chord_def['duration'].append(objects.ChordDuration(int(number), unit))
    return chord_def, end_i


def _all_open_chars():
    """ Convenience method to gather all directive open chars

    .. doctests ::

        >>> _all_open_chars()
        ['[', '(', '{']

    :rtype: list
    """
    ret = [CHORD_MARKUP['open_char']]
    ret += sorted([pg['open_char'] for pg in PROGRESSION_GROUPS.values()])
    return ret


def _parse_group(progression_substr, group_type):
    """ Parse a group of chord directives in a progression.  Return both the group
        data and index of the ending character

    .. doctests ::

        >>> _parse_group('groupname[G][A]', 'badtype')  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        ValueError: invalid group type: badtype
        >>> _parse_group('groupname[G][A]', 'suffix')  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        ValueError: reached end of string...
        >>> parsed, end_i = _parse_group('groupname[G][A])adsf', 'suffix')
        >>> parsed['group']
        'suffix'
        >>> parsed['note']
        'groupname'
        >>> len(parsed['progression'])
        2

    :param progression_substr: part of a progression string
    :param group_type: valid group type, dictated by open_char that comes before
    :rtype: tuple
    :raises: ValueError
    """
    if group_type not in PROGRESSION_GROUPS.keys():
        raise ValueError('invalid group type: ' + group_type)
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
    ret['progression'] = _parse_progression_str(progression_substr[first_directive_open_i:end_i])
    return ret, end_i


def _raise_garbage_exception(progression_str, start_i, end_i):
    raise ValueError(
        'found garbage characters at in progression: "{}"[{}:{}] ({})'.format(
            progression_str,
            start_i,
            end_i,
            progression_str[start_i:end_i]
        )
    )


def _parse_progression_str(progression_str):
    """ Parse an entire progression, returning a list of chord definitions and sub-progressions

    .. doctests ::

        >>> _parse_progression_str('')  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        ValueError: no valid progression parts...
        >>> _parse_progression_str('asdf')  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        ValueError: no valid progression parts...
        >>> _parse_progression_str('[A]asdfasdf')  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        ValueError: found garbage...
        >>> _parse_progression_str('[A]asdfasdf[B]')  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        ValueError: found garbage...
        >>> parts = _parse_progression_str('[A][B]')
        >>> len(parts)
        2
        >>> parts = _parse_progression_str('{2[A][B7#9]}')
        >>> len(parts)
        1

    :param progression_str: complete progression definition
    :rtype: list
    :raises: ValueError
    """
    progression_str = re.sub(r'\s+', '', progression_str)
    ret = []
    i = 0
    last_directive_close = 0
    while i < len(progression_str):
        offset = 0
        progression_char = progression_str[i]
        group_flag = False
        for group_type in PROGRESSION_GROUPS.keys():
            if progression_char == PROGRESSION_GROUPS[group_type]['open_char']:
                if last_directive_close < i:
                    _raise_garbage_exception(progression_str, last_directive_close, i)
                group_def, offset = _parse_group(progression_str[i+1:], group_type)
                ret.append(group_def)
                group_flag = True
                last_directive_close = i + offset + 2
        if not group_flag:
            if progression_char == CHORD_MARKUP['open_char']:
                if last_directive_close < i:
                    _raise_garbage_exception(progression_str, last_directive_close, i)
                chord_def, offset = _parse_chord(progression_str[i+1:])
                ret.append(chord_def)
                last_directive_close = i + offset + 2
            elif progression_char == constants.ARG_ROW_BREAK:
                if last_directive_close < i:
                    _raise_garbage_exception(progression_str, last_directive_close, i)
                ret.append({'arg': constants.ARG_ROW_BREAK})
                last_directive_close = i + 2
        i += offset + 1
    if last_directive_close == 0:
        raise ValueError('no valid progression parts found in "{}"'.format(progression_str))
    if last_directive_close < i:
        _raise_garbage_exception(progression_str, last_directive_close, i)
    return ret


def _process_progression_chords(song_data):
    for progression in song_data['progressions']:
        logger.debug('parsing chords for progression: ' + progression['name'])
        progression['chords'] = _parse_progression_str(progression['chords'])


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


def _parse_time_signature_string(time_signature_str):
    """ Take in a string representation of a time signature and return an objects.TimeSignature

    .. doctests ::

        >>> _parse_time_signature_string('7')  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        ValueError: bad time signature...
        >>> _parse_time_signature_string('4/5')  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        ValueError: bad time signature...
        >>> _parse_time_signature_string('0/4')  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        ValueError: bad time signature...
        >>> _parse_time_signature_string('4/4')
        TimeSignature(count=4, unit=4)

    :param time_signature_str: string representation of a time signature
    :rtype: objects.TimeSignature
    :raises: ValueError
    """
    tokens = funcy.re_find(r'^(\d+)/([48])$', time_signature_str)
    if tokens is None:
        raise ValueError('bad time signature, must be of the form int/int, with ' +
                         'only 4 and 8 supported as units')
    if int(tokens[0]) < 1:
        raise ValueError('bad time signature, cannot have a count of 0')
    return objects.TimeSignature(int(tokens[0]), int(tokens[1]))


def _process_time_signature(song_data):
    if song_data['time']:
        song_data['time'] = _parse_time_signature_string(song_data['time'])


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
