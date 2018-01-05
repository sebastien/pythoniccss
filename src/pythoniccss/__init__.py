#!/usr/bin/env python2.7
# encoding=utf8 ---------------------------------------------------------------
# Project           : PythonicCSS
# -----------------------------------------------------------------------------
# Author            : FFunction
# License           : BSD License
# -----------------------------------------------------------------------------
# Creation date     : 14-Jul-2013
# Last modification : 21-Nov-2016
# -----------------------------------------------------------------------------

from .command   import run, parse, parseString, processResult

VERSION    = "0.7.0"
LICENSE    = "http://ffctn.com/doc/licenses/bsd"

__doc__ = """
Processor for the PythonicCSS language. This module use a PEG-based parsing
engine <http://github.com/sebastien/parsing>, which sadly has an important
performance penalty, but offers greated easy of development/update.
"""

process = lambda text,path=None:parseString(text, path, True)

if __name__ == "__main__":
	import sys
	run(sys.argv[1:])

# EOF
