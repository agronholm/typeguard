from collections import deque
from typing import Deque


class TypeHintWarning(UserWarning):
    """
    A warning that is emitted when a type hint in string form could not be resolved to an actual
    type.
    """


class TypeCheckWarning(UserWarning):
    """Emitted by typeguard's type checkers when a type mismatch is detected."""

    def __init__(self, message: str):
        super().__init__(message)


class TypeCheckError(Exception):
    """
    Raised by typeguard's type checkers when a type mismatch is detected.
    """

    def __init__(self, message: str):
        super().__init__(message)
        self._path: Deque[str] = deque()

    def append_path_element(self, element: str) -> None:
        self._path.append(element)

    def __str__(self) -> str:
        if len(self.args) == 0:
            raise ValueError("No args are given.")
        elif self._path:
            return " of ".join(self._path) + f" {self.args[0]}"
        else:
            return f"{self.args[0]}"
