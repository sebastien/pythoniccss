#!/usr/bin/env python2.7
# encoding=utf8 ---------------------------------------------------------------
# Project           : PythonicCSS
# -----------------------------------------------------------------------------
# Author            : FFunction
# License           : BSD License
# -----------------------------------------------------------------------------
# Creation date     : 14-Jul-2013
# Last modification : 12-May-2017
# -----------------------------------------------------------------------------

from __future__ import print_function
from copy import copy
import sys, colorsys

__doc__ = """
Defines an abstract model for CSS stylesheets.
"""

# A list of CSS properties that allow duplicates
ALLOW_DUPLICATES = [
	"cursor",
	"color",
	"background-color",

]

NOTHING = object()
OPERATOR_PRIORITY = {
	"+" : 0,
	"-" : 0,
	"*" : 1,
	"/" : 1,
	"%" : 1,
}

class SyntaxError(Exception):
	pass

class SemanticError(Exception):
	pass

class ImplementationError(Exception):
	pass

def copy( element ):
	"""Returns a copy of the given element."""
	if isinstance(element, Element):
		return element.copy()
	elif isinstance(element, list):
		return [copy(_) for _ in element]
	elif isinstance(element, tuple):
		return tuple(copy(_) for _ in element)
	elif isinstance(element, dict):
		return dict((k,copy(v)) for k,v in element.items())
	else:
		return element

# -----------------------------------------------------------------------------
#
# FACTORY
#
# -----------------------------------------------------------------------------

class Factory(object):

	def stylesheet( self, path ):
		return Stylesheet(path)

	def comment( self, value ):
		return Comment(value)

	def selector( self, node, name="", classes="", attributes="", suffix="" ):
		return Selector( node, name, classes, attributes, suffix )

	def var( self, name, value, decorator=None ):
		return Variable(name, value, decorator)

	def block( self, name=None ):
		return Block(name=name)

	def macro( self, name, arguments=None):
		return Macro(name, arguments)

	def invokemacro( self, name, arguments=None ):
		return MacroInvocation(name, arguments)

	def invokemethod( self, name, arguments=None ):
		return MethodInvocation(name, arguments)

	def invokefunction( self, name, arguments=None ):
		return FunctionInvocation(name, arguments)

	def list( self, value, separator=None ):
		return List(value, separator)

	def keyframes( self, name ):
		return Keyframes(name)

	def keyframe( self, selector ):
		return Keyframe(selector)

	def property( self, name, value, important):
		return Property(name, value, important)

	def url( self, url, path ):
		return URL(url, path)

	def compute( self, op, lvalue, rvalue ):
		op = op.strip()
		if isinstance(rvalue, Computation) and OPERATOR_PRIORITY[op] > OPERATOR_PRIORITY[rvalue.operator]:
			# We have (op, None, rvalue:Computation)
			res = Computation(op, lvalue, rvalue.lvalue())
			rvalue.lvalue(res)
			return  rvalue
		return Computation(op, lvalue, rvalue)

	def parens( self, value ):
		return Parens(value)

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
		return Reference(name)

	def module( self, name):
		return NamespaceDirective(name)

	def unit( self, name, value ):
		return Unit(name, value)

	def _import( self, source, stylesheet, path=None):
		return ImportDirective(source, stylesheet, path)

	def use( self, source, stylesheet, path=None):
		return UseDirective(source, stylesheet, path)

# -----------------------------------------------------------------------------
#
# AST
#
# -----------------------------------------------------------------------------

class TNamed(object):
	"""Trait for a named element, used by the `Element.resolve` method."""

	def __init__( self, name ):
		self.name = name

class Output(object):
	"""A trait that denotes objects that produce significant output (ie. not comments)"""

	def __init__( self ):
		pass

class Element( object ):

	def __init__( self ):
		self._indent  = None
		self._parent  = None
		self.isNode   = False
		self._offsets = [None, None]

	def copy( self ):
		return self.__class__()

	def offsets( self, match ):
		self._offsets[0] = match.offset
		self._offsets[1] = match.offset + match.length
		return self

	def resolve( self, name ):
		if not name:
			return None
		if isinstance( self, Node):
			for _ in self.content:
				if isinstance(_, TNamed) and _.name == name:
					return _
		if self._parent:
			return self._parent.resolve(name)

	def resolveUnit( self, name ):
		if not name: return None
		root = self
		while root._parent:
			root =  root._parent
		return root.resolve(name)

	def findSelector( self, selector, block=None ):
		"""Returns the first rule that matches the given selector."""
		if not selector:
			return None
		imports = []
		if isinstance( self, Node):
			for _ in self.content:
				if isinstance(_, ImportDirective):
					imports.append(_)
				elif isinstance(_, Block) and _ is not block:
					for s in _.selectors():
						if s.expr(namespace=False) == selector:
							return _
			for _ in self.content:
				s = _.findSelector(selector, block)
				if s and s is not block: return s
		# We resolve in imports as well
		for _ in reversed(imports):
			if _.stylesheet:
				s = _.stylesheet.findSelector(selector, block)
				if s: return s
		return None

	def invoke( self, name, arguments ):
		raise SemanticError("{0} does not respond to method `{1}`".format(self, name))

	def root( self ):
		if self._parent:
			return self._parent.root()
		else:
			return self

	def parent( self, value=NOTHING ):
		if value is NOTHING:
			return self._parent
		else:
			self._parent = value
			return self

	def balance( self ):
		pass

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
			slots += [_.name for _ in self.content if isinstance(_, TNamed)]
		if not own and self._parent:
			for _ in self._parent.slots():
				if _ not in slots:
					slots.append(_)
		return slots

class Leaf( Element ):

	def __init__( self, value=None ):
		Element.__init__(self)
		self.value = value
		if isinstance(value, Element):
			value.parent(self)
		elif isinstance(value, tuple) or isinstance(value, list):
			for _ in value:
				if isinstance(_, Element):
					_.parent(self)

	def copy( self ):
		return self.__class__(copy(self.value))

class Node( Element ):

	@classmethod
	def CopyContent( cls, src, dst ):
		for _ in src.content:
			dst.add(_.copy())
		return dst

	def __init__( self ):
		Element.__init__(self)
		self.content = []
		self.isNode  = True

	def getUniqueContent( self ):
		"""Filters out properties that are overriden"""
		result     = []
		properties = {}
		for _ in reversed(self.content):
			if isinstance(_, Property):
				if _.name not in properties or _.name in ALLOW_DUPLICATES:
					result.append(_)
					properties[_.name] = True
			else:
				result.append(_)
		return reversed(result)

	def copy( self ):
		c = self.__class__()
		c.content = []
		for _ in self.content:
			c.add(_.copy())
		return c

	def add( self, value ):
		if isinstance(value, tuple) or isinstance(value, list):
			for _ in value:
				self.add(_)
		else:
			self._add(value)
		return self

	def remove( self, value ):
		if isinstance(value, tuple) or isinstance(value, list):
			for _ in value:
				self.remove(_)
		else:
			self._remove(value)
		return self

	def balance( self ):
		for _ in self.content:
			_.balance()

	def _add( self, value ):
		self.content.append(value)
		value.parent(self)
		return value

	def _remove( self, value ):
		self.content.remove(value)
		value.parent(None)
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

	def suffix( self, suffix ):
		if isinstance(suffix, Invocation):
			suffix.target = self
			return suffix
		if isinstance(suffix, Computation):
			# NOTE: This is where we place the lvalue in a nested computation
			# See Factory.compute for that.
			target = suffix
			while target.lvalue():
				target = target.lvalue()
			target.lvalue(self)
			return suffix
		else:
			raise ImplementationError("Suffix not supported: {0}".format(suffix))

	def eval( self, context=None ):
		return self.value

	def add( self, value ):
		raise ImplementationError("{0}.add not implemented".format(self))

	def mul( self, value ):
		raise ImplementationError("{0}.mul not implemented".format(self))

	def div( self, value ):
		raise ImplementationError("{0}.div not implemented".format(self))

	def sub( self, value ):
		raise ImplementationError("{0}.sub not implemented".format(self))

	def expand( self ):
		return self

class Parens( Value ):

	def expand( self ):
		return self.value.expand()

	def __repr__( self ):
		return "<Parens {0}>".format(self.value)

class Reference( Value ):

	def expand( self ):
		value = self.resolve(self.value)
		if value is None:
			raise SemanticError("Variable `{0}` not defined in {1}".format(self.value, self.parent()))
		return value.expand()

	def add( self, value ):
		return self.expand().add(value)

	def mul( self, value ):
		return self.expand().mul(value)

	def div( self, value ):
		return self.expand().div(value)

	def sub( self, value ):
		return self.expand().sub(value)

	# FIXME: Does not work
	# def invoke( self, name, arguments ):
	# 	return self.value.invoke(name, arguments)

	def eval( self ):
		return self.expand().eval()

class URL( Value ):

	def __init__( self, value, path=None ):
		Value.__init__(self, value)
		self.path = path

	def copy( self ):
		return self.__class__(copy(self.value), copy(self.path))

class RawString( Value ):
	pass

class String( Value ):

	def __init__( self, value, quote=None ):
		Leaf.__init__(self, value)
		self.quote = quote

	def copy( self ):
		return self.__class__(copy(self.value), copy(self.quote))

	def __repr__( self ):
		return "<str:{0}>".format(self.value)

class Number( Value ):

	def __init__( self, value, unit=None ):
		Leaf.__init__(self, value)
		self.unit  = unit
		self._isDirty = True
		self._evaluated = None

	def copy( self ):
		return self.__class__(copy(self.value), copy(self.unit))

	def write( self, stream=sys.stdout):
		stream.write(str(self.value))
		if self.unit: stream.write(self.unit)

	def eval( self ):
		if self._isDirty:
			self._isDirty = False
			custom = self.resolveUnit(self.unit)
			if custom:
				value = custom.value.eval()
				self._evaluated = Number(
					value.value * self.value,
					value.unit
				)
			else:
				self._evaluated = self
		return self._evaluated

	def unify( self, value ):
		a = self.unit
		b = value.unit
		a = self.resolveUnit(a) or a
		b = self.resolveUnit(b) or b
		if not a or not b or a == b:
			return a or b
		else:
			raise SemanticError("Cannot unify {0} with {1}".format(self.unit, unit))

	def convert( self, unit ):
		custom = self.resolveUnit(unit)
		if custom:
			if custom.unit in (self.unit, None):
				return self.mul(custom.value).value
			else:
				raise SemanticError("Cannot convert {0} to {1}".format(self, unit))
		else:
			if not unit or not self.unit or unit == self.unit:
				return self.value
			else:
				raise SemanticError("Cannot convert {0} to {1}".format(self, unit))

	def add( self, value ):
		value = value.eval()
		if isinstance(value, Number):
			return Number(self.value + value.convert(self.unit), self.unify(value))
		else:
			raise ImplementationError("{0}.add({1}) not implemented".format(self, value))

	def sub( self, value ):
		value = value.eval()
		if isinstance(value, Number):
			return Number(self.value - value.convert(self.unit), self.unify(value))
		else:
			raise ImplementationError("{0}.sub({1}) not implemented".format(self, value))

	def mul( self, value ):
		value = value.eval()
		if isinstance(value, Number):
			return Number(float(self.value) * value.convert(self.unit), self.unify(value))
		else:
			raise ImplementationError("{0}.mul({1}) not implemented".format(self, value))

	def div( self, value ):
		value = value.eval()
		if isinstance(value, Number):
			return Number(float(self.value) / value.convert(self.unit), self.unify(value))
		else:
			raise ImplementationError("{0}.div({1}) not implemented".format(self, value))

	def __repr__( self ):
		return "<Number {0}{1}>".format(self.value, self.unit or "", id(self))

class Color( Value ):

	def invoke( self, name, arguments ):
		# FIXME: This is a bit of a hack
		arguments = [_.value if isinstance(_, Number) else _ for _ in arguments or ()]
		if name == "brighten":
			return self.brighten(*arguments)
		elif name == "darken":
			return self.darken(*arguments)
		elif name == "blend":
			return self.blend(*arguments)
		elif name == "fade":
			return self.fade(*arguments)
		else:
			return super(Color, self).invoke(name, arguments)

	def brighten( self, k=0.1 ):
		h,l,s = colorsys.rgb_to_hls(self.value[0], self.value[1], self.value[2])
		r,g,b = colorsys.hls_to_rgb(h, l + k, s)
		if len(self.value) == 3:
			self.value = [r,g,b]
		else:
			self.value = [r,g,b, self.value[3]]
		return self

	def fade( self, k=0.1 ):
		"""Fades the color by multiplying `A` by `1-k`."""
		r,g,b,a = self.rgba()
		return RGBA((r,g,b,min(1.0,max(0,a - a*k))))

	def darken( self, k=0.1 ):
		return self.brighten(0 - k)

	def blend( self, color, k):
		k = k.eval().value
		ca = self.rgba()
		cb = color.rgba()
		r = ca[0] + (cb[0] - ca[0]) * k
		g = ca[1] + (cb[1] - ca[1]) * k
		b = ca[2] + (cb[2] - ca[2]) * k
		a = ca[3] + (cb[3] - ca[3]) * k
		if a >= 1.0:
			return RGB((r,g,b)).normalize()
		else:
			return RGBA((r,g,b,a)).normalize()

	def normalize( self ):
		r = max(0, min(self.value[0], 255))
		g = max(0, min(self.value[1], 255))
		b = max(0, min(self.value[2], 255))
		if len(self.value) > 3:
			a = max(0, min(1.0, self.value[3]))
			self.value = [r,g,b,a]
		else:
			self.value = [r,g,b]
		return self

	def rgb( self ):
		return (self.value[0], self.value[1], self.value[2])

	def rgba( self ):
		return (self.value[0], self.value[1], self.value[2], self.value[3] if len(self.value) > 3 else 1.0)

	def mul( self, value ):
		return self.__class__(self.normalize() * value.value)

	def div( self, value ):
		return self.__class__(self.normalize() / value.value)


class RGB( Color ):
	pass

class RGBA( Color ):
	pass

class List( Leaf, Output ):

	def __init__( self, value, separator=None ):
		Leaf.__init__(self, value)
		assert not value or isinstance(value, list)
		Output.__init__(self)
		self.separator = separator

	def copy( self ):
		return self.__class__(copy(self.value), copy(self.separator))

	def unwrap( self ):
		"""Unwraps the list if it has only one element"""
		if self.value and len(self.value) == 1:
			return self.value[0]
		else:
			return self

# -----------------------------------------------------------------------------
#
# OPERATIONS
#
# -----------------------------------------------------------------------------

class Computation( Value ):

	def __init__( self, operator, lvalue, rvalue=None ):
		Value.__init__(self)
		self.operator = operator
		self._lvalue  = None
		self._rvalue  = None
		self.lvalue(lvalue)
		self.rvalue(rvalue)

	def copy( self ):
		return self.__class__(self.operator, copy(self._lvalue), copy(self._rvalue))

	def lvalue( self, value=NOTHING ):
		if value is NOTHING:
			return self._lvalue
		else:
			if isinstance(value, Element):
				value.parent(self)
			self._lvalue = value
			return self

	def rvalue( self, value=NOTHING ):
		if value is NOTHING:
			return self._rvalue
		else:
			if isinstance(value, Element):
				value.parent(self)
			self._rvalue = value
			return self

	def add( self, value ):
		return self.eval().add(value)

	def mul( self, value ):
		return self.eval().mul(value)

	def div( self, value ):
		return self.eval().div(value)

	def sub( self, value ):
		return self.eval().sub(value)

	def eval( self, context=None ):
		result = None
		lvalue = self.lvalue().eval()
		rvalue = self.rvalue().eval()
		if   self.operator == "*":
			result = lvalue.mul(rvalue)
		elif self.operator == "-":
			result = lvalue.sub(rvalue)
		elif self.operator == "+":
			result = lvalue.add(rvalue)
		elif self.operator == "/":
			result = lvalue.div(rvalue)
		else:
			raise Exception("Unsuported computation operator: {0}".format(self.operator))
		return result

	def expand( self ):
		return self.eval()

	def __repr__( self ):
		return "<Computation {1} {0} {2} at {3}>".format(self.operator, self.lvalue(), self.rvalue(), id(self))

# -----------------------------------------------------------------------------
#
# STATEMENTS
#
# -----------------------------------------------------------------------------

class Comment( Leaf ):
	pass

class Directive( Leaf):
	pass

class TPrivateScope(object):
	pass

# TODO: Refactor to namespace
class NamespaceDirective( Directive, TNamed, TPrivateScope ):

	def __init__( self, value ):
		Directive.__init__(self, value)
		TNamed.__init__(self, "__namespace__")
		TPrivateScope.__init__(self)

class ImportDirective( Directive, TPrivateScope  ):

	def __init__( self, value, stylesheet, path=None ):
		Directive.__init__(self, value)
		TPrivateScope.__init__(self)
		self.stylesheet = stylesheet
		self.path       = path

	# TODO: Should resolve the module

	def copy( self ):
		# NOTE: Not sure that we should copy the stylesheet
		return self.__class__(copy(self.value), self.stylesheet)

class UseDirective(ImportDirective, TPrivateScope ):
	pass

class Unit( Directive, TNamed) :

	def __init__( self, name, value ):
		Directive.__init__(self, value)
		TNamed.__init__(self, name)

	def eval( self ):
		return self.value.eval()

	def copy( self ):
		return self.__class__(self.name, copy(self.value))

class Invocation( Directive ):

	def __init__( self, name, arguments):
		Directive.__init__(self, arguments)
		self.name     = name
		self.arguments = arguments

	def copy( self ):
		return self.__class__(self.name, copy(self.arguments))

class FunctionInvocation( Invocation ):

	def __init__( self, name, arguments):
		Invocation.__init__(self, name, arguments)

class MethodInvocation( Invocation):

	def __init__( self, name, arguments, target=None):
		Invocation.__init__(self, name, arguments)
		self.target = target

	def copy( self ):
		# NOTE: Not sure we should copy the target
		return MethodInvocation(self.name, copy(self.arguments), copy(self.target))

	def eval( self ):
		return self.target.invoke(self.name, self.arguments)

class MacroInvocation( Invocation, Output ):

	def __init__( self, name, arguments):
		Invocation.__init__(self, name, arguments)
		Output.__init__(self)

class Variable( Value, TNamed ):

	def __init__( self, name, value, decorator=None ):
		Value.__init__(self, value)
		TNamed.__init__(self, name)
		self.decorator = decorator

	def eval( self ):
		return self.value.eval()

	def copy( self ):
		# TODO: Might need to copy the value as well
		return self.__class__(self.name, copy(self.value), copy(self.decorator))

	def expand( self ):
		return self.value

class Property( Leaf, Output ):

	def __init__( self, name, value, important=None):
		Leaf.__init__(self, value)
		Output.__init__(self)
		self.name  = name
		self.important = important

	def copy( self ):
		# We need to copy the value as well
		return self.__class__(self.name, self.value.copy(), self.important)

	def __repr__( self ):
		return "<Property {0}={1} at {2}>".format(self.name, self.value, id(self))

# -----------------------------------------------------------------------------
#
#  COMPOSITES
#
# -----------------------------------------------------------------------------

class Context( Node, Output ):
	"""A node that is not tied to a specific syntax but that is able
	to declare slots that will be resolved by children."""

	def __init__( self, arguments, name ):
		Node.__init__(self)
		self.name  = name
		self._indent = 0
		self.slots = {}
		for k in arguments or {}:
			self.set(k, arguments[k])

	def copy( self ):
		return Node.CopyContent(self, self.__class__(dict((k,copy(v)) for k,v in self.slots.items()), self.name))

	def set( self, name, value):
		self.slots[name] = value
		return value

	def has( self, name):
		return name in self.slots

	def get( self, name):
		return self.slots.get(name)

	def resolve( self, name ):
		if not name:
			return None
		if self.has(name):
			return self.get(name)
		else:
			return super(Node, self).resolve(name)

	def __repr__( self ):
		return "<Context for `{0}`:{1} at {2}>".format(self.name, [_ for _ in self.slots.keys()], id(self))

class Block(Node, TNamed):

	def __init__( self, selections=None, name=None ):
		Node.__init__(self)
		TNamed.__init__(self, name)
		self.selections = []
		self._selectors = []
		self._indent    = 0
		self._isDirty   = True
		if selections:
			self.select(selections)

	def copy( self ):
		r = self.__class__([]+self.selections, self.name)
		return Node.CopyContent(self, r)

	def select( self, selection ):
		if isinstance(selection, tuple) or isinstance(selection, list):
			for _ in selection: self.select(_)
		elif selection:
			selection.parent(self)
			self.selections.append(selection)
			self._isDirty = True
		return self

	def balance( self ):
		blocks     = []
		non_blocks = []
		# TODO: There's an opportunity to filter out stuff here
		for _ in self.content:
			_.balance()
			if isinstance(_, Block):
				blocks.append(_)
			else:
				non_blocks.append(_)
		self.content = non_blocks + blocks

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
							# NOTE: Narrow already copies
							rs = prefix.narrow(suffix.copy())
							r.append(rs)
			else:
				r += bs
			module = self.resolve("__namespace__")
			if module:
				namespace = module.value
				r = [_.ns(namespace) for _ in r]
			self._selectors = r
			self._isDirty   = False
		return self._selectors

	def __repr__( self ):
		return "<Block `{0}` at {1}>".format(", ".join(_.expr() for _ in self.selections), id(self))

class Macro( Node, TNamed ):

	def __init__( self, name, parameters=None ):
		Node.__init__(self)
		self._indent = 0
		TNamed.__init__(self, name)
		self.parameters = parameters

	def copy( self ):
		return Node.CopyContent(self, self.__class__(self.name, self.parameters))

	def apply( self, arguments ):
		# NOTE: This has the side-effect of the new block "borrowing" the
		# content. In theory, we should deep-copy the content, but it's
		# OK like that as we're not multi-threading.
		args    = dict((k,arguments[i]) for i,k in enumerate(self.parameters) if i < len(arguments)) if arguments else {}
		context = Context(args, self.name)
		return context

class Keyframes( Node, TNamed ):

	def __init__( self, name ):
		Node.__init__(self)
		TNamed.__init__(self, name)

	def copy( self ):
		return Node.CopyContent(self, self.__class__(self.name))

class Keyframe( Node ):

	def __init__( self, selector ):
		Node.__init__(self)
		self.selector = selector

class Stylesheet(Node):

	def __init__( self, path=None ):
		Node.__init__(self)
		self.units    = {}
		self.path     = path

	def resolve( self, name ):
		v = Node.resolve(self, name)
		if not v:
			for stylesheet in reversed([_.stylesheet for _ in self.content if (isinstance(_, ImportDirective) or isinstance(_, UseDirective)) and _.stylesheet]):
				v = stylesheet.resolve(name)
				if v and not isinstance(v, TPrivateScope):
					return v
		else:
			return v

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
		self.classes    = classes if isinstance(classes, list) else [_.strip() for _ in classes.split(".") if _]
		self.attributes = attributes
		if suffix:
			# NOTE: We need to preserve the `::`
			self.suffix = [] + suffix if isinstance(suffix, list) else [_.replace("∷",":") for _ in suffix.replace("::",":∷").split(":") if _]
		else:
			self.suffix = []
		self.next       = None
		self.namespace  = None

	def ns( self, value ):
		self.namespace = value
		return self

	def copy( self, deep=True ):
		sel = Selector(self.node, self.id, [] + self.classes, self.attributes, [] + self.suffix)
		if deep:
			sel.next = (self.next[0], self.next[1].copy()) if self.next else None
		else:
			sel.next = self.next
		return sel

	def last( self, value=NOTHING ):
		if value is NOTHING:
			return self.next[1].last() if self.next else self
		else:
			tail = self
			while tail.next:
				tail = tail.next[1]
			tail.next = (tail.next[0] if tail.next else None, value)
			return self

	def narrow( self, selector, operator=None):
		"""Returns a copy of this selector prefixed with the given selector."""
		if operator == "<<":
			return selector.narrow(self)
		elif operator == "<":
			return selector.narrow(self, ">")
		else:
			copy       = self.copy(deep=True)
			last       = copy.last()
			bem_prefix = copy.getBEMPrefix()
			bem_suffix = selector.getBEMSuffix()
			if bem_prefix:
				# OK, so this conditional requires some explanation: if we narrow
				# the current selector and the current selector has a BEM prefix,
				# we have the following cases:
				#
				# 1) The new selector has a BEM PREFIX
				#    `.XXX- -YYY`
				#
				# 2) The new selector has no BEM prefix
				#    `.XXX- .YYY` or has a node `.-XXX div`.
				#
				# In case (2) we need to use `.XXX` as a full class prefix,
				# but only if it does not already appear in the last selector (
				# selectors should have their BEM classes expanded at this stage).
				# However, or if copy == last, which means we're directly narrowing
				# the current selector (not its tail).
				if bem_suffix:
					selector = selector.expandBEM(bem_prefix, bem_suffix)
				elif selector.node != "&" and selector.node and (last == copy or not last.hasBEMPrefix(bem_prefix)):
					#if len([_.hasBEMPrefix(bem_prefix) for _ in self.children()]) == 0:
					copy.classes.append(bem_prefix[0:-1])
			if selector.node == "&":
				assert copy.node == "&" or selector.node == "&"
				last.merge(selector)
				# NOTE: We don't need to copy the selector.next as we won't change
				# it
				last.next = selector.next
			else:
				last.next = (operator, selector)
			return copy

	def prefix( self, selector ):
		"""Returns a copy of this selector prefixed with the given selector."""
		return selector.copy().narrow(self)

	def merge( self, selector ):
		"""Merges the given selector with this one. This takes care of the
		'&'. NOTE: This does not return a copy"""
		# NOTE: no copying here
		s             = self
		s.node        = s.node if selector.node == "&" else selector.node
		s.id         += selector.id
		s.classes    += selector.classes
		s.attributes += selector.attributes
		for _ in selector.suffix:
			if _ not in s.suffix:
				s.suffix.append(_)
		return s

	def expandBEM( self, prefix, suffix ):
		"""Expands the BEM suffix to be prefixed with the given prefix in this
		selector and its children."""
		res         = self.copy(False)
		if self.classes:
			res.classes = [prefix + _[1:] if _ and _[0] == "-" else _ for _ in self.classes]
		elif prefix and (self.node or self.attributes or self.id):
			# When there is no classes, we add the prefix
			res.classes = [prefix]
		res.next    = (res.next[0], res.next[1].expandBEM(prefix, suffix)) if res.next else None
		return res

	def hasBEMPrefix( self, prefix="-" ):
		for _ in self.classes:
			if _.startswith(prefix) or _.startswith("-"): return True
		return False

	# FIXME: This should be cached as it can be quite expensive to construct
	def expr( self, single=False, namespace=True ):
		classes     = []
		bem_classes = []
		for _ in self.classes:
			if not _: continue
			is_suffix = _.startswith("-")
			is_prefix = _.endswith("-")
			if is_prefix:
				bem_classes.append(_)
				# If there is an attribute selector or a next selector with no BEM suffix
				if len(self.suffix) > 0 or self.attributes:
					classes.insert(0,_[:-1])
			elif  is_suffix:
				bem_classes.append(_)
			else:
				classes.insert(0,_)
		prefix   = u""
		suffixes = []
		# We add the namespace
		if namespace and self.namespace:
			prefix = ".use-{0}".format(self.namespace)
		# We add the suffixes
		if not single and self.next:
			# In this case the selector has a next selector
			op, sel = self.next
			if op and op != " ":
				suffixes.append(op)
			# We add the BEM classes that are not contained in the next selector
			bem_to_add = [_ for _ in bem_classes if not sel.hasBEMPrefix(_)]
			classes += [self._stripBEM(_) for _ in bem_to_add]
			suffixes.append(sel.expr(namespace=False))
		else:
			# BEM classes are always first
			classes = [self._stripBEM(_) for _ in bem_classes] + classes
		# And now we output the result
		suffixes = (" ".join(_ for _ in suffixes if _)) if suffixes else ""
		classes  = ("." + ".".join(set(classes))) if classes else ""
		suffix   = "".join(":" + _ for _ in self.suffix)
		sel      = u"{0}{1}{2}{3}{4}".format(self.node, self.id, classes, self.attributes, suffix)
		# In the case where we have a module definition an & rule as a direct
		# child, we remove the & and make it relative to the module, otherwise
		# it defaults to `*`.
		if sel and sel[0] == "&" and self.node == "&" and not self.id:
			if prefix:
				sel = sel[1:]
			else:
				sel = "*" + sel[1:]
		# This supports the special case where we have a  `&[data-XXX]` as a root
		res = prefix
		if sel:
			if sel[0] == "[":
				res += sel
			else:
				res += (" " if res else "") + sel
		if suffixes:
			res += (" " if res else "") + suffixes
		if res.endswith("&"):
			res = res[:-1].strip() or ".__namespace__"
		return res

	def _stripBEM( self, text ):
		if text.startswith("-"): text = text[1:]
		if text.endswith("-"):   text = text[:-1]
		return text

	def getBEMPrefix( self ):
		prefix = None
		for name in self.classes:
			if name.endswith("-"):
				prefix = name
				break
		if self.next:
			return self.next[1].getBEMPrefix() or prefix
		else:
			return prefix

	def getBEMSuffix( self ):
		for name in self.classes:
			if name.startswith("-"): return name
		if self.next:
			return self.next[1].getBEMSuffix()
		return None

	def isBEMPrefix( self ):
		for _ in self.classes:
			if _.endswith("-"):
				return True
		return self.next and self.next[1].isBEMPrefix() or False

	def isBEMSuffix( self ):
		for _ in self.classes:
			if _.startswith("-"):
				return True
		return self.next and self.next[1].isBEMSuffix() or False

	def isBEM( self ):
		return self.isBEMPrefix() or self.isBEMSuffix()

	def children( self ):
		sel = self
		while sel and sel.next:
			sel, n = sel.next
			yield n

	def __repr__( self ):
		return "<Selector `{0}` at {1}>".format(self.expr(), id(self))

# EOF - vim: ts=4 sw=4 noet
