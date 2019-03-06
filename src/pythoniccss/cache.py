import re, os, time, stat, io
from typing      import List,Optional,Dict,TypeVar,Generic,Callable
from .grammar    import getGrammar as getPCSSGrammar
from .processor  import PCSSProcessor
from  .writer    import CSSWriter

__doc__ = """
Implements a minimal cache system with dynamic dependencies, used to speed
up the compilation of PCSS files.
"""

T = TypeVar('T')

def now( at:Optional[float] ) -> float:
	return time.time() if at is None else at

# -----------------------------------------------------------------------------
#
# DEPENDENCIES
#
# -----------------------------------------------------------------------------

class Dependencies:

	RE_INCLUDE = re.compile("@include\s+([^\s]+)")
	RE_IMPORT  = re.compile("@(import|use)\s+(.+)")
	RE_URL     = re.compile(".*url\(([^\)]+)\)")

	@classmethod
	def Parse( cls, path ):
		with open(path) as f:
			yield from cls.ParseString(f.read())

	@classmethod
	def ParseString( cls, text ):
		for m in cls.RE_INCLUDE.finditer(text):
			yield ("include", m.group(1).strip())
		for m in cls.RE_IMPORT.finditer(text):
			yield (m.group(1), m.group(2).strip())

# -----------------------------------------------------------------------------
#
# RESOLVER
#
# -----------------------------------------------------------------------------

class Resolver:

	PATHS = [
		"lib/pcss",
		"lib/css",
		"src/pcss",
		"src/css",
	]

	EXT = [".pcss", ".css"]

	def __init__( self ):
		self.paths = self.PATHS
		self.exts  = self.EXT

	def resolve( self, type:str, name:str ) -> Optional[str]:
		for path in self.paths:
			for ext in self.exts:
				p = os.path.join(path, "{0}{1}".format(name, ext))
				if os.path.exists(p):
					return p
		return None

# -----------------------------------------------------------------------------
#
# CACHED
#
# -----------------------------------------------------------------------------

class Cached(Generic[T]):
	"""A cached value with a timestamp. It keeps an `updated` timestamp
	corresponding to the moment where the  value was last set."""


	def __init__( self ):
		self.updated = 0
		self._value:Optional[T]  = None

	@property
	def value( self ):
		"""Returns the value as it is."""
		return self._value

	@value.setter
	def value( self, value ):
		"""Sets the value and updates the timestamp to the current time."""
		self._value  = value
		self.updated = time.time()

	def __repr__( self ):
		return "<{1}:{0}>".format(self._value, self.__class__.__name__.rsplit(".", 1)[-1])

# -----------------------------------------------------------------------------
#
# MEMOIZED
#
# -----------------------------------------------------------------------------

class Memoized(Cached[T]):
	"""A memoized function call with a timestamp, which is guarded by
	a `changed` function that returns a timestamp that must be met by
	the `updated` property of the memoized value."""

	def __init__( self, updater:Callable[[],T], changed:Callable[[],float] ):
		super().__init__()
		self._value:T = None
		self._updater = updater
		self._changed = changed

	@property
	def hasExpired( self ) -> bool:
		return self.updated < self.changed

	@property
	def changed( self ) -> float:
		return self._changed()

	@property
	def value( self ) -> T:
		if self.hasExpired:
			self._value  = self._updater()
			self.updated = time.time()
		return self._value

	@value.setter
	def value( self, value ):
		raise Exception("A memoized value cannot have its value set.")

# -----------------------------------------------------------------------------
#
# NODE
#
# -----------------------------------------------------------------------------

# TODO: Should we differentiate between direct an indirect dependencies?
class Node:
	"""Represents a node in a dependency graph."""

	def __init__( self, graph:'Graph', path:str ) :
		self.graph                      = graph
		self.path                       = os.path.abspath(path)
		self._directDependencies:Memoized[List['Node']] = Memoized(self.listDirectDependencies, lambda:self.modified)

	@property
	def modified( self ) -> float:
		"""Tells when the node was modified locally"""
		# OPTIMIZATION. We might want to cache the `stat` and only update
		# it every 5s or so.
		return os.stat(self.path)[stat.ST_MTIME]

	@property
	def changed( self ) -> float:
		"""Tells when the aggregate content of this node and its dependencies
		have changed, which is the maximum modified value. """
		v = self.modified
		# NOTE: Alternatively, we could do changed on direct dependencies
		for _ in self.walkDependencies():
			v = max(v,_.modified)
		return v

	@property
	def dependencies( self ):
		"""Returns the cached list of DIRECT and INDIRECT dependencies for the node."""
		return list(_ for _ in self.walkDependencies())

	@property
	def directDependencies( self ):
		"""Returns the cached list of DIRECT dependencies for the node."""
		return self._directDependencies.value

	def hasChanged( self, since:float ) -> bool:
		"""A  node has changed when its `changed` attribute is greated than
		the given timestamp."""
		return self.changed > since

	def listDirectDependencies( self ):
		"""Returns a freshly calculated list of the direct dependencies of this node."""
		return list(_ for _ in (self.graph.resolve(*_) for _ in Dependencies.Parse(self.path)) if _)

	def walkDependencies( self, visited:Optional[List['Node']]=None ):
		"""Walks ALL dependencies (direct and indirect) within that node,
		making sure not to visit the same node twice."""
		visited_nodes:List['Node'] = [] if visited is None else visited
		deps    = [] + self.directDependencies
		while deps:
			node = deps.pop(0)
			if node not in visited_nodes:
				yield node
				visited_nodes.append(node)
				yield from node.walkDependencies(visited_nodes)

	def __repr__( self ):
		return "<Node:{0}>".format(self.path)

# -----------------------------------------------------------------------------
#
# SYNTHETIC NODE
#
# -----------------------------------------------------------------------------

class PCSSNode( Node ):
	"""A node with a value that is the synthesized when the node changes."""

	def __init__( self, graph:'Graph', path:str ):
		super().__init__(graph, path)
		# These are the synthesized attributes for the node.
		self._ast   = Memoized(lambda:self.getAST(),   lambda:self.modified)
		self._model = Memoized(lambda:self.getModel(), lambda:self.changed)
		self._css   = Memoized(lambda:self.getCSS(),   lambda:self.changed)

	@property
	def ast( self ):
		return self._ast.value

	@property
	def model( self ):
		return self._model.value

	@property
	def css( self ):
		return self._css.value

	def getAST( self ):
		# NOTE: We need to return the match, otherwise it won't work
		return getPCSSGrammar().parsePath(self.path)

	def getModel( self ):
		return PCSSProcessor(path=self.path,graph=self.graph).process(self.ast.match) if self.ast.isSuccess else None

	def getCSS( self ):
		path = self.path
		model = self.model
		if model:
			s = io.BytesIO()
			writer = CSSWriter(output=s).write(model)
			s.seek(0)
			v = s.getvalue()
			s.close()
			return v
		else:
			None

# -----------------------------------------------------------------------------
#
# GRAPH
#
# -----------------------------------------------------------------------------

# TODO: Now we need a strategy to clear the cache: which nodes do we want
# to remove, which attributes do we want to free? We would need to reify
# access times, count and weight in order to make a good decision.

class Graph:

	def __init__( self ):
		self.nodes = {}
		self._resolver = Resolver()
		self._types = {
			".pcss": PCSSNode
		}

	def synthesizePCSS( self, node ):
		res = getPCSSGrammar().parsePath(node.path)
		p   = PCSSProcessor(path=node.path)
		m   = p.process(res.match)
		return m

	def get(self, path:str) -> Optional[Node]:
		path = os.path.abspath(path)
		if path not in self.nodes:
			name,ext = os.path.splitext(path)
			node_type = self._types.get(ext, Node)
			node = node_type(self, path)
			self.nodes[path] = node
		return self.nodes[path]

	def resolve(self, type:str, name:str) -> Optional[Node]:
		res =  self._resolver.resolve(type, name)
		return self.get(res) if res else None

# EOF - vim: ts=4 sw=4 noet
