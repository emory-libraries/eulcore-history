# eulcore documentation build configuration file

import eullocal

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx']

#templates_path = ['templates']
exclude_trees = ['build']
source_suffix = '.rst'
master_doc = 'index'

project = 'EULlocal'
copyright = '2010, Emory University Libraries'
version = '%d.%d' % eullocal.__version_info__[:2]
release = eullocal.__version__
modindex_common_prefix = ['eullocal.']

pygments_style = 'sphinx'

html_style = 'default.css'
#html_static_path = ['static']
htmlhelp_basename = 'eulcoredoc'

latex_documents = [
  ('index', 'eulcore.tex', 'EULlocal Documentation',
   'Emory University Libraries', 'manual'),
]


# configuration for intersphinx: refer to the Python standard library, eulxml, django
intersphinx_mapping = {
    'http://docs.python.org/': None,
    'http://docs.djangoproject.com/en/1.3/ref/': 'http://docs.djangoproject.com/en/dev/_objects/',
    'http://waterhouse.library.emory.edu:8080/hudson/job/eulxml/javadoc/': None,
    'http://waterhouse.library.emory.edu:8080/hudson/job/eulfedora/javadoc/': None,
#    'http://waterhouse.library.emory.edu:8080/hudson/job/eulexistdb/javadoc/': None,
#    'http://waterhouse.library.emory.edu:8080/hudson/job/eulcommon/javadoc/': None,
}
