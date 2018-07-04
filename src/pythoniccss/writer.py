# encoding=utf8 ---------------------------------------------------------------
# Project           : PythonicCSS
# -----------------------------------------------------------------------------
# Author            : FFunction
# License           : BSD License
# -----------------------------------------------------------------------------
# Creation date     : 23-Mar-2017
# Last modification : 12-May-2017
# -----------------------------------------------------------------------------

from __future__ import print_function
import sys, types, io

IS_PYTHON3 = sys.version_info.major >= 3

from .model import *

PREFIXABLE_PROPERTIES = (
	"animation",
	"appearance",
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
		# NOTE: In Python2 and Python3 sys.std{out,err} don't have the same
		# type. They're binary/str in Python2 and unicode/str in Python3
		if isinstance(self.output, io.TextIOBase):
			self._writeUnicode(value)
		else:
			self._writeBinary(value)

	def _writeUnicode( self, value ):
		if isinstance(value, types.GeneratorType) or isinstance(value, list) or isinstance(value, tuple):
			for _ in value: self._writeUnicode(_)
		elif IS_PYTHON3 and isinstance(value, str):
			self.output.write(value)
		elif not IS_PYTHON3 and isinstance(value, unicode):
			self.output.write(value)
		elif isinstance(value, bytes):
			self.output.write(value.decode("utf-8"))
		elif not IS_PYTHON3 and isinstance(value, str):
			self.output.write(value.decode("utf-8"))
		elif value:
			raise ValueError("Does not know how to write value: `{0}`".format(repr(value)))

	def _writeBinary( self, value ):
		if isinstance(value, types.GeneratorType) or isinstance(value, list) or isinstance(value, tuple):
			for _ in value: self._writeBinary(_)
		elif IS_PYTHON3 and isinstance(value, str):
			self.output.write(value.encode("utf-8"))
		elif not IS_PYTHON3 and isinstance(value, unicode):
			self.output.write(value.encode("utf-8"))
		elif isinstance(value, bytes):
			self.output.write(value)
		elif not IS_PYTHON3 and isinstance(value, str):
			self.output.write(value)
		elif value:
			raise ValueError("Does not know how to write value: `{0}`".format(repr(value)))

	def on( self, element ):
		if isinstance(element, Comment):
			pass
		elif isinstance(element, NamespaceDirective):
			pass
		elif isinstance(element, UseDirective):
			yield self.onUseDirective(element)
		elif isinstance(element, ImportDirective):
			yield self.onImportDirective(element)
		elif isinstance(element, Macro):
			pass
		elif isinstance(element, MacroInvocation):
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
		for _ in element.getUniqueContent():
			yield self.on(_)

	def onContext( self, element ):
		for _ in element.content:
			yield self.on(_)

	def onSelector( self, element ):
		if self._namespace is self:
			self._namespace = element.resolve("__namespace__")
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
		yield "url(" + element.value + ")"

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
		path   = element.path
		source = element.value
		if not path:
			if isinstance(source, URL):
				path = source.value
			elif isinstance(source, String):
				path = source.value
		if path:
			yield "@import url(\"{0}\");".format(path.replace(".pcss", ".css"))

	def onUseDirective( self, element ):
		# NOTE: We don't need to do anything
		pass

	def _findSelector( self, element, selector ):
		s = self._selectors.get(selector) or element.root().findSelector(selector)
		if s: self._selectors[selector] = s
		return s

# EOF
