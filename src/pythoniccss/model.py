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

from __future__ import print_function
import sys

__doc__ = """
Defines an abstract model for CSS stylesheets.
"""

NOTHING = object()

class SyntaxError(Exception):
	pass

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

	def selector( self, node, name="", classes="", attributes="", suffix="" ):
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

class Named:
	"""Trait for a named element, used by the `Element.resolve` method."""

	def __init__( self, name ):
		self.name = name

class Output:
	"""A trait that denotes objects that produce significant output (ie. not comments)"""

class Element( object ):

	def __init__( self ):
		self._indent = None
		self._parent  = None

	def resolve( self, name ):
		if isinstance( self, Node):
			for _ in self.content:
				if isinstance(_, Named) and _.name == name:
					return _
		if self._parent:
			return self._parent.resolve(name)

	def parent( self, value=NOTHING ):
		if value is NOTHING:
			return self._parent
		else:
			self._parent = value
			return self

	def ancestors( self ):
		if self._parent:
			return [self._parent] + self._parent.ancestors()
		else:
			return []

	def ancestor( self, like ):
		if self._parent:
			return self._parent if isinstance(self._parent, like) else self._parent.ancestor(like)
		else:
			return None

	def indent( self, value=NOTHING ):
		if value is NOTHING:
			return self._indent
		else:
			self._indent = value
			return self

	def write( self, stream=sys.stdout ):
		stream.write("/* {0}.write not implemented */".format(self.__class__.__name__))

	def slots( self, own=False ):
		slots = []
		if isinstance( self, Node ):
			slots += [_.name for _ in self.content if isinstance(_, Named)]
		if not own and self._parent:
			for _ in self._parent.slots():
				if _ not in slots:
					slots.append(_)
		return slots

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
		if isinstance(value, Block):
			parent = self.lastWithIndent(value._indent, Node)
			if not (parent is self or parent is None):
				assert parent._indent < value._indent
				parent.add(value)
				return value
		if self._indent is not None:
			value._indent = self._indent + 1 if value._indent is None else value._indent
		self.content.append(value)
		value.parent(self)
		return value

	def iter( self, predicate=None ):
		for _ in self.content:
			if predicate is None or predicate(_):
				yield _

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

class Value( Leaf, Output ):

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

	def write( self, stream=sys.stdout ):
		stream.write("url(")
		stream.write(self.value)
		stream.write(")")

class RawString( Value ):

	def write( self, stream=sys.stdout ):
		stream.write(self.value)

class String( Value ):

	def __init__( self, value, quote=None ):
		Leaf.__init__(self, value)
		self.quote = quote

	def write( self, stream=sys.stdout ):
		if self.quote: stream.write(self.quote)
		stream.write(self.value)
		if self.quote: stream.write(self.quote)

class Number( Value ):

	def __init__( self, value, unit=None ):
		Leaf.__init__(self, value)
		self.unit  = unit

	def write( self, stream=sys.stdout):
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

	def write( self, stream=sys.stdout):
		stream.write("{0}{1}".format(self.eval(), self.unit or ""))

class RGB( Value ):

	def write( self, stream=sys.stdout):
		stream.write("rgb({0},{1},{2})".format(*self.value))

class RGBA( Value ):

	def write( self, stream=sys.stdout):
		stream.write("rgba({0},{1},{2})".format(*self.value))

class List( Leaf, Output ):

	def __init__( self, value, separator=None ):
		Leaf.__init__(self, value)
		self.separator = separator

	def unwrap( self ):
		if self.value and len(self.value) == 1:
			return self.value[0]
		else:
			return self

	def write( self, stream=sys.stdout):
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

	def write( self, stream=sys.stdout):
		self.eval().write(stream)

# -----------------------------------------------------------------------------
#
# STATEMENTS
#
# -----------------------------------------------------------------------------

class Comment( Leaf ):

	def write( self, stream=sys.stdout):
		pass

class Directive( Leaf):

	def apply( self, context ):
		raise NotImplementedError

class ModuleDirective( Directive, Named ):

	def __init__( self, value ):
		Directive.__init__(self, value)
		Named.__init__(self, "__module__")

	def apply( self, context ):
		context.set("__module__", self.value)

	def write( self, stream=sys.stdout):
		pass

class MacroInvocation( Directive ):

	def __init__( self, name, arguments):
		Directive.__init__(self, arguments)
		self.name = name
		self.arguments = arguments

	def write( self, stream=sys.stdout):
		macro = self.resolve(self.name)
		if not macro:
			raise SyntaxError("Macro cannot be resolved: {0}".format(self.name))
		if not isinstance(macro, Macro):
			raise SyntaxError("Macro invocation does not resolve to a macro: {0} = {1}".format(self.name, macro))
		block = macro.apply(self.arguments, self.parent())
		block.write(stream)

class Variable( Directive ):

	def __init__( self, name, value, decorator=None ):
		Directive.__init__(self, value)
		self.name = name
		self.decorator = decorator

	def write( self, stream=sys.stdout):
		pass

class Property( Leaf, Output ):

	def __init__( self, name, value, important=None):
		Leaf.__init__(self)
		self.name  = name
		self.value = value
		self.important = important

	def write( self, stream=sys.stdout):
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

class Context( Node ):
	"""A node that is not tied to a specific syntax but that is able
	to declare slots that will be resolved by children."""

	def __init__( self, arguments, parent ):
		Node.__init__(self)
		self.slots = {}
		for k in arguments or {}:
			self.set(k, arguments[k])
		self.parent(parent)

	def set( self, name, value):
		self.slots[name] = value
		return value

	def has( self, name):
		return name in self.slots

	def get( self, name):
		return self.slots.get(name)

	def resolve( self, name ):
		if self.has(name):
			return self.get(name)
		else:
			return super(Node, self).resolve(name)

	def write( self, stream=sys.stdout):
		for _ in self.content:
			_.write(stream)

class Block(Node):

	def __init__( self, selections=None ):
		Node.__init__(self)
		self.selections = []
		self._selectors = []
		self._indent    = 0
		self._isDirty   = True
		if selections:
			self.select(selections)

	def select( self, selection ):
		if isinstance(selection, tuple) or isinstance(selection, list):
			for _ in selection: self.select(_)
		else:
			self.selections.append(selection)
			self._isDirty = True
		return self

	# FIXME: Attempts at pruning out duplicates
	# def add( self, value ):
	# 	if isinstance(value, Property) and next(self.iter(lambda _:isinstance(_,Property) and _.name == value.name), False):
	# 		return self
	# 	else:
	# 		return super(Block, self).add(value)

	def parent( self, value=NOTHING ):
		if value is not NOTHING: self._isDirty = True
		return super(Node, self).parent(value)

	def selectors( self ):
		if self._isDirty:
			r  = []
			pb = self.ancestor(Block)
			ps = [_ for _ in pb.selectors()] if pb else []
			bs = self.selections
			if ps:
				if not bs:
					r += [_.copy() for _ in ps]
				else:
					for prefix in ps:
						for suffix in bs:
							r.append(prefix.copy().narrow(suffix.copy()))
			else:
				r += bs
			module = self.resolve("__module__")
			if module:
				namespace = module.value
				r = [_.ns(namespace) for _ in r]
			self._selectors = r
			self._isDirty   = False
		return self._selectors

	def write( self, stream=sys.stdout):
		# Here we only output the selectors if we know we have one
		# direct child with significant output.
		if next((_ for _ in self.content if isinstance(_, Output)), False):
			sel = self.selectors()
			l = len(sel) - 1
			for i,_ in enumerate(sel):
				_.write(stream)
				if i < l:
					stream.write(", ")
			if sel:
				stream.write(":\n")
		for _ in self.content:
			_.write(stream)

	def __repr__( self ):
		return "<Block `{0}` at {1}>".format(", ".join(_.expr() for _ in self.selections), id(self))

class Macro( Node, Named ):

	def __init__( self, name, parameters=None ):
		Node.__init__(self)
		Named.__init__(self, name)
		self.parameters = parameters

	def apply( self, arguments, parent ):
		# NOTE: This has the side-effect of the new block "borrowing" the
		# content. In theory, we should deep-copy the content, but it's
		# OK like that as we're not multi-threading.
		return Context(arguments, parent).add(self.content)

	def write( self, stream=sys.stdout):
		pass

class Stylesheet(Node):

	def __init__( self ):
		Node.__init__(self)



	def write( self, stream=sys.stdout ):
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

	def __init__( self, node="", id="", classes="", attributes="", suffix="" ):
		Leaf.__init__(self)
		self.node       = node
		self.id         = id
		self.classes    = classes
		self.attributes = attributes
		self.suffix     = suffix
		self.next       = None
		self.namespace  = None

	def ns( self, value ):
		self.namespace = value
		return self

	def copy( self ):
		sel = Selector(self.node, self.id, self.classes, self.attributes, self.suffix)
		sel.next = (self.next[0], self.next[1].copy()) if self.next else None
		return sel

	def last( self, value=NOTHING ):
		if value is NOTHING:
			return self.next[1].last() if self.next else self
		else:
			tail = self
			while tail.next:
				tail = tail.next[1]
			tail.next = (tail.next[0], value)
			return self

	def narrow( self, selector, operator=None):
		"""Returns a copy of this selector prefixed with the given selector."""
		last = self.last()
		if self.isBEMPrefix() and selector.isBEMSuffix():
			last.mergeBEM(selector)
			last.next = selector.next
		elif selector.node == "&":
			assert self.node == "&" or selector.node == "&"
			last.merge(selector)
			last.next = selector.next
		else:
			last.next = (operator, selector)
		return self

	def prefix( self, selector ):
		"""Returns a copy of this selector prefixed with the given selector."""
		return selector.copy().narrow(self)

	def merge( self, selector ):
		"""Merges the given selector with this one. This takes care of the
		'&'."""
		self.node        = self.node if selector.node == "&" else selector.node
		self.id         += selector.id
		self.classes    += selector.classes
		self.attributes += selector.attributes
		self.suffix     += selector.suffix
		return self


	def mergeBEM( self, selector ):
		pa=[] ; ca=[]
		for _ in self.classes.split("."):
			if not _: continue
			(pa if _.endswith("-") else ca).append(_)
		pb=[] ; cb=[]
		for _ in selector.classes.split("."):
			if not _: continue
			(pb if _.startswith("-") else cb).append(_)
		assert len(pa) == 1, "Expected 1 BEM prefix, got: {0}".format(pa)
		assert len(pb) == 1, "Expected 1 BEM suffix, got: {0}".format(pb)
		classes = ".".join([pa[0] + pb[0][1:]] + ca + cb)
		classes = "." + classes if classes else ""
		self.merge(selector)
		self.classes = classes
		return self

	def expr( self, single=False, namespace=True ):
		classes = self.classes
		if classes:
			classes = ".".join(_[0:-1] if _.endswith("-") else _ for _ in classes.split("."))
		res = u"{0}{1}{2}{3}{4}".format(self.node, self.id, classes, self.attributes, self.suffix)
		if namespace and self.namespace:
			res = ".use-{0} ".format(self.namespace) + res
		if not single and self.next:
			op, sel = self.next
			res += " "
			if op and op != " ":
				res += op
				res += " "
			res += sel.expr(namespace=False)
		return res

	def isBEMPrefix( self ):
		return self.classes.endswith("-") or "-." in self.classes

	def isBEMSuffix( self ):
		return self.classes.startswith("-") or ".-" in self.classes

	def isBEM( self ):
		return self.isBEMPrefix() or self.isBEMSuffix()

	def write( self, stream=sys.stdout ):
		stream.write(self.expr())

	def __repr__( self ):
		return "<Selector `{0}` at {1}>".format(self.expr(), id(self))

# EOF
