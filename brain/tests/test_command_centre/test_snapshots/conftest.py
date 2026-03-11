"""Auto-skip snapshot tests when pytest-textual-snapshot is not installed.

The snap_compare fixture requires pytest-textual-snapshot, which depends on
platform-specific rendering (fonts, Rich SVG output). Snapshots are a local
dev guard — CI skips them gracefully rather than erroring out.
"""

import pytest

try:
    import pytest_textual_snapshot  # noqa: F401

    _HAS_SNAPSHOT = True
except ImportError:
    _HAS_SNAPSHOT = False


def pytest_collection_modifyitems(items):
    """Skip tests marked @pytest.mark.snapshot when plugin is missing."""
    if _HAS_SNAPSHOT:
        return
    skip = pytest.mark.skip(reason="pytest-textual-snapshot not installed")
    for item in items:
        if "snapshot" in item.keywords:
            item.add_marker(skip)
