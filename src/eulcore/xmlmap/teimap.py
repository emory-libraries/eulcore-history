from eulcore import xmlmap

# TODO: generic/base tei xml object with common attributes?

class TeiDiv(xmlmap.XmlObject):
    id       = xmlmap.StringField('@id')
    type     = xmlmap.StringField('@type')
    author   = xmlmap.StringField('docAuthor')
    title    = xmlmap.StringField('@n')  # is this mapping relevant/valid/useful?
    text     = xmlmap.StringField('.')   # short-hand mapping for full text of a div (e.g., for short divs)
    # reference to top-level elements, e.g. for retrieving a single div
    doctitle = xmlmap.StringField('ancestor::TEI.2/teiHeader/fileDesc/titleStmt/title')
    doc_id   = xmlmap.StringField('ancestor::TEI.2/@id')
    div      = xmlmap.NodeListField('div', 'self')

class TeiSection(xmlmap.XmlObject):
    # top-level sections -- front/body/back
    div = xmlmap.NodeListField('div', TeiDiv)

# note: not currently mapped to any of the existing tei objects...  where to add?
class TeiFigure(xmlmap.XmlObject):
    entity      = xmlmap.StringField("@entity")
    # TODO: ana should be a more generic attribute, common to many elements...
    ana         = xmlmap.StringField("@ana")    # FIXME: how to split on spaces? should be a list...
    head        = xmlmap.StringField("head")
    description = xmlmap.StringField("figDesc")

# currently not mapped... should it be mapped by default? at what level?
class TeiInterp(xmlmap.XmlObject):
    id          = xmlmap.StringField("@id")
    value       = xmlmap.StringField("@value")

class TeiInterpGroup(xmlmap.XmlObject):
    type        = xmlmap.StringField("@type")
    interp      = xmlmap.NodeListField("interp", TeiInterp)

class Tei(xmlmap.XmlObject):
    """xmlmap object for a TEI (Text Encoding Initiative) XML document """
    id     = xmlmap.StringField('@id')
    title  = xmlmap.StringField('teiHeader/fileDesc/titleStmt/title')
    author = xmlmap.StringField('teiHeader/fileDesc/titleStmt/author')
    editor = xmlmap.StringField('teiHeader/fileDesc/titleStmt/editor')

    front  = xmlmap.NodeField('text/front', TeiSection)
    body   = xmlmap.NodeField('text/body', TeiSection)
    back   = xmlmap.NodeField('text/back', TeiSection)
    

