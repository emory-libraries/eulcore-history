# eulcore documentation build configuration file

import eulexistdb

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx']

#templates_path = ['templates']
exclude_trees = ['build']
source_suffix = '.rst'
master_doc = 'index'

project = 'EULexistdb'
copyright = '2011, Emory University Libraries'
version = '%d.%d' % eulexistdb.__version_info__[:2]
release = eulexistdb.__version__
modindex_common_prefix = ['eulexistdb.']

pygments_style = 'sphinx'

html_style = 'default.css'
#html_static_path = ['static']
htmlhelp_basename = 'eulcoredoc'

latex_documents = [
  ('index', 'eulcore.tex', 'EULexistdb Documentation',
   'Emory University Libraries', 'manual'),
]

# configuration for intersphinx: refer to the Python standard library, eulxml, django
intersphinx_mapping = {
    'http://docs.python.org/': None,
    'http://waterhouse.library.emory.edu:8080/hudson/job/eulxml/javadoc/': None,
    'http://docs.djangoproject.com/en/1.3/': 'http://docs.djangoproject.com/en/dev/_objects/',
}
