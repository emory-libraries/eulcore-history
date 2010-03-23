from eulcore import xmlmap

# xmlmap objects for various sections of an ead
# organized from smallest/lowest level to highest level

class Note(xmlmap.XmlObject):
    """EAD note."""
    content = xmlmap.XPathStringList("p") 
    "list of paragraphs - `p`"

class Section(xmlmap.XmlObject):
    """Generic EAD section.  Currently only has mappings for head, paragraph, and note."""
    head   = xmlmap.XPathString("head")
    "heading - `head`"
    content = xmlmap.XPathStringList("p")       # ??
    "list of paragraphs - `p`"
    note = xmlmap.XPathNode("note", Note)
    ":class:`Note`"

class Heading(xmlmap.XmlObject):
    """Generic xml object for headings used under `controlaccess`"""
    source = xmlmap.XPathString("@source")
    "source vocabulary for controlled term - `@source`"
    value  = xmlmap.XPathString(".")
    "controlled term text value (content of the heading element)"

    def __str__(self):
        return self.value

class ControlledAccessHeadings(Section):
    """
    Controlled access headings, such as subject terms, family and corporate
    names, etc.

    Expected dom_node element passed to constructor: `contolaccess`.
    """
    person_name = xmlmap.XPathNodeList("persname", Heading)
    "person name :class:`Heading` list - `persname`"
    family_name = xmlmap.XPathNodeList("famname", Heading)
    "family name :class:`Heading` list  - `famname`"
    corporate_name = xmlmap.XPathNodeList("corpname", Heading)
    "corporate name :class:`Heading` list  - `corpname`"
    subject = xmlmap.XPathNodeList("subject", Heading)
    "subject :class:`Heading` list - `subject`"
    geographic_name = xmlmap.XPathNodeList("geogname", Heading)
    "geographic name :class:`Heading` list - `geogname`"
    genre_form = xmlmap.XPathNodeList("genreform", Heading)
    "genre or form :class:`Heading` list - `genreform`"
    occupation = xmlmap.XPathNodeList("occupation", Heading)
    "occupation :class:`Heading` list - `occupation`"
    function = xmlmap.XPathNodeList("function", Heading)
    "function :class:`Heading` list - `function`"
    title = xmlmap.XPathNodeList("title", Heading)
    "title :class:`Heading` list - `title`"
    # catch-all to get any of these, in order
    terms = xmlmap.XPathNodeList("corpname|famname|function|genreform|geogname|occupation|persname|subject|title", Heading)
    "list of :class:`Heading` - any allowed control access terms, in whatever order they appear"

    # recursive - has to be set after class is defined; setting here for documentation purposes
    controlaccess = xmlmap.XPathStringList("controlaccess")
    "list of :class:`ControlledAccessHeadings` - recursive mapping to `controlaccess`"
    
# recursive mapping - currently has to be declared after class has been defined
ControlledAccessHeadings.controlaccess = xmlmap.XPathNodeList("controlaccess", ControlledAccessHeadings)


class Container(xmlmap.XmlObject):
    """
    Container - :class:`DescriptiveIdentification` subelement for locating materials.

    Expected dom_node element passed to constructor: `did/container`.
    """
    type = xmlmap.XPathString("@type")
    "type - `@type`"
    value = xmlmap.XPathString(".")
    "text value - (contents of the container element)"

    def __str__(self):
        return self.value

class DescriptiveIdentification(xmlmap.XmlObject):
    """Descriptive Information (`did` element) for materials in a component"""
    unitid = xmlmap.XPathString("unitid")
    "unit id - `unitid`"
    unittitle = xmlmap.XPathString("unittitle")
    "unit title - `unittitle`"
    unitdate = xmlmap.XPathString("unitdate")
    "unit date - `unitdate`"
    physdesc = xmlmap.XPathString("physdesc")
    "physical description - `physdesc`"
    abstract = xmlmap.XPathString('abstract')
    "abstract - `abstract`"
    langmaterial = xmlmap.XPathString("langmaterial")
    "language of materials - `langmaterial`"
    origination = xmlmap.XPathString("origination")
    "origination - `origination`"
    location = xmlmap.XPathString("physloc")
    "physical location - `physloc`"
    container = xmlmap.XPathNodeList("container", Container)
    ":class:`Container` - `container`"    

class Component(xmlmap.XmlObject):
    """Generic component `cN` (`c1`-`c12`) element - a subordinate component of the materials"""
    level = xmlmap.XPathString("@level")
    "level of the component - `@level`"
    id = xmlmap.XPathString("@id")
    "component id - `@id`"
    did = xmlmap.XPathNode("did", DescriptiveIdentification)
    ":class:`DescriptiveIdentification` - `did`"
    # FIXME: these sections overlap significantly with those in archdesc; share/inherit?
    use_restriction = xmlmap.XPathNode("userestrict", Section)
    "usage restrictions :class:`Section` - `userestrict`"
    alternate_form = xmlmap.XPathNode("altformavail", Section)
    "alternative form available :class:`Section` - `altformavail`"
    originals_location = xmlmap.XPathNode("originalsloc", Section)
    "location of originals :class:`Section` - `originalsloc`"
    related_material = xmlmap.XPathNode("relatedmaterial", Section)
    "related material :class:`Section` - `relatedmaterial`"
    separated_material = xmlmap.XPathNode("separatedmaterial", Section)
    "separated material :class:`Section` - `separatedmaterial`"
    acquisition_info = xmlmap.XPathNode("acqinfo", Section)
    "acquistion info :class:`Section` - `acqinfo`"
    custodial_history = xmlmap.XPathNode("custodhist", Section)
    "custodial history :class:`Section` - `custodhist`"
    preferred_citation = xmlmap.XPathNode("prefercite", Section)
    "preferred citation :class:`Section` - `prefercite`"
    biography_history = xmlmap.XPathNode("bioghist", Section)
    "biography or history :class:`Section` - `bioghist`"
    bibliography = xmlmap.XPathNode("bibliography", Section)
    "bibliography :class:`Section` - `bibliograhy`"
    scope_content  = xmlmap.XPathNode("scopecontent", Section)
    "scope and content :class:`Section` - `scopecontent`"
    arrangement = xmlmap.XPathNode("arrangement", Section)
    "arrangement :class:`Section` - `arrangement`"
    other = xmlmap.XPathNode("otherfindaid", Section)
    "other finding aid :class:`Section` - `otherfindaid`"
    use_restriction = xmlmap.XPathNode("userestrict", Section)
    "use restrictions :class:`Section` - `userestrict`"
    access_restriction = xmlmap.XPathNode("accessrestrict", Section)
    "access restrictions :class:`Section` - `accessrestrict`"

    # has to be set after Component is defined; setting here for documentation purposes
    c = xmlmap.XPathStringList("c02|c03|c04|c05|c06|c07|c08|c09|c10|c11|c12")
    "list of :class:`Component` - recursive mapping to any c-level 2-12; `c02|c03|c04|c05|c06|c07|c08|c09|c10|c11|c12`"
    
    # using un-numbered mapping for c-series or container lists
    def hasSubseries(self):
        """Check if this component has subseries or not.

           Determined based on level of first subcomponent (series or subseries)
           or if first component has subcomponents present.

            :rtype: boolean
        """
        if self.c and self.c[0] and ((self.c[0].level in ('series', 'subseries')) or
            (self.c[0].c and self.c[0].c[0])):            
            return True
        else:
            return False

# another recursive mapping - currently has to be declared after class has been defined
Component.c = xmlmap.XPathNodeList("c02|c03|c04|c05|c06|c07|c08|c09|c10|c11|c12", Component)

class SubordinateComponents(Section):
    """Description of Subordinate Components (dsc element); container lists and series.
    
       Expected dom_node element passed to constructor: `ead/archdesc/dsc`.
    """

    type = xmlmap.XPathString("@type")
    "type of component - `@type`"
    c = xmlmap.XPathNodeList("c01", Component)
    "list of :class:`Component` - `c01`; list of c01 elements directly under this section"
    
    def hasSeries(self):
        """Check if this finding aid has series/subseries.

           Determined based on level of first component (series) or if first
           component has subcomponents present.

           :rtype: boolean
        """
        if self.c[0].level == 'series' or (self.c[0].c and self.c[0].c[0]):
            return True
        else:
            return False

class Reference(xmlmap.XmlObject):
    """Internal linking element that may contain text.

    Expected dom_node element passed to constructor: `ref`.
    """
    type = xmlmap.XPathString("@linktype")
    "link type"
    target = xmlmap.XPathString("@target")
    "link target"
    value = xmlmap.XPathString(".")
    "text content of the reference"

    def __str__(self):
        return self.value

class PointerGroup(xmlmap.XmlObject):
    """Group of pointer or reference elements in an index entry
    
    Expected dom_node element passed to constructor: `ptrgrp`.
    """
    ref = xmlmap.XPathNodeList("ref", Reference)
    "list of :class:`Reference` - references"

class IndexEntry(xmlmap.XmlObject):
    "Index entry in an archival description index."
    name = xmlmap.XPathString("corpname|famname|function|genreform|geogname|name|namegrp|occupation|persname|title|subject")
    "access element, e.g. name or subject"
    ptrgroup = xmlmap.XPathNode("ptrgrp", PointerGroup)
    ":class:`PointerGroup` - group of references for this index entry"


class Index(Section):
    """Index (index element); list of key terms and reference information.

       Expected dom_node element passed to constructor: `ead/archdesc/index`.
    """
    entry = xmlmap.XPathNodeList("indexentry", IndexEntry)
    "list of :class:`IndexEntry` - `index`; entry in the index"


class ArchivalDescription(xmlmap.XmlObject):
    """Archival description, contains the bulk of the information in an EAD document.

      Expected dom_node element passed to constructor: `ead/archdesc`.
      """
    origination = xmlmap.XPathString("did/origination")
    "origination - `did/origination`"
    unitid = xmlmap.XPathString("did/unitid")
    "unit id - `did/untid`"
    extent = xmlmap.XPathStringList("did/physdesc/extent")
    "extent from the physical description - `did/physdesc/extent`"
    langmaterial = xmlmap.XPathString("did/langmaterial")
    "language of the materials - `did/langmaterial`"
    location = xmlmap.XPathString("did/physloc")
    "physical location - `did/physloc`"
    access_restriction = xmlmap.XPathNode("accessrestrict", Section)
    "access restrictions :class:`Section` - `accessrestrict`"
    use_restriction = xmlmap.XPathNode("userestrict", Section)
    "use restrictions :class:`Section` - `userestrict`"
    alternate_form = xmlmap.XPathNode("altformavail", Section)
    "alternative form available :class:`Section` - `altformavail`"
    originals_location = xmlmap.XPathNode("originalsloc", Section)
    "location of originals :class:`Section` - `originalsloc`"
    related_material = xmlmap.XPathNode("relatedmaterial", Section)
    "related material :class:`Section` - `relatedmaterial`"
    separated_material = xmlmap.XPathNode("separatedmaterial", Section)
    "separated material :class:`Section` - `separatedmaterial`"
    acquisition_info = xmlmap.XPathNode("acqinfo", Section)
    "acquistion info :class:`Section` - `acqinfo`"
    custodial_history = xmlmap.XPathNode("custodhist", Section)
    "custodial history :class:`Section` - `custodhist`"
    preferred_citation = xmlmap.XPathNode("prefercite", Section)
    "preferred citation :class:`Section` - `prefercite`"
    biography_history = xmlmap.XPathNode("bioghist", Section)
    "biography or history :class:`Section` - `bioghist`"
    bibliography = xmlmap.XPathNode("bibliography", Section)
    "bibliography :class:`Section` - `bibliograhy`"
    scope_content  = xmlmap.XPathNode("scopecontent", Section)
    "scope and content :class:`Section` - `scopecontent`"
    arrangement = xmlmap.XPathNode("arrangement", Section)
    "arrangement :class:`Section` - `arrangement`"
    other = xmlmap.XPathNode("otherfindaid", Section)
    "other finding aid :class:`Section` - `otherfindaid`"
    controlaccess = xmlmap.XPathNode("controlaccess", ControlledAccessHeadings)
    ":class:`ControlledAccessHeadings` - `controlaccess`; subject terms, names, etc."
    index = xmlmap.XPathNode("index", Index)

class EncodedArchivalDescription(xmlmap.XmlObject):
    """xmlmap object for an Encoded Archival Description (EAD) Finding Aid

       Expects dom_node passed to constructor to be top-level `ead` element.
    """
    id = xmlmap.XPathString('@id')
    "top-level id attribute - `@id`; preferable to use eadid"
    eadid = xmlmap.XPathString('eadheader/eadid')
    "ead id - `eadheader/eadid`"
    # mappings for fields common to access or display as top-level information
    title = xmlmap.XPathString('eadheader/filedesc/titlestmt/titleproper')
    "record title - `eadheader/filedesc/titlestmt/titleproper`"
    author = xmlmap.XPathString('eadheader/filedesc/titlestmt/author')
    "record author - `eadheader/filedesc/titlestmt/author`"
    unittitle = xmlmap.XPathString('archdesc[@level="collection"]/did/unittitle')
    """unit title for the archive - `archdesc[@level="collection"]/did/unittitle`"""
    physical_desc = xmlmap.XPathString('archdesc[@level="collection"]/did/physdesc')
    """collection level physical description - `archdesc[@level="collection"]/did/physdesc`"""
    abstract = xmlmap.XPathString('archdesc[@level="collection"]/did/abstract')
    """collection level abstract - `archdesc[@level="collection"]/did/abstract`"""
    
    archdesc  = xmlmap.XPathNode("archdesc", ArchivalDescription)
    ":class:`ArchivalDescription` - `archdesc`"
    # dsc is under archdesc, but is a major section - mapping at top-level for convenience
    dsc = xmlmap.XPathNode("archdesc/dsc", SubordinateComponents)
    ":class:`SubordinateComponents` `archdesc/dsc`; accessible at top-level for convenience"

