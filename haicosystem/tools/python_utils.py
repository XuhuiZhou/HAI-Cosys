import functools
import logging
import multiprocessing
import multiprocessing.queues
import re
import sys
from io import StringIO
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=None)
def warn_once() -> None:
    """Warn once about the dangers of PythonREPL."""
    logger.warning("Python REPL can execute arbitrary code. Use with caution.")


class PythonREPL(BaseModel):
    """Simulates a standalone Python REPL."""

    globals: Optional[dict[str, Any]] = Field(default_factory=dict, alias="_globals")
    locals: Optional[dict[str, Any]] = Field(default_factory=dict, alias="_locals")

    @staticmethod
    def sanitize_input(query: str) -> str:
        """Sanitize input to the python REPL.

        Remove whitespace, backtick & python
        (if llm mistakes python console as terminal)

        Args:
            query: The query to sanitize

        Returns:
            str: The sanitized query
        """
        query = re.sub(r"^(\s|`)*(?i:python)?\s*", "", query)
        query = re.sub(r"(\s|`)*$", "", query)
        return query

    @classmethod
    def worker(
        cls,
        command: str,
        globals: Optional[dict[str, Any]],
        locals: Optional[dict[str, Any]],
        queue: multiprocessing.queues.Queue, # type: ignore[type-arg]
    ) -> None:
        old_stdout = sys.stdout
        sys.stdout = mystdout = StringIO()
        try:
            cleaned_command = cls.sanitize_input(command)
            exec(cleaned_command, globals, locals)
            sys.stdout = old_stdout
            queue.put(mystdout.getvalue())
        except Exception as e:
            sys.stdout = old_stdout
            queue.put(repr(e))

    def run(self, command: str, timeout: Optional[int] = None) -> str:
        """Run command with own globals/locals and returns anything printed.
        Timeout after the specified number of seconds."""

        # Warn against dangers of PythonREPL
        warn_once()

        queue: multiprocessing.queues.Queue = multiprocessing.Queue() # type: ignore[type-arg]

        # Only use multiprocessing if we are enforcing a timeout
        if timeout is not None:
            # create a Process
            p = multiprocessing.Process(
                target=self.worker, args=(command, self.globals, self.locals, queue)
            )

            # start it
            p.start()

            # wait for the process to finish or kill it after timeout seconds
            p.join(timeout)

            if p.is_alive():
                p.terminate()
                return "Execution timed out"
        else:
            self.worker(command, self.globals, self.locals, queue)
        # get the result from the worker function
        return queue.get() # type: ignore[no-any-return]