"""Core XPath parsing glue.

This module builds a lexer and parser for XPath expressions for import into
eulcore.xpath. To understand how this module builds the lexer and parser, it
is helpful to understand how the `ply <http://www.dabeaz.com/ply/>`_ module
works.

Node that most client applications will import these objects from
eulcore.xpath, not directly from here."""

import os
import re
from ply import lex, yacc

from eulcore.xpath import lexrules
from eulcore.xpath import parserules
from eulcore.xpath.ast import serialize

__all__ = [ 'lexer', 'parser', 'parse', 'serialize' ]

# build the lexer. This will generate a lextab.py in the eulcore.xpath
# directory. Unfortunately the lexer generated by default by ply doesn't
# track the last token returned, which we need for xpath lexing (see the
# lexrules comments for details). To overcome that, we create a wrapper
# class that extends token() to record the last token returned, and we
# dynamically set the lexer's __class__ to this wrapper. That's pretty weird
# and ugly, but Python allows it. If you can find a prettier solution to the
# problem then I welcome a fix.
lexdir = os.path.dirname(lexrules.__file__)
lexer = lex.lex(module=lexrules, optimize=1, outputdir=lexdir, 
    reflags=re.UNICODE)

class LexerWrapper(lex.Lexer):
    def token(self):
        self.last = lex.Lexer.token(self)
        return self.last
lexer.__class__ = LexerWrapper

# build the parser. This will generate a parsetab.py in the eulcore.xpath
# directory. Other than that, it's much less exciting than the lexer
# wackiness.
parsedir = os.path.dirname(parserules.__file__)
parser = yacc.yacc(module=parserules, outputdir=parsedir)
parse = parser.parse

def ptokens(s):
    '''Lex a string as XPath tokens, and print each token as it is lexed.
    This is used primarily for debugging. You probably don't want this
    function.'''

    lexer.input(s)
    for tok in lexer:
            print tok
