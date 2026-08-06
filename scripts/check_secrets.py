"""Fail before commit/push when common credentials are stored in tracked files."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


PATTERNS = (
    re.compile(r"NGROK_TOKEN\s*=\s*[\"'][^\"']+[\"']"),
    re.compile(r"NGROK_AUTHTOKEN\s*=\s*[\"'][^\"']+[\"']"),
    re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*[\"'][^\"']{12,}[\"']"),
)
ALLOWLIST = ("xxxxxxxx", "your_", "replace_me", "changeme", "example")


def main() -> int:
    files = subprocess.check_output(["git", "ls-files", "-co", "--exclude-standard"], text=True).splitlines()
    findings: list[str] = []
    for name in files:
        path = Path(name)
        if path.suffix in {".png", ".jpg", ".jpeg", ".pdf", ".faiss", ".zip"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if any(pattern.search(line) for pattern in PATTERNS):
                lowered = line.lower()
                if not any(item in lowered for item in ALLOWLIST):
                    findings.append(f"{name}:{number}")
    if findings:
        print("Secret-like values found:")
        print("\n".join(findings))
        return 1
    print("[OK] No secret-like values found in tracked files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
