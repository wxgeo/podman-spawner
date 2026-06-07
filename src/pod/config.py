from pathlib import Path

from pod.tools import academic_year

# ---------------------------------
# SECTION À MODIFIER ÉVENTUELLEMENT
SAE_ID = "201"
# ---------------------------------

PREFIX = f"sae-{SAE_ID}"
IMG_NAME = f"{PREFIX}:latest"
TEST = "test-0.0"

PROMPT = "\\[\\e[1;36m\\]\\H\\[\\e[0;36m\\]:\\w # \\[\\e[0m\\]"
CURRENT_YEAR = academic_year()
PORT = 2000 + CURRENT_YEAR[1]
COPY_PATH = (
    Path("~").expanduser() / f"sae/{SAE_ID}/{CURRENT_YEAR[0]}-{CURRENT_YEAR[1]}/rendus"
)
POD_DIR = Path(__file__).parent
ASSETS_DIR = POD_DIR / "assets"
POD_BUILD_DIRNAME = "pod-build"

COPY_PATH.mkdir(parents=True, exist_ok=True)
