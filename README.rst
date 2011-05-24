EULcore history
===============

Before `eulxml <https://github.com/emory-libraries/eulxml>`_,
`eulfedora <https://github.com/emory-libraries/eulfedora>`_,
`eulexistdb <https://github.com/emory-libraries/eulexistdb>`_, and
`eulcommon <https://github.com/emory-libraries/eulcommon>`_ were split
apart for release, they were all developed in one larger module that
was internally known as **eulcore**.  This repository contains the
development history for each of those modules.

To view the development history for any of those modules, you will
need to get the code and then patch in the history as follows::

  git clone git://github.com/emory-libraries/eulxml.git
  cd eulxml
  git remote add history git://github.com/emory-libraries/eulcore-history.git
  git fetch history
  git replace history/eulxml history/eulxml-history

After this, operations such as ``git log`` will show the full
development history of the code.

These commands should work for any of **eulxml**, **eulfedora**,
**eulexistdb**, or **eulcommon**.  Simply replace every occurrence of
``eulxml`` in the example above with the repository you are working
with.


Contact Information
-------------------

**eulcore-history** was created by the Digital Programs and Systems Software
Team of `Emory University Libraries <http://web.library.emory.edu/>`_.
 
libsysdev-l@listserv.cc.emory.edu 


License
-------
**eulcore-history** is distributed under the Apache 2.0 License.
