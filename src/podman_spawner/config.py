"""Package-level constants and paths.

These are static values baked in at install time.  Runtime configuration
(prefix, port, user) lives in ``config.toml`` and is accessed via
:func:`pod.tools.config`.
"""

from pathlib import Path

# Name shown in pod test containers and used as the TEST suffix.
TEST = "test-0.0"

# Absolute path to the installed package directory.
POD_DIR = Path(__file__).parent

# Absolute path to the bundled asset tree (Dockerfile skeleton, etc.).
ASSETS_DIR = POD_DIR / "assets"

# Expected name of the pod build context directory.
POD_BUILD_DIRNAME = "pod-build"

CONFIG_FILE = "pod-config.toml"
