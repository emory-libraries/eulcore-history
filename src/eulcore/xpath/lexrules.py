"""XPath lexing rules.

To understand how this module works, it is valuable to have a strong
understanding of the `ply <http://www.dabeaz.com/ply/>` module.
"""

from ply.lex import TOKEN

reserved = {
    'or': 'OR_OP',
    'and': 'AND_OP',
    'div': 'DIV_OP',
    'mod': 'MOD_OP',
}

tokens = [
        'PATH_SEP',
        'ABBREV_PATH_SEP',
        'ABBREV_STEP_SELF',
        'ABBREV_STEP_PARENT',
        'AXIS_SEP',
        'ABBREV_AXIS_AT',
        'OPEN_PAREN',
        'CLOSE_PAREN',
        'OPEN_BRACKET',
        'CLOSE_BRACKET',
        'UNION_OP',
        'EQUAL_OP',
        'REL_OP',
        'PLUS_OP',
        'MINUS_OP',
        'MULT_OP',
        'STAR_OP',
        'COMMA',
        'LITERAL',
        'FLOAT',
        'INTEGER',
        'NCNAME',
        'NODETYPE',
        'COLON',
        'DOLLAR',
    ] + list(reserved.values())

t_PATH_SEP = r'/'
t_ABBREV_PATH_SEP = r'//'
t_ABBREV_STEP_SELF = r'\.'
t_ABBREV_STEP_PARENT = r'\.\.'
t_AXIS_SEP = r'::'
t_ABBREV_AXIS_AT = r'@'
t_OPEN_PAREN = r'\('
t_CLOSE_PAREN = r'\)'
t_OPEN_BRACKET = r'\['
t_CLOSE_BRACKET = r'\]'
t_UNION_OP = r'\|'
t_EQUAL_OP = r'!?='
t_REL_OP = r'[<>]=?'
t_PLUS_OP = r'\+'
t_MINUS_OP = r'-'
t_COMMA = r','
t_COLON = r':'
t_DOLLAR = r'\$'

t_ignore = ' \t\r\n'

def t_LITERAL(t):
    r""""[^"]*"|'[^']*'"""
    t.value = t.value[1:-1]
    return t

def t_FLOAT(t):
    r'\d+\.\d*|\.\d+'
    t.value = float(t.value)
    return t
    
def t_INTEGER(t):
    r'\d+'
    t.value = int(t.value)
    return t

# NOTE: some versions of python cannot compile regular expressions that
# contain unicode characters above U+FFFF, which are allowable in NCNames.
# These characters can be used in Python 2.6.4, but can NOT be used in 2.6.2
# (status in 2.6.3 is unknown).  The code below accounts for that and excludes
# the higher character range if Python can't handle it.


# Monster regex derived from:
#  http://www.w3.org/TR/REC-xml/#NT-NameStartChar
#  http://www.w3.org/TR/REC-xml/#NT-NameChar
# EXCEPT:
# Technically those productions allow ':'. NCName, on the other hand:
#  http://www.w3.org/TR/REC-xml-names/#NT-NCName
# explicitly excludes those names that have ':'. We implement this by
# simply removing ':' from our regexes.

# NameStartChar regex without characters about U+FFFF
NameStartChar = ur'[A-Z]|_|[a-z]|\xc0-\xd6]|[\xd8-\xf6]|[\xf8-\u02ff]|' + \
    ur'[\u0370-\u037d]|[\u037f-\u1fff]|[\u200c-\u200d]|[\u2070-\u218f]|' + \
    ur'[\u2c00-\u2fef]|[\u3001-\uD7FF]|[\uF900-\uFDCF]|[\uFDF0-\uFFFD]'
# complete NameStartChar regex
Full_NameStartChar = ur'(' + NameStartChar + ur'| [\U00010000-\U000EFFFF]' + r')'
# additional characters allowed in NCNames after the first character
NameChar_extras = ur'[-.0-9\xb7\u0300-\u036f\u203f-\u2040]'

try:
    import re
    # test whether or not re can compile unicode characters above U+FFFF
    re.compile(ur'[\U00010000-\U00010001]')
    # if that worked, then use the full ncname regex
    NameStartChar = Full_NameStartChar
except:
    # if compilation failed, leave NameStartChar regex as is, which does not
    # include the unicode character ranges above U+FFFF
    pass

NCNAME_REGEX = r'(' + NameStartChar + r')(' + \
                      NameStartChar + r'|' + NameChar_extras + r')*'
                      
NODE_TYPES = set(['comment', 'text', 'processing-instruction', 'node'])

@TOKEN(NCNAME_REGEX)
def t_NCNAME(t):
#    ur'[A-Z_a-z\xc0-\xd6\xd8-\xf6\xf8-\u02ff\u0370-\u037d\u037f-\u1fff\u200c-\u200d\u2070-\u218f\u2c00-\u2fef\u2001-\ud7ff\uf900-\ufdcf\ufdf0-\ufffd\U00010000-\U000EFFFF][A-Z_a-z\xc0-\xd6\xd8-\xf6\xf8-\u02ff\u0370-\u037d\u037f-\u1fff\u200c-\u200d\u2070-\u218f\u2c00-\u2fef\u2001-\ud7ff\uf900-\ufdcf\ufdf0-\ufffd\U00010000-\U000EFFFF.0-9\xb7\u0300-\u036f\u203f-\u2040-]*'

    # I coulda sworn ply would recognize reserved keywords automatically.
    # Apparently not, so here we check for them ourselves.
    kwtoken = reserved.get(t.value, None)
    if kwtoken:
        t.type = kwtoken
    elif t.value in NODE_TYPES:
        # FIXME: technically foo:node is a QNname. We'll lex it as NCNAME
        # COLON NODETYPE, which is not a valid construction in our grammar.
        t.type = 'NODETYPE'
    return t


# Per http://www.w3.org/TR/xpath/#exprlex : 
#   "If there is a preceding token and the preceding token is not one of @,
#    ::, (, [, , or an Operator, then a * must be recognized as a
#    MultiplyOperator...."
#   "Otherwise, the token must not be recognized as a MultiplyOperator...."
#
# Note that the spec doesn't list ':' but we do. They can remove it because
# in the lexical structure defined by that section, ':' never exists on its
# own: It is always part of a NameTest or QName. Instead, we break QName
# down into NCName ':' NCName and put the parts together in the parser. That
# means that we need to pass the parser a STAR_OP for NCName ':' '*', not a
# MULT_OP. That means ':' needs to force the next '*' to be a STAR_OP not a
# MULT_OP. That means ':' needs to be in this list.
#
# We implement this by making the lexer keep track of its last token. Note
# that the ply lexer doesn't do this by default. This only works because
# core.py tweaks the token() logic to do so.
STAR_FORCERS = set([
    '@', '::', '(', '[', ',', 'and', 'or', 'mod', 'div', '*', '/', '//',
    '|', '+', '-', '=', '!=', '<', '<=', '>', '>=', ':',
])
def t_MULT_OP(t):
    r'\*'
    last = getattr(t.lexer, 'last', None)
    if last is None or last.value in STAR_FORCERS:
        t.type = 'STAR_OP'
    # else stick with MULT_OP
    return t
    
def t_error(t):
    raise TypeError("Unknown text '%s'" % (t.value,))
