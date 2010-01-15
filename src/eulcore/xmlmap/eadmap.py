from eulcore import xmlmap

class ead(xmlmap.XmlObject):
    """xmlmap object for an EAD (Encoded Archival Description) Finding Aid"""
    title 	= xmlmap.XPathString('eadheader/filedesc/titlestmt/titleproper')
    author 	= xmlmap.XPathString('eadheader/filedesc/titlestmt/author')
    unittitle 	= xmlmap.XPathString('archdesc[@level="collection"]/did/unittitle')
    physical_desc = xmlmap.XPathString('archdesc[@level="collection"]/did/physdesc')
    abstract    = xmlmap.XPathString('archdesc[@level="collection"]/did/abstract')
