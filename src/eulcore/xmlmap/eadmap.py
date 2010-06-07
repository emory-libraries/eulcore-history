from eulcore import xmlmap

# xmlmap objects for various sections of an ead
# organized from smallest/lowest level to highest level

class Note(xmlmap.XmlObject):
    """EAD note."""
    content = xmlmap.StringListField("p") 
    "list of paragraphs - `p`"

class Section(xmlmap.XmlObject):
    """Generic EAD section.  Currently only has mappings for head, paragraph, and note."""
    head   = xmlmap.StringField("head")
    "heading - `head`"
    content = xmlmap.NodeListField("p", xmlmap.XmlObject)       # ??
    "list of paragraphs - `p`"
    note = xmlmap.NodeField("note", Note)
    ":class:`Note`"


class Heading(xmlmap.XmlObject):
    """Generic xml object for headings used under `controlaccess`"""
    source = xmlmap.StringField("@source")
    "source vocabulary for controlled term - `@source`"
    value  = xmlmap.StringField(".")
    "controlled term text value (content of the heading element)"

    def __unicode__(self):
        return self.value


class ControlledAccessHeadings(Section):
    """
    Controlled access headings, such as subject terms, family and corporate
    names, etc.

    Expected dom_node element passed to constructor: `contolaccess`.
    """
    person_name = xmlmap.NodeListField("persname", Heading)
    "person name :class:`Heading` list - `persname`"
    family_name = xmlmap.NodeListField("famname", Heading)
    "family name :class:`Heading` list  - `famname`"
    corporate_name = xmlmap.NodeListField("corpname", Heading)
    "corporate name :class:`Heading` list  - `corpname`"
    subject = xmlmap.NodeListField("subject", Heading)
    "subject :class:`Heading` list - `subject`"
    geographic_name = xmlmap.NodeListField("geogname", Heading)
    "geographic name :class:`Heading` list - `geogname`"
    genre_form = xmlmap.NodeListField("genreform", Heading)
    "genre or form :class:`Heading` list - `genreform`"
    occupation = xmlmap.NodeListField("occupation", Heading)
    "occupation :class:`Heading` list - `occupation`"
    function = xmlmap.NodeListField("function", Heading)
    "function :class:`Heading` list - `function`"
    title = xmlmap.NodeListField("title", Heading)
    "title :class:`Heading` list - `title`"
    # catch-all to get any of these, in order
    terms = xmlmap.NodeListField("corpname|famname|function|genreform|geogname|occupation|persname|subject|title", Heading)
    "list of :class:`Heading` - any allowed control access terms, in whatever order they appear"

    controlaccess = xmlmap.NodeListField("controlaccess", "self")
    "list of :class:`ControlledAccessHeadings` - recursive mapping to `controlaccess`"


class Container(xmlmap.XmlObject):
    """
    Container - :class:`DescriptiveIdentification` subelement for locating materials.

    Expected dom_node element passed to constructor: `did/container`.
    """
    type = xmlmap.StringField("@type")
    "type - `@type`"
    value = xmlmap.StringField(".")
    "text value - (contents of the container element)"

    def __unicode__(self):
        return self.value

class DateField(xmlmap.XmlObject):
    """
    DateField - for access to date and unitdate elements value and attributes.
    When converted to unicode, will be the non-normalized version of the date
    in the text content of the element.
    """
    normalized = xmlmap.StringField("@normal")
    "normalized form of the date - `@normal`"
    calendar = xmlmap.StringField("@calendar")
    "calendar (e.g. gregorian) - `@calendar`"
    era = xmlmap.StringField("@era")
    "era (e.g. ce) - `@era`"
    value = xmlmap.StringField(".")
    "human-readable date - (contents of the date element)"

    def __unicode__(self):
        return self.value
    
class DescriptiveIdentification(xmlmap.XmlObject):
    """Descriptive Information (`did` element) for materials in a component"""
    unitid = xmlmap.StringField("unitid")
    "unit id - `unitid`"
    unittitle = xmlmap.NodeField("unittitle", xmlmap.XmlObject)
    "unit title - `unittitle`"
    unitdate = xmlmap.NodeField(".//unitdate", DateField)
    "unit date - `.//unitdate' can be anywhere under did"
    physdesc = xmlmap.StringField("physdesc")
    "physical description - `physdesc`"
    abstract = xmlmap.NodeField('abstract', xmlmap.XmlObject)
    "abstract - `abstract`"
    langmaterial = xmlmap.StringField("langmaterial")
    "language of materials - `langmaterial`"
    origination = xmlmap.StringField("origination")
    "origination - `origination`"
    location = xmlmap.StringField("physloc")
    "physical location - `physloc`"
    container = xmlmap.NodeListField("container", Container)
    ":class:`Container` - `container`"    


class Component(xmlmap.XmlObject):
    """Generic component `cN` (`c1`-`c12`) element - a subordinate component of the materials"""
    level = xmlmap.StringField("@level")
    "level of the component - `@level`"
    id = xmlmap.StringField("@id")
    "component id - `@id`"
    did = xmlmap.NodeField("did", DescriptiveIdentification)
    ":class:`DescriptiveIdentification` - `did`"
    # FIXME: these sections overlap significantly with those in archdesc; share/inherit?
    use_restriction = xmlmap.NodeField("userestrict", Section)
    "usage restrictions :class:`Section` - `userestrict`"
    alternate_form = xmlmap.NodeField("altformavail", Section)
    "alternative form available :class:`Section` - `altformavail`"
    originals_location = xmlmap.NodeField("originalsloc", Section)
    "location of originals :class:`Section` - `originalsloc`"
    related_material = xmlmap.NodeField("relatedmaterial", Section)
    "related material :class:`Section` - `relatedmaterial`"
    separated_material = xmlmap.NodeField("separatedmaterial", Section)
    "separated material :class:`Section` - `separatedmaterial`"
    acquisition_info = xmlmap.NodeField("acqinfo", Section)
    "acquistion info :class:`Section` - `acqinfo`"
    custodial_history = xmlmap.NodeField("custodhist", Section)
    "custodial history :class:`Section` - `custodhist`"
    preferred_citation = xmlmap.NodeField("prefercite", Section)
    "preferred citation :class:`Section` - `prefercite`"
    biography_history = xmlmap.NodeField("bioghist", Section)
    "biography or history :class:`Section` - `bioghist`"
    bibliography = xmlmap.NodeField("bibliography", Section)
    "bibliography :class:`Section` - `bibliograhy`"
    scope_content  = xmlmap.NodeField("scopecontent", Section)
    "scope and content :class:`Section` - `scopecontent`"
    arrangement = xmlmap.NodeField("arrangement", Section)
    "arrangement :class:`Section` - `arrangement`"
    other = xmlmap.NodeField("otherfindaid", Section)
    "other finding aid :class:`Section` - `otherfindaid`"
    use_restriction = xmlmap.NodeField("userestrict", Section)
    "use restrictions :class:`Section` - `userestrict`"
    access_restriction = xmlmap.NodeField("accessrestrict", Section)
    "access restrictions :class:`Section` - `accessrestrict`"

    c = xmlmap.NodeListField("c02|c03|c04|c05|c06|c07|c08|c09|c10|c11|c12", "self")
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


class SubordinateComponents(Section):
    """Description of Subordinate Components (dsc element); container lists and series.
    
       Expected dom_node element passed to constructor: `ead/archdesc/dsc`.
    """

    type = xmlmap.StringField("@type")
    "type of component - `@type`"
    c = xmlmap.NodeListField("c01", Component)
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
    type = xmlmap.StringField("@linktype")
    "link type"
    target = xmlmap.StringField("@target")
    "link target"
    value = xmlmap.StringField(".")
    "text content of the reference"

    def __unicode__(self):
        return self.value


class PointerGroup(xmlmap.XmlObject):
    """Group of pointer or reference elements in an index entry
    
    Expected dom_node element passed to constructor: `ptrgrp`.
    """
    ref = xmlmap.NodeListField("ref", Reference)
    "list of :class:`Reference` - references"


class IndexEntry(xmlmap.XmlObject):
    "Index entry in an archival description index."
    name = xmlmap.StringField("corpname|famname|function|genreform|geogname|name|namegrp|occupation|persname|title|subject")
    "access element, e.g. name or subject"
    ptrgroup = xmlmap.NodeField("ptrgrp", PointerGroup)
    ":class:`PointerGroup` - group of references for this index entry"


class Index(Section):
    """Index (index element); list of key terms and reference information.

       Expected dom_node element passed to constructor: `ead/archdesc/index`.
    """
    entry = xmlmap.NodeListField("indexentry", IndexEntry)
    "list of :class:`IndexEntry` - `index`; entry in the index"
    id = xmlmap.StringField("@id")


class ArchivalDescription(xmlmap.XmlObject):
    """Archival description, contains the bulk of the information in an EAD document.

      Expected dom_node element passed to constructor: `ead/archdesc`.
      """
    origination = xmlmap.StringField("did/origination")
    "origination - `did/origination`"
    unitid = xmlmap.StringField("did/unitid")
    "unit id - `did/untid`"
    extent = xmlmap.StringListField("did/physdesc/extent")
    "extent from the physical description - `did/physdesc/extent`"
    langmaterial = xmlmap.StringField("did/langmaterial")
    "language of the materials - `did/langmaterial`"
    location = xmlmap.StringField("did/physloc")
    "physical location - `did/physloc`"
    access_restriction = xmlmap.NodeField("accessrestrict", Section)
    "access restrictions :class:`Section` - `accessrestrict`"
    use_restriction = xmlmap.NodeField("userestrict", Section)
    "use restrictions :class:`Section` - `userestrict`"
    alternate_form = xmlmap.NodeField("altformavail", Section)
    "alternative form available :class:`Section` - `altformavail`"
    originals_location = xmlmap.NodeField("originalsloc", Section)
    "location of originals :class:`Section` - `originalsloc`"
    related_material = xmlmap.NodeField("relatedmaterial", Section)
    "related material :class:`Section` - `relatedmaterial`"
    separated_material = xmlmap.NodeField("separatedmaterial", Section)
    "separated material :class:`Section` - `separatedmaterial`"
    acquisition_info = xmlmap.NodeField("acqinfo", Section)
    "acquistion info :class:`Section` - `acqinfo`"
    custodial_history = xmlmap.NodeField("custodhist", Section)
    "custodial history :class:`Section` - `custodhist`"
    preferred_citation = xmlmap.NodeField("prefercite", Section)
    "preferred citation :class:`Section` - `prefercite`"
    biography_history = xmlmap.NodeField("bioghist", Section)
    "biography or history :class:`Section` - `bioghist`"
    bibliography = xmlmap.NodeField("bibliography", Section)
    "bibliography :class:`Section` - `bibliograhy`"
    scope_content  = xmlmap.NodeField("scopecontent", Section)
    "scope and content :class:`Section` - `scopecontent`"
    arrangement = xmlmap.NodeField("arrangement", Section)
    "arrangement :class:`Section` - `arrangement`"
    other = xmlmap.NodeField("otherfindaid", Section)
    "other finding aid :class:`Section` - `otherfindaid`"
    controlaccess = xmlmap.NodeField("controlaccess", ControlledAccessHeadings)
    ":class:`ControlledAccessHeadings` - `controlaccess`; subject terms, names, etc."
    index = xmlmap.NodeListField("index", Index)
    "list of :class:`Index` - `index`; e.g., index of selected correspondents"

class Address(xmlmap.XmlObject):
    """Address information.

      Expected dom_node element passed to constructor: `address`.
    """
    lines = xmlmap.StringListField("addressline")
    "list of lines in an address - `line`"

class PublicationStatement(xmlmap.XmlObject):
    """Publication information for an EAD document.

      Expected dom_node element passed to constructor: `ead/eadheader/filedesc/publicationstmt`.
      """
    date = xmlmap.NodeField("date", DateField)
    ":class:`DateField` - `date`"
    publisher = xmlmap.StringField("publisher")
    "publisher - `publisher`"
    address = xmlmap.NodeField("address", Address)
    "address of publication/publisher - `address`"

class ProfileDescription(xmlmap.XmlObject):
    """Profile Descriptor for an EAD document.
       Expected dom_node element passed to constructor: 'ead/eadheader/profiledesc'.
    """
    date = xmlmap.NodeField("creation/date", DateField)
    ":class:`DateField` - `creation/date`"
    languages = xmlmap.StringListField("langusage/language")
    "language information - `langusage/language`"
    language_codes = xmlmap.StringListField("langusage/language/@langcode")
    "language codes - `langusage/language/@langcode`"
    
class FileDescription(xmlmap.XmlObject):
    """Bibliographic information about this EAD document.

      Expected dom_node element passed to constructor: `ead/eadheader/filedesc`.
      """
    publication = xmlmap.NodeField("publicationstmt", PublicationStatement)
    "publication information - `publicationstmt`"


class EncodedArchivalDescription(xmlmap.XmlObject):
    """xmlmap object for an Encoded Archival Description (EAD) Finding Aid

       Expects dom_node passed to constructor to be top-level `ead` element.
    """
    id = xmlmap.StringField('@id')
    "top-level id attribute - `@id`; preferable to use eadid"
    eadid = xmlmap.StringField('eadheader/eadid')
    "ead id - `eadheader/eadid`"
    # mappings for fields common to access or display as top-level information
    title = xmlmap.NodeField('eadheader/filedesc/titlestmt/titleproper', xmlmap.XmlObject)
    "record title - `eadheader/filedesc/titlestmt/titleproper`"
    author = xmlmap.StringField('eadheader/filedesc/titlestmt/author')
    "record author - `eadheader/filedesc/titlestmt/author`"
    unittitle = xmlmap.NodeField('archdesc[@level="collection"]/did/unittitle', xmlmap.XmlObject)
    """unit title for the archive - `archdesc[@level="collection"]/did/unittitle`"""
    physical_desc = xmlmap.StringField('archdesc[@level="collection"]/did/physdesc')
    """collection level physical description - `archdesc[@level="collection"]/did/physdesc`"""
    abstract = xmlmap.NodeField('archdesc[@level="collection"]/did/abstract', xmlmap.XmlObject)
    """collection level abstract - `archdesc[@level="collection"]/did/abstract`"""
    
    archdesc  = xmlmap.NodeField("archdesc", ArchivalDescription)
    ":class:`ArchivalDescription` - `archdesc`"
    # dsc is under archdesc, but is a major section - mapping at top-level for convenience
    dsc = xmlmap.NodeField("archdesc/dsc", SubordinateComponents)
    ":class:`SubordinateComponents` `archdesc/dsc`; accessible at top-level for convenience"
    file_desc = xmlmap.NodeField("eadheader/filedesc", FileDescription)
    ":class:`FileDescription` - `filedesc`"
    profiledesc = xmlmap.NodeField("eadheader/profiledesc", ProfileDescription)
    ":class:`ProfileDescription` - `profiledesc`"

