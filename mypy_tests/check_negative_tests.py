import os
import re
import subprocess
from typing import Set

OUTPUT_FILE = "negative.output"
SOURCE_FILE = "negative.py"
LINE_PATTERN = SOURCE_FILE + ":([0-9]+):"


def get_mypy_output() -> str:
    try:
        subprocess.check_call(f"mypy negative.py > {OUTPUT_FILE}", shell=True)
    except subprocess.CalledProcessError:
        pass

    with open(OUTPUT_FILE) as f:
        return f.read()


def get_expected_output() -> str:
    expected_file = OUTPUT_FILE + ".expected"

    if os.path.exists(expected_file):
        with open(expected_file) as f:
            return f.read()
    else:
        return ""


def get_expected_error_lines() -> Set[int]:
    with open(SOURCE_FILE) as f:
        lines = f.readlines()

    error_lines = {
        idx + 1 for idx, line in enumerate(lines) if line.rstrip().endswith("# Error")
    }

    assert error_lines
    return error_lines


def get_mypy_error_lines(mypy_output: str) -> Set[int]:
    return {int(m.group(1)) for m in re.finditer(LINE_PATTERN, mypy_output)}


def main() -> None:
    got_output = get_mypy_output()
    expected_output = get_expected_output()

    if got_output != expected_output:
        with open(OUTPUT_FILE + ".expected", "w") as f:
            f.write(got_output)
        raise RuntimeError(
            "Got output did not match expected output. Expected output has been"
            " updated. Rerun the test."
        )

    got_error_lines = get_mypy_error_lines(got_output)
    expected_error_lines = get_expected_error_lines()
    if got_error_lines != expected_error_lines:
        raise RuntimeError(
            f"Expected error lines {expected_error_lines} does not match the "
            f"got error lines {got_error_lines}."
        )


if __name__ == "__main__":
    main()
