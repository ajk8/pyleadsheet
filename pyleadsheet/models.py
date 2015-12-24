import funcy
import collections
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


Mode = collections.namedtuple('Mode', ['name', 'step', 'shorthand'])


class Key(MusicStr):
    """ Class representing a musical key

    .. doctests ::

        >>> Key('C-')
        Key(C-)
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
    """

    valid_modes = [
        Mode('Major', 1, ['']),
        Mode('Minor', 6, ['-'])
    ]

    def __init__(self, content):
        self._content = self.from_unicode(content)
        self.root, remainder = Note.split_str(content)
        self.mode = None
        for mode in self.__class__.valid_modes:
            if remainder in mode.shorthand:
                self.mode = mode
        if self.mode is None:
            raise ValueError('did not recognize mode of key "{}" ({})'.format(content, remainder))

    def _stitch_content(self):
        return self.root + self.mode.shorthand[0]

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, self.from_unicode(self._stitch_content()))

    def __str__(self):
        return self.to_unicode(self._stitch_content())


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
