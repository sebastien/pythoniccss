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


PREFIXABLE_PROPERTIES = (
	"animation",
	"border-radius",
	"box",
	"box-align",
	"box-shadow",
	"background-size",
	"column-width",
	"column-gap",
	"column-count",
	"column-span",
	"filter",
	"transition-property",
	"transition-duration",
	"transition-timing-function",
	"transform",
	"transform-origin",
	"transform-style",
	"perspective",
	"perspective-origin",
	"box-sizing",
	"backface-visibility",
	"image-rendering",
	"user-select",
	"white-space-collapsing",
)

PREFIXABLE_PROPERTIES_OVERRIDES = {
	"-ms-box"       : "-ms-flexbox",
	"-ms-box-align" : "-ms-flex-align",
}

PREFIXES = (
	"",
	"-moz-",
	"-webkit-",
	"-o-",
	"-ms-",
)

# -----------------------------------------------------------------------------
#
# CSS WRITER
#
# -----------------------------------------------------------------------------

class CSSWriter( object ):

	def __init__( self, output=sys.stdout ):
		self.output     = output
		self.isOpen     = None
		self._namespace = None
		self._selectors = []

	def write( self, element ):
		self._namespace = self
		self._selectors = {}
		for _ in self.on(element):
			self._write(_)
		self.output.flush()

	def _write( self, value ):
		if isinstance(value, unicode):
			self.output.write(value.encode("utf8"))
		elif isinstance(value, str):
			self.output.write(value)
		elif value:
			for _ in value:
				self._write(_)

	def on( self, element ):
		if isinstance(element, Comment):
			pass
		elif isinstance(element, ModuleDirective):
			pass
		elif isinstance(element, ImportDirective):
			yield self.onImportDirective(element)
		elif isinstance(element, Macro):
			pass
		elif isinstance(element, Unit):
			pass
		elif isinstance(element, Stylesheet):
			yield self.onStylesheet(element)
		elif isinstance(element, Block):
			yield self.onBlock(element)
		elif isinstance(element, Context):
			yield self.onContext(element)
		elif isinstance(element, FunctionInvocation):
			yield self.onFunctionInvocation(element)
		elif isinstance(element, MethodInvocation):
			yield self.onMethodInvocation(element)
		elif isinstance(element, MacroInvocation):
			yield self.onMacroInvocation(element)
		elif isinstance(element, Property):
			yield self.onProperty(element)
		elif isinstance(element, Selector):
			yield self.onSelector(element)
		elif isinstance(element, String):
			yield self.onString(element)
		elif isinstance(element, RawString):
			yield self.onRawString(element)
		elif isinstance(element, URL):
			yield self.onURL(element)
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
		elif isinstance(element, Parens):
			yield self.onParens(element)
		elif isinstance(element, Variable):
			yield self.onVariable(element)
		elif isinstance(element, Computation):
			yield self.onComputation(element)
		elif isinstance(element, Keyframes):
			yield self.onKeyframes(element)
		elif isinstance(element, Keyframe):
			yield self.onKeyframe(element)
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
		for s in element.selectors():
			self._selectors[s.expr(namespace=False)] = element
		if has_content:
			if self.isOpen:
				yield "}\n"
				self.isOpen = False
			sel = element.selectors()
			l = len(sel) - 1
			for i,_ in enumerate(sel):
				if i == 0:
					yield "\n"
				yield self.on(_)
				if i < l:
					yield ",\n"
		if has_content:
			yield " {\n"
			self.isOpen = True
		for _ in element.content:
			yield self.on(_)

	def onContext( self, element ):
		for _ in element.content:
			yield self.on(_)

	def onSelector( self, element ):
		if self._namespace is self:
			self._namespace = element.resolve("__module__")
		yield element.expr()

	def onFunctionInvocation( self, element ):
		name  = element.name
		value = element.value
		yield name
		yield "("
		yield self.on(element.arguments)
		yield ")"

	def onMethodInvocation( self, element ):
		for _ in self.on(element.eval()):
			yield _

	def onMacroInvocation( self, element ):
		if element.name == "merge":
			if len(element.arguments) != 1:
				raise SemanticError("merge() macro only takes one argument")
			elif not isinstance(element.arguments[0], String):
				raise SemanticError("merge() expects a string as argument")
			else:
				selector = element.arguments[0].value
				name     = selector
				macro    = self._findSelector(element, selector)
				if macro:
					macro = macro.copy()
					macro.content = [_ for _ in macro.content if not isinstance(_, Block)]
		elif element.name == "extend":
			if len(element.arguments) != 1:
				raise SemanticError("extend() macro only takes one argument")
			elif not isinstance(element.arguments[0], String):
				raise SemanticError("extend() expects a string as argument")
			else:
				selector = element.arguments[0].value
				name     = selector
				macro    = self._findSelector(element, selector)
		else:
			# Macro resolves as selectors by default
			macro = element.resolve(element.name) or self._findSelector(element, "." + element.name)
			name  = element.name
		if not macro:
			raise SyntaxError("Macro {0} cannot be resolved: {1}".format(element.name, name))
		if isinstance(macro, Macro):
			block = macro.apply(element.arguments, element.parent())
			for _ in self.on(block):
				yield _
		elif isinstance(macro, Block):
			block = macro.apply(element.parent())
			for _ in self.on(block):
				yield _
		else:
			raise SyntaxError("Macro invocation does not resolve to a macro: {0} = {1}".format(element.name, macro))

	def onProperty( self, element ):
		name  = element.name
		value = element.value
		lines = ((p, name, value) for p in PREFIXES) if name in PREFIXABLE_PROPERTIES else ((None, name, value),)
		for p, n, value in lines:
			yield "  "
			if p: yield p
			yield n
			yield ": "
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
		sep  = (element.separator or "") + " "
		for i,_ in enumerate(element.value):
			yield self.on(_)
			if i < last:
				yield sep

	def onReference( self, element ):
		yield self.on(element.expand())

	def onVariable( self, element ):
		if element.parent().__class__ not in (Context, Block, Stylesheet, Macro):
			yield self.on(element.expand())

	def onRGB( self, element ):
		r,g,b = element.value
		yield ("#{0:02X}{1:02X}{2:02X}".format(int(r), int(g), int(b)))

	def onRGBA( self, element ):
		r,g,b,a = element.value
		yield ("rgba({0:d},{1:d},{2:d},{3:0.2f})".format(int(r), int(g), int(b), a))

	def onNumber( self, element ):
		element = element.eval()
		value   = element.value
		if element.unit == "%":
			value = value * 100
		if value == int(value):
			value = int(value)
			yield "{0:d}{1}".format(value, element.unit or "")
		else:
			value = "{0:0.3f}".format(value)
			while value[-1] in "0.": value = value[:-1]
			yield "{0}{1}".format(value, element.unit or "")

	def onRawString( self, element ):
		yield (element.value)

	def onParens( self, element ):
		yield "("
		yield (self.on(element.value))
		yield ")"

	def onString( self, element ):
		if element.quote: yield (element.quote)
		yield (element.value)
		if element.quote: yield (element.quote)

	def onURL( self, element ):
		yield element.value

	def onKeyframes( self, element ):
		yield ("@keyframes ")
		yield (element.name)
		yield (" {\n")
		for _ in element.content:
			yield self.on(_)
		yield ("}\n")

	def onKeyframe( self, element ):
		yield ("\t")
		if element.selector.value == 100 and element.selector.unit == "%":
			yield ("to")
		elif element.selector.value == 0 and element.selector.unit == "%":
			yield ("from")
		else:
			yield self.on(element.selector)
		yield (" {\n")
		for _ in element.content:
			yield ("\t")
			yield self.on(_)
		yield ("\t}\n")

	def onImportDirective( self, element ):
		# We don't output imports for now
		pass

	def _findSelector( self, element, selector ):
		s = self._selectors.get(selector) or element.root().findSelector(selector)
		if s: self._selectors[selector] = s
		return s

# EOF
