import os
import re
import subprocess
from typing import Set

SOURCE_FILE = "negative.py"
EXPECTED_FILE = "negative.expected"
LINE_PATTERN = SOURCE_FILE + ":([0-9]+):"


def get_mypy_output() -> str:
    process = subprocess.run(["mypy", SOURCE_FILE], capture_output=True, check=False)
    return process.stdout.decode()


def get_expected_output() -> str:
    if os.path.exists(EXPECTED_FILE):
        with open(EXPECTED_FILE) as f:
            return f.read()
    else:
        return ""


def get_expected_error_lines() -> Set[int]:
    with open(SOURCE_FILE) as f:
        lines = f.readlines()

    error_lines = {
        idx + 1 for idx, line in enumerate(lines) if line.rstrip().endswith("# Error")
    }

    # Sanity check.  Should update if negative.py changes.
    assert len(error_lines) == 4
    return error_lines


def get_mypy_error_lines(mypy_output: str) -> Set[int]:
    return {int(m.group(1)) for m in re.finditer(LINE_PATTERN, mypy_output)}


def main() -> None:
    got_output = get_mypy_output()
    expected_output = get_expected_output()

    if got_output != expected_output:
        with open(EXPECTED_FILE, "w") as f:
            f.write(got_output)
        msg = " ".join([
            "Mypy output did not match expected output.",
            "{} has been updated with the new mypy output.".format(EXPECTED_FILE),
            "If this is intended, re-run the test with the new expected output.",
            "If this is not intended, view the diff to see what's changed.",
        ])
        raise RuntimeError(msg)

    got_error_lines = get_mypy_error_lines(got_output)
    expected_error_lines = get_expected_error_lines()
    if got_error_lines != expected_error_lines:
        raise RuntimeError(
            "Expected error lines {} does not ".format(expected_error_lines) +
            "match mypy error lines {}.".format(got_error_lines)
        )


if __name__ == "__main__":
    main()
