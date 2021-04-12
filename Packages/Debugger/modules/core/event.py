from ..typecheck import *

from .core import call_soon_threadsafe

T = TypeVar('T')

class Handle (Generic[T]):
	def __init__(self, event: 'Event[T]', callback: Callable[[T], None]) -> None:
		self.callback = callback
		self.event = event

	def dispose(self) -> None:
		self.event.handlers.remove(self)


class Event (Generic[T]):
	def __init__(self) -> None:
		self.handlers = [] # type: List[Handle[T]]

	@overload
	def add(self: 'Event[None]', callback: Callable[[], None]) -> Handle[None]:
		...

	@overload
	def add(self, callback: Callable[[T], None]) -> Handle[T]:
		...

	def add(self, callback: Callable[[T], None]) -> Handle[T]: #type: ignore
		handle = Handle(self, callback)
		self.handlers.append(handle)
		return handle

	def add_handle(self, handle: Handle[T]) -> None:
		self.handlers.append(handle)

	def __call__(self, *data: T) -> None:
		self.post(*data)

	def post(self, *data: T) -> None:
		for h in self.handlers:
			h.callback(*data)
