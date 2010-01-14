from setuptools import setup
import os
import sys

sys.path.append('src')
from eulcore import __version__

# fullsplit and packages calculation inspired by django setup.py

def fullsplit(path):
    result = []
    while path:
        path, tail = os.path.split(path)
        result.append(tail)
    result.reverse()
    return result

srcdir = 'src' + os.path.sep
packages = []
for path, dirs, files in os.walk(srcdir + 'eulcore'):
    for i, dir in enumerate(dirs):
        if dir.startswith('.'):
            del dirs[i]
        if '__init__.py' in files:
            if path.startswith(srcdir): # it does
                packagedir = path[len(srcdir):]
            packages.append(packagedir.replace(os.path.sep, '.'))

setup(
    name='eulcore',
    version=__version__,
    author='Emory University Libraries',
    author_email='libsysdev-l@listserv.cc.emory.edu',
    packages=packages,
    package_dir={'': 'src'},
    package_data={'eulcore.django.existdb': ['exist_fixtures/*']},
)
