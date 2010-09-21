# file xmlmap/teimap.py
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

from eulcore import xmlmap

# TODO: generic/base tei xml object with common attributes?

TEI_NAMESPACE = 'http://www.tei-c.org/ns/1.0'

class _TeiBase(xmlmap.XmlObject):
    '''Common TEI namespace declarations, for use by all TEI XmlObject instances.'''
    ROOT_NS = TEI_NAMESPACE
    ROOT_NAME = 'tei'
    ROOT_NAMESPACES = {
        'tei' : ROOT_NS,
    }

class TeiLine(_TeiBase):
    rend        = xmlmap.StringField("@rend")

    """set up indents for lines with @rend=indent or @rend=indent plus some number"""
    def indent(self):
        if self.rend.startswith("indent"):
            indentation = self.rend[len("indent"):]
            if indentation:
                return int(indentation)
            else:
                return 0
            
class TeiQuote(_TeiBase):
    line    = xmlmap.NodeListField('tei:l', TeiLine)

class TeiEpigraph(_TeiBase):
    quote = xmlmap.NodeListField('tei:q|tei:quote', TeiQuote)

class TeiLineGroup(_TeiBase):
    head        = xmlmap.StringField('tei:head')
    linegroup   = xmlmap.NodeListField('tei:lg', 'self')
    line        = xmlmap.NodeListField('tei:l', TeiLine)

class TeiDiv(_TeiBase):
    id       = xmlmap.StringField('@xml:id')
    type     = xmlmap.StringField('@type')
    author   = xmlmap.StringField('tei:docAuthor')
    title    = xmlmap.StringField('@n')  # is this mapping relevant/valid/useful?
    text     = xmlmap.StringField('.')   # short-hand mapping for full text of a div (e.g., for short divs)
    # reference to top-level elements, e.g. for retrieving a single div
    doctitle = xmlmap.StringField('ancestor::tei:TEI/tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:title')
    doc_id   = xmlmap.StringField('ancestor::tei:TEI/@xml:id')
    head     = xmlmap.StringField('tei:head')
    linegroup = xmlmap.NodeListField('tei:lg', TeiLineGroup)
    div      = xmlmap.NodeListField('tei:div', 'self')
    byline   = xmlmap.StringField('tei:byline')

class TeiSection(_TeiBase):
    # top-level sections -- front/body/back
    div = xmlmap.NodeListField('tei:div', TeiDiv)

# note: not currently mapped to any of the existing tei objects...  where to add?
class TeiFigure(_TeiBase):
    entity      = xmlmap.StringField("@entity")
    # TODO: ana should be a more generic attribute, common to many elements...
    ana         = xmlmap.StringField("@ana")    # FIXME: how to split on spaces? should be a list...
    head        = xmlmap.StringField("tei:head")
    description = xmlmap.StringField("tei:figDesc")

# currently not mapped... should it be mapped by default? at what level?
class TeiInterp(_TeiBase):
    id          = xmlmap.StringField("@xml:id")
    value       = xmlmap.StringField("@value")

class TeiInterpGroup(_TeiBase):
    type        = xmlmap.StringField("@type")
    interp      = xmlmap.NodeListField("tei:interp", TeiInterp)

class Tei(_TeiBase):
    """xmlmap object for a TEI (Text Encoding Initiative) XML document """
    id     = xmlmap.StringField('@xml:id')
    title  = xmlmap.StringField('tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:title')
    author = xmlmap.StringField('tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:author/tei:name/tei:choice/tei:sic')
    editor = xmlmap.StringField('tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:editor/tei:name/tei:choice/tei:sic')

    front  = xmlmap.NodeField('tei:text/tei:front', TeiSection)
    body   = xmlmap.NodeField('tei:text/tei:body', TeiSection)
    back   = xmlmap.NodeField('tei:text/tei:back', TeiSection)

