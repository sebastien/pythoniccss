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
from libparsing import Processor, ensure_str, is_string
from .grammar import grammar, getGrammar
from .model   import Selection, Selector
import os, sys, re, io

try:
	import reporter
	logging = reporter.bind("pcss.processor")
except ImportError:
	import logging

BASE = os.path.dirname(os.path.abspath(__file__))

# -----------------------------------------------------------------------------
#
# PCSS PROCESSOR
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

class PCSSProcessor(Processor):
	"""Replaces some of the grammar's symbols processing functions. This is
	the main code that converts the parsing's recognized data to the output
	CSS. There is not really an intermediate AST (excepted for expressions),
	and the result is streamed out through the `_write` call."""

	RGB        = None
	PRECISION  = "0.3f"

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
		"box",
		"box-align",
		"box-shadow",
		"background-size",
		"column-width",
		"column-gap",
		"column-count",
		"column-span",
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
		"white-space-collapsing",
	)

	PREFIXABLE_PROPERTIES_OVERRIDES = {
		"-ms-box"       : "-ms-flexbox",
		"-ms-box-align" : "-ms-flex-align",
	}

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
		"+"  : lambda a,b,u:[a[0] + b[0], a[1] or b[1] or u],
		"- " : lambda a,b,u:[a[0] - b[0], a[1] or b[1] or u],
		"*"  : lambda a,b,u:[float(a[0]) * b[0], a[1] or b[1] or u],
		"/"  : lambda a,b,u:[float(a[0]) / b[0], a[1] or b[1] or u],
		"%"  : lambda a,b,u:[a[0] % b[0], a[1] or b[1] or u],
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
			with open(os.path.join(BASE, "rgb.txt")) as f:
				# FIXME: Somehow, this creates a sefault
				# for line in f.readlines():
				# 	print (line)
				for line in f.read().split("\n"):
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
		Processor.__init__(self, grammar or getGrammar())
		self.reset()
		self.output = output
		self.path   = None
		self.strategy = self.LAZY

	def _process( self, match, path=False ):
		if path is not False: self.path = path
		return self.process(match)

	def reset( self ):
		"""Resets the state of the processor. To be called inbetween parses."""
		self.result     = []
		self.indent     = 0
		self.variables  = [{}]
		self.units      = {}
		self.module     = None
		self._evaluated = [{}]
		self.scopes     = []
		self._blocks    = []
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
		elif e[0] == "L":
			return [[self.evaluate(_, unit, name, resolve, prefix) for _ in e[1]], "L"]
		elif e[0] == "V":
			assert isinstance(e, tuple) or isinstance(e, list) and len(e) == 2, "evaluate: value expected to be `(V, (value, type))`, got {1}".format(e)
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
				return (self.ColorFromName(v[0][0]) or v[0][0], "C")
			elif v[1] == "S":
				value, quote = v[0]
				if name in self.PREFIXABLE_VALUES_PROPERTIES and prefix and value in self.PREFIXABLE_PROPERTIES:
					# FIXME: Not sure
					# We're in a property that references prexiable properties
					p = prefix + value
					p = self.PREFIXABLE_PROPERTIES_OVERRIDES.get(p) or p
					return ([p, quote], v[1])
				else:
					return v
			else:
				return v
		elif e[0] == "O":
			# O = Operation
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
			# I = Invocation
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
		"""Resolves the given name at the given level. This will bubble up the levels
		until the name is found, returning `None` if never found."""
		level     = len(self.variables) - depth
		variables = self.variables[level] if len(self.variables) >= depth else None
		if variables is None:
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


	def processWord(self, result):
		return ensure_str(result)

	def processToken(self, result):
		return ensure_str(result[0])

	def onURL(self, match ):
		return ((self.process(match)[0], None), "S")

	def onCOLOR_HEX(self, match ):
		c = (self.process(match)[1])
		while len(c) < 6: c += "0"
		r = int(c[0:2], 16)
		g = int(c[2:4], 16)
		b = int(c[4:6], 16)
		if len(c) > 6:
			a = int(c[6:], 16) / 255.0
			return [(r,g,b,a), "C"]
		else:
			return [(r,g,b), "C"]

	def onCOLOR_RGB(self, match ):
		c = self.process(match)[1].split(",")
		if len(c) == 3:
			c = [[int(_) for _ in c], "C"]
		else:
			c = [[int(_) for _ in c[:3]] + [float(c[3])], "C"]
		return c

	def onREFERENCE(self, match):
		return (self.process(match)[1], "R")

	def onSTRING_BQ(self, match ):
		return [self._stringEscapeFix(self.process(match)[1]), '']

	def onSTRING_DQ(self, match ):
		return [self._stringEscapeFix(self.process(match)[1]), '"']

	def onSTRING_SQ(self, match ):
		return [self._stringEscapeFix(self.process(match)[1]), "'"]

	def onSTRING_UQ(self, match ):
		return [self.process(match)[0], None]

	def onPERCENTAGE(self, match ):
		if self._mode == "macro":
			self._macro.append(lambda: self.onPERCENTAGE(match))
			return None
		self._write(match[0] + " {")

	def onCheckIndent(self, match, tabs ):
		return len(tabs) if tabs else 0

	def onString( self, match ):
		value = self.process(match[0])
		return (value, "S")

	def onValue( self, match ):
		value = ["V", self.process(match[0])]
		#assert isinstance(value, tuple) or isinstance(value, list) and len(value) == 2, "onValue: value expected to be `(V, (value, type))`, got {1} from {2}".format(value, match)
		return value

	def onParameters( self, match ):
		a = self.process(match[0])
		b = self.process(match[1])
		return [a] + [_[1] for _ in b or []]

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
		return self.process(match[0])

	def onPrefix( self, match ):
		result  = self.process(match[0])
		result = ["(", result[1]] if len(result) == 3 else result
		return result

	def onExpression( self, match ):
		prefix   = self.process(match[0])
		suffixes = self.process(match[1])
		res      = prefix
		for suffix in suffixes or ():
			if suffix[0] == "O":
				suffix[2] = res
			elif suffix[0] == "I":
				suffix[1] = res
			res = suffix
		# We rework operator precedence here
		if res[0] == "O" and res[3][0] == "O":
			# We're in this situation
			# ['O', '*', ['V', (4, None)], ['O', '+', ['V', (10, None)], ['V', (5, None)]]]
			# while we want
			# ['O', '+', ['O', '*', ['V', (4, None)], ['V', (10, None)]], ['V', (5, None)]]]
			op  = res[1]
			rop = res[3][1]
			if self.OPERATOR_PRIORITY[rop] < self.OPERATOR_PRIORITY[op]:
				a = res[2]
				b = res[3][2]
				c = res[3][3]
				res = ["O", rop, ["O", op, a, b], c]
		return res

	def onExpressionList( self, match, head, tail ):
		if tail:
			return [["L", [head] + [_[1] for _ in tail]]]
		else:
			return [head]

	def onAttribute( self, match ):
		name  =  self.process(match["name"])
		value =  self.process(match["value"])
		return "[{0}{1}{2}]".format(name, value[0] if value else "", value[1] if value else "")

	def onAttributes( self, match ):
		head =  self.process(match["head"])
		tail =  self.process(match["tail"])
		assert not tail
		result = "".join([head] + (tail or []))
		return  result

	def onSelector( self, match ):
		"""Selectors are returned as tuples `(scope, id, class, attributes, suffix)`.
		We need to keep this structure as we need to be able to expand the `&`
		reference."""
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
			return Selector(node, nid, nclass, attributes or "", suffix)
		else:
			return None

	def onSelectorNarrower( self, match, op, sel ):
		"""Returns a `(op, selector)` couple."""
		if op: op = op.strip() or " "
		sel = sel or None
		return [op, sel] if (op or sel) else None

	def onSelection( self, match, head, tail ):
		"""Returns a structure like the following:
		>   [[('div', '', '', '', ''), '> ', ('label', '', '', '', '')]]
		>   ---SELECTOR------------   OP   --SELECTOR----------------
		>   +--head---------------+   +----------tail---------------+
		"""
		if not head and not tail: return None
		res = Selection(head, self.module)
		for op, sel in tail:
			if not op: continue
			res.add(op, sel)
		return res

	def onScope( self, match, head, tail ):
		"""Updates the current scope and writes the scope selection line."""
		# tail is [[s.COMMA, s.Selection], ...]
		scope = [head or Selection(module=self.module)]
		if tail:
			for t in (_[1] for _ in tail if _[1]):
				scope += [t]
		# print ("onSelectionList: head=", head)
		# print ("onSelectionList: tail=", tail)
		# print (" tail.value", match[1].value)
		# print (" tail.process", self.process(match[1]))
		# print (" tail.value", match[1].value)
		# print ("onSelectionList: scopes=", scopes)
		# We want to epxand the `&` in the scopes
		full_scopes = self._expandScope(scope or [])
		# We push the expanded scopes in the scopes stack
		self._pushScope(full_scopes)
		self._header = u",\n".join(str(_) for _ in full_scopes) + " {"
		return self._header

	def onSpecialDeclaration( self, match, type, filter, name, parameters ):
		return (type, filter, name, parameters)

	def onMacroDeclaration( self, match ):
		name       = self.process(match["name"])
		parameters = self.process(match["parameters"])
		return ("@macro", None, name, parameters)

	def onMacroInvocation( self, match ):
		name      = self.process(match["name"])
		arguments = self.process(match["arguments"])
		if self._mode == "macro":
			self._macro.append(lambda self:self.onMacroInvocation(match, name, arguments))
			return None
		if name not in self._macros:
			raise Exception("Macro not defined: {0}, got {1}".format(name, self._macros.keys()))
		params    = self._macros[name][0] or []
		scope     = {}
		arguments = arguments or []
		assert len(arguments) <= len(params), "Too many arguments given to macro: {0}, {1} given, expecting {2}".format(name, arguments, params)
		for i,a in enumerate(arguments):
			scope[params[i]] = ["V", a]
		scope["indent"] = ("V", (self.indent, None))
		self.variables.append(scope)
		self._evaluated.append({})
		for line in self._macros[name][1]:
			line(self)
		self.variables.pop()
		self._evaluated.pop()

	def onNumber( self, match, value, unit ):
		value = float(value) if "." in value else int(value)
		unit  = unit if unit else None
		if unit == "%": value = value / 100.0
		return (value, unit)

	def onInclude( self, match, path ):
		if not os.path.exists(path) and self.path:
			path = os.path.join(os.path.dirname(os.path.abspath(self.path)), path)
		assert os.path.exists(path), "@include {0}: file does not exist.".format(path)
		# We create an entirely new processor with a new grammar to avoid
		# reference issues (and core dumps). I'm definitely not an expert
		# at writing Python C extensions.
		g            = grammar(0)
		subprocessor = self.__class__(grammar=g, output=self.output)
		match  = g.parsePath(path)
		result = subprocessor.process(match.match)
		self.variables[-1].update(subprocessor.variables[0])
		self._evaluated[-1].update(subprocessor._evaluated[0])
		self.units.update(subprocessor.units)
		self._macros.update(subprocessor._macros)

	def onDeclaration( self, match, decorator, name, value ):
		assert len(value) == 1
		decorator  = decorator if decorator else None
		self._mode = None
		value      = value[0]
		if not decorator:
			name = name
			self.variables[-1][name] = value
		elif decorator == "@unit":
			self.units[name] = value
		elif decorator == "@module":
			self.module      = value
		else:
			raise NotImplementedError
		return None

	def onDirective( self, match, directive, value ):
		if directive == "@module":
			self.module  = value
		else:
			raise NotImplementedError
		return None

	def onCSSDirective( self, match, directive, value ):
		self._write(directive[1:] + value + ";")
		return None

	def onAssignment( self, match, name, values, important ):
		name      = self.process(match["name"])
		values    = self.process(match["values"])
		important = self.process(match["important"])
		return self._onAssignment(name, values, important, match)

	def _onAssignment( self, name, values, important, match=None ):
		values = values or ()
		if self._mode == "macro":
			self._macro.append(lambda self: self._onAssignment(name, values, important))
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
			logging.error("{0} at  offset {1}:".format(e, match.range))
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

	def onBlock( self, match, indent, delta=-1 ):
		indent = delta + self.resolve("indent")[0] if indent is None else (indent or 0)
		if indent == 0:
			self._mode   = None
		elif self._mode == "macro":
			delta = indent - len(self.scopes)
			self._macro.append(lambda self: self.onBlock(match, None, delta))
			return None
		self.indent = indent
		self._writeFooter()
		while len(self.scopes) > indent:
			self._popScope()
		self.process(match["selector"])
		self.process(match["code"])

	def onMacroBlock( self, match, type, indent=0):
		if indent == 0:
			self._mode  = None
		assert self._mode != "macro"
		type, filter, name, params = type
		name = name or None
		self._mode   = "macro"
		self._macro  = []
		self._macros[name] = [params, self._macro]
		self.process(match["code"])

	def onSpecialBlock( self, match, type, indent=None):
		if indent == 0:
			self._mode  = None
		elif self._mode == "macro":
			self._macro.append(lambda self: self.onSpecialBlock(indent, match, type))
			return None
		self._writeFooter()
		type, filter, name, params = type
		self._write("{0}{1} {2} {3} {{".format(type, filter or "", name or "", ", ".join(params) if params else  ""))
		self._mode = None
		self.process(match["code"])
		self._footer = "}"

	def onSource( self, match ):
		result = [self.process(_) for _ in match]
		if self._footer:
			self._write(self._footer)
			self._footer = None
		return result

	# ==========================================================================
	# OUTPUT
	# ==========================================================================

	def _writeFooter( self ):
		if self._footer and self._mode == None:
			self._write(self._footer)
			self._footer = None

	def _write( self, line=None, indent=0 ):
		line = "  " * indent + ensure_str(line) + "\n"
		if isinstance(self.output, io.TextIOBase):
			self.output.write(line)
		else:
			self.output.write(line)
		return line

	# ==========================================================================
	# VARIABLES
	# ==========================================================================

	def _pushScope( self, scopes ):
		self.scopes.append(scopes)
		self.variables.append({})
		self._evaluated.append({})

	def _popScope( self ):
		self.variables.pop()
		self._evaluated.pop()
		return self.scopes.pop()

	# ==========================================================================
	# SCOPE & SELECTION HELPERS
	# ==========================================================================

	def _listCurrentScopes( self ):
		"""Lists the current scopes"""
		return self.scopes[-1] if self.scopes else None

	def _expandScope( self, scope ):
		"""Expands the given scope so that it is fully prefixed by the parent.
		The resulting cardinality should be `len(parents) * len(scope)`."""
		parent_scopes = self._listCurrentScopes()
		# If there's not parent scope, we return the scope as-is
		if not parent_scopes: return scope or []
		res = []
		for parent_selection in parent_scopes:
			for selection in scope:
				new_selection = parent_selection.copy().extend(selection)
				res.append(new_selection)
		assert len(res) == len(parent_scopes) * len(scope)
		return res

	def _copySelector( self, selector ):
		"""A relatively bad way to copy the CFFI ParsingResult"""
		# FIXME: This is slightly brittle, I think selection
		# might be a parsing result from CFFI. It's not
		# ideal, but it works.
		ns = []
		for i in range(len(selector)): ns.append(selector[i])
		return ns

	# FIXME: This is not supported anymore
	def _selectionProcessBEM( self, selection ):
		"""Processes the given selection, extracting BEM classes
		from the selectors."""
		bem_prefixes = []
		# First step, we extract the BEM classes (-XXX-) from
		# the selectors.
		if not selection: return selection
		new_selection = []
		for s in selection:
			new_classes  = []
			if s and len(s) >= 3:
				# We filter out BEM prefixes from the class list
				for c in (s[2] or "").split("."):
					if c and (c[0] == "-" or c[-1] == "-"):
						bem_prefixes.append(c)
					else:
						new_classes.append(c)
				ns    = self._copySelector(s)
				ns[2] = ".".join(new_classes)
				new_selection.append(ns)
			else:
				new_selection.append(s)
		# Now that we have the BEM prefixes, we reverse them.
		if bem_prefixes:
			new_selection[-1] = self._copySelector(new_selection[-1])
			i = len(bem_prefixes) - 1
			r = []
			while i >= 0:
				p = bem_prefixes[i]
				# This is an edge case where we don't have
				# a closing BEM class, ie.
				# `one- -two- -three-`
				# instead of
				# `one- -two- -three`
				# (note the absence of a trailing dash)
				if not r and p[-1] == "-":
					break
				r.insert(0, p[1:] if p[0] == "-" else p)
				if p[0] == "-":
					i -=1
				else:
					break
			bem_class = "." + "".join(r)
			cur_class = new_selection[-1][2] or ""
			new_selection[-1][2] = cur_class + bem_class
		# The new selection contains the aggregated BEM
		# classes.
		return new_selection

	def _stringEscapeFix( self, text ):
		# NOTE: CleverCSS had some trouble with the empty content string, which
		# lead us to write content: "\"\"/\"\"". This escapes that
		if text.startswith(self.FIX_STRING_DELIMITER) and text.endswith(self.FIX_STRING_DELIMITER):
			return text[len(self.FIX_STRING_DELIMITER):-len(self.FIX_STRING_DELIMITER)]
		else:
			return text

	def _valueAsString( self, value ):
		"""Converts a value `(value:any, type:char)` into its CSS string
		representation."""
		# if isinstance(value, str) or isinstance(value,unicode): return value
		# assert isinstance(value, list) or isinstance(value, tuple) and len(value) == 2, "{0}: Expected `(type, value)`, got {1}".format(self._valueAsString, repr(value))
		v, u = value ; u = u or ""
		# == UNITS
		if   u == "L":
			return ", ".join([self._valueAsString(e) for e in v])
		elif u == "l":
			return " ".join([self._valueAsString(e) for e in v])
		elif u == "%":
			v = 100.0 * v
			d = int(v)
			if v == d:
				return "{0:d}%".format(d)
			else:
				return "{0:0.3f}%".format(v)
		elif   u == "C":
			if is_string(v):
				# If we have a string instead of a tuple, we pass it as-is
				return ensure_str(v)
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
		elif u == "S":
			s,q = v
			if q:
				return q + ensure_str(s) + q
			else:
				return ensure_str(s)
		# == VALUES
		if   type(v) == int:
			return "{0:d}{1}".format(v,u)
		elif type(v) == float:
			# We remove the trailing 0 to have the most compact representation
			v = "{0:0.3f}".format(v)
			while len(v) > 2 and v[-1] == "0" and v[-2] != ".":
				v = v[0:-1]
			if v.endswith(".0"):v = v[:-2]
			return v + u
		elif (isinstance(v, tuple) or isinstance (v, list)) and v[1] in (None, "'", '"', ""):
			if self._property == "content":
				v,p = v
				v   = json.dumps(v)
				return (p + v + p) if p else v
			else:
				return str(v)
		elif is_string(v):
			return ensure_str(v)
		else:
			raise ProcessingException("Value string conversion not implemented: {0}".format(value))

# EOF
