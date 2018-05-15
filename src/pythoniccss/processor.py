
from __future__ import print_function
from libparsing import Processor, ensure_str, is_string
from .grammar import grammar, getGrammar
from .model   import Factory, Stylesheet, Element, Block, Macro, MacroInvocation, URL, Node, String, SemanticError
import re, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
PCSS_PATHS = [
	".",
	"lib/pcss",
	"src/pcss"
]

COLOR_PROPERTIES     = (
	"background",
	"background-color",
	"color",
	"gradient"
	"linear-gradient"
)

class PCSSProcessor(Processor):
	"""Creates the model for the CSS stylesheet based on the result returned
	by the grammar. This is essentially an AST-like generator for the grammar."""

	RGB = None

	@classmethod
	def ColorFromName( cls, name ):
		"""Retrieves the (R,G,B) color triple for the color of the given name."""
		if not cls.RGB:
			colors = {}
			# We extract the color names from X11's rgb file
			# SEE: https://en.wikipedia.org/wiki/X11_color_names#Color_name_chart
			with open(os.path.join(BASE, "rgb.txt")) as f:
				# FIXME: Somehow, this creates a sefault
				# for line in f.readlines():
				# 	print (line)
				for line in f.read().split("\n"):
					if not line or line[0] == "!": continue
					r = line[0:4]
					g = line[4:8]
					b = line[8:12]
					r, g, b = (int(_.strip()) for _ in (r,g,b))
					n = line[12:].lower().strip()
					colors[n] = (r, g, b)
			cls.RGB = colors
		name = name.lower().strip()
		if name not in cls.RGB:
			None
		else:
			return cls.RGB[name.lower().strip()]

	def __init__( self, grammar=None, path="."):
		Processor.__init__(self, grammar or getGrammar())
		self.F      = Factory()
		self.path   = path
		self._stylesheets = {}

	def resolvePCSS( self, name ):
		"""Resolves the PCSS file with the given name, or by URL if
		name is @model.URL instance."""
		if isinstance(name, URL):
			rp = os.path.relpath(name.value, self.path)
			ap = os.path.abspath(name.value)
			dp = os.path.normpath(name.value)
			if os.path.exists(rp): return rp
			if os.path.exists(ap): return ap
			if os.path.exists(dp): return dp
			return None
		else:
			name = name.value if isinstance(name,String) else name
			current = os.path.dirname(self.path) if os.path.isfile(self.path) else self.path
			for parent in [current] + PCSS_PATHS:
				for ext in ("", ".pcss"):
					path = os.path.join(parent, name + ext)
					if os.path.exists(path):
						return path
			return False

	# =========================================================================
	# HIGH-LEVEL STRUCTURE
	# =========================================================================

	def onSource( self, match ):
		"""Regroups the lines of the stylesheet based on their indentation."""
		def dispatch( element, stack, guard=None ):
			"""Processes the given element so that it is added to the matching
			parent in the stack. If `guard` is given, then the stack is not
			unwinded past `guard`."""
			if isinstance(element, Stylesheet):
				# Stylesheets are added as direct children of the root
				# (which happens to be a stylesheet)
				for _ in element.content:
					stack[0].add(_)
				return stack
			elif isinstance(element, MacroInvocation):
				# When we register a macro invocation we look for defined
				# blocks and expand them
				if  element.name in ("merge", "extend"):
					sel_name = element.value[0].value
					block    = stack[0].findSelector(sel_name)
					if not block:
						raise SemanticError("`{0}` could not find referenced block: `{1}`".format(element.name, sel_name))
					recursive = element.name == "extend"
					# Like macros, we make sure the stack is not unwound past
					# the head.
					head      = stack[-1]
					# It's important to have a copy of the stack here
					substack  = [] + stack
					for _ in block.content:
						if recursive or not isinstance(_, Node):
							substack = dispatch(_.copy(), substack, head)
				else:
					macro = stack[0].resolve(element.name) or stack[0].findSelector("." + element.name)
					stack[-1].add(element)
					if isinstance(macro, Macro):
						context = macro.apply(element.arguments)
						# We need to preserve the stack and make sure the
						# dispatching does not unwind past the context
						stack[-1].add(context)
						substack = stack + [context]
						# For macros,
						for _ in macro.content:
							_ = _.copy().parent(context)
							substack = dispatch(_, substack, context)
					elif macro:
						raise SemanticError("`{0}` does not resolve `{1}` to macro, got {2}".format(element.name, element.name, macro))
					else:
						raise SemanticError("`{0}()` could not find macro: `{1}`".format(element.name, element.name))
			elif isinstance(element, Macro):
				# Macros are toplevel, so we don't need to take indentation into
				# account.
				while len(stack) > 1: stack.pop()
				stack[0].add(element)
				stack.append(element)
				return stack
			elif isinstance(element, Element):
				if element._indent is not None:
					while stack and stack[-1]._indent != None and stack[-1]._indent >= element._indent and stack[-1] != guard:
						stack.pop()
					assert stack
				stack[-1].add(element)
				if isinstance(element, Node):
					stack.append(element)
			elif isinstance(element, tuple) or isinstance(element, list):
				for _ in element:
					stack = dispatch(_, stack)
			else:
				pass
				# ERROR: Not expected
			return stack
		# We parse the content
		s     = self.F.stylesheet()
		stack = [s]
		for m in match:
			for _ in self.process(m):
				dispatch(_, stack)
		s.balance()
		return s.offsets(match)

	def onBlock( self, match, indent, selections, name, code ):
		# The ordering of statements is deferred to the `onSource` rule
		return [self.F.block(name).select(selections).indent(indent).offsets(match)] + code

	def onBlockName( self, match, name ):
		return name

	def onNamespace( self, match, name ):
		return self.F.module(name).offsets(match)

	def onInclude( self, match, path ):
		rpath = self.resolvePCSS(path)
		if rpath:
			result = self.grammar.parsePath(rpath)
			result = self.process(result)
			return result
		else:
			raise SemanticError("Cannot resolve PCSS file: {0}".format(path))

	def onImport( self, match, source ):
		return self._onImportOrUse(match, source, self.F._import)

	def onUse( self, match, source ):
		return self._onImportOrUse(match, source, self.F.use)

	def _onImportOrUse( self, match, source, factoryMethod ):
		source = source[0]
		source = source.value if isinstance(source,String) else source
		path   = self.resolvePCSS(source)
		if path == self.path:
			raise SemanticError("Stylesheet importing itself: {0} at {1}".format(source, path))
		elif path:
			stylesheet = self.parseStylesheet(path)
			relpath    = os.path.relpath(path ,os.path.dirname(self.path))
			return factoryMethod(source, stylesheet, relpath).offsets(match)
		elif isinstance(source, URL):
			return factoryMethod(source, None).offsets(match)
		else:
			raise SemanticError("Cannot resolve PCSS module: {0}".format(source))

	def parseStylesheet( self, path ):
		if path in self._stylesheets:
			return self._stylesheets[path]
		else:
			result     = self.grammar.parsePath(path)
			stylesheet = PCSSProcessor(path=path).process(result)
			self._stylesheets[path] = stylesheet
			return stylesheet

	def onStatement( self, match ):
		indent  = self.process(match["indent"])
		op      = self.process(match["op"])[0]
		return op.indent(indent)

	def onDirective( self, match ):
		return self.process(match[0])

	def onUnit(self, match, name, value ):
		return self.F.unit(name, value).offsets(match)

	def onMacroDeclaration( self, match, name, parameters ):
		return self.F.macro(name, parameters).offsets(match)

	def onMacroBlock( self, match, indent, type, code):
		return type.add(code).indent(indent)

	def onMacroInvocation( self, match, name, arguments ):
		return self.F.invokemacro(name, arguments).offsets(match)

	def onKeyframesBlock( self, match, indent, name, frames ):
		return self.F.keyframes(name).add(frames).indent(indent).offsets(match)

	def onKeyframe( self, match, indent, selector, code):
		return self.F.keyframe(selector).add(code).indent(indent).offsets(match)

	def onKeyframeSelector( self, match):
		value = self.process(match[0])
		if value == "from":
			return self.F.number(0, "%").offsets(match)
		if value == "to":
			return self.F.number(100, "%").offsets(match)
		value.unit = value.unit or "%"
		return value

	# =========================================================================
	# STATEMENTS
	# =========================================================================

	def onCSSProperty( self, match ):
		"""The main CSS declaration."""
		name      = self.process(match["name"])
		values    = self.process(match["values"])
		values    = self.F.list(values).unwrap() if isinstance(values, list) else values
		important = self.process(match["important"])
		if name in COLOR_PROPERTIES and values:
			if isinstance(values, String):
				rgb = self.ColorFromName(values.value)
				if rgb: values = self.F.rgb(rgb)
		return self.F.property(name, values, important).offsets(match)

	def onAssignment( self, match ):
		"""The statement of a declaration."""
		return self.process(match["declaration"])

	def onVariable( self, match, name, value ):
		"""The declaration of a variable or special directive
		such as @unit."""
		return self.F.var(name, value).offsets(match)

	# =========================================================================
	# EXPRESSION
	# =========================================================================

	def onExpressions( self, match, head, tail):
		tail  = [_[1] for _  in tail]
		return self.F.list([head] + tail, " ").unwrap().offsets(match)

	def onExpressionList( self, match, head, tail):
		tail  = [_[1] for _  in tail]
		return self.F.list([head] + tail, ",").unwrap().offsets(match)

	def onPrefix( self, match ):
		return self.process(match)[0]

	def onSuffix( self, match ):
		return self.process(match[0])

	def onParens( self, match, value ):
		return self.F.parens(value)

	def onParameters( self, match, head, tail ):
		return [head] + [_[1] for _ in tail]

	def onArguments( self, match, head, tail ):
		return [head] + [_[1] for _ in tail]

	def onExpression( self, match, prefix, suffixes ):
		prefix = prefix[1] if not isinstance(prefix, Element) else prefix
		for suffix in suffixes:
			prefix = prefix.suffix(suffix)
		return prefix

	def onCSSInvocation( self, match, name, values ):
		return self.F.invokefunction(name, values)

	def onMethodInvocation( self, match, method, arguments):
		method = method[1] if method else None
		return self.F.invokemethod(method, arguments)

	def onInfixOperation( self, match, op, rvalue):
		return self.F.compute(op, None, rvalue)

	# =========================================================================
	# VALUES
	# =========================================================================

	def onValue( self, match ):
		return self.process(match[0])

	def onNumber( self, match, value, unit ):
		value = float(value) if "." in value else int(value)
		unit  = unit if unit else None
		if unit == "%": value = value / 100.0
		return self.F.number(value, unit)

	def onString( self, match ):
		return self.process(match[0])

	def onURL(self, match ):
		url = self.process(match)[1]
		if url[0] == url[1] and url[0] in "\"'": url = url[1:-1]
		return self.F.url(url)

	def onCOLOR_HEX(self, match ):
		c = (self.process(match)[1])
		while len(c) < 6: c += "0"
		r = int(c[0:2], 16)
		g = int(c[2:4], 16)
		b = int(c[4:6], 16)
		if len(c) > 6:
			a = int(c[6:], 16) / 255.0
			return self.F.rgba((r,g,b,a))
		else:
			return self.F.rgb((r,g,b))

	def onCOLOR_RGB(self, match ):
		c = self.process(match)[1].split(",")
		if len(c) == 3:
			return self.F.rgb([int(_) for _ in c])
		else:
			return self.F.rgba([int(_) for _ in c[:3]] + [float(c[3])])

	def onREFERENCE(self, match):
		return self.F.reference(self.process(match)[1])

	def onSTRING_BQ(self, match ):
		return self.F.rawstring((self.process(match)[1]))

	def onSTRING_DQ(self, match ):
		return self.F.string((self.process(match)[1]), '"')

	def onSTRING_SQ(self, match ):
		return self.F.string((self.process(match)[1]), "'")

	def onSTRING_UQ(self, match ):
		return self.F.string((self.process(match)[0]), None)

	# =========================================================================
	# COMMENTS
	# =========================================================================

	def onCOMMENT( self, match ):
		return self.F.comment(self.process(match)[0][2:])

	def onComment( self, match ):
		return self.F.comment("\n".join(_.value for _ in self.process(match[0])))

	# =========================================================================
	# SELECTIONS
	# =========================================================================

	def onSelections( self, match ):
		head = self.process(match["head"])
		tail = self.process(match["tail"])
		head = [head] + ([_[1] for _ in tail or []])
		return head

	def onSelection( self, match ):
		head = self.process(match["head"])
		tail = self.process(match["tail"])
		for op, sel in tail:
			if sel:
				if not head:
					head = self.F.selector("&")
					head.indent(sel.indent())
				head = head.narrow(sel, op.strip() if op else None)
		return head

	def onSelector( self, match ):
		node       =  self.process(match["node"])
		nid        =  self.process(match["nid"])
		nclass     =  self.process(match["nclass"])
		attributes =  self.process(match["attributes"])
		suffix     =  self.process(match["suffix"])
		node       = node[0] if node else ""
		nid        = nid if nid else ""
		bang_suffix = []
		reg_suffix  = []
		for _ in suffix or ():
			(bang_suffix if _.startswith("!") else reg_suffix).append(_)
		suffix     = "".join(reg_suffix)
		nclass     = "".join(nclass) if nclass else ""
		attributes = "".join(attributes) if attributes else ""
		for _ in bang_suffix:
			attributes+="[data-state~=\"{0}\"]".format(_[1:])
		if (node or nid or nclass or attributes or suffix):
			return self.F.selector(node, nid, nclass, attributes or "", suffix)
		else:
			return None

	def onSelectorNarrower( self, match, op, sel ):
		"""Returns a `(op, selector)` couple."""
		if op: op = op.strip() or " "
		sel = sel or None
		return [op, sel] if (op or sel) else None

	def onAttribute( self, match ):
		name  =  self.process(match["name"])
		value =  self.process(match["value"])
		return "[{0}{1}{2}]".format(name, value[0] if value else "", value[1] if value else "")

	def onAttributes( self, match ):
		head =  self.process(match["head"])
		tail =  self.process(match["tail"])
		assert not tail
		result = "".join([head] + (tail or []))
		return  result

	# =========================================================================
	# INDENTATION
	# =========================================================================

	def onCheckIndent( self, match ):
		return len(self.process(match["tabs"]))

	# =========================================================================
	# GENERIC GRAMMAR RULES
	# =========================================================================

	def processWord(self, result):
		return ensure_str(result)

	def processToken(self, result):
		return ensure_str(result[0])

# EOF
