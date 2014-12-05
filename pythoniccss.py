#!/usr/bin/env python
from parsing import Grammar

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
	print "INDENT", i + 1
	return True

def doCheckIndent(context):
	v          = context.getVariables()
	tab_match  = context.getVariables().get("tabs")
	tab_indent = len(tab_match.group())
	req_indent = v.get("requiredIndent") or 0
	print "CHECK INDENT", tab_indent, "REQ", req_indent
	return tab_indent == req_indent

def doDedent(context):
	v = context.getVariables().getParent ()
	i = v.get("requiredIndent") or 0
	v.set("requiredIndent", i - 1)
	print "DEDENT", i - 1
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
	g.token   ("COMMENT",          "[ \t]*\#[^\n]*")
	g.token   ("EQUAL",             "=")
	g.token   ("EOL",              "[ ]*\n(\s*\n)*")
	g.token   ("NUMBER",           "-?(0x)?[0-9]+(\.[0-9]+)?")
	g.token   ("SUFFIX",           ":[a-z][a-z0-9\-]*")
	g.token   ("SELECTION_OPERATOR", "\>")
	g.word    ("INCLUDE",             "%include")
	g.word    ("COLON",            ":")
	g.word    ("DOT",              ".")
	g.word    ("LP",               "(")
	g.word    ("RP",               ")")
	g.word    ("SELF",             "&")
	g.word    ("COMMA",            ",")
	g.word    ("TAB",              "\t")

	g.token   ("PATH",             "\"[^\"]+\"|'[^']'|[^\s\n]+")
	g.token   ("PERCENTAGE",       "\d+(\.\d+)?%")
	g.token   ("STRING_SQ",        "'(\\\\'|[^'\\n])*'")
	g.token   ("STRING_DQ",        "\"(\\\\\"|[^\"\\n])*\"")
	g.token   ("INFIX_OPERATOR",   "[\-\+\*\/]")

	g.token   ("NODE",             "[a-zA-Z][a-zA-Z0-9\-]*")
	g.token   ("NODE_CLASS",       "\.[a-zA-Z][a-zA-Z0-9\-]*")
	g.token   ("NODE_ID",          "#[a-zA-Z][a-zA-Z0-9\-]*")
	# SEE: http://www.w3schools.com/cssref/css_units.asp
	g.token   ("UNIT",             "em|ex|px|cm|mm|in|pt|pc|ch|rem|vh|vmin|vmax|\%")
	g.token   ("VARIABLE_NAME",    "[\w_][\w\d_]*")
	g.token   ("METHOD_NAME",      "[\w_][\w\d_]*")
	g.token   ("REFERENCE",        "\$[\w_][\w\d_]*")
	g.token   ("COLOR_NAME",       "[a-z][a-z0-9\-]*")
	g.token   ("COLOR_HEX",        "\#[A-Fa-f0-9][A-Fa-f0-9][A-Fa-f0-9][A-Fa-f0-9][A-Fa-f0-9][A-Fa-f0-9]([A-Fa-f0-9][A-Fa-f0-9])?")
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

	# TODO: support nth(10)
	g.rule      ("Selector",         g.agroup(s.SELF, s.NODE, s.NODE_ID, s.NODE_CLASS), s.SUFFIX.optional())
	g.rule      ("SelectorNarrower", s.SELECTION_OPERATOR.optional(), s.Selector)
	g.rule      ("Selection",        g.agroup(s.Selector), s.SelectorNarrower.zeroOrMore ())

	# =========================================================================
	# VALUES & EXPRESSIONS
	# =========================================================================

	g.group     ("Suffixes")
	g.rule      ("Number",           s.NUMBER, s.UNIT.optional())
	g.group     ("String",           s.STRING_SQ, s.STRING_DQ)
	g.group     ("Value",            s.Number, s.COLOR_HEX, s.COLOR_RGB, s.REFERENCE, s.COLOR_NAME, s.String)
	g.rule      ("Expression")
	# NOTE: We use Prefix and Suffix to avoid recursion, which creates a lot
	# of problems with parsing expression grammars
	g.group     ("Prefix", s.Value, g.arule(s.LP, s.Expression, s.RP))
	s.Expression.set(s.Prefix, s.Suffixes.zeroOrMore())
	g.rule      ("Parameters",       s.VARIABLE_NAME, g.arule(s.COMMA, s.VARIABLE_NAME).zeroOrMore())
	g.rule      ("Invocation",     s.DOT,     s.METHOD_NAME, s.LP, s.Parameters.optional(), s.RP)
	g.rule      ("InfixOperation", s.INFIX_OPERATOR, s.Expression)
	s.Suffixes.set(s.Invocation, s.InfixOperation)

	# =========================================================================
	# LINES (BODY)
	# =========================================================================

	g.rule      ("Comment",          s.COMMENT.oneOrMore(), s.EOL)
	g.rule      ("Include",          s.INCLUDE, s.PATH,     s.EOL)
	g.rule      ("Declaration",      s.VARIABLE_NAME, s.EQUAL, s.Expression, s.EOL)

	# =========================================================================
	# OPERATIONS
	# =========================================================================

	g.rule      ("Assignment",       s.CSS_PROPERTY, s.COLON, s.Expression.oneOrMore())

	# =========================================================================
	# BLOCK STRUCTURE
	# =========================================================================

	g.group("Code")
	# NOTE: If would be good to sort this out and allow memoization for some
	# of the failures. A good idea would be to append the indentation value to
	# the caching key.
	# .processMemoizationKey(lambda _,c:_ + ":" + c.getVariables().get("requiredIndent", 0))
	g.rule("Statement",     s.CheckIndent, g.agroup(s.Assignment, s.COMMENT), s.EOL).disableFailMemoize()
	g.rule("Block",         s.CheckIndent, g.agroup(s.Selection, s.PERCENTAGE), s.COLON, s.EOL, s.Indent, s.Code.zeroOrMore(), s.Dedent).disableFailMemoize()
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

class Processor:
	"""Processes the raw grammar output and directly outputs the CSS code."""

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
	getGrammar().log.verbose = True
	getGrammar().log.level   = 100
	getGrammar().log.enabled = True
	for path in args:
		print parse(path)

# Todo, what should happen:
# """
# Parser failed with rest:  'div:\n\twidth: 100%\n'
#  at line (0, 0)
#     div:
#  *
# 	width: 100%
#
# Parse tree is:
# 	Source(a=xx,b=xxx,c=xxx)
# 		XXX..
# 			XXX.
# None
# """
# EOF
