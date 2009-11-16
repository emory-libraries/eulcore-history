from setuptools import setup
import sys

sys.path.append('src')
from eulcore import __version__

setup(
    name='eulcore',
    version=__version__,
    author='Emory University Libraries',
    author_email='libsysdev-l@listserv.cc.emory.edu',
    packages=('eulcore',),
    package_dir={'': 'src'}
)
