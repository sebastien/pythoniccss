
from __future__ import print_function
from libparsing import Processor, ensure_str, is_string
from .grammar import grammar, getGrammar
from .model   import Factory, Element
import re, sys

class PCSSProcessor(Processor):
	"""Creates the model for the CSS stylesheet based on the result returned
	by the grammar. This is essentially an AST-like generator for the grammar."""

	def __init__( self, grammar=None, output=sys.stdout ):
		Processor.__init__(self, grammar or getGrammar())
		self.F      = Factory()
		self.output = output

	def _process( self, match, path=False ):
		if path is not False: self.path = path
		res = self.process(match)
		# FIXME: This should be moved to the command
		return res.write(self.output)

	# =========================================================================
	# HIGH-LEVEL STRUCTURE
	# =========================================================================

	def onSource( self, match ):
		s = self.F.stylesheet()
		for m in match:
			for _ in self.process(m):
				s.add(_)
		return s

	def onBlock( self, match ):
		indent     = self.process(match["indent"])
		selections = self.process(match["selections"])[0]
		code       = self.process(match["code"])
		return self.F.block().select(selections).add(code).indent(indent)

	def onStatement( self, match ):
		indent  = self.process(match["indent"])
		op      = self.process(match["op"])[0]
		return op.indent(indent)

	def onDirective( self, match ):
		directive = self.process(match["directive"])
		value     = self.process(match["value"])
		return self.F.directive(directive, value)

	def onMacroDeclaration( self, match, name, parameters ):
		return self.F.macro(name, parameters)

	def onMacroBlock( self, match, indent, type, code):
		return type.add(code).indent(indent)

	def onMacroInvocation( self, match, name, arguments ):
		return self.F.invokemacro(name, arguments)

	# =========================================================================
	# STATEMENTS
	# =========================================================================

	def onCSSProperty( self, match ):
		"""The main CSS declaration."""
		name      = self.process(match["name"])
		values    = self.F.list(self.process(match["values"])).unwrap()
		important = self.process(match["important"])
		return self.F.property(name, values, important)

	def onVariableDeclaration( self, match ):
		"""The statement of a declaration."""
		return self.process(match["declaration"])

	def onVariable( self, match, decorator, name, value ):
		"""The declaration of a variable or special directive
		such as @unit."""
		return self.F.var(name, value, decorator)

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

	def onExpression( self, match, prefix, suffixes ):
		prefix = prefix[1] if not isinstance(prefix, Element) else prefix
		for op, rvalue in suffixes:
			prefix = prefix.suffix(op, rvalue)
		return prefix

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
			return self.F.rgba(((int(_) for _ in c[:3] + [float(c[3])])))

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
		return [head] + (tail or [])

	def onSelection( self, match ):
		head = self.process(match["head"])
		tail = self.process(match["tail"])
		for op, sel in tail:
			if sel:
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
		suffix     = "".join(suffix) if suffix else ""
		nclass     = "".join(nclass) if nclass else ""
		attributes = "".join(attributes) if attributes else ""
		if (node or nid or nclass or attributes or suffix):
			return self.F.selector(node, nid, nclass, attributes or "", suffix)
		else:
			return None

	def onSelectorNarrower( self, match, op, sel ):
		"""Returns a `(op, selector)` couple."""
		if op: op = op.strip() or " "
		sel = sel or None
		return [op, sel] if (op or sel) else None

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
