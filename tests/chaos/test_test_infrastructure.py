"""The test harness's own assumptions, pinned so a refactor cannot silently break them."""

import os
import subprocess
import sys
from pathlib import Path

from chaos_harness import *  # noqa: F401,F403

REPO = Path(__file__).resolve().parents[2]


def test_tests_conftest_resolves_to_the_api_test_suite():
    """The chaos tests do `from tests.conftest import ...` (a namespace package): it must be the
    API suite's conftest, not another `tests` package or `conftest` module on the path."""
    import tests.conftest

    assert Path(tests.conftest.__file__).resolve() == REPO / "apps" / "api" / "tests" / "conftest.py"


def test_the_test_database_file_is_named_per_process():
    from tests import conftest

    assert conftest.TEST_DB_FILE == f"test_temp_{os.getpid()}.db"
    assert conftest.DATABASE_URL.endswith(conftest.TEST_DB_FILE)


def test_two_sessions_do_not_share_a_database_file_name():
    code = "import tests.conftest as c; print(c.TEST_DB_FILE)"
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)}
    other = subprocess.run(
        [sys.executable, "-c", code], cwd=REPO, env=env, capture_output=True, text=True, timeout=120
    )
    assert other.returncode == 0, other.stderr[-500:]
    from tests import conftest

    assert other.stdout.strip().splitlines()[-1] != conftest.TEST_DB_FILE
