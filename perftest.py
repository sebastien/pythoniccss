from   pythoniccss import *
import ctypes

__doc__ = """
walk_c                        =     60125 0.001s
walk_ctypes_count             =     60125 0.017s
walk_ctypes_wrap              =     60126 0.768s
walk_ctypes_wrap_children     =     60126 1.123s
walk_python                   =     60126 0.700s

with numbers like that, it becomes clear that the walking itself it very
easy, but the wrapping of Match objects as Python objects is very expensive, to
the extent where a pure Python walk is faster than a C-backed walk, as we have
to pay overhead for callback with C backed version.

The solution for improving performance is to improve the wrapping function.

"""
def walk_c(r):
	return r.match.countAll()

def walk_ctypes_count(r):
	def walk( match, step, context ):
		return step
	callback = C.TYPES["WalkingCallback"](walk)
	return LIB.symbols.Match__walk(r.match._cobjectPointer, callback, 0, None)

def walk_ctypes_wrap(r):
	def walk( match, step, matches ):
		matches = ctypes.cast(matches, ctypes.py_object).value
		match   = ctypes.cast(match, C.TYPES["Match*"])
		match   = LIB.wrap(match)
		assert isinstance(match, Match), "Expected match, got {0} {1} {2}".format(type(match), step, len(matches))
		matches.append(match)
		return step
	callback  = C.TYPES["WalkingCallback"](walk)
	matches   = []
	c_matches = ctypes.py_object(matches)
	LIB.symbols.Match__walk(r.match._cobjectPointer, callback, 0, c_matches)
	return len(matches)

def walk_ctypes_wrap_children(r):
	def walk( match, step, matches ):
		matches = ctypes.cast(matches, ctypes.py_object).value
		match   = ctypes.cast(match, C.TYPES["Match*"])
		match   = LIB.wrap(match)
		assert isinstance(match, Match)
		matches.append(match.children)
		return step
	callback = C.TYPES["WalkingCallback"](walk)
	matches  = []
	c_matches = ctypes.py_object(matches)
	LIB.symbols.Match__walk(r.match._cobjectPointer, callback, 0, c_matches)
	return len(matches)

def walk_python(r):
	result = []
	def walk(match, step):
		result.append(match)
		for m in match.children:
			step = walk(m, step+1)
		return step
	walk(r.match, 0)
	return len(result)

def walk_process(r):
	def walk( match, step, matches ):
		matches    = ctypes.cast(matches, ctypes.py_object).value
		match      = ctypes.cast(match, C.TYPES["Match*"])
		match_type = match.contents.element.contents.type
		if   match_type == TYPE_REFERENCE:
			value = None
		elif match_type == TYPE_RULE:
			value = None
		elif match_type == TYPE_GROUP:
			value = None
		elif match_type == TYPE_TOKEN:
			value = LIB.symbols.TokenMatch_group(match,0)
		elif match_type == TYPE_WORD:
			value = LIB.symbols.WordMatch_group(match)
		context["matches"].append(match)
		return step
	callback  = C.TYPES["WalkingCallback"](walk)
	context = {
		"matches":[],
	}
	c_context = ctypes.py_object(context)
	LIB.symbols.Match__walk(r.match._cobjectPointer, callback, 0, c_context)
	return len(context["matches"])



if __name__ == "__main__":
	r = parse(sys.argv[1] if len(sys.argv) > 1 else "moneyball.pcss")
	f = sorted([(_[0],_[1]) for _ in locals().items() if _[0].startswith("walk_")])
	for n,c in f:
		t = time.time()
		v = c(r)
		print ("{0:30s}={1:-10d} {2:0.3f}s".format(n, v, time.time() - t))

# EOF
