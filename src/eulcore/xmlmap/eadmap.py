from eulcore import xmlmap

# xmlmap objects for various sections of an ead
# organized from smallest/lowest level to highest level

class Section(xmlmap.XmlObject):
    # generic section - head and paragraph
    head   = xmlmap.XPathString("head")
    content = xmlmap.XPathStringList("p")       # ??

class Heading(xmlmap.XmlObject):
    """Generic xml object for headings used under controlaccess"""
    source = xmlmap.XPathString("@source")
    value  = xmlmap.XPathString(".")

    def __str__(self):
        return self.value

class ControlledAccessHeadings(Section):
    """controlaccess element - controlled access headings"""
    person_name = xmlmap.XPathNodeList("persname", Heading)
    family_name = xmlmap.XPathNodeList("famname", Heading)
    corporate_name = xmlmap.XPathNodeList("corpname", Heading)
    subject = xmlmap.XPathNodeList("subject", Heading)
    geographic_name = xmlmap.XPathNodeList("geogname", Heading)
    genre_form = xmlmap.XPathNodeList("genreform", Heading)
    occupation = xmlmap.XPathNodeList("occupation", Heading)
    function = xmlmap.XPathNodeList("function", Heading)
    title = xmlmap.XPathNodeList("title", Heading)
    # catch-all to get any of these, in order
    terms = xmlmap.XPathNodeList("corpname|famname|function|genreform|geogname|occupation|persname|subject|title", Heading)

# recursive mapping - currently has to be declared after class has been defined
ControlledAccessHeadings.controlaccess = xmlmap.XPathNodeList("controlaccess", ControlledAccessHeadings)

class Container(xmlmap.XmlObject):
    """container element - did subelement for locating materials"""
    type = xmlmap.XPathString("@type")
    value = xmlmap.XPathString(".")

    def __str__(self):
        return self.value

class DescriptiveIdentification(xmlmap.XmlObject):
    """did element - Descriptive Information for materials in a component"""
    unitid = xmlmap.XPathString("unitid")
    unittitle = xmlmap.XPathString("unittitle")
    unitdate = xmlmap.XPathString("unitdate")
    physdesc = xmlmap.XPathString("physdesc")
    container = xmlmap.XPathNodeList("container", Container)

class Component(xmlmap.XmlObject):
    """generic cN (c1-c12) element - a subordinate component of the materials"""
    level = xmlmap.XPathString("@level")
    did = xmlmap.XPathNode("did", DescriptiveIdentification)
    # using un-numbered mapping for c-series or container lists
    def hasSubseries(self):
        """check if this component has subseries"""        
        if self.c and self.c[0] and ((self.c[0].level in ('series', 'subseries')) or
            (self.c[0].c and self.c[0].c[0])):            
            return True
        else:
            return False

# another recursive mapping - currently has to be declared after class has been defined
Component.c = xmlmap.XPathNodeList("c02|c03|c04|c05|c06|c07|c08|c09|c10|c11|c12", Component)

class SubordinateComponents(Section):
    """dsc element - Description of Subordinate Components; container lists and series"""
    type = xmlmap.XPathString("@type")
    c = xmlmap.XPathNodeList("c01", Component)
    
    def hasSeries(self):
        """check if this finding aid has series/subseries"""
        if self.c[0].level == 'series' or (self.c[0].c and self.c[0].c[0]):
            return True
        else:
            return False

class ArchivalDescription(xmlmap.XmlObject):
    """archdesc element, Archival description; makes up the bulk of an EAD document"""
    origination = xmlmap.XPathString("did/origination")
    unitid = xmlmap.XPathString("did/unitid")
    extent = xmlmap.XPathString("did/physdesc/extent")
    langmaterial = xmlmap.XPathString("did/langmaterial")
    location = xmlmap.XPathString("did/physloc")
    access_restriction = xmlmap.XPathNode("accessrestrict", Section)
    use_restriction = xmlmap.XPathNode("userestrict", Section)
    alternate_form = xmlmap.XPathNode("altformavail", Section)
    originals_location = xmlmap.XPathNode("originalsloc", Section)
    related_material = xmlmap.XPathNode("relatedmaterial", Section)
    separated_material = xmlmap.XPathNode("separatedmaterial", Section)
    acquisition_info = xmlmap.XPathNode("acqinfo", Section)
    custodial_history = xmlmap.XPathNode("custodhist", Section)
    preferred_citation = xmlmap.XPathNode("prefercite", Section)
    biography_history = xmlmap.XPathNode("bioghist", Section)
    bibliography = xmlmap.XPathNode("bibliography", Section)
    scope_content  = xmlmap.XPathNode("scopecontent", Section)
    arrangement = xmlmap.XPathNode("arrangement", Section)
    other = xmlmap.XPathNode("otherfindaid", Section)
    controlaccess = xmlmap.XPathNode("controlaccess", ControlledAccessHeadings)

class EncodedArchivalDescription(xmlmap.XmlObject):
    """xmlmap object for an Encoded Archival Description (EAD) Finding Aid"""
    id = xmlmap.XPathString('@id')
    eadid = xmlmap.XPathString('eadheader/eadid')
    # mappings for fields common to access or display as top-level information
    title = xmlmap.XPathString('eadheader/filedesc/titlestmt/titleproper')
    author = xmlmap.XPathString('eadheader/filedesc/titlestmt/author')
    unittitle = xmlmap.XPathString('archdesc[@level="collection"]/did/unittitle')
    physical_desc = xmlmap.XPathString('archdesc[@level="collection"]/did/physdesc')
    abstract = xmlmap.XPathString('archdesc[@level="collection"]/did/abstract')

    archdesc  = xmlmap.XPathNode("archdesc", ArchivalDescription)
    # dsc is under archdesc, but is a major section - mapping at top-level for convenience
    dsc = xmlmap.XPathNode("archdesc/dsc", SubordinateComponents)

