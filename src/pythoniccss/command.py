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
from   io        import StringIO
from  .grammar   import getGrammar
from  .processor import PCSSProcessor

try:
	import reporter
	logging = reporter.bind("pcss")
except ImportError:
	import logging

def parse(path):
	return getGrammar().parsePath(path)

def parseString(text):
	return getGrammar().parseString(text)

def convert(path):
	result = parse(path)
	if result.status == "S":
		s = StringIO()
		p = PCSSProcessor(output=s)
		p._process(result.match, path)
		s.seek(0)
		v = s.getvalue()
		s.close()
		return v
	else:
		raise Exception("Parsing of {0} failed at line:{1}\n> {2}".format("string", result.line, result.textAround()))

def run(args):
	"""Processes the command line arguments."""
	USAGE = "pythoniccss FILE..."
	if reporter: reporter.install(reporter.StderrReporter())
	if type(args) not in (type([]), type(())): args = [args]
	oparser = argparse.ArgumentParser(
		prog        = os.path.basename(__file__.split(".")[0]),
		description = "Compiles PythonicCSS files to CSS"
	)
	oparser.add_argument("files", metavar="FILE", type=str, nargs='*', help='The .pcss files to parse')
	oparser.add_argument("-v", "--verbose",  dest="verbose",  action="store_true", default=False)
	oparser.add_argument("-o", "--output",  type=str,  dest="output", default=None)
	oparser.add_argument("--report",  dest="report",  action="store_true", default=False)
	oparser.add_argument("--stats",    dest="stats", action="store_true", default=False)
	oparser.add_argument("--symbols",  dest="symbols", action="store_true", default=False)
	oparser.add_argument("--json",  dest="json", action="store_true", default=None)
	# We create the parse and register the options
	args = oparser.parse_args(args=args)
	# p = TreeWriter(output=sys.stdout)
	if not args.files:
		sys.stderr.write(USAGE + "\n")
	output = sys.stdout
	g = getGrammar()
	if args.verbose: g.isVerbose = True
	if args.output: output = open(args.output, "w")
	g.prepare()
	p = PCSSProcessor(output=output, grammar=g)
	# We output the list of symbols
	if args.symbols:
		for s in sorted(g.symbols, lambda a,b:cmp(a.id, b.id)):
			reporter.info("Symbol #{0:10s} = {1}".format(str(s.id), s))
	for path in args.files:
		start_time = time.time()
		result = g.parsePath(path)
		parse_time = time.time()
		if args.report:
			output.write("Report for : {0}\n".format(path))
			stats = result.stats
			stats.report(getGrammar(), output)
		else:
			if result is None:
				reporter.error("Could not find path: {0}".format(path))
			elif result.isSuccess():
				if args.json:
					result.toJSON()
				else:
					# FIXME: Should set path
					result = p._process(result.match, path)
					return result
					# print ("RESULT", result)
					# process_time = time.time()
					# if args.stats:
					# 	parse_d   = parse_time - start_time
					# 	process_d = process_time  - start_time
					# 	parse_p   = 100.0 * parse_d   / (parse_d + process_d)
					# 	process_p = 100.0 * process_d / (parse_d + process_d)
					# 	reporter.info("Parsing time    {0:0.4f}s {1:0.0f}%".format(parse_d,   parse_p))
					# 	reporter.info("Processing time {0:0.4f}s {1:0.0f}%".format(process_d, process_p))
					# except HandlerException as e:
					# 	reporter.error(e)
					# 	for _ in e.context:
					# 		reporter.warn(_)
			else:
				msg = "Parsing of `{0}` failed at line:{1}#{2}".format(path, result.line, result.offset)
				reporter.error(msg)
				reporter.error("{0} lines".format( len(open(path).read()[0:result.offset].split("\n"))))
				reporter.error(result.textAround())
				# FIXME: This is inaccurate, the parsingresult does not return
				raise Exception("Parsing of `{0}` failed at line:{1}\n> {2}".format(path, result.line, result.textAround()))
	if args.output:
		output.close()

if __name__ == "__main__":
	import sys
	run(sys.argv[1:])

# EOF
