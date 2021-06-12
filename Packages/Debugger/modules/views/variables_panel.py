from __future__ import annotations
from ..typecheck import *

from ..import ui
from ..import dap

from ..watch import Watch
from .variable import VariableComponent
from . import css


class VariablesPanel (ui.div):
	def __init__(self, sessions: dap.Sessions):
		super().__init__()
		self.watch_view = WatchView(sessions.watch)
		self.variables_view = VariablesView(sessions)

	def render(self) -> ui.div.Children:
		return [
			self.watch_view,
			self.variables_view,
		]


class VariablesView (ui.div):
	def __init__(self, sessions: dap.Sessions):
		super().__init__()
		self.sessions = sessions
		self.sessions.on_updated_variables.add(lambda session: self.on_updated(session))
		self.sessions.on_removed_session.add(lambda session: self.on_updated(session))
		self.variables = []

	def on_updated(self, session: dap.Session):
		if self.sessions.has_active:
			self.variables = [VariableComponent(variable) for variable in self.sessions.active.variables]
			if self.variables:
				self.variables[0].set_expanded()
		else:
			self.variables = []

		self.dirty()

	def render(self):
		session = self.sessions.selected_session
		if not session:
			return

		variables = [VariableComponent(variable) for variable in session.variables]
		if variables:
			variables[0].set_expanded()

		return variables


class WatchView(ui.div):
	def __init__(self, provider: Watch):
		super().__init__()
		self.provider = provider
		self.open = True

	def added(self, layout: ui.Layout):
		self.on_updated_handle = self.provider.on_updated.add(self.dirty)

	def removed(self):
		self.on_updated_handle.dispose()

	def toggle_expand(self):
		self.open = not self.open
		self.dirty()

	def render(self) -> ui.div.Children:
		if not self.provider.expressions:
			return None

		header = ui.div(height=css.row_height)[
			ui.click(self.toggle_expand)[
				ui.icon(ui.Images.shared.open if self.open else ui.Images.shared.close)
			],
			ui.text('Watch', css=css.label_secondary)
		]
		if not self.open:
			return header

		return [
			header,
			ui.div(css=css.table_inset)[
				[WatchExpressionView(expresion, on_edit_not_available=self.provider.edit_run) for expresion in self.provider.expressions]
			]
		]

class WatchExpressionView(ui.div):
	def __init__(self, expression: Watch.Expression, on_edit_not_available: Callable[[Watch.Expression], None]):
		super().__init__()
		self.expression = expression
		self.on_edit_not_available = on_edit_not_available

	def added(self, layout: ui.Layout):
		self.on_updated_handle = self.expression.on_updated.add(self.dirty)

	def removed(self):
		self.on_updated_handle.dispose()

	def render(self):
		if self.expression.evaluate_response:
			component = VariableComponent(self.expression.evaluate_response)
			return [component]

		return [
			ui.div(height=css.row_height, css=css.padding_left)[
				ui.click(lambda: self.on_edit_not_available(self.expression))[
					ui.text(self.expression.value, css=css.label_secondary),
					ui.spacer(1),
					ui.text("not available", css=css.label),
				]
			]
		]
