from pathlib import Path

IMG_NAME = "sae:latest"
PROMPT = "\\[\\e[1;36m\\]\\H\\[\\e[0;36m\\]:\\w # \\[\\e[0m\\]"

# --------------------------
# SECTION A MODIFIER
PORT = 2025
COPY_PATH = Path("~").expanduser() / f"sae/201/24-25/rendus"
# --------------------------

assert COPY_PATH.is_dir(), COPY_PATH.resolve()
