from   pythoniccss import *
import ctypes

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
		matches.append(LIB.wrap(match))
		return step
	callback = C.TYPES["WalkingCallback"](walk)
	return LIB.symbols.Match__walk(r.match._cobjectPointer, callback, 0, ctypes.py_object([]))

def walk_python(r):
	def walk(match, step):
		for m in match.children:
			step = walk(m, step+1)
		return step
	return walk(r.match, 0)

if __name__ == "__main__":
	r = parse(sys.argv[1] if len(sys.argv) > 1 else "moneyball.pcss")
	f = sorted([(_[0],_[1]) for _ in locals().items() if _[0].startswith("walk_")])
	for n,c in f:
		t = time.time()
		v = c(r)
		print ("{0:20s}={1:-10d} {2:0.3f}s".format(n, v, time.time() - t))

# EOF
