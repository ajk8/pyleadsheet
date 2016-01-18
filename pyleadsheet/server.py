import os
import logging
from flask import Flask, render_template, request
from . import views

logger = logging.getLogger(__name__)
app = Flask(__name__)


def _filepath_to_shortstr(filepath):
    """ Take a path and return the filename without any extension

    .. doctests ::

        >>> _filepath_to_shortstr('/path/to/some.file')
        'some'
    """
    return '.'.join(os.path.basename(filepath).split('.')[:-1])


def _shortstr_to_filepath(from_shortstr):
    """ Take a filename with no extension, and return the path, which has previously
        been loaded into app.song_files

    .. doctests ::

        >>> monkeypatch = getfixture('monkeypatch')
        >>> monkeypatch.setattr(app, 'song_files', ['/path/to/some.file'], raising=False)
        >>> _shortstr_to_filepath('some')
        '/path/to/some.file'
        >>> _shortstr_to_filepath('other')  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        ValueError: could not convert shortstr to filepath: other
    """
    for filepath in app.song_files:
        filepath_shortstr = _filepath_to_shortstr(filepath)
        if filepath_shortstr == from_shortstr:
            return filepath
    raise ValueError('could not convert shortstr to filepath: ' + from_shortstr)


def _get_song_view_url(song_view_type, filepath):
    """ Generate a URL endpoint for serving a song based the path to a source file

    .. doctests ::

        >>> _get_song_view_url('complete', '/path/to/some.file')
        '/song/some/complete'
    """
    shortstr = _filepath_to_shortstr(filepath)
    return '/song/{shortstr}/{song_view_type}'.format(**locals())


@app.route('/', methods=['GET'])
def _serve_index():
    view_kwargs = views.compose_index_kwargs(app.song_files)
    for letter, songs in view_kwargs['songs_by_first_letter'].items():
        for song in songs:
            song['urls'] = []
            for song_view_type in view_kwargs['song_view_types']:
                song['urls'].append(_get_song_view_url(song_view_type, song['filepath']))
    return render_template('server_index.jinja2', **view_kwargs)


@app.route('/song/<shortstr>/<song_view_type>', methods=['GET', 'POST'])
def _serve_song(shortstr, song_view_type):
    filepath = _shortstr_to_filepath(shortstr)
    transpose_root = request.form.get('transpose_root', None)
    condense_measures = True if request.form.get('condense_measures', None) == 'true' else False
    view_kwargs = views.compose_song_kwargs(
        filepath, song_view_type, transpose_root, condense_measures
    )
    return render_template('song.jinja2', **view_kwargs)


@app.before_request
def _load_files():
    if not hasattr(app, 'song_files'):
        setattr(app, 'song_files', None)
    filenames = [x for x in os.listdir(app.song_files_dir) if x.endswith('yaml')]
    app.song_files = [
        os.path.join(app.song_files_dir, filename) for filename in filenames
    ]


def run(input_dir, debug=False):
    setattr(app, 'song_files_dir', os.path.abspath(input_dir))
    app.run(debug=debug)
