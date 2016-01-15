import copy
from . import models


def transpose_chord_by_new_root(chord, from_key, to_root):
    """ Transpose an instance of models.Chord (in place) from one key to another

    Note: valid string representations of from_key and to_root are accepted, but
          not chord

    .. doctests ::

        >>> chord = models.Chord('c')
        >>> transpose_chord_by_new_root(chord, models.Key('C'), 'G')
        >>> chord.root
        Note(G)
        >>> chord = models.Chord('C/B')
        >>> transpose_chord_by_new_root(chord, models.Key('G'), 'F')
        >>> chord.base
        Note(A)

    :param chord: instance of models.Chord
    :param from_key: instance of models.Key
    :param to_root: instance of models.Note
    """
    to_root = models.Note(to_root)
    to_key = from_key.to_root(to_root)
    interval = models.Interval.from_notes(from_key.root, to_root)
    half_steps = interval.half_steps
    for attr_name in 'root', 'base':
        if hasattr(chord, attr_name):
            chord_part = getattr(chord, attr_name)
            if chord_part:
                chord_part = models.Note(chord_part)
                from_i = chord_part.chromatic_index
                to_i = (from_i + half_steps) % 12
                choices = to_key.note_lookup_list[to_i]
                for choice in choices:
                    if len(choice) == 1:
                        break
                setattr(chord, attr_name, choice)


def transpose_chord_by_half_steps(chord, from_key, half_steps):
    """ Transpose an instance of models.Chord (in place) from one key to another

    Note: valid string representations of from_key and to_root are accepted, but
          not chord

    .. doctests ::

        >>> chord = models.Chord('F')
        >>> transpose_chord_by_half_steps(chord, models.Key('E'), 6)
        >>> chord.root
        Note(B)

    :param chord: instance of models.Chord
    :param from_key: instance of models.Key
    :param half_steps: interval in half steps
    """
    to_chromatic_index = (from_key.root.chromatic_index + half_steps) % 12
    for note in models.Note.all()[to_chromatic_index]:
        try:
            from_key.to_root(note)
            return transpose_chord_by_new_root(chord, from_key, note)
        except ValueError:
            pass
    # should never get here!
    raise ValueError(
        'could not transpose {} by {} half steps based on {}'.format(chord, half_steps, from_key)
    )


def _transpose_progression_data_by_new_root(progression_data, from_key, to_root):
    for datum in progression_data:
        if 'group' in datum.keys():
            _transpose_progression_data_by_new_root(datum['progression'], from_key, to_root)
        elif 'chord' in datum.keys():
            transpose_chord_by_new_root(datum['chord'], from_key, to_root)


def _transpose_nonprogression_data_by_new_root(data, from_key, to_root):
    for key in ['comment']:
        if key in data.keys():
            for i in range(len(data[key])):
                if type(data[key][i]) == models.Chord:
                    transpose_chord_by_new_root(data[key][i], from_key, to_root)


def transpose_song_data_by_new_root(song_data, to_root):
    from_key = copy.deepcopy(song_data['key'])
    song_data['key'] = song_data['key'].to_root(to_root)
    for progression_data in song_data['progressions']:
        _transpose_progression_data_by_new_root(progression_data['chords'], from_key, to_root)
        _transpose_nonprogression_data_by_new_root(progression_data, from_key, to_root)
    for form_section in song_data['form']:
        _transpose_nonprogression_data_by_new_root(form_section, from_key, to_root)
