from ..typecheck import *

import sublime
import sublime_plugin

from ..libs import asyncio

from .core import call_soon_threadsafe, create_future, coroutine, awaitable
from .event import Handle

@coroutine
def sublime_open_file_async(window: sublime.Window, file: str, line: Optional[int] = None) -> awaitable[sublime.View]:
	view = window.open_file(file)
	yield from wait_for_view_to_load(view)
	if line is None:
		return view
	view.show(view.text_point(line, 0), True)
	return view


@coroutine
def wait_for_view_to_load(view: sublime.View):
	from .. import ui
	if view.is_loading():
		future_view = create_future()

		def loaded_view(v: sublime.View) -> None:
			if view.id() == v.id():
				future_view.set_result(view)

		handle = ui.view_loaded.add(loaded_view)
		yield from future_view
		handle.dispose()
