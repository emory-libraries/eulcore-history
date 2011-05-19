# eulcore documentation build configuration file

import eulcore

extensions = ['sphinx.ext.autodoc']

#templates_path = ['templates']
exclude_trees = ['build']
source_suffix = '.rst'
master_doc = 'index'

project = 'EULcore'
copyright = '2010, Emory University Libraries'
version = '%d.%d' % eulcore.__version_info__[:2]
release = eulcore.__version__
#modindex_common_prefix = ['eulcore.', 'eulcore.django.']
modindex_common_prefix = ['eulcore.']

pygments_style = 'sphinx'

html_style = 'default.css'
#html_static_path = ['static']
htmlhelp_basename = 'eulcoredoc'

latex_documents = [
  ('index', 'eulcore.tex', 'EULcore Documentation',
   'Emory University Libraries', 'manual'),
]
