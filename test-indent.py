#!/usr/bin/env python
from parsing import Grammar

G = None

__doc__ = """
This is a test-case to exercise the relationship between using side-effect
based rules and memoization, which triggered problems with PythonicCSS in the
first place. Basically, any rule that has a CheckIndent as a first element,
and any rule that references this rule as first child should be marked
as not memoizing failures, because CheckIndent might become valid after
successful deindent and implicit closing of previous blocks.
"""

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
	g.word    ("BLOCK",     "BLOCK")
	g.word    ("STATEMENT", "STATEMENT")
	g.word    ("EOL",       "\n")
	g.token   ("TABS",      "\t*")

	# =========================================================================
	# INDENTATION
	# =========================================================================

	g.procedure ("Indent",           doIndent)
	g.procedure ("Dedent",           doDedent)
	g.rule      ("CheckIndent",      s.TABS.bindAs("tabs"), g.acondition(doCheckIndent)).disableMemoize ()


	g.group("Code")
	# We need to disable the fail memoize as we want to retry these when the indent changes
	g.rule("Statement", s.CheckIndent, s.STATEMENT, s.EOL).disableFailMemoize()
	g.rule("Block", s.CheckIndent, s.BLOCK, s.EOL, s.Indent, s.Code.zeroOrMore(), s.Dedent).disableFailMemoize()
	s.Code.set(s.Statement, s.Block).disableFailMemoize()

	# =========================================================================
	# AXIOM
	# =========================================================================

	g.group     ("Source", s.Code.oneOrMore())
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

def parseString(text, grammar=None):
	return (grammar or getGrammar()).parse(text)

def compile(path, treebuilderClass, grammar=None):
	# FIXME: Compile should return the text
	builder = treebuilderClass(path)
	grammar = grammar or getGrammar()
	return builder.build(parse(path, grammar), grammar)

TEST_1 = """\
BLOCK
	STATEMENT
	STATEMENT
"""

TEST_2 = """\
BLOCK
	STATEMENT
	BLOCK
		STATEMENT
	STATEMENT
"""

TEST_3 =  """\
BLOCK
	STATEMENT
	BLOCK
		STATEMENT
	BLOCK
		STATEMENT
"""

TEST_4 =  """\
BLOCK
	BLOCK
		STATEMENT
		BLOCK
			STATEMENT
"""

TEST_5 =  """\
BLOCK
	BLOCK
		STATEMENT
		BLOCK
			STATEMENT
"""

TEST_6 =  """\
BLOCK
	BLOCK
		STATEMENT
		BLOCK
			STATEMENT
	STATEMENT
"""
TEST =  """\
BLOCK
	BLOCK
		STATEMENT
"""

if __name__ == "__main__":
	import sys, os
	args = sys.argv[1:]
	getGrammar().log.verbose = True
	getGrammar().log.level   = 100
	getGrammar().log.enabled = True
	print parseString(TEST)

# EOF
