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
        self.root = self.spec = self.base = ''

        if len(content) == 1:
            self.root = Note(content)
            return

        try:
            self.root = Note(content[:2])
            remainder = content[2:]
        except ValueError:
            self.root = Note(content[0])
            remainder = content[1:]

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

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, self._content)

    def __str__(self):
        return MusicStr.to_unicode(self._content)


# class Measure(object):
#     def __init__(self, time_signature):
#         self.start_bar = self.end_bar = constants.BAR_SINGLE
#         self.start_note = self.end_note = ''
#         self.time = time_signature
#         self.args = []
#         self.subdivisions = []
