from collections import deque


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
        self._path = deque()

    def append_path_element(self, element: str) -> None:
        self._path.append(element)

    def __str__(self) -> str:
        if self._path:
            return ' of '.join(self._path) + ' ' + self.args[0]
        else:
            return self.args[0]
