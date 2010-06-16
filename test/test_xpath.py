#!/usr/bin/env python

import unittest

from eulcore import xpath
from eulcore.xpath import ast

from testcore import main

class ParseTest(unittest.TestCase):
    def test_nametest_step(self):
        xp = xpath.parse('''author''')
        self.assert_(isinstance(xp, ast.Step))
        self.assert_(xp.axis is None) # or should this be 'child', the default?
        self.assert_(isinstance(xp.node_test, ast.NameTest))
        self.assert_(xp.node_test.prefix is None)
        self.assertEqual('author', xp.node_test.name)
        self.assertEqual(0, len(xp.predicates))

    def test_nodetype_step(self):
        xp = xpath.parse('''text()''')
        self.assert_(isinstance(xp, ast.Step))
        self.assert_(isinstance(xp.node_test, ast.NodeType))
        self.assertEqual('text', xp.node_test.name)

    def test_axis(self):
        xp = xpath.parse('''ancestor::lib:book''')
        self.assert_(isinstance(xp, ast.Step))
        self.assertEqual('ancestor', xp.axis)
        self.assertEqual('lib', xp.node_test.prefix)
        self.assertEqual('book', xp.node_test.name)

    def test_relative_path(self):
        xp = xpath.parse('''book//author/first-name''')
        self.assert_(isinstance(xp, ast.BinaryExpression))
        self.assert_(isinstance(xp.left, ast.BinaryExpression))
        self.assertEqual('book', xp.left.left.node_test.name)
        self.assertEqual('//', xp.left.op)
        self.assertEqual('author', xp.left.right.node_test.name)
        self.assertEqual('/', xp.op)
        self.assertEqual('first-name', xp.right.node_test.name)

    def test_absolute_path(self):
        xp = xpath.parse('''/book//author''')
        self.assert_(isinstance(xp, ast.AbsolutePath))
        self.assertEqual('/', xp.op)
        self.assertEqual('book', xp.relative.left.node_test.name)

    def test_step_predicate(self):
        xp = xpath.parse('''book[author]''')
        self.assertEqual('book', xp.node_test.name)
        self.assertEqual(1, len(xp.predicates))
        self.assertEqual('author', xp.predicates[0].node_test.name)

    def test_function(self):
        xp = xpath.parse('''author[position() = 1]''')
        self.assert_(isinstance(xp.predicates[0], ast.BinaryExpression))
        self.assertEqual('=', xp.predicates[0].op)
        self.assert_(isinstance(xp.predicates[0].left, ast.FunctionCall))
        self.assertEqual('position', xp.predicates[0].left.name)
        self.assertEqual(0, len(xp.predicates[0].left.args))
        self.assertEqual(1, xp.predicates[0].right)

    def test_variable(self):
        xp = xpath.parse('''title[substring-after(text(), $pre:separator) = "world"]''')
        self.assertEqual('title', xp.node_test.name)
        self.assert_(isinstance(xp.predicates[0], ast.BinaryExpression))
        self.assertEqual('=', xp.predicates[0].op)
        self.assertEqual('world', xp.predicates[0].right) # no quotes, just a string
        self.assert_(isinstance(xp.predicates[0].left, ast.FunctionCall))
        self.assertEqual('substring-after', xp.predicates[0].left.name)
        self.assertEqual(2, len(xp.predicates[0].left.args))
        self.assert_(isinstance(xp.predicates[0].left.args[0], ast.Step))
        self.assertEqual('text', xp.predicates[0].left.args[0].node_test.name)
        self.assert_(isinstance(xp.predicates[0].left.args[1], ast.VariableReference))
        self.assertEqual(('pre', 'separator'), xp.predicates[0].left.args[1].name)

    def test_predicated_expression(self):
        xp = xpath.parse('''(book or article)[author/last-name = "Jones"]''')
        self.assert_(isinstance(xp, ast.PredicatedExpression))
        self.assert_(isinstance(xp.base, ast.BinaryExpression))
        self.assertEqual('book', xp.base.left.node_test.name)
        self.assertEqual('or', xp.base.op)
        self.assertEqual('article', xp.base.right.node_test.name)

        self.assertEqual(1, len(xp.predicates))
        self.assertEqual('=', xp.predicates[0].op)
        self.assertEqual('Jones', xp.predicates[0].right)
        self.assertEqual('/', xp.predicates[0].left.op)
        self.assertEqual('author', xp.predicates[0].left.left.node_test.name)
        self.assertEqual('last-name', xp.predicates[0].left.right.node_test.name)

if __name__ == '__main__':
    main()
