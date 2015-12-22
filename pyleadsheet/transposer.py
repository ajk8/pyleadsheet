import copy
from . import objects

SHARPS = [objects.Note(n) for n in [
    'A', 'A#', 'B', 'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#'
]]
FLATS = [objects.Note(n) for n in [
    'A', 'Bb', 'B', 'C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab'
]]
PREFER_FLATS = [objects.Note('F')]


def _lookup_from_note(note):
    """ Get the appropriate one of SHARPS or FLATS given an input note

    Note: valid string representations of a Note are also accepted

    .. doctests ::

        >>> _lookup_from_note(objects.Note('D')) == SHARPS
        True
        >>> _lookup_from_note(objects.Note('F')) == FLATS
        True
        >>> _lookup_from_note(objects.Note('Ab')) == FLATS
        True
        >>> _lookup_from_note('C#') == SHARPS
        True
        >>> _lookup_from_note('H')  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        ValueError: "H" is not a valid pyleadsheet note

    :param note: instance of objects.Note
    :rtype: list of objects.Note instances
    """
    note = objects.Note(note)
    if 'b' in note or note in PREFER_FLATS:
        return FLATS
    return SHARPS


def _get_relative_major(key):
    """ Take an instance of objects.Key and return its relative major

    Note: valid string representations of a Key are also accepted

    .. doctests ::

        >>> _get_relative_major(objects.Key('Bb-'))
        Key(Db)
        >>> _get_relative_major(objects.Key('F'))
        Key(F)
        >>> _get_relative_major('C-')
        Key(Eb)
        >>> _get_relative_major(objects.Key('A-'))
        Key(C)
        >>> _get_relative_major('zazzle')  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        ValueError: "z" is not a valid pyleadsheet note

    :param key: instance of objects.Key
    :rtype: objects.Key
    """
    key = objects.Key(key)
    if key.mode.step == 1:
        return key
    from_root = key.root
    from_lookup = _lookup_from_note(from_root)
    from_i = from_lookup.index(from_root)
    to_i = (from_i + 3) % 12
    to_lookup = FLATS
    to_root = to_lookup[to_i]
    return objects.Key(to_root)


def _get_enharmonic_equal_note(note):
    """ Take an instance of objects.Note and return its enharmonic equal

    Note: valid string representations of a Note are also accepted

    .. doctests ::

        >>> _get_enharmonic_equal_note(objects.Note('A#'))
        Note(Bb)
        >>> _get_enharmonic_equal_note(objects.Note('Gb'))
        Note(F#)
        >>> _get_enharmonic_equal_note('C')
        Note(C)
        >>> _get_enharmonic_equal_note('Cb')
        Note(B)
        >>> _get_enharmonic_equal_note('E#')
        Note(F)

    :param note: instance of objects.Note
    :rtype: objects.Note
    """
    note = objects.Note(note)
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


def _copy_key_to_new_root(from_key, to_root):
    """ Create a copy of from_key and re-anchor it at to_root

    Note: valid string representations of inputs are also accepted

    .. doctests ::

        >>> _copy_key_to_new_root(objects.Key('A'), 'B')
        Key(B)
        >>> _copy_key_to_new_root(objects.Key('Bb-'), objects.Note('C'))
        Key(C-)

    :param from_key: instance of objects.Key
    :param to_root: instance of objects.Note
    :rtype: objects.Key
    """
    from_key = objects.Key(from_key)
    to_root = objects.Note(to_root)
    ret = copy.deepcopy(from_key)
    ret.root = objects.Note(to_root)
    return ret


def _get_enharmonic_equal_key(key):
    """ Take and instance of objects.Key and return a copy anchored at the enharmonic
        equal of its root

    Note: valid string representations of Key are also accepted

    .. doctests ::

        >>> _get_enharmonic_equal_key(objects.Key('B'))
        Key(B)
        >>> _get_enharmonic_equal_key(objects.Key('A#-'))
        Key(Bb-)
        >>> _get_enharmonic_equal_key('C')
        Key(C)

    :param key: instance of objects.Key
    :rtype: objects.Key
    """
    key = objects.Key(key)
    to_root = _get_enharmonic_equal_note(key.root)
    return key if key.root == to_root else _copy_key_to_new_root(key, to_root)


def _lookup_from_key(key):
    """ Get the appropriate one of SHARPS or FLATS given an input key

    Note: valid string representations of Key are also accepted

    .. doctests ::

        >>> _lookup_from_key(objects.Key('G')) == SHARPS
        True
        >>> _lookup_from_key(objects.Key('C#-')) == SHARPS
        True
        >>> _lookup_from_key(objects.Key('Ab-'))  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        ValueError: A♭- is not a realistic key...

    :param key: instance of objects.Key
    :rtype: list of objects.Note instances
    """
    key = objects.Key(key)
    major_key = _get_relative_major(key)
    ret = _lookup_from_note(major_key)
    if 'b' in key and ret == SHARPS:
        raise ValueError('{0} is not a realistic key, you should use {1}'.format(
            key, _get_enharmonic_equal_key(key)
        ))
    return ret


def _note_interval_to_half_steps(from_note, to_note):
    """ Return the interval between two notes in half steps

    Note: valid string representations of inputs are also accepted

    .. doctests ::

        >>> _note_interval_to_half_steps(objects.Note('C#'), objects.Note('G'))
        6
        >>> _note_interval_to_half_steps('C#', objects.Note('Db'))
        0

    :param from_note: instance of objects.Note
    :param to_note: instance of objects.Note
    :rtype: int
    """
    from_note = objects.Note(from_note)
    to_note = objects.Note(to_note)
    from_i = SHARPS.index(from_note) if from_note in SHARPS else FLATS.index(from_note)
    to_i = SHARPS.index(to_note) if to_note in SHARPS else FLATS.index(to_note)
    return (to_i - from_i) % 12


def _half_steps_interval_to_note(from_note, half_steps, key):
    """ Take a note, number of half steps, and key, and calculate the note at that interval

    Note: valid string representations of inputs are also accepted

    .. doctests ::

        >>> _half_steps_interval_to_note('Ab', 4, objects.Key('F-'))
        Note(C)
        >>> _half_steps_interval_to_note('C', 7, objects.Key('F'))
        Note(G)

    :param from_note: instance of objects.Note
    :param half_steps: number of half steps to the target note
    :param key: key to calculate the interval in
    :rtype: objects.Note
    """
    lookup = _lookup_from_key(key)
    from_i = lookup.index(from_note)
    to_i = (from_i + half_steps) % 12
    return lookup[to_i]


def transpose_by_new_root(chord, from_key, to_root):
    """ Transpose an instance of objects.Chord (in place) from one key to another

    Note: valid string representations of from_key and to_root are accepted, but
          not chord

    .. doctests ::

        >>> chord = objects.Chord('c')
        >>> transpose_by_new_root(chord, objects.Key('C'), 'G')
        >>> chord.root
        Note(G)
        >>> chord = objects.Chord('C/B')
        >>> transpose_by_new_root(chord, objects.Key('G'), 'F')
        >>> chord.base
        Note(A)

    :param chord: instance of objects.Chord
    :param from_key: instance of objects.Key
    :param to_root: instance of objects.Note
    """
    from_key = objects.Key(from_key)
    to_root = objects.Note(to_root)
    to_key = _copy_key_to_new_root(from_key, to_root)
    half_steps = _note_interval_to_half_steps(from_key.root, to_root)
    for attr_name in 'root', 'base':
        if getattr(chord, attr_name):
            from_lookup = _lookup_from_key(from_key)
            from_i = from_lookup.index(getattr(chord, attr_name))
            to_lookup = _lookup_from_key(to_key)
            to_i = (from_i + half_steps) % 12
            setattr(chord, attr_name, to_lookup[to_i])


def transpose_by_half_steps(chord, from_key, half_steps):
    """ Transpose an instance of objects.Chord (in place) from one key to another

    Note: valid string representations of from_key and to_root are accepted, but
          not chord

    .. doctests ::

        >>> chord = objects.Chord('F')
        >>> transpose_by_half_steps(chord, objects.Key('E'), 6)
        >>> chord.root
        Note(B)

    :param chord: instance of objects.Chord
    :param from_key: instance of objects.Key
    :param half_steps: interval in half steps
    """
    to_root = _half_steps_interval_to_note(from_key.root, half_steps, from_key)
    return transpose_by_new_root(chord, from_key, to_root)
