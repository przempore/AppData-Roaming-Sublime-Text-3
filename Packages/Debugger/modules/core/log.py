from ..typecheck import *

_should_log_exceptions = True
_should_log_error = True
_should_log_info = True


def log_configure(log_info: bool, log_errors: bool, log_exceptions: bool):
	global _should_log_exceptions
	global _should_log_error
	global _should_log_info

	_should_log_exceptions = log_exceptions
	_should_log_error = log_errors
	_should_log_info = log_info


def log_error(*args) -> None:
	if not _should_log_error:
		return
	print('Debugger: error:', *args)


def log_exception(*args) -> None:
	import traceback
	if not _should_log_exceptions:
		return
	print(*args, end='')
	print(traceback.format_exc())


def log_info(*args) -> None:
	if not _should_log_info:
		return
	print('Debugger:', *args)


class Logger(Protocol):
	def error(self, value: str):
		self.log('error', value)
	def info(self, value: str):
		self.log('info', value)
	def log(self, type: str, value: str):
		...

class StdioLogger(Logger):
	def log(self, type: str, value: str):
		print(f'Debugger: {type}: {value}')

stdio = StdioLogger()