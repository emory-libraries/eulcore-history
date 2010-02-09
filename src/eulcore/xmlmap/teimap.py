from eulcore import xmlmap

# TODO: generic/base tei xml object with common attributes?

class TeiDiv(xmlmap.XmlObject):
    id	 	= xmlmap.XPathString('@id')
    type	= xmlmap.XPathString('@type')
    author 	= xmlmap.XPathString('docAuthor')
    title 	= xmlmap.XPathString('@n')          # is this mapping relevant/valid/useful?
    text    = xmlmap.XPathString('.')       # short-hand mapping for full text of a div (e.g., for short divs)
    # reference to top-level elements, e.g. for retrieving a single div
    doctitle    = xmlmap.XPathString('ancestor::TEI.2/teiHeader/fileDesc/titleStmt/title')
    doc_id      = xmlmap.XPathString('ancestor::TEI.2/@id')

# recursive mapping - can't be set until TeiDiv is declared
# NOTE: recursive node handling may need to be revisited
TeiDiv.div = xmlmap.XPathNodeList('div', TeiDiv)

class TeiSection(xmlmap.XmlObject):
    # top-level sections -- front/body/back
    div = xmlmap.XPathNodeList('div', TeiDiv)

# note: not currently mapped to any of the existing tei objects...  where to add?
class TeiFigure(xmlmap.XmlObject):
    entity      = xmlmap.XPathString("@entity")
    # TODO: ana should be a more generic attribute, common to many elements...
    ana         = xmlmap.XPathString("@ana")	# FIXME: how to split on spaces? should be a list...
    head        = xmlmap.XPathString("head")
    description = xmlmap.XPathString("figDesc")

# currently not mapped... should it be mapped by default? at what level?
class TeiInterp(xmlmap.XmlObject):
    id          = xmlmap.XPathString("@id")
    value       = xmlmap.XPathString("@value")

class TeiInterpGroup(xmlmap.XmlObject):
    type        = xmlmap.XPathString("@type")
    interp      = xmlmap.XPathNodeList("interp", TeiInterp)

class Tei(xmlmap.XmlObject):
    """xmlmap object for a TEI (Text Encoding Initiative) XML document """
    id   	= xmlmap.XPathString('@id')
    title 	= xmlmap.XPathString('teiHeader/fileDesc/titleStmt/title')
    author 	= xmlmap.XPathString('teiHeader/fileDesc/titleStmt/author')
    editor 	= xmlmap.XPathString('teiHeader/fileDesc/titleStmt/editor')

    front   = xmlmap.XPathNode('text/front', TeiSection)
    body    = xmlmap.XPathNode('text/body', TeiSection)
    back    = xmlmap.XPathNode('text/back', TeiSection)
    

