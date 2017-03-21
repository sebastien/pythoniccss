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

class Factory(object):

	def stylesheet( self ):
		return Stylesheet()

	def comment( self, value ):
		return Comment(value)

	def selector( self, node, name, classes, attributes, suffix ):
		return Selector( node, name, classes, attributes, suffix )

	def block( self ):
		return Block()

	def list( self, value, separator=None ):
		return List(value, separator)

	def property( self, name, value, important):
		return Property(name, value, important)

	def url( self, url ):
		return URL(text)

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

class Element( object ):

	def write( self, stream ):
		stream.write("/* {0}.write not implemented */\n".format(self.__class__.__name__))

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
			self.content += value
		else:
			self.content.append(value)
		return self

class Value( Leaf ):

	def suffix( self, suffix ):
		print ("SUFFIXING", suffix)
		return self

class RGB( Value ):
	pass

class RGBA( Value ):
	pass

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

class List( Leaf ):

	def __init__( self, value, separator=None ):
		Leaf.__init__(self, value)
		self.separator = separator

	def write( self, stream ):
		last = len(self.value) - 1
		for i,_ in enumerate(self.value):
			_.write(stream)
			if i < last:
				stream.write(self.separator or " ")


class Comment( Leaf ):

	def write( self, stream ):
		stream.write("//")
		stream.write(self.value)
		stream.write("\n")

class Property( Leaf ):

	def __init__( self, name, value, important=None):
		Leaf.__init__(self)
		self.name  = name
		self.value = value
		self.important = important

	def write( self, stream ):
		stream.write(self.name)
		stream.write(":")
		if self.value:
			assert isinstance(self.value, Node) or isinstance(self.value, Leaf), "Value neither node or leaf: {0} in {1}".format(self.value, self)
			self.value.write(stream)
		if self.important:
			stream.write("important")
		stream.write(";\n")

class Directive( Leaf):

	def apply( self, context ):
		raise NotImplementedError

class ModuleDirective( Directive ):

	def apply( self, context ):
		context.set("__module__", self.value)

class Context(Element):

	def __init__( self ):
		self.values = {}
		self.parent = None

	def set( self, key, value ):
		self.values[key] = value

	def get( self, key ):
		if key in self.values:
			return self.values
		else:
			return self.parent.get(key) if self.parent else None

class Block(Node):

	def __init__( self, selections=None ):
		Node.__init__(self)
		self.selections = []
		self.indent     = 0
		if selections:
			self.select(selections)

	def select( self, selections ):
		self.selections += selections
		return self

	def write( self, stream ):
		i = "\t" * self.indent
		j = i + "\t"
		stream.write(i)
		for _ in self.selections:
			_.write(stream)
		stream.write(":\n")
		for _ in self.content:
			stream.write(j)
			_.write(stream)
			stream.write("\n")



class Stylesheet(Node):

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
	and suffixes."""

	def __init__( self, node, name, classes, attributes, suffix ):
		self.node       = node
		self.name       = name
		self.classes    = classes
		self.attributes = attributes
		self.suffix     = suffix
		self.next       = None

	def tail( self ):
		return self.next[1].tail() if self.next else self

	def narrow( self, operator, selector ):
		tail = self.tail()
		tail.next = (operator, selector)
		return self

	def merge( self, selector ):
		"""Merges the given selector with this one. This takes care of the
		'&'."""
		res= Selector(
			self.node if selector.node == "&" else selector.node
			,self.name       + selector.name
			,self.classes    + selector.classes
			,self.attributes + selector.attributes
			,self.suffix     + selector.suffix
		)
		return res

	def isSelf( self ):
		"""Tells if the selector's node is an `&`."""
		return self.node == "&"

	def write( self, stream ):
		stream.write("{0}{1}{2}{3}{4}".format(self.node, self.name, self.classes, self.attributes, self.suffix))

	def __repr__( self ):
		return "<Selector scope={0} id={1} class={2} attributes={3} suffix={4}@{5}>".format(self.node, self.name, self.classes, self.attributes, self.suffix, id(self))


# -----------------------------------------------------------------------------
#
# SELECTION
#
# -----------------------------------------------------------------------------

class Selection(object):
	"""Represents selectors connected together by selector operators."""

	def __init__( self, selector=None, module=None, parent=None ):
		assert isinstance(selector, Selector) or not selector
		self.module = module
		self.parent = parent
		if selector:
			self.elements = ["", selector]
		else:
			self.elements = []

	def head( self ):
		return self.elements[1]

	def last( self ):
		return self.elements[-1]

	def rest( self ):
		return self.elements[2:]

	def copy( self ):
		return Selection(module=self.module, parent=self.parent).extend(self)

	def extend( self, selection ):
		assert isinstance(selection, Selection)
		head = selection.head()
		if head and head.isSelf():
			self.elements[-1] = self.elements[-1].merge(head)
			self.elements += selection.rest()
		else:
			self.elements += selection.elements
		return self

	def add( self, operator, selector ):
		assert isinstance(operator, str)
		if operator.strip() or selector:
			assert isinstance(selector, Selector) or not selector
			self.elements.append(operator.strip())
			self.elements.append(selector)
		return self

	def __str__( self ):
		# NOTE: This fixed BEM-style stuff
		res =  " ".join(str(_) for _ in self.elements if _).replace("- .-", "-")
		if res.endswith("-"): res = res[:-1]
		if self.parent:
			res = str(self.parent) + " " + res
		elif self.module:
			return ".use-" + self.module + ((" " + res) if res else "")
		else:
			return res

	def __repr__( self ):
		return "<Selector {0}@{1}>".format(str(self), id(self))

# EOF
