#!/usr/bin/env python
# encoding=utf8 ---------------------------------------------------------------
# Project           : PythonicCSS
# -----------------------------------------------------------------------------
# Author            : FFunction
# License           : BSD License
# -----------------------------------------------------------------------------
# Creation date     : 14-Jul-2013
# Last modification : 19-Jan-2015
# -----------------------------------------------------------------------------

import re, os, sys, argparse, json
from   libparsing import Grammar, Token, Word, Rule, Group, Condition, Procedure, Reference, AbstractProcessor, TreeWriter

try:
	import reporter
except ImportError:
	reporter = None

VERSION = "0.1.0"
LICENSE = "http://ffctn.com/doc/licenses/bsd"

__doc__ = """
Processor for the PythonicCSS language. This module use a PEG-based parsing
engine <http://github.com/sebastien/parsing>, which sadly has an important
performance penalty, but offers greated easy of development/update.
"""

G = None

# -----------------------------------------------------------------------------
#
# INDENTATION FUNCTIONS
#
# -----------------------------------------------------------------------------

def doIndent(context):
	"""Increases the indent requirement in the parsing context"""
	v = context.getVariables().getParent ()
	i = v.get("requiredIndent") or 0
	v.set("requiredIndent", i + 1)
	return True

def doCheckIndent(context):
	"""Ensures that the indent requirement is matched."""
	v          = context.getVariables()
	tab_match  = context.getVariables().get("tabs")
	tab_indent = len(tab_match.group())
	req_indent = v.get("requiredIndent") or 0
	return tab_indent == req_indent

def doDedent(context):
	"""Decreases the indent requirement in the parsing context"""
	v = context.getVariables().getParent ()
	i = v.get("requiredIndent") or 0
	v.set("requiredIndent", i - 1)
	return True

# -----------------------------------------------------------------------------
#
# GRAMMAR
#
# -----------------------------------------------------------------------------

def grammar(g=None):
	"""Definition of the grammar for the PythonicCSS language, using
	the parsing module parsing elements."""
	if not g:g=Grammar("PythonicCSS", verbose=False)
	s = g.symbols
	g.token   ("SPACE",            "[ ]+")
	g.token   ("TABS",             "\t*")
	g.token   ("COMMENT",          "[ \t]*\//[^\n]*")
	g.token   ("EQUAL",             "=")
	g.token   ("EOL",              "[ ]*\n(\s*\n)*")
	g.token   ("NUMBER",           "-?(0x)?[0-9]+(\.[0-9]+)?")
	g.token   ("ATTRIBUTE",        "[a-zA-Z\-_][a-zA-Z0-9\-_]*")
	g.token   ("ATTRIBUTE_VALUE",  "\"[^\"]*\"|'[^']*'|[^,\]]+")
	g.token   ("SELECTOR_SUFFIX",  "::?[\-a-z][a-z0-9\-]*(\([^\)]+\))?")
	g.token   ("SELECTION_OPERATOR", "\>|\+|[ ]+")
	g.word    ("INCLUDE",          "%include")
	g.word    ("COLON",            ":")
	g.word    ("DOT",              ".")
	g.word    ("LP",               "(")
	g.word    ("IMPORTANT",        "!important")
	g.word    ("RP",               ")")
	g.word    ("SELF",             "&")
	g.word    ("COMMA",            ",")
	g.word    ("MACRO",            "@macro")
	g.word    ("SEMICOLON",        ";")
	g.word    ("EQUAL",            "=")
	g.word    ("LSBRACKET",        "[")
	g.word    ("RSBRACKET",        "]")

	g.token   ("PATH",             "\"[^\"]+\"|'[^']'|[^\s\n]+")
	g.token   ("PERCENTAGE",       "\d+(\.\d+)?%")
	g.token   ("STRING_SQ",        "'((\\\\'|[^'\\n])*)'")
	g.token   ("STRING_DQ",        "\"((\\\\\"|[^\"\n])*)\"")
	g.token   ("STRING_UQ",        "[^\s\n\*\+,:;\(\)\[\]]+")
	g.token   ("INFIX_OPERATOR",   "[\-\+\*\/]")

	g.token   ("NODE",             "\*|([a-zA-Z][\-_a-zA-Z0-9\-]*)")
	g.token   ("NODE_CLASS",       "\.[_a-zA-Z][_a-zA-Z0-9_\-]*")
	g.token   ("NODE_ID",          "#[_a-zA-Z][_a-zA-Z0-9\-]*")

	# SEE: http://www.w3schools.com/cssref/css_units.asp
	#g.token   ("UNIT",             "em|ex|px|pem|cm|mm|in|pt|pc|ch|rem|vh|vmin|vmax|s|deg|rad|grad|ms|Hz|kHz|\%")
	g.token   ("UNIT",             "[\w]+|\%")
	g.token   ("VARIABLE_NAME",    "[\w_][\w\d_]*")
	g.token   ("METHOD_NAME",      "[\w_][\w\d_]*")
	g.token   ("NAME",             "[\w_][\w\d_]*")
	g.token   ("REFERENCE",        "\$([\w_][\w\d_]*)")
	g.token   ("COLOR_NAME",       "[a-z][a-z0-9\-]*")
	g.token   ("COLOR_HEX",        "\#([A-Fa-f0-9][A-Fa-f0-9]?[A-Fa-f0-9]?[A-Fa-f0-9]?[A-Fa-f0-9]?[A-Fa-f0-9]?([A-Fa-f0-9][A-Fa-f0-9])?)")
	g.token   ("COLOR_RGB",        "rgba?\((\s*\d+\s*,\s*\d+\s*,\s*\d+\s*(,\s*\d+(\.\d+)?\s*)?)\)")
	g.token   ("CSS_PROPERTY",    "[\-a-z][\-a-z0-9]*")
	g.token   ("SPECIAL_NAME",     "@[A-Za-z][A-Za-z0-9\_\-]*")
	g.token   ("SPECIAL_FILTER",   "\[[^\]]+\]")

	# =========================================================================
	# INDENTATION
	# =========================================================================

	g.procedure ("Indent",           doIndent)
	g.procedure ("Dedent",           doDedent)
	g.rule      ("CheckIndent",      s.TABS._as("tabs"), g.acondition(doCheckIndent)).disableMemoize ()

	g.rule      ("Attribute",        s.ATTRIBUTE._as("name"), g.arule(s.EQUAL, s.ATTRIBUTE_VALUE).optional()._as("value"))
	g.rule      ("Attributes",       s.LSBRACKET, s.Attribute._as("head"), g.arule(s.COMMA, s.Attribute).zeroOrMore()._as("tail"), s.RSBRACKET)

	g.rule      ("Selector",         g.agroup(s.SELF, s.NODE).optional()._as("scope"), s.NODE_ID.optional()._as("nid"), s.NODE_CLASS.zeroOrMore()._as("nclass"), s.Attributes.zeroOrMore()._as("attributes"), s.SELECTOR_SUFFIX.zeroOrMore()._as("suffix"))
	g.rule      ("SelectorNarrower", s.SELECTION_OPERATOR._as("op"), s.Selector._as("sel"))

	g.rule      ("Selection",        g.agroup(s.Selector)._as("head"), s.SelectorNarrower.zeroOrMore()._as("tail"))
	g.rule      ("SelectionList",    s.Selection._as("head"), g.arule(s.COMMA, s.Selection).zeroOrMore()._as("tail"))

	# =========================================================================
	# VALUES & EXPRESSIONS
	# =========================================================================

	g.group     ("Suffixes")
	g.rule      ("Number",           s.NUMBER._as("value"), s.UNIT.optional()._as("unit"))
	g.group     ("String",           s.STRING_SQ, s.STRING_DQ, s.STRING_UQ)
	g.group     ("Value",            s.Number, s.COLOR_HEX, s.COLOR_RGB, s.REFERENCE, s.String)
	g.rule      ("Parameters",       s.VARIABLE_NAME, g.arule(s.COMMA, s.VARIABLE_NAME).zeroOrMore())
	g.rule      ("Arguments",        s.Value, g.arule(s.COMMA, s.Value).zeroOrMore())
	g.rule      ("Expression")
	g.rule      ("ExpressionList", s.Expression._as("head"), g.arule(s.COMMA, s.Expression).zeroOrMore()._as("tail"))

	# NOTE: We use Prefix and Suffix to avoid recursion, which creates a lot
	# of problems with parsing expression grammars
	g.group     ("Prefix", s.Value, g.arule(s.LP, s.Expression, s.RP))
	s.Expression.set(s.Prefix, s.Suffixes.zeroOrMore())

	g.rule      ("Invocation",   g.arule(s.DOT,     s.METHOD_NAME).optional()._as("method"), s.LP, s.Arguments.optional()._as("arguments"), s.RP)
	g.rule      ("InfixOperation", s.INFIX_OPERATOR, s.Expression)
	# TODO: Might be better to use COMMA as a suffix to chain expressions
	s.Suffixes.set(s.InfixOperation, s.Invocation)

	# =========================================================================
	# LINES (BODY)
	# =========================================================================

	g.rule      ("Comment",          s.COMMENT.oneOrMore(), s.EOL)
	g.rule      ("Include",          s.INCLUDE, s.PATH,     s.EOL)
	g.rule      ("Declaration",      s.SPECIAL_NAME.optional()._as("decorator"), s.VARIABLE_NAME._as("name"), s.EQUAL, s.ExpressionList._as("value"), s.EOL)

	# =========================================================================
	# OPERATIONS
	# =========================================================================

	g.rule      ("Assignment",       s.CSS_PROPERTY._as("name"), s.COLON, s.ExpressionList.oneOrMore()._as("values"), s.IMPORTANT.optional()._as("important"), s.SEMICOLON.optional())
	#g.rule      ("Assignment",       s.CSS_PROPERTY._as("name"), s.COLON, s.Expression.oneOrMore()._as("values"), s.IMPORTANT.optional()._as("important"), s.SEMICOLON.optional())
	g.rule      ("MacroInvocation",  s.NAME._as("name"),   s.LP, s.Arguments.optional()._as("arguments"), s.RP)

	# =========================================================================
	# BLOCK STRUCTURE
	# =========================================================================

	# NOTE: If would be good to sort this out and allow memoization for some
	# of the failures. A good idea would be to append the indentation value to
	# the caching key.
	# .processMemoizationKey(lambda _,c:_ + ":" + c.getVariables().get("requiredIndent", 0))
	g.rule("Statement",     s.CheckIndent._as("indent"), g.agroup(s.Assignment, s.MacroInvocation, s.COMMENT), s.EOL).disableFailMemoize()
	g.rule("Block",         s.CheckIndent._as("indent"), g.agroup(s.PERCENTAGE, s.SelectionList)._as("selector"), s.COLON.optional(), s.EOL, s.Indent, s.Statement.zeroOrMore()._as("code"), s.Dedent).disableFailMemoize()

	g.rule    ("MacroDeclaration", s.MACRO, s.NAME._as("name"), s.Parameters.optional()._as("parameters"), s.COLON.optional())
	g.rule    ("MacroBlock",       s.CheckIndent._as("indent"), s.MacroDeclaration._as("type"), s.EOL, s.Indent, s.Statement.zeroOrMore()._as("code"), s.Dedent).disableFailMemoize()

	# FIXME: The special declaration is a bit broken... should work better
	g.rule    ("SpecialDeclaration",   s.SPECIAL_NAME._as("type"), s.SPECIAL_FILTER.optional()._as("filter"),  s.NAME.optional()._as("name"), s.Parameters.optional()._as("parameters"), s.COLON.optional())
	g.rule    ("SpecialBlock",         s.CheckIndent._as("indent"), s.SpecialDeclaration._as("type"), s.EOL, s.Indent, s.Statement.zeroOrMore()._as("code"), s.Dedent).disableFailMemoize()

	# =========================================================================
	# AXIOM
	# =========================================================================

	g.group     ("Source",  g.agroup(s.Comment, s.Block, s.MacroBlock, s.SpecialBlock, s.Declaration, s.Include).zeroOrMore())
	g.skip(s.SPACE)
	g.axiom(s.Source)
	return g

# -----------------------------------------------------------------------------
#
# PROCESSOR
#
# -----------------------------------------------------------------------------

class ProcessingException(Exception):

	def __init__( self, message, context=None ):
		Exception.__init__(self, message)
		self.context = context

	def __str__( self ):
		msg = self.message
		if self.context:
			l, c = self.context.getCurrentCoordinates()
			msg = "Line {0}, char {1}: {2}".format(l, c, msg)
		return msg

class Processor(AbstractProcessor):
	"""Replaces some of the grammar's symbols processing functions. This is
	the main code that converts the parsing's recognized data to the output
	CSS. There is not really an intermediate AST (excepted for expressions),
	and the result is streamed out through the `_write` call."""

	RGB        = None

	RE_SPACES            = re.compile("\s+")
	RE_UNQUOTED          = re.compile("\!?[\./\w\d_-]+")
	FIX_STRING_DELIMITER = "\\\"\\\""
	COLOR_PROPERTIES     = (
		"background",
		"background-color",
		"color",
		"gradient"
		"linear-gradient"
	)

	PREFIXABLE_PROPERTIES = (
		"animation",
		"border-radius",
		"box-shadow",
		"background-size",
		"column-width",
		"column-gap",
		"column-count",
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
	)

	PREFIXABLE_VALUES_PROPERTIES = (
		"transition",
		"transition-property",
	)

	PREFIXES = (
		"",
		"-moz-",
		"-webkit-",
		"-o-",
		"-ms-",
	)

	# Defines the operations that are used in `Processor.evaluate`. These
	# operation take (value, unit) for a and b, and unit is the default
	# unit that will override the others.
	OPERATIONS = {
		"+" : lambda a,b,u:[a[0] + b[0], a[1] or b[1] or u],
		"-" : lambda a,b,u:[a[0] - b[0], a[1] or b[1] or u],
		"*" : lambda a,b,u:[float(a[0]) * b[0], a[1] or b[1] or u],
		"/" : lambda a,b,u:[float(a[0]) / b[0], a[1] or b[1] or u],
		"%" : lambda a,b,u:[a[0] % b[0], a[1] or b[1] or u],
	}

	OPERATOR_PRIORITY = {
		"+" : 0,
		"-" : 0,
		"*" : 1,
		"/" : 1,
		"%" : 1,
	}

	@classmethod
	def IsColorProperty( cls, name ):
		return name in cls.COLOR_PROPERTIES

	@classmethod
	def ColorFromName( cls, name ):
		"""Retrieves the (R,G,B) color triple for the color of the given name."""
		if not cls.RGB:
			colors = {}
			# We extract the color names from X11's rgb file
			# SEE: https://en.wikipedia.org/wiki/X11_color_names#Color_name_chart
			with open("/usr/share/X11/rgb.txt") as f:
				for line in f.readlines():
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

	def __init__( self, grammar=None, output=sys.stdout ):
		AbstractProcessor.__init__(self, grammar or getGrammar())
		self.reset()
		self.output = output

	def reset( self ):
		"""Resets the state of the processor. To be called inbetween parses."""
		self.result     = []
		self.indent     = 0
		self.variables  = [{}]
		self.units      = {}
		self._evaluated = [{}]
		self.scopes     = []
		self._header    = None
		self._footer    = None
		self._mode      = None
		self._macro     = None
		self._macros    = {}
		self._property  = None

	# ==========================================================================
	# EVALUATION
	# ==========================================================================

	def evaluate( self, e, unit=None, name=None, resolve=True, prefix=None ):
		"""Evaluates expressions with the internal expression format, which is
		as follows:

		- values are encoded as `('V', (value, unit))`
		- operations are encoded as `('O', operator, lvalue, rvalue)`
		- literals are encoded as `('c', string)`
		"""
		if isinstance(e,list) and not isinstance(e[0], str):
			return [[self.evaluate(_, unit, name, resolve, prefix) for _ in e], "l"]
		if e[0] == "L":
			return [[self.evaluate(_, unit, name, resolve, prefix) for _ in e[1]], "L"]
		elif e[0] == "V":
			v = e[1]
			u = v[1]
			if u in self.units:
				# FIXME: It might be better to pre-calculate the unit values
				# as this surely adds quite a lot of CPU time
				u    = self.evaluate(self.units[u])
				v    = (v[0] * u[0], u[1])
			if resolve and v[1] == "R":
				# We have a reference
				n = v[0]
				v = self.resolve(v[0], propertyName=name, prefix=prefix)
				return v
			if self.IsColorProperty(name) and v[1] == "S":
				# We have a color name as a string in a color property, we expand it
				return (self.ColorFromName(v[0]) or v[0], "C")
			elif v[1] == "S":
				if name in self.PREFIXABLE_VALUES_PROPERTIES and prefix and v[0] in self.PREFIXABLE_PROPERTIES:
					# We're in a property that refernces prexialbe properties
					return (prefix + v[0], v[1])
				else:
					return v
			else:
				return v
		elif e[0] == "O":
			o  = e[1]
			lv = self.evaluate(e[2], unit, name=name, prefix=prefix)
			rv = self.evaluate(e[3], unit, name=name, prefix=prefix)
			lu = lv[1]
			ru = rv[1]
			lu = lu or ru or unit
			ru = ru or lu or unit
			if lu != ru:
				raise ProcessingException("Incompatible unit types {0} vs {1}".format(lu, ru))
			else:
				r = self.OPERATIONS[o](lv, rv, lu)
				return r
		elif e[0] == "I":
			_, scope, method, args = e
			r = ""
			if scope:  r += self._valueAsString(scope[1])
			if method: r += "." + method
			# TODO: Should detect the scope type and apply the corresponding method
			r += "({0})".format(",".join((self._valueAsString(_) for _ in args or [])))
			return (r, None)
		elif e[0] == "(":
			return self.evaluate(e[1])
		else:
			raise ProcessingException("Evaluate not implemented for: {0} in {1}".format(e, name))

	def resolve( self, name, propertyName=None, prefix=None, depth=1 ):
		level     = len(self.variables) - depth
		variables = self.variables[level] if len(self.variables) >= depth else None
		if not variables:
			raise ProcessingException("Variable not defined: {0}".format(name))
		elif name not in variables:
			return self.resolve(name, propertyName, prefix, depth + 1)
		else:
			cname = name + (":" + propertyName if propertyName else "") + (":" + prefix if prefix else "")
			if cname in self._evaluated[level]:
				return self._evaluated[level][cname]
			else:
				v = self.evaluate(variables[name], name=propertyName, prefix=prefix)
				self._evaluated[level][cname] = v
				return v

	# ==========================================================================
	# GRAMMAR RULES
	# ==========================================================================

	def onCOLOR_HEX(self, match ):
		c = (match.group(1))
		while len(c) < 6: c += "0"
		r = int(c[0:2], 16)
		g = int(c[2:4], 16)
		b = int(c[4:6], 16)
		if len(c) > 6:
			a = int(c[6:], 16) / 255.0
			return [(r,g,b,a), "C"]
		else:
			return [(r,g,b), "C"]

	def onMETHOD_NAME(self, match ):
		return match.group()

	def onCOLOR_RGB(self, match ):
		c = match.group(1).split(",")
		if len(c) == 3:
			return [[int(_) for _ in c], "C"]
		else:
			return [[int(_) for _ in c[:3] + [float(c[3])]], "C"]

	def onREFERENCE(self, match):
		return (match.group(1), "R")

	def onCSS_PROPERTY(self, match ):
		return match.group()

	def onSTRING_DQ(self, match ):
		return self._stringEscapeFix(match.group(1))

	def onSTRING_SQ(self, match ):
		return self._stringEscapeFix(match.group(1))

	def onSTRING_UQ(self, match ):
		return match.group()

	def onCheckIndent(self, match, tabs):
		return len(tabs) if tabs else 0

	def onString( self, match ):
		return (self.process(match.group()), "S")

	def onValue( self, match ):
		value = self.process(match.group())
		return ["V", value]

	def onParameters( self, match ):
		a = self.defaultProcess(match[0])
		b = self.defaultProcess(match[1])
		return [self.defaultProcess(match[0])] + [_[1] for _ in b or []]

	def onArguments( self, match ):
		m0 = self.process(match[0])
		m1 = self.process(match[1])
		p = [m0] + ([_[1] for _ in m1] if m1 else [])
		return [self.evaluate(_) for _ in p]

	def onInvocation( self, match, method, arguments ):
		return ["I", None, method and method[1] or None, arguments]

	def onInfixOperation( self, match ):
		op   = self.process(match[0])
		expr = self.process(match[1])
		return ["O", op, None, expr]

	def onSuffixes( self, match ):
		return self.process(match.group())

	def onPrefix( self, match ):
		result = self.defaultProcess(match)
		child          = match[0]
		grand_children = child.children()
		result         = self.process(child)
		result         = ["(", result[1]] if len(result) == 3 else result
		return result

	def onExpression( self, match ):
		prefix   = self.process(match[0])
		suffixes = self.process(match[1])
		res      = prefix
		for suffix in suffixes or []:
			if suffix[0] == "O":
				suffix[2] = res
			elif suffix[0] == "I":
				suffix[1] = res
			res = suffix
		# We rework operator precedence here
		if res[0] == "O" and res[3][0] == "O":
			# We're in this situation
			# ['O', '*', ['V', (4, None)], ['O', '+', ['V', (10, None)], ['V', (5, None)]]]
			# while we ant
			# ['O', '+', ['O', '*', ['V', (4, None)], ['V', (10, None)]], ['V', (5, None)]]]
			op  = res[1]
			rop = res[3][1]
			if self.OPERATOR_PRIORITY[rop] < self.OPERATOR_PRIORITY[op]:
				a = res[2]
				b = res[3][2]
				c = res[3][3]
				res = ["O", rop, ["O", op, a, b], c]
		return res

	def onExpressionList( self, match, head, tail=None ):
		if tail:
			return [["L", [head] + [_[1] for _ in tail]]]
		else:
			return [head]

	def onAttribute( self, match, name, value ):
		return "[{0}{1}{2}]".format(name, value[0] if value else "", value[1] if value else "")

	def onAttributes( self, match, head, tail ):
		assert not tail
		result = "".join([head] + (tail or []))
		return  result

	def onSelector( self, match, scope, nid,  nclass, attributes, suffix ):
		"""Selectors are returned as tuples `(scope, id, class, attributes, suffix)`.
		We need to keep this structure as we need to be able to expand the `&`
		reference."""
		scope      = scope[0] if scope else ""
		nid        = nid if nid else ""
		suffix     = "".join(suffix) if suffix else ""
		nclass     = "".join(nclass) if nclass else ""
		attributes = "".join(attributes) if attributes else ""
		if (scope or nid or nclass or attributes or suffix):
			return [scope, nid, nclass, attributes or "", suffix]
		else:
			return None

	def onSelectorNarrower( self, match, op, sel ):
		"""Returns a `(op, selector)` couple."""
		if op:
			op = op.strip() or " "
		return (op, sel) if op or sel else None

	def onSelection( self, match, head, tail ):
		"""Returns a structure like the following:
		>   [[('div', '', '', '', ''), '> ', ('label', '', '', '', '')]]
		>   ---SELECTOR------------   OP   --SELECTOR---------------
		"""
		if not head and not tail: return None
		if head:
			res = head
			if tail:
				for narrower in tail:
					if not narrower: continue
					res.extend(narrower)
			return res
		else:
			res = []
			for i, v in enumerate(tail):
				if i == 0:
					if v[0] == " ":
						res.append(v[1])
					else:
						res.extend(v)
				else:
					res.extend(v)
			return res

	def onSelectionList( self, match, head, tail ):
		"""Updates the current scope and writes the scope selection line."""
		# tail is [[s.COMMA, s.Selection], ...]
		tail   = [_[1] for _ in tail or [] if _[1]]
		scopes = [head] + tail if tail else [head]
		# print "onSelectionList: head=", head
		# print "onSelectionList: tail=", tail
		# print "onSelectionList: scopes=", scopes
		# We want to epxand the `&` in the scopes
		scopes = self._expandScopes(scopes)
		# We push the expanded scopes in the scopes stack
		self.scopes.append(scopes)
		self._header = ",\n".join((self._selectionAsString(_) for _ in self.scopes[-1])) + " {"
		return self._header

	def onSpecialDeclaration( self, match, type, filter, name, parameters ):
		return (type, filter, name, parameters)

	def onMacroDeclaration( self, match, name, parameters ):
		return ("@macro", None, name, parameters)

	def onMacroInvocation( self, match, name, arguments ):
		if self._mode == "macro":
			self._macro.append(lambda: self.onMacroInvocation(match, name, arguments))
			return None
		if name not in self._macros:
			raise Exception("Macro not defined: {0}, got {1}".format(name, self._macros.keys()))
		params    = self._macros[name][0] or []
		scope     = {}
		arguments = arguments or []
		assert len(arguments) <= len(params), "Too many arguments given to macro: {0}, {1} given, expecting {2}".format(name, arguments, params)
		for i,a in enumerate(arguments):
			scope[params[i]] = ["V", a]
		self.variables.append(scope)
		self._evaluated.append({})
		for line in self._macros[name][1]:
			line()
		self.variables.pop()
		self._evaluated.pop()

	def onNumber( self, match, value, unit ):
		value = float(value) if "." in value else int(value)
		unit  = unit if unit else None
		if unit == "%": value = value / 100.0
		return (value, unit)

	def onDeclaration( self, match, decorator, name, value ):
		assert len(value) == 1
		value = value[0]
		self._mode = None
		if not decorator:
			name = name
			self.variables[-1][name] = value
		elif decorator == "@unit":
			self.units[name] = value
		else:
			raise NotImplementedError
		return None

	def onAssignment( self, match, name, values, important ):
		if self._mode == "macro":
			self._macro.append(lambda: self.onAssignment(match, name, values, important))
			return None
		if self._header:
			self._write(self._header)
			self._header = None
			self._footer = "}\n"
		suffix = "!important" if important else ""
		self._property = name
		try:
			evalues = [self._valueAsString(self.evaluate(_, name=name)) for _ in values]
		except ProcessingException as e:
			if reporter:
				reporter.error("{0} at  offset {1}:".format(e, match.range()))
			raise e
		if name in self.PREFIXABLE_PROPERTIES:
			res = []
			for prefix in self.PREFIXES:
				# FIXME: Optimize this
				# It's a bit slower to re-evaluate here but it would otherwise
				# lead to complex machinery.
				evalues = [self._valueAsString(self.evaluate(_, name=name, prefix=prefix)) for _ in values]
				l       = self._write("{3}{0}: {1}{2};".format(name, " ".join(evalues), suffix, prefix), indent=1)
				res.append(l)
			return res
		else:
			return self._write("{0}: {1}{2};".format(name, " ".join(evalues), suffix), indent=1)

	def onBlock( self, match, indent ):
		if indent == 0:
			self._mode   = None
		elif self._mode == "macro":
			self._macro.append(lambda: self.onBlock(match, indent + self.indent))
			return None
		self.indent = indent
		if self._footer and self._mode == None:
			self._write(self._footer)
			self._footer = None
		while len(self.scopes) > indent:
			self.scopes.pop()
		self.process(match["selector"])
		self.process(match["code"])

	def onMacroBlock( self, match, type, indent=None):
		if indent == 0:
			self._mode  = None
		assert self._mode != "macro"
		type, filter, name, params = type
		self._mode   = "macro"
		self._macro  = []
		self._macros[name] = [params, self._macro]
		self.process(match["code"])

	def onSpecialBlock( self, match, type, indent=None):
		if indent == 0:
			self._mode  = None
		elif self._mode == "macro":
			self._macro.append(lambda: self.onSpecialBlock(indent, match, type))
			return None
		if self._footer and self._mode == None:
			self._write(self._footer)
			self._footer = None
		type, filter, name, params = type
		self._write("{0}{1} {2} {3} {{".format(type, filter or "", name or "", ", ".join(params) if params else  ""))
		self._mode = None
		self.process(match["code"])
		self._footer = "}"

	def onSource( self, match ):
		result = self.defaultProcess(match)
		if self._footer:
			self._write(self._footer)
			self._footer = None
		return result

	# ==========================================================================
	# OUTPUT
	# ==========================================================================

	def _write( self, line=None, indent=0 ):
		line = "  " * indent + line + "\n"
		self.output.write(line)
		return line

	# ==========================================================================
	# SCOPE & SELECTION HELPERS
	# ==========================================================================

	def _listCurrentScopes( self ):
		"""Lists the current scopes"""
		return self.scopes[-1] if self.scopes else None

	def _expandScopes( self, scopes ):
		"""Expands the `&` in the list of given scopes."""
		res = []
		parent_scopes = self._listCurrentScopes()
		for scope in scopes:
			# If you have a look at onSelectionList, you'll see that the
			# scope is a list of selectors joined by operators, ie:
			# [ [NODE, ID, CLASS, ATTRIBUTES, SUFFIX], OP, [NODE...], ... ]
			if parent_scopes:
				if scope[0] is None:
					for full_scope in parent_scopes:
						res.append(full_scope + [" "] + scope[1:])
				elif scope[0][0] == "&":
					# If there is an `&` in the scope, we list the
					# curent scopes and merge the scope with them
					scope[0][0] = ''
					for full_scope in parent_scopes:
						# This is a tricky operation, but we get the very first
						# selector of the given scope, which starts with an &,
						# merge it with the most specific part of the current
						# scopes and prepend the rest of th fulle scope.
						merged = [self._mergeScopes(scope[0], full_scope[-1])] + scope[1:]
						res.append(full_scope[0:-1] + merged)
				else:
					for full_scope in parent_scopes:
						res.append(full_scope + [" "] + scope)
			else:
				res.append(scope)
		return res

	def _mergeScopeUnit( self, a, b):
		"""Helper function for _mergeScopes"""
		if not a: return b
		if not b: return a
		return b + a

	def _mergeScopes( self, a, b):
		# Merges the contents of scope A and B
		if not b: return a
		if not a: return b
		return [self._mergeScopeUnit(a[i], b[i]) or None for i in range(len(a))]

	def _scopeAsString( self, scope ):
		return "".join(_ or "" for _ in scope)

	def _selectionAsString( self, selection ):
		return "".join(self._scopeAsString(_) if isinstance(_, list) else _ for _ in selection if _) if selection else ""

	def _stringEscapeFix( self, text ):
		# NOTE: CleverCSS had some trouble with the empty content string, which
		# lead us to write content: "\"\"/\"\"". This escapes that
		if text.startswith(self.FIX_STRING_DELIMITER) and text.endswith(self.FIX_STRING_DELIMITER):
			return text[len(self.FIX_STRING_DELIMITER):-len(self.FIX_STRING_DELIMITER)]
		else:
			return text

	def _valueAsString( self, value ):
		v, u = value ; u = u or ""
		if   u == "L":
			return ", ".join([self._valueAsString(_) for _ in v])
		elif u == "l":
			return " ".join([self._valueAsString(_) for _ in v])
		elif u == "%":
			v = 100.0 * v
			d = int(v)
			if v == d:
				return "{0:d}%".format(d)
			else:
				return "{0:f}%".format(v)
		elif   u == "C":
			if type(v) in (str, unicode):
				# If we have a string instead of a tuple, we pass it as-is
				return v
			elif len(v) == 3:
				r, g, b = v
				r = ("0" if r < 16 else "") + hex(r)[2:].upper()
				g = ("0" if g < 16 else "") + hex(g)[2:].upper()
				b = ("0" if b < 16 else "") + hex(b)[2:].upper()
				return "#" + r + g + b
			elif len(v) == 4:
				return "rgba({0},{1},{2},{3:0.2f})".format(*v)
			else:
				raise ProcessingException("Expected RGB triple, RGBA quadruple or string, got: {0} in {1}".format(v, value))
		if   type(v) == int:
			return "{0:d}{1}".format(v,u)
		elif type(v) == float:
			# We remove the trailing 0 to have the most compact representation
			v = str(v)
			while len(v) > 2 and v[-1] == "0" and v[-2] != ".":
				v = v[0:-1]
			if v.endswith(".0"):v = v[:-2]
			return v + u
		elif type(v) == str:
			# FIXME: Proper escaping
			if self._property != "content" and self.RE_UNQUOTED.match(v):
				return "{0:s}".format(v,u)
			else:
				return "{0:s}".format(json.dumps(v).replace("\u", "\\"),u)
		elif type(v) == unicode:
			# FIXME: Proper escaping
			if self._property != "content" and self.RE_UNQUOTED.match(v):
				return "{0:s}".format(v,u)
			else:
				return "{0:s}".format(json.dumps(v).replace("\u", "\\"),u)
		else:
			raise ProcessingException("Value string conversion not implemented: {0}".format(value))

# -----------------------------------------------------------------------------
#
# CORE FUNCTIONS
#
# -----------------------------------------------------------------------------

def getGrammar():
	global G
	if not G: G = grammar()
	# G.setVerbose(False)
	return G

def parse(path):
	return getGrammar().parsePath(path)

def run(args):
	"""Processes the command line arguments."""
	USAGE = "pythoniccss FILE..."
	if reporter: reporter.install(reporter.StderrReporter())
	if type(args) not in (type([]), type(())): args = [args]
	oparser = argparse.ArgumentParser(
		prog        = os.path.basename(__file__.split(".")[0]),
		description = "Compiles PythonicCSS files to CSS"
	)
	oparser.add_argument("files", metavar="FILE", type=str, nargs='+', help='The .pcss files to parse')
	oparser.add_argument("--report",  dest="report",  action="store_true", default=False)
	oparser.add_argument("--verbose",  dest="verbose",  action="store_true", default=False)
	oparser.add_argument("--output",  type=str,  dest="output", default=None)
	# We create the parse and register the options
	args = oparser.parse_args(args=args)
	p   = Processor(output=sys.stdout)
	# p = TreeWriter(output=sys.stdout)
	if not args.files:
		sys.stderr.write(USAGE + "\n")
	output = sys.stdout
	# if args.verbose: getGrammar().setVerbose()
	if args.output: output = open(args.output, "w")
	for a in args.files:
		if reporter: reporter.info("Processing: {0}".format(a))
		match = parse(a)
		if args.report:
			output.write("Report for : {0}\n".format(a))
			stats = match.stats()
			stats.report(getGrammar(), output)
		else:
			if match.status() == "S":
				p.process(match)
			else:
				msg = "Parsing of {0} failed at line:{1}".format(a, match.line())
				reporter.error(msg)
				reporter.error(match.textaround())
				raise Exception("Parsing of {0} failed at line:{1}\n> {2}".format(a, match.line(), match.textaround()))
	if args.output:
		output.close()
if __name__ == "__main__":
	import sys
	run(sys.argv[1:])
# EOF
