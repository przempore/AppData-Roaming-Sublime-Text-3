from ...typecheck import *
from ...import (
	core,
	dap,
	ui,
)
from .terminal import Terminal
from ..variables import Variable

if TYPE_CHECKING:
	from ..debugger_session import DebuggerSession

class TermianlDebugger (Terminal):
	def __init__(self, debugger: 'DebuggerSession', on_run_command: Callable[[str], None]):
		super().__init__("Debugger Console")
		self.on_run_command = on_run_command
		self.debugger = debugger

	def writeable(self) -> bool:
		return True

	def writeable_prompt(self) -> str:
		return "click to input debugger command"

	def write(self, text: str):
		self.on_run_command(text)

	def program_output(self, client: Optional[dap.Client], event: dap.OutputEvent):
		variablesReference = event.variablesReference
		if variablesReference and client:
			# this seems to be what vscode does it ignores the actual message here.
			# Some of the messages are junk like "output" that we probably don't want to display
			@core.coroutine
			def appendVariabble() -> core.awaitable[None]:
				variables = yield from client.GetVariables(variablesReference)
				for variable in variables:
					variable.name = "" # this is what vs code does?
					self.append_variable(variable, event.source, event.line)

			# this could make variable messages appear out of order. Do we care??
			core.run(appendVariabble())
		else:
			self.append_text(event.category, event.text, event.source, event.line)

	def append_variable(self, variable: dap.Variable, source: Optional[dap.Source], line: Optional[int]):
		v = Variable(self.debugger, variable)
		if source:
			self.add_variable(v, (source, line))
		else:
			self.add_variable(v)

	def append_text(self, type: str, text: str, source: Optional[dap.Source], line: Optional[int]):
		if type == "telemetry":
			return

		if source:
			self.add(type, text, (source, line))
		else:
			self.add(type, text)

	def log_error(self, text: str) -> None:
		self.append_text('debugger.error', text + '\n', None, None)

	def log_info(self, text: str) -> None:
		self.append_text('debugger.info', text + '\n', None, None)
