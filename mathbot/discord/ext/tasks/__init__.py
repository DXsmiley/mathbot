import asyncio
import aiohttp
import websockets
import discord
import inspect
import logging
import datetime

from collections.abc import Sequence
from discord.backoff import ExponentialBackoff

MAX_ASYNCIO_SECONDS = 3456000

log = logging.getLogger(__name__)

def _get_time_parameter(time, *, inst=isinstance, dt=datetime.time, utc=datetime.timezone.utc):
    if inst(time, dt):
        return [time if time.tzinfo is not None else time.replace(tzinfo=utc)]
    if not inst(time, Sequence):
        raise TypeError('time parameter must be datetime.time or a sequence of datetime.time')
    if not time:
        raise ValueError('time parameter must not be an empty sequence.')

    ret = []
    for index, t in enumerate(time):
        if not inst(t, dt):
            raise TypeError('index %d of time sequence expected %r not %r' % (index, dt, type(t)))
        ret.append(t if t.tzinfo is not None else t.replace(tzinfo=utc))
    return sorted(ret)

class Loop:
    """A background task helper that abstracts the loop and reconnection logic for you.

    The main interface to create this is through :func:`loop`.
    """
    def __init__(self, coro, seconds, hours, minutes, time, count, reconnect, loop):
        self.coro = coro
        self.reconnect = reconnect
        self.loop = loop or asyncio.get_event_loop()
        self.count = count
        self._current_loop = 0
        self._task = None
        self._injected = None
        self._valid_exception = (
            OSError,
            discord.HTTPException,
            discord.GatewayNotFound,
            discord.ConnectionClosed,
            aiohttp.ClientError,
            asyncio.TimeoutError,
            websockets.InvalidHandshake,
            websockets.WebSocketProtocolError,
        )

        self._before_loop = None
        self._after_loop = None
        self._is_being_cancelled = False
        self._has_failed = False
        self._stop_next_iteration = False
        self._exception = None

        if self.count is not None and self.count <= 0:
            raise ValueError('count must be greater than 0 or None.')

        self.change_interval(seconds=seconds, minutes=minutes, hours=hours, time=time)

        if not inspect.iscoroutinefunction(self.coro):
            raise TypeError('Expected coroutine function, not {0.__name__!r}.'.format(type(self.coro)))

    async def _call_loop_function(self, name):
        coro = getattr(self, '_' + name)
        if coro is None:
            return

        if self._injected is not None:
            await coro(self._injected)
        else:
            await coro()

    async def _loop(self, *args, **kwargs):
        backoff = ExponentialBackoff()
        await self._call_loop_function('before_loop')
        try:
            # If a specific time is needed, wait before calling the function
            if self._time is not None:
                await asyncio.sleep(self._get_next_sleep_time())

            while True:
                try:
                    await self.coro(*args, **kwargs)
                except self._valid_exception as exc:
                    if not self.reconnect:
                        raise
                    await asyncio.sleep(backoff.delay())
                else:
                    if self._stop_next_iteration:
                        return
                    self._current_loop += 1
                    if self._current_loop == self.count:
                        break

                    await asyncio.sleep(self._get_next_sleep_time())
        except asyncio.CancelledError:
            self._is_being_cancelled = True
            raise
        except Exception as e:
            self._has_failed = True
            self._exception = e
            log.exception('Internal background task failed.')
            raise
        finally:
            await self._call_loop_function('after_loop')
            self._is_being_cancelled = False
            self._current_loop = 0
            self._stop_next_iteration = False
            self._has_failed = False
            self._exception = None

    def __get__(self, obj, objtype):
        if obj is None:
            return self
        self._injected = obj
        return self

    @property
    def current_loop(self):
        """:class:`int`: The current iteration of the loop."""
        return self._current_loop

    def start(self, *args, **kwargs):
        r"""Starts the internal task in the event loop.

        Parameters
        ------------
        \*args
            The arguments to to use.
        \*\*kwargs
            The keyword arguments to use.

        Raises
        --------
        RuntimeError
            A task has already been launched and is running.

        Returns
        ---------
        :class:`asyncio.Task`
            The task that has been created.
        """

        if self._task is not None and not self._task.done():
            raise RuntimeError('Task is already launched and is not completed.')

        if self._injected is not None:
            args = (self._injected, *args)

        self._task = self.loop.create_task(self._loop(*args, **kwargs))
        return self._task

    def stop(self):
        r"""Gracefully stops the task from running.

        Unlike :meth:`cancel`\, this allows the task to finish its
        current iteration before gracefully exiting.

        .. note::

            If the internal function raises an error that can be
            handled before finishing then it will retry until
            it succeeds.

            If this is undesirable, either remove the error handling
            before stopping via :meth:`clear_exception_types` or
            use :meth:`cancel` instead.

        .. versionadded:: 1.2.0
        """
        if self._task and not self._task.done():
            self._stop_next_iteration = True

    def _can_be_cancelled(self):
        return not self._is_being_cancelled and self._task and not self._task.done()

    def cancel(self):
        """Cancels the internal task, if it is running."""
        if self._can_be_cancelled():
            self._task.cancel()

    def restart(self, *args, **kwargs):
        r"""A convenience method to restart the internal task.

        .. note::

            Due to the way this function works, the task is not
            returned like :meth:`start`.

        Parameters
        ------------
        \*args
            The arguments to to use.
        \*\*kwargs
            The keyword arguments to use.
        """

        def restart_when_over(fut, *, args=args, kwargs=kwargs):
            self._task.remove_done_callback(restart_when_over)
            self.start(*args, **kwargs)

        if self._can_be_cancelled():
            self._task.add_done_callback(restart_when_over)
            self._task.cancel()

    def add_exception_type(self, *exceptions):
        r"""Adds exception types to be handled during the reconnect logic.

        By default the exception types handled are those handled by
        :meth:`discord.Client.connect`\, which includes a lot of internet disconnection
        errors.

        This function is useful if you're interacting with a 3rd party library that
        raises its own set of exceptions.

        Parameters
        ------------
        \*exceptions: Type[:class:`BaseException`]
            An argument list of exception classes to handle.

        Raises
        --------
        TypeError
            An exception passed is either not a class or not inherited from :class:`BaseException`.
        """

        for exc in exceptions:
            if not inspect.isclass(exc):
                raise TypeError('{0!r} must be a class.'.format(exc))
            if not issubclass(exc, BaseException):
                raise TypeError('{0!r} must inherit from BaseException.'.format(exc))

        self._valid_exception = (*self._valid_exception, *exceptions)

    def clear_exception_types(self):
        """Removes all exception types that are handled.

        .. note::

            This operation obviously cannot be undone!
        """
        self._valid_exception = tuple()

    def remove_exception_type(self, *exceptions):
        r"""Removes exception types from being handled during the reconnect logic.

        Parameters
        ------------
        \*exceptions: Type[:class:`BaseException`]
            An argument list of exception classes to handle.

        Returns
        ---------
        :class:`bool`
            Whether all exceptions were successfully removed.
        """
        old_length = len(self._valid_exception)
        self._valid_exception = tuple(x for x in self._valid_exception if x not in exceptions)
        return len(self._valid_exception) == old_length - len(exceptions)

    def get_task(self):
        """Optional[:class:`asyncio.Task`]: Fetches the internal task or ``None`` if there isn't one running."""
        return self._task

    def is_being_cancelled(self):
        """Whether the task is being cancelled."""
        return self._is_being_cancelled

    def failed(self):
        """:class:`bool`: Whether the internal task has failed.

        .. versionadded:: 1.2.0
        """
        return self._has_failed

    def exception(self):
        """Optional[:class:`Exception`]: The exception that the internal task failed with.

        .. versionadded:: 1.3.0
        """
        if self._exception is not None:
            return self._exception
        if self._task is not None:
            return self._task.exception()

    def before_loop(self, coro):
        """A decorator that registers a coroutine to be called before the loop starts running.

        This is useful if you want to wait for some bot state before the loop starts,
        such as :meth:`discord.Client.wait_until_ready`.

        The coroutine must take no arguments (except ``self`` in a class context).

        Parameters
        ------------
        coro: :ref:`coroutine <coroutine>`
            The coroutine to register before the loop runs.

        Raises
        -------
        TypeError
            The function was not a coroutine.
        """

        if not inspect.iscoroutinefunction(coro):
            raise TypeError('Expected coroutine function, received {0.__name__!r}.'.format(type(coro)))

        self._before_loop = coro
        return coro

    def after_loop(self, coro):
        """A decorator that register a coroutine to be called after the loop finished running.

        The coroutine must take no arguments (except ``self`` in a class context).

        .. note::

            This coroutine is called even during cancellation. If it is desirable
            to tell apart whether something was cancelled or not, check to see
            whether :meth:`is_being_cancelled` is ``True`` or not.

        Parameters
        ------------
        coro: :ref:`coroutine <coroutine>`
            The coroutine to register after the loop finishes.

        Raises
        -------
        TypeError
            The function was not a coroutine.
        """

        if not inspect.iscoroutinefunction(coro):
            raise TypeError('Expected coroutine function, received {0.__name__!r}.'.format(type(coro)))

        self._after_loop = coro
        return coro

    def _get_next_sleep_time(self):
        if self._sleep is not None:
            return self._sleep

        # microseconds in the calculations sometimes leads to the sleep time
        # being too small
        now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
        if self._time_index >= len(self._time):
            self._time_index = 0

        # note: self._time is sorted by earliest -> latest
        current_time = self._time[self._time_index]
        if current_time >= now.timetz():
            as_dt = datetime.datetime.combine(now.date(), current_time)
        else:
            tomorrow = now + datetime.timedelta(days=1)
            as_dt = datetime.datetime.combine(tomorrow.date(), current_time)

        delta = (as_dt - now).total_seconds()
        self._time_index += 1
        return max(delta, 0.0)

    def _prepare_index(self):
        # pre-condition: self._time is set
        # find the current index that we should be in
        now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).timetz()
        for index, dt in enumerate(self._time):
            if dt >= now:
                self._time_index = index
                break

    def change_interval(self, *, seconds=0, minutes=0, hours=0, time=None):
        """Changes the interval for the sleep time.

        .. note::

            This only applies on the next loop iteration. If it is desirable for the change of interval
            to be applied right away, cancel the task with :meth:`cancel`.

        .. versionadded:: 1.2.0

        Parameters
        ------------
        seconds: :class:`float`
            The number of seconds between every iteration.
        minutes: :class:`float`
            The number of minutes between every iteration.
        hours: :class:`float`
            The number of hours between every iteration.
        time: Union[Sequence[:class:`datetime.time`], :class:`datetime.time`]
            The exact times to run this loop at. Either a list or a single
            value of :class:`datetime.time` should be passed. Note that
            this cannot be mixed with the relative time parameters.

            .. versionadded:: 1.3.0

        Raises
        -------
        ValueError
            An invalid value was given.
        TypeError
            Mixing ``time`` parameter with relative time parameter or
            passing an improper type for the ``time`` parameter.
        """

        if any((seconds, minutes, hours)) and time is not None:
            raise TypeError('Cannot mix relative time with explicit time.')

        self.seconds = seconds
        self.hours = hours
        self.minutes = minutes
        self._time_index = 0

        if time is None:
            sleep = seconds + (minutes * 60.0) + (hours * 3600.0)
            if sleep >= MAX_ASYNCIO_SECONDS:
                fmt = 'Total number of seconds exceeds asyncio imposed limit of {0} seconds.'
                raise ValueError(fmt.format(MAX_ASYNCIO_SECONDS))

            if sleep < 0:
                raise ValueError('Total number of seconds cannot be less than zero.')

            self._sleep = sleep
            self._time = None
        else:
            self._sleep = None
            self._time = _get_time_parameter(time)
            self._prepare_index()

def loop(*, seconds=0, minutes=0, hours=0, count=None, time=None, reconnect=True, loop=None):
    """A decorator that schedules a task in the background for you with
    optional reconnect logic. The decorator returns a :class:`Loop`.

    Parameters
    ------------
    seconds: :class:`float`
        The number of seconds between every iteration.
    minutes: :class:`float`
        The number of minutes between every iteration.
    hours: :class:`float`
        The number of hours between every iteration.
    count: Optional[:class:`int`]
        The number of loops to do, ``None`` if it should be an
        infinite loop.
    time: Union[Sequence[:class:`datetime.time`], :class:`datetime.time`]
        The exact times to run this loop at. Either a list or a single
        value of :class:`datetime.time` should be passed. Note that
        this cannot be mixed with the relative time parameters.

        .. versionadded:: 1.3.0
    reconnect: :class:`bool`
        Whether to handle errors and restart the task
        using an exponential back-off algorithm similar to the
        one used in :meth:`discord.Client.connect`.
    loop: :class:`asyncio.AbstractEventLoop`
        The loop to use to register the task, if not given
        defaults to :func:`asyncio.get_event_loop`.

    Raises
    --------
    ValueError
        An invalid value was given.
    TypeError
        The function was not a coroutine.
    """
    def decorator(func):
        return Loop(func, seconds=seconds, minutes=minutes, hours=hours,
                          time=time, count=count, reconnect=reconnect, loop=loop)
    return decorator
