from itertools import chain

__all__ = [
    'serialize',
    'UnaryExpression',
    'BinaryExpression',
    'PredicatedExpression',
    'AbsolutePath',
    'Step',
    'NameTest',
    'NodeType',
    'AbbreviatedStep',
    'VariableReference',
    'FunctionCall',
    ]

def serialize(xp_ast):
    return ''.join(_serialize(xp_ast))

def _serialize(xp_ast):
    if hasattr(xp_ast, '_serialize'):
        for tok in xp_ast._serialize():
            yield tok
    elif isinstance(xp_ast, basestring):
        # FIXME: There are several interesting cases where this is wrong.
        yield repr(xp_ast)
    else:
        yield str(xp_ast)

class UnaryExpression(object):
    def __init__(self, op, right):
        self.op = op
        self.right = right

    def __repr__(self):
        return '<%s %s %s>' % (self.__class__.__name__,
                self.op, serialize(self.right))

    def _serialize(self):
        yield self.op
        for tok in _serialize(self.right):
            yield tok

    def struct(self):
        return [self.op, self.right]

KEYWORDS = set(['or', 'and', 'div', 'mod'])
class BinaryExpression(object):
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right

    def __repr__(self):
        return '<%s %s %s %s>' % (self.__class__.__name__,
                serialize(self.left), self.op, serialize(self.right))

    def _serialize(self):
        for tok in _serialize(self.left):
            yield tok

        if self.op in KEYWORDS:
            yield ' '
            yield self.op
            yield ' '
        else:
            yield self.op
            
        for tok in _serialize(self.right):
            yield tok

    def struct(self):
        return [self.op, self.left, self.right]

class PredicatedExpression(object):
    def __init__(self, base, predicates=None):
        self.base = base
        self.predicates = predicates or []

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__,
                serialize(self))

    def append_predicate(self, pred):
        self.predicates.append(pred)

    def _serialize(self):
        yield '('
        for tok in _serialize(self.base):
            yield tok
        yield ')'
        for pred in self.predicates:
            yield '['
            for tok in _serialize(pred):
                yield tok
            yield ']'

    def struct(self):
        if self.predicates:
            return [ '()[]', self.base ] + self.predicates
        else:
            return self.base

class AbsolutePath(object):
    def __init__(self, op='/', relative=None):
        self.op = op
        self.relative = relative

    def __repr__(self):
        return '<%s %s %s>' % (self.__class__.__name__,
                self.op, serialize(self.relative))

    def _serialize(self):
        yield self.op
        for tok in _serialize(self.relative):
            yield tok

    def struct(self):
        return [self.op, self.relative]

class Step(object):
    def __init__(self, axis, node_test, predicates):
        self.axis = axis
        self.node_test = node_test
        self.predicates = predicates

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__,
                serialize(self))

    def _serialize(self):
        if self.axis == '@':
            yield '@'
        elif self.axis:
            yield self.axis
            yield '::'

        for tok in self.node_test._serialize():
            yield tok

        for predicate in self.predicates:
            yield '['
            for tok in _serialize(predicate):
                yield tok
            yield ']'

    def struct(self):
        name = str(self.node_test)
        if self.axis is not None:
            name = self.axis + '::' + name
        if self.predicates:
            return [name + '[]'] + self.predicates
        else:
            return name

class NameTest(object):
    def __init__(self, prefix, name):
        self.prefix = prefix
        self.name = name

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__,
                serialize(self))

    def _serialize(self):
        if self.prefix:
            yield self.prefix
            yield ':'
        yield self.name

    def __str__(self):
        return ''.join(self._serialize())

class NodeType(object):
    def __init__(self, name, literal=None):
        self.name = name
        self.literal = literal

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__,
                serialize(self))

    def _serialize(self):
        yield self.name
        yield '('
        if self.literal is not None:
            for tok in _serialize(self.literal):
                yield self.literal
        yield ')'

    def __str__(self):
        return ''.join(self._serialize())

class AbbreviatedStep(object):
    def __init__(self, abbr):
        self.abbr = abbr

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__,
                serialize(self))

    def _serialize(self):
        yield self.abbr

    def struct(self):
        return self.abbr

class VariableReference(object):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__,
                serialize(self))

    def _serialize(self):
        yield '$'
        prefix, localname = self.name
        if prefix:
            yield prefix
            yield ':'
        yield localname

    def struct(self):
        return '$' + self.name

class FunctionCall(object):
    def __init__(self, prefix, name, args):
        self.prefix = prefix
        self.name = name
        self.args = args

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__,
                serialize(self))

    def _serialize(self):
        if self.prefix:
            yield self.prefix
            yield ':'
        yield self.name
        yield '('
        if self.args:
            for tok in _serialize(self.args[0]):
                yield tok

            for arg in self.args[1:]:
                yield ','
                for tok in _serialize(arg):
                    yield tok
        yield ')'

    def struct(self):
        return [self.name + '()'] + self.args
