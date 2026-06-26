import time, sys, atexit, os

INFO = 2
DEBUG = 4
WARNING = 8
ERROR = 16
CRITICAL = 32
NOTSET = 62

class _logger():
	def __init__(self):
		self._timer = time.perf_counter()
		self._buffer = []
		self.path = None
		self.showframe = False
		self.level = NOTSET
		atexit.register(self._flush)
	
	def basicConfig(self, filename=None, showframe=None, level=None):
		if isinstance(filename, str): self.path = filename
		if isinstance(showframe, bool): self.showframe = showframe
		if isinstance(level, int): self.level = level

	def _log(self, level, msg, args):
		if isinstance(msg, str) and args:
			msg = msg % args
		self._buffer.append(f"{os.getpid()}::")
		self._buffer[-1] += f"{(time.perf_counter() - self._timer):.6f}::{level}"
		if self.showframe: self._buffer[-1] += f"::{sys._getframe(2).f_globals.get('__name__', '')}"
		self._buffer[-1] += f"::{msg}\n"

		if level not in ("ERROR", "CRITICAL") and len(self._buffer) < 12:
			return
		self._flush()
	
	def _flush(self):
		if self.path is None:
			return
		with open(self.path, "a", encoding="UTF-8") as f:
			f.write("".join(self._buffer))
		self._buffer = []

	def info(self, msg, *args):
		if INFO & self.level:
			self._log("INFO", msg, list(args))

	def debug(self, msg, *args):
		if DEBUG & self.level:
			self._log("DEBUG", msg, list(args))

	def warning(self, msg, *args):
		if WARNING & self.level:
			self._log("WARNING", msg, list(args))
	
	def error(self, msg, *args):
		if ERROR & self.level:
			self._log("ERROR", msg, list(args))
	
	def critical(self, msg, *args):
		if CRITICAL & self.level:
			self._log("CRITICAL", msg, list(args))
	
def getLogger(name=None):
	if name not in _loggers:
		_loggers[name] = _logger()
	return _loggers[name]

_loggers = {}
logger = getLogger()
