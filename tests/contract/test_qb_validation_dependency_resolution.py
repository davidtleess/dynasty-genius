from importlib.metadata import version

from src.dynasty_genius.eval.qb_validation.inference import (
    EXPECTED_SCIPY_VERSION,
)


def test_fresh_environment_declares_registered_scipy_version() -> None:
    assert version("scipy") == EXPECTED_SCIPY_VERSION
