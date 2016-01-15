import funcy
import collections
import string
from . import constants

TimeSignature = collections.namedtuple('TimeSignature', ['count', 'unit'])
ChordDuration = collections.namedtuple('ChordDuration', ['count', 'unit'])


class MusicStr(str):
    """ Class used for switching between unicode representations of musical
        symbols, and their common text counterparts

    .. doctests ::

        >>> MusicStr('a')
        MusicStr(a)
        >>> MusicStr('♭')
        MusicStr(b)
        >>> str(MusicStr('#'))
        '♯'
    """

    @classmethod
    def to_unicode(cls, content):
        """ Replace certain bare string characters with unicode characters

        .. doctests ::

            >>> MusicStr.to_unicode('a')
            'a'
            >>> MusicStr.to_unicode('b')
            '♭'
            >>> MusicStr.to_unicode('#')
            '♯'
            >>> MusicStr.to_unicode('♯')
            '♯'
        """
        return content.replace('b', u'\u266d').replace('#', u'\u266F')

    @classmethod
    def from_unicode(cls, content):
        """ Reverse effects of to_unicode

        .. doctests ::

            >>> MusicStr.from_unicode('a')
            'a'
            >>> MusicStr.from_unicode('♭')
            'b'
            >>> MusicStr.from_unicode('♯')
            '#'
            >>> MusicStr.from_unicode('#')
            '#'
        """
        return content.replace(u'\u266d', 'b').replace(u'\u266F', '#')

    def __new__(cls, content):
        content = cls.from_unicode(content)
        return str.__new__(cls, content)

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, self.__class__.from_unicode(self))

    def __str__(self):
        return self.__class__.to_unicode(self)


class Note(MusicStr):
    """ Class representing a musical note

    .. doctests ::

        >>> Note('C/')  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        ValueError: "C/" is not a valid...
        >>> Note('C#')
        Note(C#)
        >>> Note('H')  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        ValueError: "H" is not a valid...
        >>> str(Note('bb'))
        'B♭'
        >>> Note('Ab').lookup_list[-1][0]
        Note(Ab)
        >>> Note('C').lookup_list[-1][0]
        Note(G#)
    """

    _chromatic_index_map = collections.OrderedDict([
        ('A', 0), ('A#', 1), ('Bb', 1), ('B', 2), ('Cb', 2), ('B#', 3), ('C', 3),
        ('C#', 4), ('Db', 4), ('D', 5), ('D#', 6), ('Eb', 6), ('E', 7), ('Fb', 7),
        ('E#', 8), ('F', 8), ('F#', 9), ('Gb', 9), ('G', 10), ('G#', 11), ('Ab', 11)
    ])
    # _chromatic_index_map = collections.OrderedDict([
    #     ('A', 0), ('B', 2), ('C', 3), ('D', 5), ('E', 7), ('F', 8), ('G', 10)
    # ])

    def __new__(cls, content):
        content = cls.from_unicode(content)
        if not funcy.re_test(r'^[A-Ga-g][b#]?$', content):
            raise ValueError('"{0}" is not a valid pyleadsheet note'.format(content))
        content = content.capitalize()
        return str.__new__(cls, content)

    @classmethod
    def split_str(cls, content):
        """ Split a string into a Note object and a string containing the remainder

        .. doctests ::

            >>> Note.split_str('C#asdf')
            (Note(C#), 'asdf')
            >>> Note.split_str('')  # doctest: +ELLIPSIS
            Traceback (most recent call last):
                ...
            ValueError: "" is not a valid...
        """
        if len(content) == 1:
            return cls(content), ''
        try:
            ret = cls(content[:2])
            remainder = content[2:]
        except ValueError:
            ret = Note(content[:1])
            remainder = content[1:]
        return ret, remainder

    @classmethod
    def all(cls, flatten=False):
        """ Return a chromatic scale including all standard notes, starting with A

        .. doctests ::

            >>> Note.all()  # doctest: +NORMALIZE_WHITESPACE
            [[Note(A)], [Note(A#), Note(Bb)], [Note(B), Note(Cb)], [Note(B#), Note(C)],
             [Note(C#), Note(Db)], [Note(D)], [Note(D#), Note(Eb)], [Note(E), Note(Fb)],
             [Note(E#), Note(F)], [Note(F#), Note(Gb)], [Note(G)], [Note(G#), Note(Ab)]]
        """
        ret = []
        for note, index in cls._chromatic_index_map.items():
            if len(ret) == index:
                ret.append([cls(note)])
            else:
                ret[-1].append(cls(note))
        return ret

    @classmethod
    def sharps(cls):
        """ Return a chromatic scale of sharps, starting with A

        .. doctests ::

            >>> Note.sharps()  # doctest: +NORMALIZE_WHITESPACE
            [[Note(A)], [Note(A#)], [Note(B)], [Note(B#), Note(C)], [Note(C#)], [Note(D)],
             [Note(D#)], [Note(E)], [Note(E#), Note(F)], [Note(F#)], [Note(G)], [Note(G#)]]
        """
        ret = []
        for note, index in cls._chromatic_index_map.items():
            if 'b' not in note:
                if len(ret) == index:
                    ret.append([cls(note)])
                else:
                    ret[-1].append(cls(note))
        return ret

    @classmethod
    def flats(cls):
        """ Return a chromatic scale of flats, starting with A

        .. doctests ::

            >>> Note.flats()  # doctest: +NORMALIZE_WHITESPACE
            [[Note(A)], [Note(Bb)], [Note(B), Note(Cb)], [Note(C)], [Note(Db)], [Note(D)],
             [Note(Eb)], [Note(E), Note(Fb)], [Note(F)], [Note(Gb)], [Note(G)], [Note(Ab)]]
        """
        ret = []
        for note, index in cls._chromatic_index_map.items():
            if '#' not in note:
                if len(ret) == index:
                    ret.append([cls(note)])
                else:
                    ret[-1].append(cls(note))
        return ret

    @property
    def lookup_list(self):
        if 'b' in self or self == 'F':
            return self.flats()
        return self.sharps()

    @property
    def chromatic_index(self):
        """ Essentially a numeric value for a given note

        .. doctests ::

            >>> Note('C').chromatic_index
            3
        """
        return self._chromatic_index_map[self]

    @property
    def enharmonic_equivalent(self):
        """ Return the Note with the same chromatic_index as the current Note

        .. doctests ::

            >>> Note('A').enharmonic_equivalent  # doctest: +ELLIPSIS
            Traceback (most recent call last):
                ...
            ValueError: Note(A) has no enharmonic equivalent
            >>> Note('Eb').enharmonic_equivalent
            Note(D#)
        """
        notes = [k for k, v in self._chromatic_index_map.items() if v == self.chromatic_index]
        if len(notes) == 1:
            raise ValueError('{} has no enharmonic equivalent'.format(repr(self)))
        return Note(notes[1]) if notes[0] == self else Note(notes[0])


class Chord(object):
    """ Class representing a musical chord

    .. doctests ::

        >>> Chord('G')
        Chord(G)
        >>> Chord('Bb')
        Chord(Bb)
        >>> Chord('C#-7')
        Chord(C#-7)
        >>> Chord('$%#')  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        ValueError: "$" is not a valid...
        >>> Chord('C/#7/B')  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        ValueError: could not parse...too many "/"s
        >>> Chord('Asdlkfjoi/')  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        ValueError: could not parse...empty base
        >>> str(Chord('Ab-7/Gb'))
        'A♭-7/G♭'
    """

    def __init__(self, content):

        self._content = content
        self.spec = self.base = ''
        self.root, remainder = Note.split_str(content)
        if not remainder:
            return

        tokens = remainder.split('/')
        if len(tokens) > 2:
            raise ValueError(
                'could not parse "{}" as a chord: too many "/"s'.format(content)
            )
        elif len(tokens) == 2:
            if not tokens[1]:
                raise ValueError('could not parse "{}" as a chord: empty base'.format(content))
            self.base = Note(tokens[1])
        self.spec = MusicStr(tokens[0])

    def _stitch_content(self):
        ret = self.root + self.spec
        if self.base:
            ret = '/'.join((ret, self.base))
        return ret

    def __repr__(self):
        return '{}({})'.format(
            self.__class__.__name__, MusicStr.from_unicode(self._stitch_content())
        )

    def __str__(self):
        return MusicStr.to_unicode(self._stitch_content())


class Interval(object):
    """ Class representing a musical interval

    .. doctests ::

        >>> i1 = Interval(2, constants.MINOR)
        >>> i1
        Interval(minor 2)
        >>> i1.half_steps
        1
        >>> i2 = Interval.from_half_steps(1)
        >>> i1 == i2
        True
        >>> i3 = Interval(8, 'notreal')  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        ValueError: unsupported interval number: 8
        >>> i3 = Interval(6, 'notreal')  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        ValueError: unsupported interval modifier: 'notreal'
        >>> i3 = Interval(6, constants.MAJOR)
        >>> i3 != i2
        True
        >>> i3 > i2
        True
        >>> i2 < i3
        True
        >>> i1 + i2
        Interval(major 2)
        >>> i3 - i1
        Interval(minor 6)
    """
    _half_step_map = [
        [(1, constants.PERFECT)],
        [(2, constants.MINOR)],
        [(2, constants.MAJOR)],
        [(3, constants.MINOR)],
        [(3, constants.MAJOR)],
        [(4, constants.PERFECT)],
        [(4, constants.AUGMENTED), (5, constants.DIMINISHED)],
        [(5, constants.PERFECT)],
        [(6, constants.MINOR)],
        [(6, constants.MAJOR)],
        [(7, constants.MINOR)],
        [(7, constants.MAJOR)],
    ]

    def __init__(self, number, modifier):
        number = int(number)
        if number < 1 or number > 7:
            raise ValueError('unsupported interval number: ' + str(number))
        self.number = number
        supported_modifier = False
        for key in constants.MODIFIER_DISPLAY.keys():
            if modifier == key:
                supported_modifier = True
        if not supported_modifier:
            raise ValueError('unsupported interval modifier: ' + repr(modifier))
        self.modifier = modifier

    def __repr__(self):
        if self.number == 1:
            desc = 'unison'
        else:
            desc = ' '.join((
                constants.MODIFIER_DISPLAY[self.modifier]['long'],
                str(self.number)
            ))
        return '{}({})'.format(self.__class__.__name__, desc)

    @classmethod
    def from_half_steps(cls, half_steps):
        """ Create an Interval object from a number of half steps (1-11)

        .. doctests ::

            >>> Interval.from_half_steps(5)
            Interval(perfect 4)
            >>> Interval.from_half_steps(13)
            Interval(minor 2)
        """
        half_steps = half_steps % 12
        return cls(*cls._half_step_map[half_steps][0])

    @classmethod
    def from_notes(cls, first, second):
        """ Create an Interval object representing the distance between two notes

        .. doctests ::

            >>> Interval.from_notes(Note('C'), Note('D'))
            Interval(major 2)
            >>> Interval.from_notes(Note('Bb'), Note('Gb'))
            Interval(minor 6)
            >>> Interval.from_notes(Note('A'), Note('A'))
            Interval(unison)
        """
        half_steps = (second.chromatic_index - first.chromatic_index) % 12
        return Interval.from_half_steps(half_steps)

    @property
    def half_steps(self):
        for i in range(len(self._half_step_map)):
            for mapping in self._half_step_map[i]:
                if mapping[0] == self.number and mapping[1] == self.modifier:
                    return i
        raise ValueError('could not determine half steps based on interval ' + repr(self))

    def __eq__(self, other):
        if self.number == other.number and self.modifier == other.modifier:
            return True
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __gt__(self, other):
        if self.number > other.number:
            return True
        elif self.number == other.number and self.modifier > other.modifier:
            return True
        return False

    def __lt__(self, other):
        if not self.__eq__(other) and not self.__gt__(other):
            return True
        return False

    def __add__(self, other):
        return self.__class__.from_half_steps(self.half_steps + other.half_steps)

    def __sub__(self, other):
        return self.__class__.from_half_steps(self.half_steps - other.half_steps)


class Mode(object):
    """ Class representing a specific mode which can be rooted at any note

    .. doctests ::

        >>> Mode([], [])  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        ValueError: cannot instantiate a Mode with no half_steps_pattern
        >>> Mode([2, 2], [])  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        ValueError: cannot instantiate a Mode with no names
        >>> Mode([2, 2], ['stuff'])
        Mode(stuff)
        >>> major = Mode.Major
        >>> major
        Mode(Major)
        >>> ionian = Mode.Ionian
        >>> ionian == major
        True
        >>> ionian != major
        False
        >>> minor = Mode.Minor
        >>> ionian == minor
        False
        >>> ionian != minor
        True
    """

    # this will get filled in below
    _all_known_modes = []

    def __init__(self, half_steps_pattern, names, shorthand=None, ionian_interval=None):
        if not half_steps_pattern:
            raise ValueError('cannot instantiate a Mode with no half_steps_pattern')
        self.half_steps_pattern = half_steps_pattern
        if not names:
            raise ValueError('cannot instantiate a Mode with no names')
        self.names = names
        self.shorthand = shorthand or []
        self.ionian_interval = ionian_interval

    @property
    def name(self):
        return self.names[0]

    @classmethod
    def all(cls):
        return cls._all_known_modes

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, self.name)

    def __eq__(self, other):
        if self.half_steps_pattern == other.half_steps_pattern:
            return True
        return False

    def __ne__(self, other):
        if self.half_steps_pattern == other.half_steps_pattern:
            return False
        return True


known_modes = (
    ([2, 2, 1, 2, 2, 2, 1], ['Major', 'Ionian'], ['', 'M', 'maj'], 1),
    ([2, 1, 2, 2, 2, 1, 2], ['Dorian'], [], 2),
    ([1, 2, 2, 2, 1, 2, 2], ['Phrygian'], [], 3),
    ([2, 2, 2, 1, 2, 2, 1], ['Lydian'], [], 4),
    ([2, 2, 1, 2, 2, 1, 2], ['Mixolydian'], [], 5),
    ([2, 1, 2, 2, 1, 2, 2], ['Minor', 'Aeolian', 'Natural Minor'], ['-', 'm', 'min'], 6),
    ([1, 2, 2, 1, 2, 2, 2], ['Locrian'], [], 7)
)
for _pattern, _names, _shorthand, _interval in known_modes:
    for _name in _names:
        _property_name = _name.replace(' ', '_')
        setattr(Mode, _property_name, Mode(_pattern, _names, _shorthand, _interval))
        _mode_obj = getattr(Mode, _property_name)
        if not Mode._all_known_modes or _mode_obj != Mode._all_known_modes[-1]:
            Mode._all_known_modes.append(_mode_obj)


class Key(object):
    """ Class representing a musical key

    .. doctests ::

        >>> cmin = Key('C-')
        >>> cmin.relative_major
        Key(Eb)
        >>> cloc = Key('C', mode=Mode.Locrian)
        >>> cloc.relative_minor
        Key(Bb-)
        >>> Key('C#notamode')  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        ValueError: did not recognize mode...
        >>> key = Key('G')
        >>> key.mode.name
        'Major'
        >>> key.root = 'A'
        >>> str(key)
        'A'
        >>> Key('G').to_root('D')
        Key(D)
    """

    def __init__(self, content, mode=None):
        self._content = MusicStr.from_unicode(content)
        self.root, remainder = Note.split_str(content)
        if remainder and mode:
            raise ValueError('could not construct key "{}" with mode "{}"'.format(content, mode))
        elif not mode:
            self.mode = None
            for mode in Mode.all():
                if remainder in mode.shorthand:
                    self.mode = mode
            if self.mode is None:
                raise ValueError('did not recognize mode of key "{}" ({})'.format(content, remainder))
        else:
            self.mode = mode

        for lookup in (Note.sharps(), Note.flats()):
            self.note_lookup_list = lookup
            self.diatonic_notes = self._find_diatonic_notes_in_lookup(lookup)
            if self.diatonic_notes:
                break
        if not self.diatonic_notes:
            raise ValueError('{} is not a realistic key, try rooting at {}'.format(
                self, self.root.enharmonic_equivalent
            ))

    def _find_diatonic_notes_in_lookup(self, note_lookup_list):
        """ Return a flat list of the notes in the key

        .. doctests :::

            >>> Key('C')._find_diatonic_notes_in_lookup(Note.sharps())
            [Note(C), Note(D), Note(E), Note(F), Note(G), Note(A), Note(B)]
            >>> Key('C')._find_diatonic_notes_in_lookup(Note.flats())
            [Note(C), Note(D), Note(E), Note(F), Note(G), Note(A), Note(B)]
            >>> Key('Gb')._find_diatonic_notes_in_lookup(Note.sharps())
            >>> Key('Gb')._find_diatonic_notes_in_lookup(Note.flats())
            [Note(Gb), Note(Ab), Note(Bb), Note(Cb), Note(Db), Note(Eb), Note(F)]
            >>> Key('C-')._find_diatonic_notes_in_lookup(Note.flats())
            [Note(C), Note(D), Note(Eb), Note(F), Note(G), Note(Ab), Note(Bb)]
        """
        ret = []
        current_note = self.root
        next_note_i = self.root.chromatic_index
        for half_steps in self.mode.half_steps_pattern:
            ret.append(current_note)
            current_letter_i = string.ascii_uppercase.find(current_note[0])
            next_note_i = (next_note_i + half_steps) % 12
            for next_note in (note_lookup_list[next_note_i]):
                good_note = False
                next_letter_i = string.ascii_uppercase.find(next_note[0])
                if next_letter_i - current_letter_i in (1, -6):
                    good_note = True
                    break
            if not good_note:
                return None
            current_note = next_note
        return ret

    def _stitch_content(self):
        ret = self.root
        if self.mode.shorthand:
            ret += self.mode.shorthand[0]
        else:
            ret += ':' + self.mode.name
        return ret

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, MusicStr.from_unicode(self._stitch_content()))

    def __str__(self):
        return MusicStr.to_unicode(self._stitch_content())

    def to_root(self, new_root):
        return Key(new_root, mode=self.mode)

    @property
    def relative_major(self):
        if self.mode.ionian_interval is None:
            raise AttributeError('{} does not have a relative major'.format(self))
        ionian_interval_z = self.mode.ionian_interval - 1
        new_root = self.diatonic_notes[(0 - ionian_interval_z) % 7]
        return Key(new_root)

    @property
    def relative_minor(self):
        if self.mode.ionian_interval is None:
            raise AttributeError('{} does not have a relative minor'.format(self))
        ionian_interval_z = self.mode.ionian_interval - 1
        new_root = self.diatonic_notes[(5 - ionian_interval_z) % 7]
        return Key(new_root, mode=Mode.Aeolian)

    @property
    def transposable_roots(self):
        """ A list of all roots to which this key can reasonably be transposed

        .. doctests ::

            >>> Key('D').transposable_roots  # doctest: +NORMALIZE_WHITESPACE
            [Note(A), Note(Bb), Note(B), Note(Cb), Note(C), Note(C#), Note(Db), Note(D),
             Note(Eb), Note(E), Note(F), Note(F#), Note(Gb), Note(G), Note(Ab)]
            >>> Key('C-').transposable_roots  # doctest: +NORMALIZE_WHITESPACE
            [Note(A), Note(A#), Note(Bb), Note(B), Note(C), Note(C#), Note(D), Note(D#),
             Note(Eb), Note(E), Note(F), Note(F#), Note(G), Note(G#), Note(Ab)]
        """
        ret = []
        for chromatic_index in range(12):
            for note in Note.all()[chromatic_index]:
                try:
                    self.to_root(note)
                    ret.append(note)
                except ValueError:
                    pass
        return ret


class Subdivision(object):
    """ Class representing a subdivision of a measure

    .. doctests ::

        >>> Subdivision()
        Subdivision(empty)
        >>> Subdivision(optional=True)
        Subdivision(empty)
        >>> Subdivision('x')
        Subdivision('x')
        >>> Subdivision(Chord('G'), optional=True)
        Subdivision(?Chord(G))
        >>> Subdivision(Chord('A')).content
        Chord(A)
    """

    def __init__(self, content=None, optional=False):
        self.content = content
        self.optional = optional

    def __repr__(self):
        return '{}({}{})'.format(
            self.__class__.__name__,
            '?' if self.optional and self.content else '',
            repr(self.content) if self.content else 'empty'
        )


class Measure(object):
    """ Class representing a leadsheet measure

    .. doctests ::

        >>> m = Measure(8, Chord('C'))
        >>> m
        Measure(8)
        >>> m.subdivisions  # doctest: +NORMALIZE_WHITESPACE
        [Subdivision(Chord(C)), Subdivision(empty), Subdivision(empty), Subdivision(empty),
         Subdivision(empty), Subdivision(empty), Subdivision(empty), Subdivision(empty)]
        >>> m.set_next_subdivision(Chord('G'))
        >>> m[1]
        Subdivision(Chord(G))
        >>> m[4] = Chord('D')
        >>> m.subdivisions  # doctest: +NORMALIZE_WHITESPACE
        [Subdivision(Chord(C)), Subdivision(Chord(G)), Subdivision(empty), Subdivision(empty),
         Subdivision(Chord(D)), Subdivision(empty), Subdivision(empty), Subdivision(empty)]
        >>> del(m[1])
        >>> m.set_next_subdivision(Chord('G'), optional=True)
        >>> m.subdivisions  # doctest: +NORMALIZE_WHITESPACE
        [Subdivision(Chord(C)), Subdivision(empty), Subdivision(empty), Subdivision(empty),
         Subdivision(Chord(D)), Subdivision(?Chord(G)), Subdivision(empty), Subdivision(empty)]
        >>> m.subdivisions[5].optional
        True
        >>> m[0].optional
        False
        >>> m[0].content
        Chord(C)
        >>> for c in m:
        ...     c
        ...     break
        Subdivision(Chord(C))
        >>> m[8] = Chord('C')  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        IndexError: too many subdivisions (9)
    """

    def __init__(self, length, first_subdivision=None):
        self.start_bar = self.end_bar = constants.BAR_SINGLE
        self.start_note = self.end_note = ''
        self.args = []
        self.subdivisions = [Subdivision()] * length
        self._length = length
        self._last_next_i = 0
        if first_subdivision:
            self.set_next_subdivision(first_subdivision)

    def __len__(self):
        return self._length

    def __getitem__(self, i):
        return self.subdivisions[i]

    def __delitem__(self, i):
        self.subdivisions[i] = Subdivision()

    def _check_for_too_many_subdivisions(self, i):
        if i >= len(self):
            raise IndexError('too many subdivisions ({})'.format(i + 1))

    def __setitem__(self, i, v, optional=False):
        self._check_for_too_many_subdivisions(i)
        if type(v) != Subdivision:
            v = Subdivision(v)
        if optional:
            v.optional = True
        self.subdivisions[i] = v
        self._last_next_i = i + 1

    def set_next_subdivision(self, v, optional=False):
        self.__setitem__(self._last_next_i, v, optional=optional)

    def __iter__(self):
        for c in self.subdivisions:
            yield c

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, len(self))
