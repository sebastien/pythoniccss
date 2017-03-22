# encoding=utf8 ---------------------------------------------------------------
# Project           : PythonicCSS
# -----------------------------------------------------------------------------
# Author            : FFunction
# License           : BSD License
# -----------------------------------------------------------------------------
# Creation date     : 14-Jul-2013
# Last modification : 17-Nov-2016
# -----------------------------------------------------------------------------

from __future__ import print_function
from   libparsing import *

G = None

# -----------------------------------------------------------------------------
#
# INDENTATION FUNCTIONS
#
# -----------------------------------------------------------------------------

def doIndent(context, match):
	"""Increases the indent requirement in the parsing context"""
	return True
	v = context.getVariables().getParent ()
	i = v.get("requiredIndent") or 0
	v.set("requiredIndent", i + 1)
	return True

def doCheckIndent(context, match):
	"""Ensures that the indent requirement is matched."""
	return True
	v          = context.getVariables()
	tab_match  = context.getVariables().get("tabs")
	tab_indent = len(tab_match[0])
	req_indent = v.get("requiredIndent") or 0
	return tab_indent == req_indent

def doDedent(context, match):
	"""Decreases the indent requirement in the parsing context"""
	return True
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
	if not g:g=Grammar("PythonicCSS", isVerbose=False)
	s = g.symbols
	g.token   ("SPACE",            "[ ]+")
	g.token   ("TABS",             "\t*")
	g.token   ("COMMENT",          "[ \t]*(//|#\s+)[^\n]*")
	g.token   ("EOL",              "[ ]*\n(\s*\n)*")
	g.token   ("NUMBER",           "-?(0x)?[0-9]+(\.[0-9]+)?")
	g.token   ("ATTRIBUTE",        "[a-zA-Z\-_][a-zA-Z0-9\-_]*")
	g.token   ("ATTRIBUTE_VALUE",  "\"[^\"]*\"|'[^']*'|[^,\]]+")
	g.token   ("ATTRIBUTE_OPERATOR",  "[\^]?=")
	g.token   ("SELECTOR_SUFFIX",  "::?[\-a-z][a-z0-9\-]*(\([^\)]+\))?")
	g.token   ("SELECTION_OPERATOR", "\>|\+|\~|[ ]+")
	g.token   ("REST",              ".+")
	g.word    ("INCLUDE",          "@include")
	g.word    ("EQUAL",             "=")
	g.word    ("COLON",            ":")
	g.word    ("DOT",              ".")
	g.word    ("LP",               "(")
	g.word    ("IMPORTANT",        "!important")
	g.word    ("RP",               ")")
	g.word    ("SELF",             "&")
	g.word    ("COMMA",            ",")
	g.word    ("MACRO",            "@macro")
	g.word    ("SEMICOLON",        ";")
	g.word    ("LSBRACKET",        "[")
	g.word    ("RSBRACKET",        "]")

	g.token   ("PATH",             "\"[^\"]+\"|'[^']'|[^\s\n]+")
	g.token   ("PERCENTAGE",       "\d+(\.\d+)?%")
	g.token   ("STRING_SQ",        "'((\\\\'|[^'\\n])*)'")
	g.token   ("STRING_BQ",        "`((\\\\`|[^`\\n])*)`")
	g.token   ("STRING_DQ",        "\"((\\\\\"|[^\"\n])*)\"")
	g.token   ("STRING_UQ",        "[^\s\n\*\+,:;\(\)\[\]]+")
	g.token   ("INFIX_OPERATOR",   "\- |[\+\*\/]")

	g.token   ("NODE",             "\*|([a-zA-Z][\-_a-zA-Z0-9\-]*)")
	g.token   ("NODE_CLASS",       "(\.[\-_a-zA-Z][_a-zA-Z0-9_\-]*)+")
	g.token   ("NODE_ID",          "#[_a-zA-Z][_a-zA-Z0-9\-]*")

	# SEE: http://www.w3schools.com/cssref/css_units.asp
	#g.token   ("UNIT",             "em|ex|px|pem|cm|mm|in|pt|pc|ch|rem|vh|vmin|vmax|s|deg|rad|grad|ms|Hz|kHz|\%")
	g.token   ("UNIT",             "[a-zA-z]+|\%")
	g.token   ("VARIABLE_NAME",    "[\w_][\w\d_]*")
	g.token   ("METHOD_NAME",      "[\w_][\w\d_]*")
	g.token   ("NAME",             "[\w_][\w\d_]*")
	g.token   ("REFERENCE",        "\$([\w_][\w\d_]*)")
	#g.token   ("COLOR_NAME",       "[a-z][a-z0-9\-]*")
	g.token   ("COLOR_HEX",        "\#([A-Fa-f0-9][A-Fa-f0-9]?[A-Fa-f0-9]?[A-Fa-f0-9]?[A-Fa-f0-9]?[A-Fa-f0-9]?([A-Fa-f0-9][A-Fa-f0-9])?)")
	g.token   ("COLOR_RGB",        "rgba?\((\s*\d+\s*,\s*\d+\s*,\s*\d+\s*(,\s*\d+(\.\d+)?\s*)?)\)")
	g.token   ("URL",              "url\((\"[^\"]*\"|\'[^\']*\'|[^\)]*)\)")
	g.token   ("CSS_PROPERTY",    "[\-a-z][\-a-z0-9]*")
	g.token   ("SPECIAL_NAME",     "@[A-Za-z][A-Za-z0-9\_\-]*")
	g.token   ("CSS_DIRECTIVE",    "@@[A-Za-z][A-Za-z0-9\_\-]*")
	g.token   ("SPECIAL_FILTER",   "\[[^\]]+\]")

	# =========================================================================
	# INDENTATION
	# =========================================================================

	g.procedure ("Indent",           doIndent)
	g.procedure ("Dedent",           doDedent)
	g.rule      ("CheckIndent",      s.TABS._as("tabs"), g.acondition(doCheckIndent))

	g.rule      ("Attribute",        s.ATTRIBUTE._as("name"), g.arule(s.ATTRIBUTE_OPERATOR, s.ATTRIBUTE_VALUE).optional()._as("value"))
	g.rule      ("Attributes",       s.LSBRACKET, s.Attribute._as("head"), g.arule(s.COMMA, s.Attribute).zeroOrMore()._as("tail"), s.RSBRACKET)

	g.rule      ("Selector",         g.agroup(s.SELF, s.NODE).optional()._as("node"), s.NODE_ID.optional()._as("nid"), s.NODE_CLASS.optional()._as("nclass"), s.Attributes.zeroOrMore()._as("attributes"), s.SELECTOR_SUFFIX.zeroOrMore()._as("suffix"))
	g.rule      ("SelectorNarrower", s.SELECTION_OPERATOR._as("op"), s.Selector._as("sel"))

	g.rule      ("Selection",        s.Selector._as("head"),  s.SelectorNarrower.zeroOrMore()._as("tail"))
	g.rule      ("Selections",       s.Selection._as("head"), g.arule(s.COMMA, s.Selection).zeroOrMore()._as("tail"))

	# =========================================================================
	# VALUES & EXPRESSIONS
	# =========================================================================

	g.group     ("Suffix")
	g.rule      ("Number",           s.NUMBER._as("value"), s.UNIT.optional()._as("unit"))
	# TODO: Add RawString
	g.group     ("String",           s.STRING_BQ, s.STRING_SQ, s.STRING_DQ, s.STRING_UQ)
	g.group     ("Value",            s.Number, s.COLOR_HEX, s.COLOR_RGB, s.URL, s.REFERENCE, s.String)
	g.rule      ("Parameters",       s.VARIABLE_NAME, g.arule(s.COMMA, s.VARIABLE_NAME).zeroOrMore())
	g.rule      ("Arguments",        s.Value, g.arule(s.COMMA, s.Value).zeroOrMore())
	g.rule      ("Expression")
	g.rule      ("ExpressionList", s.Expression._as("head"), g.arule(s.COMMA, s.Expression).zeroOrMore()._as("tail"))

	# NOTE: We use Prefix and Suffix to avoid recursion, which creates a lot
	# of problems with parsing expression grammars
	g.group     ("Prefix", s.Value, g.arule(s.LP, s.Expression, s.RP))
	s.Expression.set(s.Prefix._as("prefix"), s.Suffix.zeroOrMore()._as("suffixes"))

	g.rule      ("Invocation",   g.arule(s.DOT,     s.METHOD_NAME).optional()._as("method"), s.LP, s.Arguments.optional()._as("arguments"), s.RP)
	g.rule      ("InfixOperation", s.INFIX_OPERATOR, s.Expression)
	# TODO: Might be better to use COMMA as a suffix to chain expressions
	s.Suffix.set(s.InfixOperation, s.Invocation)

	# =========================================================================
	# OPERATIONS
	# =========================================================================

	g.rule      ("CSSProperty",      s.CSS_PROPERTY._as("name"), s.COLON, s.ExpressionList.oneOrMore()._as("values"), s.IMPORTANT.optional()._as("important"), s.SEMICOLON.optional())
	g.rule      ("MacroInvocation",  s.NAME._as("name"),   s.LP, s.Arguments.optional()._as("arguments"), s.RP)
	g.rule      ("Variable",   s.SPECIAL_NAME.optional()._as("decorator"), s.VARIABLE_NAME._as("name"), s.EQUAL, s.ExpressionList._as("value"))

	# =========================================================================
	# LINES (BODY)
	# =========================================================================

	g.rule      ("Comment",          s.COMMENT.oneOrMore(), s.EOL)
	g.rule      ("Include",          s.INCLUDE, s.PATH._as("path"),  s.EOL)
	# FIXME: Not sure why definition needs to be standalone
	g.rule      ("VariableDeclaration",       s.Variable._as("declaration"), s.EOL)
	# FIXME: If we remove optional() from SPECIAL_NAME, we get a core dump...
	g.rule      ("Directive",        s.SPECIAL_NAME.optional()._as("directive"), s.VARIABLE_NAME._as("value"), s.EOL)
	g.rule      ("CSSDirective",     s.CSS_DIRECTIVE._as("directive"),  s.REST._as("value"), s.EOL)

	# =========================================================================
	# BLOCK STRUCTURE
	# =========================================================================

	# NOTE: If would be good to sort this out and allow memoization for some
	# of the failures. A good idea would be to append the indentation value to
	# the caching key.
	# .processMemoizationKey(lambda _,c:_ + ":" + c.getVariables().get("requiredIndent", 0))
	g.rule("Statement",     s.CheckIndent._as("indent"), g.agroup(s.CSSProperty, s.MacroInvocation, s.VariableDeclaration, s.COMMENT)._as("op"), s.EOL)
	# FIXME: Not clear why there's a PERCENTAGE here
	g.rule("Block",         s.CheckIndent._as("indent"), g.agroup(s.PERCENTAGE, s.Selections)._as("selections"), s.COLON.optional(), s.EOL, s.Indent, s.Statement.zeroOrMore()._as("code"), s.Dedent)

	g.rule    ("MacroDeclaration", s.MACRO, s.NAME._as("name"), s.Parameters.optional()._as("parameters"), s.COLON.optional())
	g.rule    ("MacroBlock",       s.CheckIndent._as("indent"), s.MacroDeclaration._as("type"), s.EOL, s.Indent, s.Statement.zeroOrMore()._as("code"), s.Dedent)

	# FIXME: The special declaration is a bit broken... should work better
	g.rule    ("SpecialDeclaration",   s.SPECIAL_NAME._as("type"), s.SPECIAL_FILTER.optional()._as("filter"),  s.NAME.optional()._as("name"), s.Parameters.optional()._as("parameters"), s.COLON.optional())
	g.rule    ("SpecialBlock",         s.CheckIndent._as("indent"), s.SpecialDeclaration._as("type"), s.EOL, s.Indent, s.Statement.zeroOrMore()._as("code"), s.Dedent)

	# =========================================================================
	# AXIOM
	# =========================================================================

	g.group     ("Source",  g.agroup(s.Comment, s.Block, s.MacroBlock, s.CSSDirective, s.Directive, s.SpecialBlock, s.VariableDeclaration, s.Include).zeroOrMore())
	g.skip  = s.SPACE
	g.axiom = s.Source
	g.prepare()
	return g

def getGrammar():
	global G
	if not G: G = grammar()
	return G



# EOF
