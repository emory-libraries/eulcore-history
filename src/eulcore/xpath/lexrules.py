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

NODE_TYPES = set(['comment', 'text', 'processing-instruction', 'node'])
def t_NCNAME(t):
    # Monster regex derived from:
    #  http://www.w3.org/TR/REC-xml/#NT-NameStartChar
    #  http://www.w3.org/TR/REC-xml/#NT-NameChar
    # EXCEPT:
    # Technically those productions allow ':'. NCName, on the other hand:
    #  http://www.w3.org/TR/REC-xml-names/#NT-NCName
    # explicitly excludes those names that have ':'. We implement this by
    # simply removing ':' from our regexes.
    #
    # This long line (370 chars!) sucks. There's probably a better way to break
    # this down and still have it work in ply, but I'm missing it.
    ur'[A-Z_a-z\xc0-\xd6\xd8-\xf6\xf8-\u02ff\u0370-\u037d\u037f-\u1fff\u200c-\u200d\u2070-\u218f\u2c00-\u2fef\u2001-\ud7ff\uf900-\ufdcf\ufdf0-\ufffd\U00010000-\U000EFFFF][A-Z_a-z\xc0-\xd6\xd8-\xf6\xf8-\u02ff\u0370-\u037d\u037f-\u1fff\u200c-\u200d\u2070-\u218f\u2c00-\u2fef\u2001-\ud7ff\uf900-\ufdcf\ufdf0-\ufffd\U00010000-\U000EFFFF.0-9\xb7\u0300-\u036f\u203f-\u2040-]*'

    # I coulda sworn ply would recognize reserved keywords automatically.
    # Apparently not, so here we check for them ourselves.
    kwtoken = reserved.get(t.value, None)
    if kwtoken:
        t.type = kwtoken
    elif t.value in NODE_TYPES:
        # FIXME: technically foo:node is a QNname. We'll lex it as
        # NCNAME COLON FNNAME, which is not a valid construction in our
        # grammar.
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
