"""
Compatibility shim for torchaudio 2.2+.

torchaudio 2.2 removed the legacy backend API that SpeechBrain 0.5.x depends on:
  - torchaudio.list_audio_backends()
  - torchaudio.get_audio_backend()
  - torchaudio.set_audio_backend()

This module patches those functions back so SpeechBrain's
`check_torchaudio_backend()` doesn't crash on import.

Usage:
    import compat.torchaudio_compat  # must be FIRST, before any speechbrain import
    from speechbrain.pretrained import VAD  # now safe
"""

import torchaudio

_PATCHED = False


def _patch_torchaudio() -> None:
    """Add missing backend functions to torchaudio if they don't exist."""
    global _PATCHED
    if _PATCHED:
        return

    # list_audio_backends() — return 'soundfile' since we use sf.write/librosa.load
    if not hasattr(torchaudio, "list_audio_backends"):
        torchaudio.list_audio_backends = lambda: ["soundfile"]

    # get_audio_backend() — return a reasonable default
    if not hasattr(torchaudio, "get_audio_backend"):
        torchaudio.get_audio_backend = lambda: "soundfile"

    # set_audio_backend() — no-op; we always use soundfile/librosa
    if not hasattr(torchaudio, "set_audio_backend"):
        torchaudio.set_audio_backend = lambda backend: None

    _PATCHED = True


# Auto-patch on import
_patch_torchaudio()
