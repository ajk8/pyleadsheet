import os
import logging
import datetime
from flask import Flask, render_template, url_for
from . import views
from . import parser

logger = logging.getLogger(__name__)
app = Flask(__name__)


def _filepath_to_shortstr(filepath):
    return '.'.join(os.path.basename(filepath).split('.')[:-1])


def _shortstr_to_filepath(from_shortstr):
    for filepath in app.song_files:
        filepath_shortstr = _filepath_to_shortstr(filepath)
        if filepath_shortstr == from_shortstr:
            return filepath
    raise ValueError('could not convert shortstr to filepath: ' + from_shortstr)


def _get_song_view_url(song_view_type, filepath):
    shortstr = _filepath_to_shortstr(filepath)
    return '/song/{shortstr}/{song_view_type}'.format(**locals())


def _amend_view_kwargs(view_kwargs):
    view_kwargs.update({
        'static_path': url_for('static', filename='pyleadsheet.css'),
        'timestamp': datetime.datetime.now()
    })
    return view_kwargs


@app.route('/', methods=['GET'])
def _serve_index():
    view_kwargs = views.compose_index_kwargs(app.song_files)
    for letter, songs in view_kwargs['songs_by_first_letter'].items():
        for song in songs:
            song['urls'] = []
            for song_view_type in view_kwargs['song_view_types']:
                song['urls'].append(_get_song_view_url(song_view_type, song['filepath']))
    return render_template('server_index.jinja2', **_amend_view_kwargs(view_kwargs))


@app.route('/song/<shortstr>/<song_view_type>', methods=['GET'])
def _serve_song(shortstr, song_view_type):
    filepath = _shortstr_to_filepath(shortstr)
    view_kwargs = views.compose_song_kwargs(filepath, song_view_type, 0, None)
    return render_template('song.jinja2', **_amend_view_kwargs(view_kwargs))


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