import os
import re
from pathlib import Path

path = Path("README.md")
content = path.read_text(encoding="utf-8")

version = (
    os.environ["GITHUB_RUN_ID"]
    + "-"
    + os.environ["GITHUB_RUN_ATTEMPT"]
)

for name in ("overview", "languages"):
    pattern = (
        r"(\./assets/stats/"
        + name
        + r'\.svg)(?:\?v=[^"]*)?'
    )

    content, count = re.subn(
        pattern,
        lambda match: match.group(1) + "?v=" + version,
        content,
    )

    if count != 1:
        raise RuntimeError(f"Referencia invalida: {name}")

path.write_text(content, encoding="utf-8")