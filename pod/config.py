from pathlib import Path

IMG_NAME = "sae:latest"
PORT = 2024
COPY_PATH = Path(__file__).parent.parent.parent / "rendus"

assert COPY_PATH.is_dir(), COPY_PATH.resolve()

PROMPT = "\\[\\e[1;36m\\]\\H\\[\\e[0;36m\\]:\\w # \\[\\e[0m\\]"
