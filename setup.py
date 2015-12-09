import re
import os
from setuptools import setup


def get_version():
    version_file = open(os.path.join('pyleadsheet', '__init__.py')).read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")

pkgversion = get_version()

setup(
    name='pyleadsheet',
    version=pkgversion,
    description='Generate pretty song leadsheets based on a concise definition file',
    author='Adam Kaufman',
    author_email='kaufman.blue@gmail.com',
    url='https://github.com/ajk8/pyleadsheet',
    download_url='https://github.com/ajk8/pyleadsheet/tarball/' + pkgversion,
    license='MIT',
    packages=['pyleadsheet'],
    entry_points={'console_scripts': ['pyleadsheet=pyleadsheet.main:main']},
    test_suite='tests',
    install_requires=[
        'docopt',
        'funcy',
        'pyyaml',
        'jinja2',
        'wkhtmltopdf-wrapper',
        'flask'
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4'
    ],
    keywords='music leadsheet songbook'
)
