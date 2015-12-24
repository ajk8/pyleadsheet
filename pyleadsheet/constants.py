import collections

DURATION_UNIT_MEASURE = 'm'
DURATION_UNIT_BEAT = 'b'
DURATION_UNIT_HALFBEAT = 'h'

BAR_SINGLE = 'bar_0_single.png'
BAR_DOUBLE = 'bar_1_double.png'
BAR_SECTION_OPEN = 'bar_2_section_open.png'
BAR_SECTION_CLOSE = 'bar_3_section_close.png'
BAR_REPEAT_OPEN = 'bar_4_repeat_open.png'
BAR_REPEAT_CLOSE = 'bar_5_repeat_close.png'

REST = '[x]'
RIFF = '&lt;riff&gt;'
FLAT = '&#9837;'
SHARP = '&#9839;'

ARG_ROW_BREAK = '/'

DIMINISHED = 1
MINOR = 2
PERFECT = 3
MAJOR = 4
AUGMENTED = 5
# ModifierDisplay = collections.namedtuple('ModifierDisplay', ('symbol', 'char', 'short', 'long'))
MODIFIER_DISPLAY = {
    MAJOR: collections.OrderedDict({
        'symbol': None,
        'char': 'M',
        'short': 'maj',
        'long': 'major'
    }),
    MINOR: collections.OrderedDict({
        'symbol': '-',
        'char': 'm',
        'short': 'min',
        'long': 'minor'
    }),
    DIMINISHED: collections.OrderedDict({
        'symbol': '⚪',
        'char': None,
        'short': 'dim',
        'long': 'diminished'
    }),
    AUGMENTED: collections.OrderedDict({
        'symbol': '+',
        'char': None,
        'short': 'aug',
        'long': 'augmented'
    }),
    PERFECT: collections.OrderedDict({
        'symbol': None,
        'char': None,
        'short': None,
        'long': 'perfect'
    })
}
