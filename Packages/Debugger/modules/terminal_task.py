from __future__ import annotations
from typing import Dict, Any, List, TypedDict

import re
import sublime
import Default #type: ignore
import time

from .import core
from .import dap

from .terminal import Terminal, Problem
from .panel import OutputPanel

class Position(TypedDict):
	line: int
	character: int|None

class Range(TypedDict):
	start: Position

class Diagnostic(TypedDict):
	range: Range
	severity: int
	message: str

class Diagnostics(TypedDict):
	file: str
	base: str
	errors: list[Diagnostic]

class TerminalTask(Terminal):
	def __init__(self, window: sublime.Window, task: dap.TaskExpanded):
		arguments = task.copy()
		name: str
		cmd: str|list[str]|None = arguments.get('cmd')

		if 'name' in arguments:
			name = arguments['name']
		elif isinstance(cmd, str):
			name = cmd
		elif isinstance(cmd, list):
			name = cmd and cmd[0] #type: ignore
		else:
			name = 'Untitled'

		self.background = arguments.get('background', False)

		super().__init__(name, arguments.get('working_dir'), arguments.get('file_regex'))

		# if we don't remove these additional arguments Default.exec.ExecCommand will be unhappy
		if 'name' in arguments:
			del arguments['name']
		if 'background' in arguments:
			del arguments['background']


		self.on_problems_updated: core.Event[None] = core.Event()
		self.diagnostics_per_file: list[Diagnostics] = []

		self.future: core.Future[None] = core.Future()
		self.window = window

		# only save the views that have an assigned file
		for view in self.window.views():
			if view.file_name() and view.is_dirty():
				view.run_command('save')

		self.panel = OutputPanel(self.window, name, show_panel=False)

		self.command = Exec(self.window)
		self.command.output_view = self.panel.view
		self.command.run(self, arguments)

		self.on_view_load_listener = core.on_view_load.add(self.on_view_load)

	def show_backing_panel(self):
		self.panel.open()

	def on_view_load(self, view: sublime.View):
		# refresh the phantoms from exec
		self.command.update_annotations()

	def dispose(self):
		try:
			self.command.proc.kill()
		except Exception as e:
			core.log_exception(e)

		self.command.hide_annotations()
		self.on_view_load_listener.dispose()
		self.panel.dispose()

	def write_stdout(self, text: str):
		self.add('terminal.output', text)

	async def wait(self) -> None:
		try:
			await self.future
		except core.CancelledError as e:
			print(f'Command cancelled {self.name()}')
			self.command.run(self, {
				'kill': True
			})
			raise e

	def on_output(self, characters: str):
		self.write_stdout(characters)

	def on_updated_errors(self, errors_by_file):
		self.diagnostics_per_file.clear()

		for file, errors in errors_by_file.items():
			diagnostics: list[Diagnostic] = []
			for error in errors:
				diagnostic: Diagnostic = {
					'severity': 1,
					'message': error[2],
					'range': {
						'start': {
							'line': error[0],
							'character': error[1]
						}
					}
				}
				diagnostics.append(diagnostic)

			self.diagnostics_per_file.append({
				'file': file,
				'base': None,
				'errors': diagnostics
			})

		self.on_problems_updated()

	def on_finished(self, exit_code: int, exit_status: str):
		self.finished = True
		self.exit_code = exit_code
		self.exit_status = exit_status

		if self.future.done():
			return

		if exit_code is None:
			self.future.cancel()
		elif exit_code == 0:
			self.future.set_result(None)
		else:
			self.future.set_exception(core.Error(f'Command {self.name()} failed with exit_code {exit_code}'))

		self.on_updated()


class Exec(Default.exec.ExecCommand):
	def run(self, instance: TerminalTask, args: Any):
		self.instance = instance
		panel = self.window.active_panel()
		super().run(**args)

		# return to previous panel we don't want to show the build results panel
		self.window.run_command("show_panel", {"panel": panel})

	def update_annotations(self):
		super().update_annotations()
		self.instance.on_updated_errors(self.errs_by_file)

	def on_finished(self, proc):
		super().on_finished(proc)

		# modified from Default exec.py
		if self.instance:
			if proc.killed:
				status = "[Cancelled]"
				code = None
			else:
				elapsed = time.time() - proc.start_time
				code: int = proc.exit_code() or 0
				if code == 0:
					status = "[Finished in %.1fs]" % elapsed
				else:
					status = "[Finished in %.1fs with exit code %d]" % (elapsed, code)

			self.instance.on_finished(code, status)
			# self.window.run_command("next_result")

	def write(self, characters: str):
		super().write(characters)
		self.instance.on_output(characters)


class Tasks:
	tasks: list[TerminalTask]

	added: core.Event[TerminalTask]
	removed: core.Event[TerminalTask]
	updated: core.Event[TerminalTask]

	def __init__(self) -> None:
		self.added = core.Event()
		self.removed = core.Event()
		self.updated = core.Event()
		self.tasks = []

	@core.schedule
	async def run(self, window: sublime.Window, task: dap.TaskExpanded):
		terminal = TerminalTask(window, task)
		terminal.on_problems_updated.add(lambda: self.updated(terminal))

		self.tasks.append(terminal)
		self.added(terminal)

		try:
			await terminal.wait()
		except:
			raise
		finally:
			self.updated(terminal)
		

	def cancel(self, task: TerminalTask):
		self.tasks.remove(task)
		# todo actually cancel...
		self.removed(task)
		task.dispose()

	def clear(self):
		while self.tasks:
			if not self.tasks[-1].finished:
				continue

			task = self.tasks.pop()
			self.removed(task)
			task.dispose()

	def dispose(self):
		while self.tasks:
			task = self.tasks.pop()
			self.removed(task)
			task.dispose()

