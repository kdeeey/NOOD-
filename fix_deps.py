#!/usr/bin/env python3
"""
Fix SpeechBrain dependency conflicts on Windows Python 3.11.

This script:
1. Uninstalls conflicting packages
2. Installs pinned compatible versions in the correct order
3. Tests that SpeechBrain imports work

Compatible version matrix (tested on Python 3.11 Windows):
    numpy           >= 1.24.0, < 2.0.0
    torch           == 2.1.2
    torchaudio      == 2.1.2
    torchvision     == 0.16.2
    huggingface_hub == 0.23.0
    tokenizers      == 0.19.1
    transformers    == 4.40.2
    hyperpyyaml     == 1.2.2
    speechbrain     == 0.5.15
    opencv-python   >= 4.8.0, < 4.10.0

Run with: python fix_deps.py
"""

import subprocess
import sys

# ---------------------------------------------------------------------------
# Pinned versions — known to work together on Python 3.11 Windows
# ---------------------------------------------------------------------------
PACKAGES_TO_UNINSTALL = [
    "speechbrain",
    "torch",
    "torchaudio",
    "torchvision",
    "transformers",
    "huggingface_hub",
    "hyperpyyaml",
    "tokenizers",
]

PACKAGES_TO_INSTALL = [
    # Order matters: numpy first, then torch ecosystem, then the rest
    "numpy>=1.24.0,<2.0.0",
    "torch==2.1.2",
    "torchaudio==2.1.2",
    "torchvision==0.16.2",  # matches torch 2.1.2
    "huggingface_hub==0.23.0",
    "tokenizers==0.19.1",
    "transformers==4.40.2",
    "hyperpyyaml==1.2.2",
    "speechbrain==0.5.15",
    "opencv-python>=4.8.0,<4.10.0",  # compatible with numpy<2
]


def run(cmd: list[str], check: bool = True) -> int:
    """Run a command and return exit code."""
    print(f"\n>>> {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if check and result.returncode != 0:
        print(f"[ERROR] Command failed with exit code {result.returncode}")
    return result.returncode


def main() -> int:
    print("=" * 60)
    print("STEP 1: Uninstalling conflicting packages")
    print("=" * 60)

    # Uninstall in one go (ignore errors if not installed)
    run(
        [sys.executable, "-m", "pip", "uninstall", "-y"] + PACKAGES_TO_UNINSTALL,
        check=False,
    )

    print("\n" + "=" * 60)
    print("STEP 2: Installing pinned compatible versions")
    print("=" * 60)

    # Install torch ecosystem first (from PyPI, not special index needed for CPU)
    for pkg in PACKAGES_TO_INSTALL:
        code = run([sys.executable, "-m", "pip", "install", pkg])
        if code != 0:
            print(f"\n[FATAL] Failed to install {pkg}")
            return 1

    print("\n" + "=" * 60)
    print("STEP 3: Testing SpeechBrain imports")
    print("=" * 60)

    test_code = """
import sys
try:
    print("  Importing torch...", end=" ")
    import torch
    print(f"OK ({torch.__version__})")

    print("  Importing torchaudio...", end=" ")
    import torchaudio
    print(f"OK ({torchaudio.__version__})")

    print("  Importing transformers...", end=" ")
    import transformers
    print(f"OK ({transformers.__version__})")

    print("  Importing speechbrain.pretrained.VAD...", end=" ")
    from speechbrain.pretrained import VAD
    print("OK")

    print("  Importing speechbrain.pretrained.EncoderDecoderASR...", end=" ")
    from speechbrain.pretrained import EncoderDecoderASR
    print("OK")

    print("  Importing speechbrain.pretrained.EncoderClassifier...", end=" ")
    from speechbrain.pretrained import EncoderClassifier
    print("OK")

    print()
    print("=" * 60)
    print("SUCCESS: All SpeechBrain imports work!")
    print("=" * 60)
    sys.exit(0)

except Exception as e:
    print(f"FAILED")
    print()
    print("=" * 60)
    print(f"ERROR: {type(e).__name__}: {e}")
    print("=" * 60)
    import traceback
    traceback.print_exc()
    sys.exit(1)
"""

    result = subprocess.run([sys.executable, "-c", test_code])
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
