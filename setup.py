from distutils.command.build_py import build_py
import os
import sys

from setuptools import setup

from eullocal import __version__

# fullsplit and packages calculation inspired by django setup.py

def fullsplit(path):
    result = []
    while path:
        path, tail = os.path.split(path)
        result.append(tail)
    result.reverse()
    return result

packages = []
for path, dirs, files in os.walk(__file__):
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

setup(
    name='eullocal',
    version=__version__,
    author='Emory University Libraries',
    author_email='libsysdev-l@listserv.cc.emory.edu',
    packages=packages,
    data_files=data_files,
    install_requires=[
        'django',
        'python-dateutil',
        'soaplib==0.8.1',
        # pypi soaplib links are dead as of 20101201. use direct link for
        # now: https://github.com/downloads/arskom/rpclib/soaplib-0.8.1.tar
        'python-ldap',
        'recaptcha-client',	# should this be required? 
    ],
)
