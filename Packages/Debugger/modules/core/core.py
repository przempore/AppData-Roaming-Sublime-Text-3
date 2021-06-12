from __future__ import annotations
from ..typecheck import *

import sublime
import concurrent
import asyncio

from .log import log_exception
from .sublime_event_loop import SublimeEventLoop

T = TypeVar('T')
Args = TypeVarTuple('Args')

CancelledError = asyncio.CancelledError

sublime_event_loop = SublimeEventLoop() #type: ignore
sublime_event_loop_executor = concurrent.futures.ThreadPoolExecutor(max_workers=8) #type: ignore
asyncio.set_event_loop(sublime_event_loop)

class Future(asyncio.Future, Generic[T]):
	def __init__(self):
		super().__init__(loop=sublime_event_loop)

	def set_result(self, result: T) -> None:
	    return super().set_result(result) #type: ignore

def call_soon_threadsafe(callback: Callable[[Unpack[Args]], None], *args: Unpack[Args]):
	return sublime_event_loop.call_soon(callback, *args) #type: ignore

def call_soon(callback: Callable[[Unpack[Args]], None], *args: Unpack[Args]):
	return sublime_event_loop.call_soon(callback, *args) #type: ignore

def call_later(interval: float, callback: Callable[[Unpack[Args]], None], *args: Unpack[Args]):
	return sublime_event_loop.call_later(interval, callback, *args) #type: ignore

def create_future():
	return sublime_event_loop.create_future()

def run_in_executor(func: Callable[[Unpack[Args]], T], *args: Unpack[Args]) -> Future[T]:
	return asyncio.futures.wrap_future(sublime_event_loop_executor.submit(func, *args), loop=sublime_event_loop) #type: ignore

def wait(fs: Iterable[Awaitable[Any]]):
	return asyncio.wait(fs, loop=sublime_event_loop)

def sleep(delay: float) -> Awaitable[None]:
	return asyncio.sleep(delay, loop=sublime_event_loop)

def schedule(func: Callable[[Unpack[Args]], Coroutine[Any, Any, T]], *args: Any) -> Callable[[Unpack[Args]], Future[T]]:
	def wrap(*args):
		return asyncio.ensure_future(func(*args), loop=sublime_event_loop) #type: ignore
	wrap.__name__ = func.__name__ #type: ignore
	return wrap

def run(awaitable: Awaitable[T], on_done: Callable[[T], None] | None = None, on_error: Callable[[BaseException], None] | None = None) -> Future[T]:
	task: Future[T] = asyncio.ensure_future(awaitable, loop=sublime_event_loop)

	def done(task: asyncio.Future[T]) -> None:
		exception = task.exception() 

		if on_error and exception:
			on_error(exception)

			try:
				raise exception
			except Exception as e:
				log_exception()

			return

		result: T = task.result()
		if on_done:
			on_done(result)

	task.add_done_callback(done)
	return task

def display(msg: 'Any'):
	sublime.error_message('{}'.format(msg))
