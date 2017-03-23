#!/usr/bin/env python2.7
# encoding=utf8 ---------------------------------------------------------------
# Project           : PythonicCSS
# -----------------------------------------------------------------------------
# Author            : FFunction
# License           : BSD License
# -----------------------------------------------------------------------------
# Creation date     : 23-Mar-2017
# Last modification : 23-Mar-2017
# -----------------------------------------------------------------------------

from __future__ import print_function
import sys

from .model import *

# -----------------------------------------------------------------------------
#
# CSS WRITER
#
# -----------------------------------------------------------------------------

class CSSWriter( object ):

	def __init__( self ):
		self.output     = sys.stdout
		self.isOpen     = None

	def write( self, element, path=None ):
		for _ in self.on(element):
			self._write(_)
		self.output.flush()

	def _write( self, value ):
		if isinstance(value, unicode) or isinstance(value, str):
			self.output.write(value)
		elif value:
			for _ in value:
				self._write(_)

	def on( self, element ):
		if isinstance(element, Comment):
			pass
		elif isinstance(element, Macro):
			pass
		elif isinstance(element, Stylesheet):
			yield self.onStylesheet(element)
		elif isinstance(element, Block):
			yield self.onBlock(element)
		elif isinstance(element, Invocation):
			yield self.onInvocation(element)
		elif isinstance(element, Property):
			yield self.onProperty(element)
		elif isinstance(element, Selector):
			yield self.onSelector(element)
		elif isinstance(element, String):
			yield self.onString(element)
		elif isinstance(element, Number):
			yield self.onNumber(element)
		elif isinstance(element, RGB):
			yield self.onRGB(element)
		elif isinstance(element, RGBA):
			yield self.onRGBA(element)
		elif isinstance(element, List):
			yield self.onList(element)
		elif isinstance(element, Reference):
			yield self.onReference(element)
		elif isinstance(element, Variable):
			yield self.onVariable(element)
		elif isinstance(element, Computation):
			yield self.onComputation(element)
		else:
			raise Exception("Writer.write: {0} not supported".format(element))

	def onStylesheet( self, element ):
		for _ in element.content:
			yield self.write(_)
		yield "}" if self.isOpen else ""

	def onBlock( self, element ):
		# Here we only output the selectors if we know we have one
		# direct child with significant output.
		has_content = next((_ for _ in element.content if isinstance(_, Output)), False)
		if has_content:
			if self.isOpen:
				yield "}\n"
				self.isOpen = False
			sel = element.selectors()
			l = len(sel) - 1
			for i,_ in enumerate(sel):
				yield self.on(_)
				if i < l:
					yield ", "
					yield (", ")
		if has_content:
			yield " {\n"
			self.isOpen = True
		for _ in element.content:
			yield self.on(_)

	def onSelector( self, element ):
		yield element.expr()

	def onInvocation( self, element ):
		import ipdb;ipdb.set_trace()

	def onMacroInvocation( self, element ):
		pass
		# macro = self.resolve(self.name)
		# if not macro:
		# 	raise SyntaxError("Macro cannot be resolved: {0}".format(self.name))
		# if not isinstance(macro, Macro):
		# 	raise SyntaxError("Macro invocation does not resolve to a macro: {0} = {1}".format(self.name, macro))
		# block = macro.apply(self.arguments, self.parent())
		# block.write(stream)

	def onProperty( self, element ):
		yield "\t"
		yield element.name
		yield ":"
		if element.value:
			assert isinstance(element.value, Node) or isinstance(element.value, Leaf), "Value neither node or leaf: {0} in {1}".format(element.value, self)
			yield self.on(element.value)
		if element.important:
			yield "important"
		yield ";\n"

	def onComputation( self, element ):
		yield self.on(element.eval())

	def onList( self, element ):
		last = len(element.value) - 1
		for i,_ in enumerate(element.value):
			yield self.on(_)
			if i < last:
				yield (element.separator or " ")

	def onReference( self, element ):
		yield self.on(element.expand())

	def onVariable( self, element ):
		yield self.on(element.expand())

	def onRGB( self, element ):
		yield ("rgba({0},{1},{2})".format(*element.value))

	def onRGBA( self, element ):
		yield ("rgba({0},{1},{2})".format(*element.value))

	def onNumber( self, element ):
		value = element.value
		if element.unit == "%":
			value = value * 100
			if value == int(value):
				value = int(value)
		yield "{0}{1}".format(value, element.unit or "")

	def onKeyframe( self, element ):
		assert None
		yield ("\t")
		if self.selector.value == 100 and self.selector.unit == "%":
			yield ("to")
		elif self.selector.value == 0 and self.selector.unit == "%":
			yield ("from")
		else:
			self.selector.write(stream)
		yield (" {\n")
		for _ in self.content:
			yield ("\t")
			_.write(stream)
		yield ("\t}\n")

	def onString( self, element ):
		if element.quote: yield (element.quote)
		yield (element.value)
		if element.quote: yield (element.quote)

	def onRawString( self, element ):
		assert None
		yield (element.value)

	def onURL( self, element ):
		assert None
		if element.quote: yield (element.quote)
		yield (element.value)
		if element.quote: yield (element.quote)


	def onKeyframes( self, element ):
		assert None
		yield ("@keyframes ")
		yield (self.name)
		yield (" {\n")
		for _ in self.content:
			_.write(stream)
		yield ("}\n")




