#!/usr/bin/env python
from parsing import Grammar
import ipdb

G = None

# -----------------------------------------------------------------------------
#
# INDENTATION FUNCTIONS
#
# -----------------------------------------------------------------------------

def doIndent(context):
	v = context.getVariables().getParent ()
	i = v.get("requiredIndent") or 0
	v.set("requiredIndent", i + 1)
	return True

def doCheckIndent(context):
	v          = context.getVariables()
	tab_match  = context.getVariables().get("tabs")
	tab_indent = len(tab_match.group())
	req_indent = v.get("requiredIndent") or 0
	return tab_indent == req_indent

def doDedent(context):
	v = context.getVariables().getParent ()
	i = v.get("requiredIndent") or 0
	v.set("requiredIndent", i - 1)
	return True

# -----------------------------------------------------------------------------
#
# GRAMMAR
#
# -----------------------------------------------------------------------------

def grammar(g=Grammar("PythonicCSS")):
	s = g.symbols
	g.token   ("SPACE",            "[ ]+")
	g.token   ("TABS",             "\t*")
	g.token   ("EMPTY_LINES",      "([ \t]*\n)+")
	g.token   ("INDENT",           "\t+")
	g.token   ("COMMENT",          "[ \t]*\//[^\n]*")
	g.token   ("EQUAL",             "=")
	g.token   ("EOL",              "[ ]*\n(\s*\n)*")
	g.token   ("NUMBER",           "-?(0x)?[0-9]+(\.[0-9]+)?")
	g.token   ("ATTRIBUTE",        "[a-zA-Z\-_][a-zA-Z0-9\-_]*")
	g.token   ("ATTRIBUTE_VALUE",  "\"[^\"]*\"|'[^']*'|[^,\]]+")
	g.token   ("SELECTOR_SUFFIX",  ":[\-a-z][a-z0-9\-]*(\([0-9]+\))?")
	g.token   ("SELECTION_OPERATOR", "\>|\s+")
	g.word    ("INCLUDE",             "%include")
	g.word    ("COLON",            ":")
	g.word    ("DOT",              ".")
	g.word    ("LP",               "(")
	g.word    ("RP",               ")")
	g.word    ("SELF",             "&")
	g.word    ("COMMA",            ",")
	g.word    ("TAB",              "\t")
	g.word    ("EQUAL",            "=")
	g.word    ("LSBRACKET",        "[")
	g.word    ("RSBRACKET",        "]")

	g.token   ("PATH",             "\"[^\"]+\"|'[^']'|[^\s\n]+")
	g.token   ("PERCENTAGE",       "\d+(\.\d+)?%")
	g.token   ("STRING_SQ",        "'(\\\\'|[^'\\n])*'")
	g.token   ("STRING_DQ",        "\"(\\\\\"|[^\"\\n])*\"")
	g.token   ("INFIX_OPERATOR",   "[\-\+\*\/]")

	g.token   ("NODE",             "\*|([a-zA-Z][a-zA-Z0-9\-]*)")
	g.token   ("NODE_CLASS",       "\.[a-zA-Z][a-zA-Z0-9\-]*")
	g.token   ("NODE_ID",          "#[a-zA-Z][a-zA-Z0-9\-]*")

	# SEE: http://www.w3schools.com/cssref/css_units.asp
	g.token   ("UNIT",             "em|ex|px|cm|mm|in|pt|pc|ch|rem|vh|vmin|vmax|\%")
	g.token   ("VARIABLE_NAME",    "[\w_][\w\d_]*")
	g.token   ("METHOD_NAME",      "[\w_][\w\d_]*")
	g.token   ("MACRO_NAME",       "[\w_][\w\d_]*")
	g.token   ("REFERENCE",        "\$[\w_][\w\d_]*")
	g.token   ("COLOR_NAME",       "[a-z][a-z0-9\-]*")
	g.token   ("COLOR_HEX",        "\#[A-Fa-f0-9][A-Fa-f0-9]?[A-Fa-f0-9]?[A-Fa-f0-9]?[A-Fa-f0-9]?[A-Fa-f0-9]?([A-Fa-f0-9][A-Fa-f0-9])?")
	g.token   ("COLOR_RGB",        "rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*(,\s*\d+\s*)?\)")
	g.token   ("CSS_PROPERTY",    "[a-z][a-z0-9\-]*")
	g.token   ("SPECIAL_NAME",     "@[A-Za-z][A-Za-z0-9\_\-]*")
	g.token   ("SPECIAL_FILTER",   "\[[^\]]+\]")

	# =========================================================================
	# INDENTATION
	# =========================================================================

	g.procedure ("Indent",           doIndent)
	g.procedure ("Dedent",           doDedent)
	g.rule      ("CheckIndent",      s.TABS.bindAs("tabs"), g.acondition(doCheckIndent)).disableMemoize ()

	g.rule      ("Attribute",        s.ATTRIBUTE._as("name"), g.arule(s.EQUAL, s.ATTRIBUTE_VALUE).optional()._as("value"))
	g.rule      ("Attributes",       s.LSBRACKET, s.Attribute._as("head"), g.arule(s.COMMA, s.Attribute).zeroOrMore()._as("tail"), s.RSBRACKET)

	g.rule      ("Selector",         g.agroup(s.SELF, s.NODE).optional()._as("scope"), s.NODE_ID.optional()._as("nid"), s.NODE_CLASS.zeroOrMore()._as("nclass"), s.Attributes.optional()._as("attributes"), s.SELECTOR_SUFFIX.zeroOrMore()._as("suffix"))
	g.rule      ("SelectorNarrower", s.SELECTION_OPERATOR._as("op"), s.Selector._as("sel"))

	g.rule      ("Selection",        g.agroup(s.Selector)._as("head"), s.SelectorNarrower.zeroOrMore()._as("tail"))
	g.rule      ("SelectionList",    s.Selection._as("head"), g.arule(s.COMMA, s.Selection).zeroOrMore()._as("tail"))

	# =========================================================================
	# VALUES & EXPRESSIONS
	# =========================================================================

	g.group     ("Suffixes")
	g.rule      ("Number",           s.NUMBER._as("value"), s.UNIT.optional()._as("unit"))
	g.group     ("String",           s.STRING_SQ, s.STRING_DQ)
	g.group     ("Value",            s.Number, s.COLOR_HEX, s.COLOR_RGB, s.REFERENCE, s.COLOR_NAME, s.String)
	g.rule      ("Parameters",       s.VARIABLE_NAME, g.arule(s.COMMA, s.VARIABLE_NAME).zeroOrMore())

	g.rule      ("Expression")
	# NOTE: We use Prefix and Suffix to avoid recursion, which creates a lot
	# of problems with parsing expression grammars
	g.group     ("Prefix", s.Value._as("value"), g.arule(s.LP, s.Expression, s.RP))
	s.Expression.set(s.Prefix, s.Suffixes.zeroOrMore())

	g.rule      ("MethodInvocation",     s.DOT,     s.METHOD_NAME, s.LP, s.Parameters.optional(), s.RP)
	g.rule      ("InfixOperation", s.INFIX_OPERATOR, s.Expression)
	s.Suffixes.set(s.MethodInvocation, s.InfixOperation)

	# =========================================================================
	# LINES (BODY)
	# =========================================================================

	g.rule      ("Comment",          s.COMMENT.oneOrMore(), s.EOL)
	g.rule      ("Include",          s.INCLUDE, s.PATH,     s.EOL)
	g.rule      ("Declaration",      s.VARIABLE_NAME, s.EQUAL, s.Expression, s.EOL)

	# =========================================================================
	# OPERATIONS
	# =========================================================================

	g.rule      ("Assignment",       s.CSS_PROPERTY._as("name"), s.COLON, s.Expression.oneOrMore()._as("values"))
	g.rule      ("MacroInvocation",  s.MACRO_NAME,   s.LP, s.Parameters.optional(), s.RP)

	# =========================================================================
	# BLOCK STRUCTURE
	# =========================================================================

	g.group("Code")
	# NOTE: If would be good to sort this out and allow memoization for some
	# of the failures. A good idea would be to append the indentation value to
	# the caching key.
	# .processMemoizationKey(lambda _,c:_ + ":" + c.getVariables().get("requiredIndent", 0))
	g.rule("Statement",     s.CheckIndent, g.agroup(s.Assignment, s.MacroInvocation, s.COMMENT), s.EOL).disableFailMemoize()
	g.rule("Block",         s.CheckIndent, g.agroup(s.PERCENTAGE, s.SelectionList)._as("selector"), s.COLON, s.EOL, s.Indent, s.Code.zeroOrMore()._as("code"), s.Dedent).disableFailMemoize()
	s.Code.set(s.Statement, s.Block).disableFailMemoize()

	g.rule    ("SpecialDeclaration",   s.CheckIndent, s.SPECIAL_NAME, s.SPECIAL_FILTER.optional(), s.Parameters.optional(), s.COLON)
	g.rule    ("SpecialBlock",         s.CheckIndent, s.SpecialDeclaration, s.EOL, s.Indent, s.Code.zeroOrMore(), s.Dedent).disableFailMemoize()

	# =========================================================================
	# AXIOM
	# =========================================================================

	g.group     ("Source",  g.agroup(s.Comment, s.Block, s.SpecialBlock, s.Declaration, s.Include).zeroOrMore())
	g.ignore    (s.SPACE)
	g.axiom     = s.Source
	return g

# -----------------------------------------------------------------------------
#
# PROCESSOR
#
# -----------------------------------------------------------------------------

class Color:

	def __init__( self, value ):
		self.value = value

class Processor:
	"""Replaces some of the grammar's symbols processing functions."""

	def __init__( self ):
		self.reset()
		self.s      = None

	def _ensureList( self, v ):
		return list(v) if type(v) not in (tuple, list) else v

	def reset( self ):
		self.result = []
		self.indent = 0
		self.scopes = []

	def bind( self, g ):
		self.s = s =  g.symbols
		for name in dir(s):
			r = getattr(s, name)
			n = "on" + name
			m = hasattr(self, n)
			if r and m:
				method = getattr(self, n)
				def wrapper(context, result, rule=r, method=method):
					values = dict( (k, rule.resolveData(k, result)) for k in rule.listBoundSymbols() )
					return method(context, result, **values)
				r.action = wrapper
		return g

	# ==========================================================================
	# GRAMMAR RULES
	# ==========================================================================

	def onCOLOR_NAME(self, context, result ):
		return (result.group())

	def onCOLOR_HEX(self, context, result ):
		return (result.group())

	def onCOLOR_RGB(self, context, result ):
		return (result.group())

	def onCSS_PROPERTY(self, context, result ):
		return result.group()

	def onValue( self, context, result ):
		return result.data

	# def onPrefix( self, context, result, value ):
	# 	if not value:
	# 		return result[1].data[1]
	# 	else:
	# 		return value

	def onExpression( self, context, result ):
		prefix = result[0].data.data
		suffix = result[1].data
		if not suffix:
			return prefix

	def onAttribute( self, context, result, name, value ):
		return "[{0}={1}]".format(name.group(), value[1].data.group())

	def onAttributes( self, context, result, head, tail ):
		tail = [_.data[1].data for _ in tail]
		return "".join([head] + tail)

	def onSelector( self, context, result, scope, nid,  nclass, attributes, suffix ):
		"""Selectors are returned as tuples `(scope, id, class, attributes, suffix)`.
		We need to keep this structure as we need to be able to expand the `&`
		reference."""
		scope  = context.text[scope] if type(scope) == int else scope  and scope.group()  or ""
		nid    = nid    and nid.group()    or ""
		suffix = "".join([_.data.group() for _ in suffix]) or ""
		nclass = "".join([_.data.group() for _ in nclass]) if isinstance(nclass, list) else nclass and nclass.group() or ""
		if (scope or nid or nclass or attributes or suffix):
			return [scope, nid, nclass, attributes or "", suffix]
		else:
			return None

	def onSelectorNarrower( self, context, result, op, sel ):
		"""Returns a `(op, selector)` couple."""
		op = op and (op.group().strip() + " ") or ""
		return (op, sel) if op or sel else None

	def onSelection( self, context, result, head, tail ):
		"""Returns a structure like the following:
		>   [[('div', '', '', '', ''), '> ', ('label', '', '', '', '')]]
		>   ---SELECTOR------------   OP   --SELECTOR---------------
		"""
		res = [head]
		for _ in tail or []:
			if type(_) in (str, unicode, list, tuple):
				res.append(_)
			else:
				res.extend(_.data)
		return res

	def onSelectionList( self, context, result, head, tail ):
		"""Updates the current scope and writes the scope selection line."""
		# head is s.Selection
		head   = [head]
		# tail is [[s.COMMA, s.Selection], ...]
		tail   = [_.data[1].data for _ in tail or []]
		scopes = head + tail
		# We want to epxand the `&` in the scopes
		scopes = self._expandScopes(scopes)
		# And output the full current scope
		if len(self.scopes) > 0: self._write("}")
		# We push the expanded scopes in the scopes stack
		self.scopes.append(scopes)
		self._write(", ".join((self._selectionAsString(_) for _ in self.scopes[-1])) + " {")

	def onNumber( self, context, result, value, unit ):
		value = value.group()
		value = float(value) if "." in value else int(value)
		unit  = unit.group() if unit else None
		return (value, unit)

	def onAssignment( self, context, result, name, values ):
		return self._write("{0}: {1}; ".format(name, values), indent=1)
		# name  = values.get("name").group()
		# value = values.get("value")
		# return "name: {0}".format(value)

	def onBlock( self, context, result, selector, code ):
		if len(self.scopes) == 1:
			self._write("}")
		self.scopes.pop()

	def onSource( self, context, result ):
		return result

	# ==========================================================================
	# OUTPUT
	# ==========================================================================

	def _write( self, line=None, indent=0 ):
		line = "\t" * indent + line
		print  ">>>", line
		return line

	# ==========================================================================
	# SCOPE & SELECTION HELPERS
	# ==========================================================================

	def _listCurrentScopes( self ):
		"""Lists the current scopes"""
		return self.scopes[-1]

	def _expandScopes( self, scopes ):
		"""Expands the `&` in the list of given scopes."""
		res = []
		for scope in scopes:
			# If you have a look at onSelectionList, you'll see that the
			# scope is a list of selectors joined by operators, ie:
			# [ [NODE, ID, CLASS, ATTRIBUTES, SUFFIX], OP, [NODE...], ... ]
			if scope[0][0] == "&":
				# If there is an `&` in the scope, we list the
				# curent scopes and merge the scope with them
				scope[0][0] = ''
				for full_scope in self._listCurrentScopes():
					# This is a tricky operation, but we get the very first
					# selector of the given scope, which starts with an &,
					# merge it with the most specific part of the current
					# scopes and prepend the rest of th full scope.
					merged = self._mergeScopes(scope[0], full_scope[-1])
					res.append(full_scope[0:-1] + [merged])
			else:
				res.append(scope)
		return res

	def _mergeScopeUnit( self, a, b):
		"""Helper function for _mergeScopes"""
		if not a: return b
		if not b: return a
		return a + b

	def _mergeScopes( self, a, b):
		# Merges the contents of scope A and B
		return [self._mergeScopeUnit(a[i], b[i]) or None for i in range(len(a))]

	def _scopeAsString( self, scope ):
		return "".join(_ or "" for _ in scope)

	def _selectionAsString( self, selection ):
		return "".join(self._scopeAsString(_) if isinstance(_, list) else _ for _ in selection if _)

# -----------------------------------------------------------------------------
#
# CORE FUNCTIONS
#
# -----------------------------------------------------------------------------

def getGrammar():
	global G
	if not G: G = grammar ()
	return G

def parse(path, grammar=None):
	# Parse should return the node tree
	with open(path, "rb") as f:
		return (grammar or getGrammar()).parse(f.read())

def compile(path, treebuilderClass, grammar=None):
	# FIXME: Compile should return the text
	builder = treebuilderClass(path)
	grammar = grammar or getGrammar()
	return builder.build(parse(path, grammar), grammar)

if __name__ == "__main__":
	import sys, os
	args = sys.argv[1:]
	# getGrammar().log.verbose = True
	# getGrammar().log.level   = 10
	getGrammar().log.enabled = True
	processor = Processor()
	g         = processor.bind(getGrammar())
	for path in args:
		result = parse(path, g)

# EOF
