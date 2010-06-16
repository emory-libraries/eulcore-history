class UnaryExpression(object):
    def __init__(self, op, right):
        self.op = op
        self.right = right

    def struct(self):
        return [self.op, self.right]

class BinaryExpression(object):
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right

    def struct(self):
        return [self.op, self.left, self.right]

class PredicatedExpression(object):
    def __init__(self, base, predicates=None):
        self.base = base
        self.predicates = predicates or []

    def append_predicate(self, pred):
        self.predicates.append(pred)

    def struct(self):
        if self.predicates:
            return [ '()[]', self.base ] + self.predicates
        else:
            return self.base

class AbsolutePath(object):
    def __init__(self, op='/', relative=None):
        self.op = op
        self.relative = relative

    def struct(self):
        return [self.op, self.relative]

class Step(object):
    def __init__(self, axis, node, predicates):
        self.axis = axis
        self.node = node
        self.predicates = predicates

    def struct(self):
        name = str(self.node)
        if self.axis is not None:
            name = self.axis + '::' + name
        if self.predicates:
            return [name + '[]'] + self.predicates
        else:
            return name

class NodeTest(object):
    def __init__(self, prefix, name):
        self.prefix = prefix
        self.name = name

    def __str__(self):
        if self.prefix:
            return '%s:%s' % (self.prefix, self.name)
        else:
            return self.name

class AbbreviatedStep(object):
    def __init__(self, abbr):
        self.abbr = abbr

    def struct(self):
        return self.abbr

class VariableReference(object):
    def __init__(self, name):
        self.name = name

    def struct(self):
        return '$' + self.name

class FunctionCall(object):
    def __init__(self, prefix, name, args):
        self.prefix = prefix
        self.name = name
        self.args = args

    def struct(self):
        return [self.name + '()'] + self.args
