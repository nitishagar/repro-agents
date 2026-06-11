"""Demo package with a SEEDED FAULT: it imports `six` but never declares it.

`six` is used because it is real and dependency-free, so the oracle can prove the
synthesized fix quickly. repro-agents should flag the undeclared dependency and
prove that adding `six` makes the project solve + import cleanly.
"""

import six


def is_py3() -> bool:
    return six.PY3
