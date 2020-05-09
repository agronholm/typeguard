
# module for syntax that does not supported in Python 3.5

import os


annotated_attribute: int = 100500

not_annotated_attribute = 100600


if 'TYPEGUARD_TEST_WRONG_ANNOTATION' in os.environ:
    wrong_annotated_attribute: int = 1.5
