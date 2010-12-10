from rdflib.namespace import ClosedNamespace

# ids copied from http://www.fedora.info/definitions/1/0/fedora-relsext-ontology.rdfs
relsext = ClosedNamespace('info:fedora/fedora-system:def/relations-external#', [
    'fedoraRelationship',
    'isPartOf',
    'hasPart',
    'isConstituentOf',
    'hasConstituent',
    'isMemberOf',
    'hasMember',
    'isSubsetOf',
    'hasSubset',
    'isMemberOfCollection',
    'hasCollectionMember',
    'isDerivationOf',
    'hasDerivation',
    'isDependentOf',
    'hasDependent',
    'isDescriptionOf',
    'HasDescription',
    'isMetadataFor',
    'HasMetadata',
    'isAnnotationOf',
    'HasAnnotation',
    'hasEquivalent',
])

# TODO: find and catalog full namespace. currently this is just a list of
# names we use in this ns.
model = ClosedNamespace('info:fedora/fedora-system:def/model#', [
    'hasModel',
])
