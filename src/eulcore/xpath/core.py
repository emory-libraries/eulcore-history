import os
import re
from ply import lex, yacc

from eulcore.xpath import lexrules
from eulcore.xpath import parserules

__all__ = [ 'lexer', 'parser', 'parse', 'ptokens', 'sprint' ]

lexdir = os.path.dirname(lexrules.__file__)
lexer = lex.lex(module=lexrules, optimize=1, outputdir=lexdir, reflags=re.UNICODE)

class LexerWrapper(lex.Lexer):
    def token(self):
        self.last = lex.Lexer.token(self)
        return self.last
lexer.__class__ = LexerWrapper

parsedir = os.path.dirname(parserules.__file__)
parser = yacc.yacc(module=parserules, outputdir=parsedir)
parse = parser.parse

def ptokens(s):
    lexer.input(s)
    for tok in lexer:
            print tok

def sprint(obj, stm=None):
    if isinstance(obj, basestring):
        obj = parser.parse(obj, lexer=lexer)

    if stm is None:
        import sys
        stm = sys.stdout
    _sprint(obj, '', stm)

def _sprint(obj, indent, stm):
    if hasattr(obj, 'struct'):
        obj = obj.struct()
    if isinstance(obj, (list, tuple)):
        print >>stm, indent + str(obj[0])
        for item in obj[1:]:
            _sprint(item, indent + '. ', stm)
    else:
        print >>stm, indent + str(obj)
