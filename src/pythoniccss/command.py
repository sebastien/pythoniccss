#!/usr/bin/env python2.7
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
import re, os, sys, argparse, json, copy, io, time
from   io        import BytesIO
from  .grammar   import getGrammar
from  .processor import PCSSProcessor
from  .writer    import CSSWriter
from  .cache     import Graph

try:
	import reporter
	logging = reporter.bind("pcss")
except ImportError:
	import logging

GRAPH = Graph()

def parse(path, convert=True):
	if GRAPH:
		node = GRAPH.get(path)
		return node.css if convert else node.ast
	else:
		res = getGrammar().parsePath(path)
		return processResult(res, path=path) if convert else res

def parseString(text, path=None, convert=True):
	res = getGrammar().parseString(text)
	return processResult(res, path=path) if convert else res

def processResult( result, path=None ):
	if result.isSuccess:
		s = BytesIO()
		p = PCSSProcessor(path=path, graph=GRAPH)
		m = p.process(result.match)
		writer = CSSWriter(output=s).write(m)
		s.seek(0)
		v = s.getvalue()
		s.close()
		return v
	else:
		raise Exception("Parsing of {0} failed at line:{1}\n> {2}".format("string", result.line, result.describe()))

def run(args):
	"""Processes the command line arguments."""
	USAGE = "pythoniccss FILE..."
	if type(args) not in (type([]), type(())): args = [args]
	oparser = argparse.ArgumentParser(
		prog        = os.path.basename(__file__.split(".")[0]),
		description = "Compiles PythonicCSS files to CSS"
	)
	oparser.add_argument("files", metavar="FILE", type=str, nargs='*', help='The .pcss files to parse')
	oparser.add_argument("-v", "--verbose",  dest="verbose",  action="store_true", default=False)
	oparser.add_argument("-o", "--output",   type=str,  dest="output", default=None)
	oparser.add_argument("--profile",  dest="profile", action="store_true", default=False, help="Profiles the parsing/processing time")
	oparser.add_argument("--json",     dest="json", action="store_true", default=None)
	# We create the parse and register the options
	args = oparser.parse_args(args=args)
	# p = TreeWriter(output=sys.stdout)
	if not args.files:
		sys.stderr.write(USAGE + "\n")
	output = sys.stdout
	g = getGrammar(isVerbose=args.verbose)
	if args.output: output = open(args.output, "wb")
	g.prepare()
	p = PCSSProcessor(grammar=g, graph=GRAPH)
	for path in args.files:
		start_time = time.time()
		result = g.parsePath(path)
		parse_time = time.time()
		if result is None:
			logging.error("Could not find path: {0}".format(path))
		elif result.isSuccess():
			if args.json:
				result.toJSON()
			else:
				# FIXME: Should set path
				p.path = path
				result = p.process(result.match)
				process_time = time.time()
				writer = CSSWriter(output=output).write(result)
				write_time  = time.time()
				if args.profile:
					parse_d   = parse_time    - start_time
					process_d = process_time  - parse_time
					write_d   = write_time    - process_time
					parse_p   = 100.0 * parse_d   / (parse_d + write_d + process_d)
					process_p = 100.0 * process_d / (parse_d + write_d + process_d)
					write_p   = 100.0 * write_p   / (parse_d + write_d + process_d)
					logging.info("Parsing time    {0:0.4f}s {1:0.0f}%".format(parse_d,   parse_p))
					logging.info("Processing time {0:0.4f}s {1:0.0f}%".format(process_d, process_p))
					logging.info("Writing time    {0:0.4f}s {1:0.0f}%".format(write_d,   write_p))
				return result
		else:
			msg = "Parsing of `{0}` failed at line:{1}#{2}".format(path, result.line, result.offset)
			logging.error(msg)
			logging.error("{0} lines".format( len(open(path).read()[0:result.offset].split("\n"))))
			logging.error(result.describe())
	if args.output:
		output.close()

if __name__ == "__main__":
	import sys
	run(sys.argv[1:])

# EOF - vim: ts=4 sw=4 noet
