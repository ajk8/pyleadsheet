import copy
from . import models


def _note_interval_to_half_steps(from_note, to_note):
    """ Return the interval between two notes in half steps

    Note: valid string representations of inputs are also accepted

    .. doctests ::

        >>> _note_interval_to_half_steps(models.Note('C#'), models.Note('G'))
        6
        >>> _note_interval_to_half_steps('C#', models.Note('Db'))
        0

    :param from_note: instance of models.Note
    :param to_note: instance of models.Note
    :rtype: int
    """
    from_note = models.Note(from_note)
    to_note = models.Note(to_note)
    from_i = from_note.lookup_list.index(from_note)
    to_i = to_note.lookup_list.index(to_note)
    return (to_i - from_i) % 12


def _half_steps_interval_to_note(from_note, half_steps, key):
    """ Take a note, number of half steps, and key, and calculate the note at that interval

    Note: valid string representations of inputs are also accepted

    .. doctests ::

        >>> _half_steps_interval_to_note('Ab', 4, models.Key('F-'))
        Note(C)
        >>> _half_steps_interval_to_note('C', 7, models.Key('F'))
        Note(G)

    :param from_note: instance of models.Note
    :param half_steps: number of half steps to the target note
    :param key: key to calculate the interval in
    :rtype: models.Note
    """
    lookup = key.note_lookup_list
    from_i = lookup.index(from_note)
    to_i = (from_i + half_steps) % 12
    return lookup[to_i]


def transpose_by_new_root(chord, from_key, to_root):
    """ Transpose an instance of models.Chord (in place) from one key to another

    Note: valid string representations of from_key and to_root are accepted, but
          not chord

    .. doctests ::

        >>> chord = models.Chord('c')
        >>> transpose_by_new_root(chord, models.Key('C'), 'G')
        >>> chord.root
        Note(G)
        >>> chord = models.Chord('C/B')
        >>> transpose_by_new_root(chord, models.Key('G'), 'F')
        >>> chord.base
        Note(A)

    :param chord: instance of models.Chord
    :param from_key: instance of models.Key
    :param to_root: instance of models.Note
    """
    to_root = models.Note(to_root)
    to_key = from_key.to_root(to_root)
    half_steps = _note_interval_to_half_steps(from_key.root, to_root)
    for attr_name in 'root', 'base':
        if getattr(chord, attr_name):
            from_i = from_key.note_lookup_list.index(getattr(chord, attr_name))
            to_i = (from_i + half_steps) % 12
            setattr(chord, attr_name, to_key.note_lookup_list[to_i])


def transpose_by_half_steps(chord, from_key, half_steps):
    """ Transpose an instance of models.Chord (in place) from one key to another

    Note: valid string representations of from_key and to_root are accepted, but
          not chord

    .. doctests ::

        >>> chord = models.Chord('F')
        >>> transpose_by_half_steps(chord, models.Key('E'), 6)
        >>> chord.root
        Note(B)

    :param chord: instance of models.Chord
    :param from_key: instance of models.Key
    :param half_steps: interval in half steps
    """
    to_root = _half_steps_interval_to_note(from_key.root, half_steps, from_key)
    try:
        to_key = from_key.to_root(to_root)
    except ValueError:
        to_root = to_root.enharmonic_equal
    return transpose_by_new_root(chord, from_key, to_root)
