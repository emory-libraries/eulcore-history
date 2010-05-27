from eulcore import xmlmap

class DublinCore(xmlmap.XmlObject):
    """
    XmlObject for Simple (unqualified) Dublin Core metadata.

    If no domnode is specified when initialized, a new, empty Dublin Core
    XmlObject will be created.
    """    

    ROOT_NS = 'http://www.openarchives.org/OAI/2.0/oai_dc/'
    ROOT_NAME = 'dc'
    ROOT_NAMESPACES = { 'oai_dc' : ROOT_NS,
                        'dc': 'http://purl.org/dc/elements/1.1/'}
    
    # schema not used yet...
    schema = "http://dublincore.org/schemas/xmls/simpledc20021212.xsd"

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
