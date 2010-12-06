from distutils.command.build_py import build_py
import os
import sys

from setuptools import setup

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
for path, dirs, files in os.walk(srcdir):
    if path.startswith(srcdir): # it does
        path = path[len(srcdir):]
    if '.svn' in dirs:
        dirs.remove('.svn')
    if '__init__.py' in files:
        packages.append(path.replace(os.path.sep, '.'))

themedir = 'themes' + os.path.sep
data_files = []
for path, dirs, files in os.walk(themedir):
    if '.svn' in dirs:
        dirs.remove('.svn')
    if files:
        targetfiles = [os.path.join(path, f) for f in files]
        data_files.append((path, targetfiles))

class build_py_with_ply(build_py):
    def run(self, *args, **kwargs):
        # importing this forces ply to generate parsetab/lextab
        import eulcore.xpath.core
        build_py.run(self, *args, **kwargs)

setup(
    cmdclass={'build_py': build_py_with_ply},

    name='eulcore',
    version=__version__,
    author='Emory University Libraries',
    author_email='libsysdev-l@listserv.cc.emory.edu',
    packages=packages,
    package_dir={'': 'src'},
    package_data={
        'eulcore.django.existdb': ['exist_fixtures/*'],
        },
    data_files=data_files,
    install_requires=[
        'ply',
        'lxml',
        'django',
        'mimeparse',
        'rdflib>=3.0',
        'python-dateutil',
        'soaplib==0.8.1',
        # pypi soaplib links are dead as of 20101201. use direct link for
        # now: https://github.com/downloads/arskom/rpclib/soaplib-0.8.1.tar
        'python-ldap',
    ],
)
