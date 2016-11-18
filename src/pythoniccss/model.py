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

# -----------------------------------------------------------------------------
#
# SELECTOR
#
# -----------------------------------------------------------------------------

class Selector(object):
	"""Reprents a node selector, include node name, classes, id, attributes
	and suffixes."""

	def __init__( self, node, name, classes, attributes, suffix ):
		self.node       = node
		self.name       = name
		self.classes    = classes
		self.attributes = attributes
		self.suffix     = suffix

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

	def __str__( self ):
		return "{0}{1}{2}{3}{4}".format(self.node, self.name, self.classes, self.attributes, self.suffix)

	def __repr__( self ):
		return "<Selector scope={0} id={1} class={2} attributes={3} suffix={4}@{5}>".format(self.node, self.name, self.classes, self.attributes, self.suffix, id(self))


# -----------------------------------------------------------------------------
#
# SELECTION
#
# -----------------------------------------------------------------------------

class Selection(object):
	"""Represents selectors connected together by selector operators."""

	def __init__( self, selector=None, module=None ):
		assert isinstance(selector, Selector) or not selector
		self.module = module
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
		return Selection(module=self.module).extend(self)

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
		res =  " ".join(str(_) for _ in self.elements if _)
		if self.module:
			return ".use-" + self.module + ((" " + res) if res else "")
		else:
			return res

	def __repr__( self ):
		return "<Selector {0}@{1}>".format(str(self), id(self))

# EOF
