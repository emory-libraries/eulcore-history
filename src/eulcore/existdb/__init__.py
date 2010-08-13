# file existdb/__init__.py
# 
#   Copyright 2010 Emory University General Library
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

"""Interact with `eXist-db`_ XML databases.

This package provides classes to ease interaction with eXist XML databases.
It contains the following modules:

 * :mod:`eulcore.existdb.db` -- Connect to the database and query
 * :mod:`eulcore.existdb.query` -- Query :class:`~eulcore.xmlmap.XmlObject`
   models from eXist with semantics like a Django_ QuerySet

Django_ users may also be interested in the related package 
:mod:`eulcore.django.existdb`.

.. _eXist-db: http://exist.sourceforge.net/
.. _Django: http://www.djangoproject.com/

"""
