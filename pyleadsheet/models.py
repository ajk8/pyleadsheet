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
        >>> Note('Ab').lookup_list[-1]
        Note(Ab)
        >>> Note('C').lookup_list[-1]
        Note(G#)
    """

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
    def all(cls):
        """ Return a list of all standard notes

        .. doctests ::

            >>> Note.all()  # doctest: +NORMALIZE_WHITESPACE
            [Note(Ab), Note(A), Note(A#), Note(Bb), Note(B), Note(C), Note(C#), Note(Db), Note(D),
             Note(D#), Note(Eb), Note(E), Note(F), Note(F#), Note(Gb), Note(G), Note(G#)]
        """
        all_notes = []
        for letter in ('A', 'B', 'C', 'D', 'E', 'F', 'G'):
            if letter not in ('C', 'F'):
                all_notes.append(cls(letter + 'b'))
            all_notes.append(cls(letter))
            if letter not in ('B', 'E'):
                all_notes.append(cls(letter + '#'))
        return all_notes

    @classmethod
    def sharps(cls):
        """ Return a chromatic scale of sharps, starting with A

        .. doctests ::

            >>> Note.sharps()  # doctest: +NORMALIZE_WHITESPACE
            [Note(A), Note(A#), Note(B), Note(C), Note(C#), Note(D),
             Note(D#), Note(E), Note(F), Note(F#), Note(G), Note(G#)]
        """
        sharps = []
        for note in cls.all():
            if 'b' not in note:
                sharps.append(note)
        return sharps

    @classmethod
    def flats(cls):
        """ Return a chromatic scale of sharps, starting with A

        .. doctests ::

            >>> Note.flats()  # doctest: +NORMALIZE_WHITESPACE
            [Note(A), Note(Bb), Note(B), Note(C), Note(Db), Note(D),
             Note(Eb), Note(E), Note(F), Note(Gb), Note(G), Note(Ab)]
        """
        flats = []
        for note in cls.all():
            if '#' not in note:
                flats.append(note)
        flats.append(flats.pop(0))
        return flats

    @property
    def lookup_list(self):
        if 'b' in self or self == 'F':
            return self.flats()
        return self.sharps()

    @property
    def lookup_list_index(self):
        for i in range(len(self.lookup_list)):
            if self == self.lookup_list[i]:
                return i

    @property
    def enharmonic_equal(self):
        if self.sharps()[self.lookup_list_index] == self:
            return self.flats()[self.lookup_list_index]
        return self.sharps()[self.lookup_list_index]


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
        >>> i3 = Interval(0, 'notreal')  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        ValueError: unsupported interval number: 0
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
        [('unison', constants.PERFECT)],
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
        if number < 2 or number > 7:
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
        return '{}({} {})'.format(
            self.__class__.__name__, constants.MODIFIER_DISPLAY[self.modifier]['long'], self.number
        )

    @classmethod
    def from_half_steps(cls, half_steps):
        if half_steps < 1 or half_steps > 11:
            raise ValueError('could not determine interval of {} half steps'.format(half_steps))
        return cls(*cls._half_step_map[half_steps][0])

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

        self.note_lookup_list = None
        if self._validate_against_lookup_list(Note.sharps()):
            self.note_lookup_list = Note.sharps()
        elif self._validate_against_lookup_list(Note.flats()):
            self.note_lookup_list = Note.flats()
        if not self.note_lookup_list:
            raise ValueError('{} is not a realistic key, try rooting at {}'.format(
                self, self.root.enharmonic_equal
            ))

    def _validate_against_lookup_list(self, note_lookup_list):
        current_note = self.root
        next_note_i = self.root.lookup_list_index
        for half_steps in self.mode.half_steps_pattern:
            current_letter_i = string.ascii_uppercase.find(current_note[0])
            next_note_i = (next_note_i + half_steps) % 12
            next_note = note_lookup_list[next_note_i]
            next_letter_i = string.ascii_uppercase.find(next_note[0])
            if next_letter_i - current_letter_i not in (1, -6):
                return False
            current_note = next_note
        return True

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
        diff = self.mode.ionian_interval - 1
        half_steps = sum(Mode.Major.half_steps_pattern[:diff])
        new_root = self.note_lookup_list[(self.root.lookup_list_index - half_steps) % 12]
        return Key(new_root)

    @property
    def relative_minor(self):
        if self.mode.ionian_interval is None:
            raise AttributeError('{} does not have a relative minor'.format(self))
        diff = 1 if self.mode.ionian_interval == 7 else self.mode.ionian_interval + 1
        half_steps = sum(Mode.Minor.half_steps_pattern[:diff])
        new_root = self.note_lookup_list[(self.root.lookup_list_index - half_steps) % 12]
        return Key('{}-'.format(new_root))

    @property
    def transposable_roots(self):
        ret = []
        for root in Note.all():
            try:
                self.to_root(root)
                ret.append(root)
            except ValueError:
                print(root)
                pass
        return ret


class Measure(object):
    """ Class representing a leadsheet measure

    .. doctests ::

        >>> m = Measure(8, Chord('C'))
        >>> m
        Measure(8)
        >>> m.subdivisions
        [Chord(C), '', '', '', '', '', '', '']
        >>> m.set_next_subdivision(Chord('G'))
        >>> m[1]
        Chord(G)
        >>> m[4] = Chord('D')
        >>> m.subdivisions
        [Chord(C), Chord(G), '', '', Chord(D), '', '', '']
        >>> del(m[1])
        >>> m.set_next_subdivision(Chord('G'))
        >>> m.subdivisions
        [Chord(C), '', '', '', Chord(D), Chord(G), '', '']
        >>> for c in m:
        ...     c
        ...     break
        Chord(C)
        >>> m[8] = Chord('C')  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        IndexError: too many subdivisions (9)
    """

    def __init__(self, length, first_subdivision=None):
        self.start_bar = self.end_bar = constants.BAR_SINGLE
        self.start_note = self.end_note = ''
        self.args = []
        self.subdivisions = [''] * length
        self._length = length
        self._last_next_i = 0
        if first_subdivision:
            self.set_next_subdivision(first_subdivision)

    def __len__(self):
        return self._length

    def __getitem__(self, i):
        return self.subdivisions[i]

    def __delitem__(self, i):
        self.subdivisions[i] = ''

    def _check_for_too_many_subdivisions(self, i):
        if i >= len(self):
            raise IndexError('too many subdivisions ({})'.format(i + 1))

    def __setitem__(self, i, v):
        self._check_for_too_many_subdivisions(i)
        self.subdivisions[i] = v
        self._last_next_i = i + 1

    def set_next_subdivision(self, v):
        self.__setitem__(self._last_next_i, v)

    def __iter__(self):
        for c in self.subdivisions:
            yield c

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, len(self))
