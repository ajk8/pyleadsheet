SHARPS = ['A', 'A#', 'B', 'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#']
FLATS = ['A', 'Bb', 'B', 'C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab']
PREFER_FLATS = ['D-', 'F']


def _lookup_from_key(key):
    if '#' in key:
        return SHARPS
    elif 'b' in key:
        return FLATS
    elif key in PREFER_FLATS:
        return FLATS
    return SHARPS


def _note_to_half_steps(from_note, to_note):
    from_i = SHARPS.index(from_note) if from_note in SHARPS else FLATS.index(from_note)
    to_i = SHARPS.index(to_note) if to_note in SHARPS else FLATS.index(to_note)
    return (to_i - from_i) % 12


def _half_steps_to_note(from_note, half_steps, key):
    lookup = _lookup_from_key(key)
    from_i = lookup.index(from_note)
    to_i = (from_i + half_steps) % 12
    return lookup[to_i]


def _get_note_from_key(key):
    return key.split('-')[0]


def _copy_key_to_new_root(from_key, to_root):
    return from_key.replace(_get_note_from_key(from_key), to_root)


def transpose_by_new_root(chord, from_key, to_root):
    to_key = _copy_key_to_new_root(from_key, to_root)
    half_steps = _note_to_half_steps(_get_note_from_key(from_key), to_root)
    for key in 'root', 'base':
        if key in chord.keys() and chord[key]:
            from_lookup = _lookup_from_key(from_key)
            from_i = from_lookup.index(chord[key])
            to_lookup = _lookup_from_key(to_key)
            to_i = (from_i + half_steps) % 12
            chord[key] = to_lookup[to_i]


def transpose_by_half_steps(chord, from_key, half_steps):
    to_root = _half_steps_to_note(_get_note_from_key(from_key), half_steps, from_key)
    return transpose_by_new_root(chord, from_key, to_root)


if __name__ == '__main__':
    for chord, key, half_steps in (
        ({'root': 'C'}, 'C', 4),
        ({'root': 'D#'}, 'C', 6),
        ({'root': 'Ab', 'base': 'Gb'}, 'Db-', 3),
        ({'root': 'C'}, 'D-', -3),
    ):
        transpose_by_half_steps(chord, key, half_steps)
