# file xmlmap/dc.py
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

class _BaseDublinCore(xmlmap.XmlObject):
    'Base Dublin Core class for common namespace declarations'
    ROOT_NS = 'http://www.openarchives.org/OAI/2.0/oai_dc/'
    ROOT_NAMESPACES = { 'oai_dc' : ROOT_NS,
                        'dc': 'http://purl.org/dc/elements/1.1/'}

class DublinCoreElement(_BaseDublinCore):
    'Generic Dublin Core element with access to element name and value'
    name = xmlmap.StringField('local-name(.)')
    value = xmlmap.StringField('.')

class DublinCore(_BaseDublinCore):
    """
    XmlObject for Simple (unqualified) Dublin Core metadata.

    If no node is specified when initialized, a new, empty Dublin Core
    XmlObject will be created.
    """    

    ROOT_NAME = 'dc'

    XSD_SCHEMA = "http://www.openarchives.org/OAI/2.0/oai_dc.xsd"
    xmlschema = xmlmap.loadSchema(XSD_SCHEMA)

    contributor = xmlmap.StringField("dc:contributor")
    contributor_list = xmlmap.StringListField("dc:contributor")

    coverage = xmlmap.StringField("dc:coverage")
    coverage_list = xmlmap.StringListField("dc:coverage")

    creator = xmlmap.StringField("dc:creator")
    creator_list = xmlmap.StringListField("dc:creator")

    date = xmlmap.StringField("dc:date")
    date_list = xmlmap.StringListField("dc:date")

    description = xmlmap.StringField("dc:description")
    description_list = xmlmap.StringListField("dc:description")

    format = xmlmap.StringField("dc:format")
    format_list = xmlmap.StringListField("dc:format")

    identifier = xmlmap.StringField("dc:identifier")
    identifier_list = xmlmap.StringListField("dc:identifier")

    language = xmlmap.StringField("dc:language")
    language_list = xmlmap.StringListField("dc:language")

    publisher = xmlmap.StringField("dc:publisher")
    publisher_list = xmlmap.StringListField("dc:publisher")

    relation = xmlmap.StringField("dc:relation")
    relation_list = xmlmap.StringListField("dc:relation")

    rights = xmlmap.StringField("dc:rights")
    rights_list = xmlmap.StringListField("dc:rights")

    source = xmlmap.StringField("dc:source")
    source_list = xmlmap.StringListField("dc:source")

    subject = xmlmap.StringField("dc:subject")
    subject_list = xmlmap.StringListField("dc:subject")

    title = xmlmap.StringField("dc:title")
    title_list = xmlmap.StringListField("dc:title")

    type = xmlmap.StringField("dc:type")
    type_list = xmlmap.StringListField("dc:type")

    elements = xmlmap.NodeListField('dc:*', DublinCoreElement)
    'list of all DC elements as instances of :class:`DublinCoreElement`'
