#!/usr/bin/env python2.7
# encoding=utf8 ---------------------------------------------------------------
# Project           : PythonicCSS
# -----------------------------------------------------------------------------
# Author            : FFunction
# License           : BSD License
# -----------------------------------------------------------------------------
# Creation date     : 14-Jul-2013
# Last modification : 18-Nov-2016
# -----------------------------------------------------------------------------

__doc__ = """
Defines an abstract model for CSS stylesheets.
"""

NOTHING = object()

# -----------------------------------------------------------------------------
#
# FACTORY
#
# -----------------------------------------------------------------------------

class Factory(object):

	def stylesheet( self ):
		return Stylesheet()

	def comment( self, value ):
		return Comment(value)

	def selector( self, node, name, classes, attributes, suffix ):
		return Selector( node, name, classes, attributes, suffix )

	def var( self, name, value, decorator=None ):
		return Variable(name, value, decorator)

	def block( self ):
		return Block()

	def macro( self, name, arguments=None):
		return Macro(name, arguments)

	def invokemacro( self, name, arguments=None ):
		return MacroInvocation(name, arguments)

	def list( self, value, separator=None ):
		return List(value, separator)

	def property( self, name, value, important):
		return Property(name, value, important)

	def url( self, url ):
		return URL(text)

	def rgb( self, rgb ):
		return RGB(rgb)

	def rgba( self, rgba ):
		return RGBA(rgba)

	def string( self, text, quoted=None ):
		return String(text, quoted)

	def number( self, value, unit ):
		return Number(value, unit)

	def rawstring( self, text ):
		return RawString(text)

	def reference( self, name ):
		return Reference(text)

	def directive( self, name, value):
		if name == "@module":
			return ModuleDirective(value)
		else:
			raise Exception("Directive not implemented: {0}".format(name))

# -----------------------------------------------------------------------------
#
# AST
#
# -----------------------------------------------------------------------------

class Element( object ):

	def __init__( self ):
		self._indent = None
		self._parent  = None

	def parent( self, value=NOTHING ):
		if value is NOTHING:
			return self._parent
		else:
			self._parent = value
			return self

	def indent( self, value=NOTHING ):
		if value is NOTHING:
			return self._indent
		else:
			self._indent = value
			return self

	def write( self, stream ):
		stream.write("/* {0}.write not implemented */".format(self.__class__.__name__))

class Leaf( Element ):

	def __init__( self, value=None ):
		Element.__init__(self)
		self.value = value


class Node( Element ):

	def __init__( self ):
		Element.__init__(self)
		self.content = []

	def add( self, value ):
		if isinstance(value, tuple) or isinstance(value, list):
			for _ in value:
				self.add(_)
		else:
			self._add(value)
		return self

	def _add( self, value ):
		if self._indent is not None:
			value._indent = self._indent + 1 if value._indent is None else value._indent
		self.content.append(value)
		value.parent = self
		return value

	def lastWithIndent( self, indent, like=None ):
		for i in range(len(self.content) - 1, -1, -1):
			element = self.content[i]
			if element._indent < indent:
				if like is None or isinstance(element, like):
					return element
		return None

# -----------------------------------------------------------------------------
#
# VALUES
#
# -----------------------------------------------------------------------------

class Value( Leaf ):

	def suffix( self, operator, rvalue ):
		return Computation(operator, self, rvalue)

	def eval( self, context=None ):
		return self.value

	def add( self, value ):
		raise NotImplementedError

	def mul( self, value ):
		raise NotImplementedError

	def div( self, value ):
		raise NotImplementedError

	def sub( self, value ):
		raise NotImplementedError

class Reference( Value ):
	pass

class URL( Value ):

	def write( self, stream ):
		stream.write("url(")
		stream.write(self.value)
		stream.write(")")

class RawString( Value ):

	def write( self, stream ):
		stream.write(self.value)

class String( Value ):

	def __init__( self, value, quote=None ):
		Leaf.__init__(self, value)
		self.quote = quote

	def write( self, stream ):
		if self.quote: stream.write(self.quote)
		stream.write(self.value)
		if self.quote: stream.write(self.quote)

class Number( Value ):

	def __init__( self, value, unit=None ):
		Leaf.__init__(self, value)
		self.unit  = unit

	def write( self, stream ):
		stream.write(str(self.value))
		if self.unit: stream.write(self.unit)

	def add( self, value ):
		if isinstance(value, Number):
			return Number(self.eval() + value.eval(), self.mergeunit(value.unit))
		else:
			raise NotImplementedError

	def sub( self, value ):
		if isinstance(value, Number):
			return Number(self.eval() - value.eval(), self.mergeunit(value.unit))
		else:
			raise NotImplementedError

	def mul( self, value ):
		if isinstance(value, Number):
			return Number(self.eval() * value.eval(), self.mergeunit(value.unit))
		else:
			raise NotImplementedError

	def div( self, value ):
		if isinstance(value, Number):
			return Number(self.eval() / value.eval(), self.mergeunit(value.unit))
		else:
			raise NotImplementedError

	def mergeunit( self, b):
		a = self.unit
		if a and not b:
			return a
		if b and not a:
			return b
		if a == b:
			return a
		raise Exception("Cannot cast unify units {0} and {1}".format(a, b))

	def write( self, stream ):
		stream.write("{0}{1}".format(self.eval(), self.unit or ""))

class RGB( Value ):

	def write( self, stream ):
		stream.write("rgb({0},{1},{2})".format(*self.value))

class RGBA( Value ):

	def write( self, stream ):
		stream.write("rgba({0},{1},{2})".format(*self.value))

class List( Leaf ):

	def __init__( self, value, separator=None ):
		Leaf.__init__(self, value)
		self.separator = separator

	def unwrap( self ):
		if self.value and len(self.value) == 1:
			return self.value[0]
		else:
			return self

	def write( self, stream ):
		last = len(self.value) - 1
		for i,_ in enumerate(self.value):
			_.write(stream)
			if i < last:
				stream.write(self.separator or " ")

# -----------------------------------------------------------------------------
#
# OPERATIONS
#
# -----------------------------------------------------------------------------

class Computation( Value ):

	def __init__( self, operator, lvalue, rvalue=None ):
		self.operator = operator
		self.lvalue   = lvalue
		self.rvalue   = rvalue

	def eval( self, context=None ):
		result = None
		if   self.operator == "*":
			result = self.lvalue.mul(self.rvalue)
		elif self.operator == "-":
			result = self.lvalue.sub(self.rvalue)
		elif self.operator == "+":
			result = self.lvalue.add(self.rvalue)
		elif self.operator == "/":
			result = self.lvalue.div(self.rvalue)
		else:
			raise Exception("Unsuported computation operator: {0}".format(self.operator))
		return result

	def write( self, stream ):
		self.eval().write(stream)

# -----------------------------------------------------------------------------
#
# STATEMENTS
#
# -----------------------------------------------------------------------------

class Comment( Leaf ):

	def write( self, stream ):
		stream.write("//")
		stream.write(self.value)
		stream.write("\n")

class Directive( Leaf):

	def apply( self, context ):
		raise NotImplementedError

class ModuleDirective( Directive ):

	def apply( self, context ):
		context.set("__module__", self.value)

	def write( self, stream ):
		pass

class MacroInvocation( Directive ):

	def __init__( self, name, arguments):
		Directive.__init__(self, arguments)
		self.name  = name

	def write( self, stream ):
		pass

class Variable( Directive ):

	def __init__( self, name, value, decorator=None ):
		Directive.__init__(self, value)
		self.name = name
		self.decorator = decorator

	def write( self, stream ):
		stream.write("/* ")
		if self.decorator:
			stream.write(self.decorator)
			stream.write(" ")
		stream.write(self.name)
		stream.write(" = ")
		self.value.write(stream)
		stream.write(" */")

class Property( Leaf ):

	def __init__( self, name, value, important=None):
		Leaf.__init__(self)
		self.name  = name
		self.value = value
		self.important = important

	def write( self, stream ):
		stream.write("\t")
		stream.write(self.name)
		stream.write(":")
		if self.value:
			assert isinstance(self.value, Node) or isinstance(self.value, Leaf), "Value neither node or leaf: {0} in {1}".format(self.value, self)
			self.value.write(stream)
		if self.important:
			stream.write("important")
		stream.write(";\n")

# -----------------------------------------------------------------------------
#
#  COMPOSITES
#
# -----------------------------------------------------------------------------

class Block(Node):

	def __init__( self, selections=None ):
		Node.__init__(self)
		self.selections = []
		self._selectors = []
		self._indent    = 0
		self._isDirty   = False
		if selections:
			self.select(selections)

	def select( self, selection ):
		if isinstance(selection, tuple) or isinstance(selection, list):
			for _ in selection: self.select(_)
		else:
			self.selections.append(selection)
			self._isDirty = True
		return self

	def parent( self, value=NOTHING ):
		if value is not NOTHING: self._isDirty = True
		return super(Node, self).parent(value)

	def selectors( self ):
		if self._isDirty:
			r = []
			s = [_.copy() for _ in self.parent.selectors()] if isinstance(self.parent, Block) else []
			for p in s:
				for q in self.selections:
					r.append(p.narrow(q))
			self._selectors = r if s else self.selections
		return self._selectors

	def write( self, stream ):
		for _ in self.selectors():
			_.write(stream)
		stream.write(":\n")
		for _ in self.content:
			_.write(stream)

class Macro(Node):

	def __init__( self, name, parameters=None ):
		Node.__init__(self)
		self.name = name
		self.parameters = parameters

	def write( self, stream ):
		stream.write("/* @macro {0} {1} */".format(self.name, self.parameters or ""))


class Stylesheet(Node):

	def _add( self, value ):
		if isinstance(value, Block):
			parent = self.lastWithIndent(value._indent, Node)
			if not (parent is self or parent is None):
				assert parent._indent < value._indent
				parent.add(value)
			else:
				super(Stylesheet, self)._add(value)
		else:
			super(Stylesheet, self)._add(value)
		return self

	def write( self, stream ):
		for _ in self.content:
			_.write(stream)

# -----------------------------------------------------------------------------
#
# SELECTOR
#
# -----------------------------------------------------------------------------

class Selector(Leaf):
	"""Reprents a node selector, include node name, classes, id, attributes
	and suffixes. Selectors can be chained together"""

	def __init__( self, node, id, classes, attributes, suffix ):
		Leaf.__init__(self)
		self.node       = node
		self.id         = id
		self.classes    = classes
		self.attributes = attributes
		self.suffix     = suffix
		self.next       = None

	def copy( self ):
		sel = Selector(self.node, self.id, self.classes, self.attributes, self.suffix)
		sel.next = (self.next[0], self.next[1].copy()) if self.next else None
		return sel

	def tail( self, value=NOTHING ):
		if value is NOTHING:
			return self.next[1].tail() if self.next else self
		else:
			tail = self
			while tail.next:
				tail = tail.next[1]
			tail.next = (tail.next[0], value)
			return self

	def narrow( self, selector, operator=None):
		"""Returns a copy of this selector prefixed with the given selector."""
		if selector.node == "&":
			assert operator is None or not operator.strip()
			res  = self.copy()
			tail = res.tail()
			tail.merge(selector)
			return res
		else:
			tail = self.tail()
			tail.next = (operator, selector)
			return self

	def prefix( self, selector ):
		"""Returns a copy of this selector prefixed with the given selector."""
		return selector.copy().narrow(self)

	def merge( self, selector ):
		"""Merges the given selector with this one. This takes care of the
		'&'."""
		assert self.node == "&" or selector.node == "&"
		self.node        = self.node if selector.node == "&" else selector.node
		self.id         += selector.id
		self.classes    += selector.classes
		self.attributes += selector.attributes
		self.suffix     += selector.suffix
		return self

	def write( self, stream ):
		stream.write("{0}{1}{2}{3}{4}".format(self.node, self.id, self.classes, self.attributes, self.suffix))
		if self.next:
			op, sel = self.next
			stream.write(" ")
			if op and op != " ":
				stream.write(op)
				stream.write(" ")
			sel.write(stream)

	def __repr__( self ):
		return "<Selector node={0} id={1} class={2} attributes={3} suffix={4}@{5}>".format(self.node, self.id, self.classes, self.attributes, self.suffix, id(self))

# EOF
