from eulcore import xmlmap

class DigitalObject(xmlmap.XmlObject):
    '''XML map for a foxml:digitalObject, typically either ingested into a
    fedora server or exported from one'''
    pid = xmlmap.XPathString('@PID')
