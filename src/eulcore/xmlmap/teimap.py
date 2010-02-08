from eulcore import xmlmap

class TeiDiv(xmlmap.XmlObject):
    id	 	= xmlmap.XPathString('@id')
    type	= xmlmap.XPathString('@type')
    author 	= xmlmap.XPathString('docAuthor')
    title 	= xmlmap.XPathString('@n')          # is this mapping relevant/valid/useful?
    # reference to top-level elements, e.g. for retrieving a single div
    doctitle    = xmlmap.XPathString('ancestor::TEI.2/teiHeader/fileDesc/titleStmt/title')
    doc_id      = xmlmap.XPathString('ancestor::TEI.2/@id')

# recursive mapping - can't be set until TeiDiv is declared
# NOTE: recursive node handling may need to be revisited
TeiDiv.div = xmlmap.XPathNodeList('div', TeiDiv)

class TeiSection(xmlmap.XmlObject):
    # top-level sections -- front/body/back
    div = xmlmap.XPathNodeList('div', TeiDiv)

class Tei(xmlmap.XmlObject):
    """xmlmap object for a TEI (Text Encoding Initiative) XML document """
    id   	= xmlmap.XPathString('@id')
    title 	= xmlmap.XPathString('teiHeader/fileDesc/titleStmt/title')
    author 	= xmlmap.XPathString('teiHeader/fileDesc/titleStmt/author')
    editor 	= xmlmap.XPathString('teiHeader/fileDesc/titleStmt/editor')

    front   = xmlmap.XPathNode('text/front', TeiSection)
    body    = xmlmap.XPathNode('text/body', TeiSection)
    back    = xmlmap.XPathNode('text/back', TeiSection)
    

