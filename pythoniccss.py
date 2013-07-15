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
	g.token   ("EOL",              "[ ]*\n(\s*\n)*")
	g.token   ("NUMBER",           "-?(0x)?[0-9]+(\.[0-9]+)?")

	g.word    ("COLON",            ":")

	g.token   ("NODE",             "[a-zA-Z][a-zA-Z0-9\-]*")
	g.token   ("NODE_CLASS",       "\.[a-zA-Z][a-zA-Z0-9\-]*")
	g.token   ("NODE_ID",          "#[a-zA-Z][a-zA-Z0-9\-]*")
	g.token   ("UNIT",             "em|pt|px|rem|\%")
	g.token   ("REFERENCE",        "\$[\w\d_]+")
	g.token   ("COLOR_HEX",        "\#\[A-Fa-f0-9][A-Fa-f0-9][A-Fa-f0-9][A-Fa-f0-9][A-Fa-f0-9][A-Fa-f0-9]([A-Fa-f0-9][A-Fa-f0-9])?")
	g.token   ("COLOR_RGB",        "rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*(,\s*\d+\s*)?\)")

	g.token   ("CSS_PROPERTY",     "[a-z][a-z0-9\-]*")

	# =========================================================================
	# INDENTATION
	# =========================================================================

	g.procedure ("Indent",           doIndent)
	g.procedure ("Dedent",           doDedent)
	g.rule      ("CheckIndent",      s.TABS.bindAs("tabs"), g.acondition(doCheckIndent)).disableMemoize ()

	g.rule      ("Comment",          s.COMMENT.oneOrMore())

	g.rule      ("Selector",         g.agroup(s.NODE, s.NODE_ID, s.NODE_CLASS))

	# =========================================================================
	# VALUES & EXPRESSIONS
	# =========================================================================

	g.rule      ("Number",           s.NUMBER, s.UNIT.optional())
	g.group     ("Value",            s.Number, s.REFERENCE)
	g.rule      ("Property",         s.CheckIndent, s.CSS_PROPERTY, s.COLON, s.Value)

	# =========================================================================
	# BLOCK STRUCTURE
	# =========================================================================

	g.group     ("Rule",             s.Property, s.Comment)
	g.rule      ("Selection",        g.agroup(s.Selector), s.COLON, s.Indent, s.Rule, s.Dedent)

	# =========================================================================
	# AXIOM
	# =========================================================================

	g.group     ("Source",  g.agroup(s.Comment, s.Rule).zeroOrMore())
	g.ignore    (s.SPACE, s.COMMENT)
	g.axiom     = s.Source
	return g

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
	import sys
	args = sys.argv[1:]
	for path in args:
		print parse(path)

Todo, what should happen:
"""
Parser failed with rest:  'div:\n\twidth: 100%\n'
 at line (0, 0)
    div:
 *
	width: 100%

Parse tree is:
	Source(a=xx,b=xxx,c=xxx)
		XXX..
			XXX.
None
"""
# EOF
