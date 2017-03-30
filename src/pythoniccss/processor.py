
from __future__ import print_function
from libparsing import Processor, ensure_str, is_string
from .grammar import grammar, getGrammar
from .model   import Factory, Stylesheet, Element, Node, String, SemanticError
import re, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))

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

	def __init__( self, grammar=None, output=sys.stdout, path="."):
		Processor.__init__(self, grammar or getGrammar())
		self.F      = Factory()
		self.output = output
		self.path   = path

	def resolvePCSS( self, name ):
		current = os.path.dirname(self.path) if os.path.isfile(self.path) else self.path
		for parent in (".", current):
			for ext in ("", ".pcss"):
				path = os.path.join(parent, name + ext)
				if os.path.exists(path):
					return path
		return None

	# =========================================================================
	# HIGH-LEVEL STRUCTURE
	# =========================================================================

	def onSource( self, match ):
		def dispatch( element, stack ):
			if isinstance(element, Stylesheet):
				for _ in element.content:
					stack[0].add(_)
				return stack
			elif isinstance(element, Element):
				if element._indent is not None:
					while stack and stack[-1]._indent >= element._indent:
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
		return s

	def onBlock( self, match, indent, selections, name, code ):
		# The ordering of statements is deferred to the `onSource` rule
		return [self.F.block(name).select(selections).indent(indent)] + code

	def onBlockName( self, match, name ):
		return name

	def onModule( self, match, name ):
		return self.F.module(name)

	def onInclude( self, match, path ):
		rpath = self.resolvePCSS(path)
		if rpath:
			result = self.grammar.parsePath(rpath)
			result = self.process(result)
			return result
		else:
			raise SemanticError("Cannot resolve PCSS file: {0}".format(path))

	def onImport( self, match, source ):
		return self.F._import(source[0])

	def onStatement( self, match ):
		indent  = self.process(match["indent"])
		op      = self.process(match["op"])[0]
		return op.indent(indent)

	def onDirective( self, match ):
		return self.process(match[0])

	def onUnit(self, match, name, value ):
		return self.F.unit(name, value)

	def onMacroDeclaration( self, match, name, parameters ):
		return self.F.macro(name, parameters)

	def onMacroBlock( self, match, indent, type, code):
		return type.add(code).indent(indent)

	def onMacroInvocation( self, match, name, arguments ):
		return self.F.invokemacro(name, arguments)

	def onKeyframesBlock( self, match, indent, name, frames ):
		return self.F.keyframes(name).add(frames).indent(indent)

	def onKeyframe( self, match, indent, selector, code):
		return self.F.keyframe(selector).add(code).indent(indent)

	def onKeyframeSelector( self, match):
		value = self.process(match[0])
		if value == "from":
			return self.F.number(0, "%")
		if value == "to":
			return self.F.number(100, "%")
		value.unit = value.unit or "%"
		return value

	# =========================================================================
	# STATEMENTS
	# =========================================================================

	def onCSSProperty( self, match ):
		"""The main CSS declaration."""
		name      = self.process(match["name"])
		values    = self.F.list(self.process(match["values"])).unwrap()
		important = self.process(match["important"])
		if name in COLOR_PROPERTIES and values:
			if isinstance(values, String):
				rgb = self.ColorFromName(values.value)
				if rgb: values = self.F.rgb(rgb)
		return self.F.property(name, values, important)

	def onAssignment( self, match ):
		"""The statement of a declaration."""
		return self.process(match["declaration"])

	def onVariable( self, match, name, value ):
		"""The declaration of a variable or special directive
		such as @unit."""
		return self.F.var(name, value)

	# =========================================================================
	# EXPRESSION
	# =========================================================================

	def onExpressionList( self, match, head, tail):
		tail  = [_[1] for _  in tail]
		return self.F.list([head] + tail, ",").unwrap()

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
		return self.F.url(self.process(match)[0])

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
