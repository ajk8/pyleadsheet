import funcy
from collections import namedtuple
# from . import constants

TimeSignature = namedtuple('TimeSignature', ['count', 'unit'])
ChordDuration = namedtuple('ChordDuration', ['count', 'unit'])


class MusicStr(str):

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
        """ Create the string instance with no special unicode characters

        .. doctests ::

            >>> MusicStr('a')
            MusicStr(a)
            >>> MusicStr('♭')
            MusicStr(b)
            >>> str(MusicStr('#'))
            '♯'
        """
        content = cls.from_unicode(content)
        return str.__new__(cls, content)

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, self.__class__.from_unicode(self))

    def __str__(self):
        return self.__class__.to_unicode(self)


class Note(MusicStr):

    def __new__(cls, content):
        """ Validate and create

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

    def __init__(self, content):
        """ Validate and create

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


Mode = namedtuple('Mode', ['name', 'step', 'shorthand'])


class Key(MusicStr):

    valid_modes = [
        Mode('Major', 1, ['']),
        Mode('Minor', 6, ['-'])
    ]

    def __init__(self, content):
        """ Validate and create

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

# class Measure(object):
#     def __init__(self, time_signature):
#         self.start_bar = self.end_bar = constants.BAR_SINGLE
#         self.start_note = self.end_note = ''
#         self.time = time_signature
#         self.args = []
#         self.subdivisions = []
