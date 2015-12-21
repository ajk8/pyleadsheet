SHARPS = ['A', 'A#', 'B', 'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#']
FLATS = ['A', 'Bb', 'B', 'C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab']
PREFER_FLATS = ['F']


def _get_root_from_key(key):
    """Doctest:
    >>> _get_root_from_key('D')
    'D'
    >>> _get_root_from_key('G#-')
    'G#'
    >>> _get_root_from_key('Ab')
    'Ab'
    """
    return key.split('-')[0]


def _lookup_from_note(note):
    """Doctest:
    >>> _lookup_from_note('D') == SHARPS
    True
    >>> _lookup_from_note('F') == FLATS
    True
    >>> _lookup_from_note('Ab') == FLATS
    True
    >>> _lookup_from_note('C#') == SHARPS
    True
    """
    if 'b' in note or note in PREFER_FLATS:
        return FLATS
    return SHARPS


def _get_relative_major(key):
    """Doctest:
    >>> _get_relative_major('Bb-')
    'Db'
    >>> _get_relative_major('F')
    'F'
    >>> _get_relative_major('C-')
    'Eb'
    >>> _get_relative_major('A-')
    'C'
    """
    if not key.endswith('-'):
        return key
    from_root = _get_root_from_key(key)
    from_lookup = _lookup_from_note(from_root)
    from_i = from_lookup.index(from_root)
    to_i = (from_i + 3) % 12
    to_lookup = FLATS
    to_root = to_lookup[to_i]
    return to_root


def _get_enharmonic_equal_note(note):
    """Doctest:
    >>> _get_enharmonic_equal_note('A#')
    'Bb'
    >>> _get_enharmonic_equal_note('Gb')
    'F#'
    >>> _get_enharmonic_equal_note('C')
    'C'
    >>> _get_enharmonic_equal_note('Cb')
    'B'
    >>> _get_enharmonic_equal_note('E#')
    'F'
    """
    if note in SHARPS:
        i = SHARPS.index(note)
        return FLATS[i]
    elif note in FLATS:
        i = FLATS.index(note)
        return SHARPS[i]
    elif '#' in note:
        i = SHARPS.index(note[:-1])
        return SHARPS[i+1]
    elif 'b' in note:
        i = FLATS.index(note[:-1])
        return FLATS[i-1]


def _get_enharmonic_equal_key(key):
    """Doctest:
    >>> _get_enharmonic_equal_key('B')
    'B'
    >>> _get_enharmonic_equal_key('A#-')
    'Bb-'
    """
    minor = key.endswith('-')
    root = _get_root_from_key(key)
    ret = _get_enharmonic_equal_note(root)
    return ret + '-' if minor else ret


def _lookup_from_key(key):
    """Doctest:
    >>> _lookup_from_key('G') == SHARPS
    True
    >>> _lookup_from_key('C#-') == SHARPS
    True
    >>> _lookup_from_key('Ab-')  # doctest: +ELLIPSIS
    Traceback (most recent call last):
        ...
    ValueError: Ab- is not a realistic key...
    """
    major_key = _get_relative_major(key)
    ret = _lookup_from_note(major_key)
    if 'b' in key and ret == SHARPS:
        raise ValueError('{0} is not a realistic key, you should use {1}'.format(
            key, _get_enharmonic_equal_key(key)
        ))
    return ret


def _note_to_half_steps(from_note, to_note):
    """Doctest:
    >>> _note_to_half_steps('C#', 'G')
    6
    >>> _note_to_half_steps('C#', 'Db')
    0
    """
    from_i = SHARPS.index(from_note) if from_note in SHARPS else FLATS.index(from_note)
    to_i = SHARPS.index(to_note) if to_note in SHARPS else FLATS.index(to_note)
    return (to_i - from_i) % 12


def _half_steps_to_note(from_note, half_steps, key):
    """Doctest:
    >>> _half_steps_to_note('Ab', 4, 'F-')
    'C'
    >>> _half_steps_to_note('C', 7, 'F')
    'G'
    """
    lookup = _lookup_from_key(key)
    from_i = lookup.index(from_note)
    to_i = (from_i + half_steps) % 12
    return lookup[to_i]


def _copy_key_to_new_root(from_key, to_root):
    """Doctest:
    >>> _copy_key_to_new_root('A', 'B')
    'B'
    >>> _copy_key_to_new_root('Bb-', 'C')
    'C-'
    """
    return from_key.replace(_get_root_from_key(from_key), to_root)


def transpose_by_new_root(chord, from_key, to_root):
    """Doctest:
    >>> chord = {'root': 'C'}
    >>> transpose_by_new_root(chord, 'C', 'G')
    >>> chord['root']
    'G'
    >>> chord = {'root': 'C', 'base': 'B'}
    >>> transpose_by_new_root(chord, 'G', 'F')
    >>> chord['base']
    'A'
    """
    to_key = _copy_key_to_new_root(from_key, to_root)
    half_steps = _note_to_half_steps(_get_root_from_key(from_key), to_root)
    for key in 'root', 'base':
        if key in chord.keys() and chord[key]:
            from_lookup = _lookup_from_key(from_key)
            from_i = from_lookup.index(chord[key])
            to_lookup = _lookup_from_key(to_key)
            to_i = (from_i + half_steps) % 12
            chord[key] = to_lookup[to_i]


def transpose_by_half_steps(chord, from_key, half_steps):
    """Doctest:
    >>> chord = {'root': 'F'}
    >>> transpose_by_half_steps(chord, 'E', 6)
    >>> chord['root']
    'B'
    """
    to_root = _half_steps_to_note(_get_root_from_key(from_key), half_steps, from_key)
    return transpose_by_new_root(chord, from_key, to_root)
