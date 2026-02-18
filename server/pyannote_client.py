from typing import Any, Optional
import logging

# Import torch lazily / gracefully so that tests can import this module
try:
    import torch
except Exception:  # pragma: no cover - tests may run without torch installed
    torch = None

# soundfile is imported inside `diarize` to avoid import-time dependency failures
from server import config

logger = logging.getLogger(__name__)


def _annotation_to_list(annotation) -> list[dict[str, Any]]:
    """Convert pyannote Annotation-like object into a JSON-serializable list.

    Handles objects that implement `.serialize()` (older behaviour), dicts
    already in `{"diarization": [...]}` form, and pyannote.core.Annotation-like
    objects exposing `itertracks` or `labels`/`get_timeline`.
    """
    # Already-serializable forms
    if hasattr(annotation, "serialize"):
        return annotation.serialize().get("diarization", [])
    if isinstance(annotation, dict):
        return annotation.get("diarization", [])

    segments: list[dict[str, Any]] = []
    try:
        # Preferred API: itertracks(yield_label=True) -> (Segment, track, label)
        if hasattr(annotation, "itertracks"):
            for segment, _, label in annotation.itertracks(yield_label=True):
                segments.append({"speaker": str(label), "start": float(segment.start), "end": float(segment.end)})
        # Fallback API: labels() + get_timeline(label)
        elif hasattr(annotation, "labels") and hasattr(annotation, "get_timeline"):
            for label in annotation.labels():
                timeline = annotation.get_timeline(label)
                for seg in timeline:
                    segments.append({"speaker": str(label), "start": float(seg.start), "end": float(seg.end)})
        else:
            logger.warning("Unknown diarization object type: %s", type(annotation))
    except Exception:
        logger.exception("Failed to convert pyannote Annotation to list")
        return []

    # Ensure deterministic ordering
    segments.sort(key=lambda s: s["start"])
    return segments


class PyannoteClient:
    """Lazy-loading pyannote speaker diarization client.

    The pipeline is loaded on first use (diarize) so the application can
    start even if the model download or HF token is not yet available.
    """

    pipeline: Any | None

    def __init__(self, hf_key: str | None = None) -> None:
        # store token but do NOT load the heavy pipeline at import/startup
        self.hf_key = hf_key or config.PYANNOTE_API_KEY
        self.pipeline = None
        if torch is not None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            # tests or light environments may not have torch installed; use string fallback
            self.device = "cpu"  # pipeline.to('cpu') accepts 'cpu' as string in most cases

    def _ensure_pipeline(self) -> None:
        """Load the pyannote pipeline on first use.
        Raises RuntimeError with a clear message on failure.
        """
        if self.pipeline is not None:
            return

        if not self.hf_key:
            raise RuntimeError("Missing HuggingFace token (PYANNOTE_TOKEN) required to load pyannote pipeline")

        try:
            # Some versions of `huggingface_hub` removed the `use_auth_token`
            # keyword. To be compatible with multiple versions we `login()`
            # first so that `Pipeline.from_pretrained()` does not need the
            # deprecated kwarg.
            try:
                from huggingface_hub import login
                if self.hf_key:
                    login(self.hf_key)
            except Exception:
                # If huggingface_hub.login is not available, fall back to
                # setting the env var so hf_hub_download() can pick it up.
                if self.hf_key:
                    import os

                    os.environ.setdefault("HUGGINGFACE_HUB_TOKEN", self.hf_key)

            # Compatibility shim: some pyannote versions call
            # `hf_hub_download(..., use_auth_token=...)` while newer
            # huggingface_hub implementations accept `token=` instead.
            # Wrap `hf_hub_download` at runtime so third-party code that
            # still passes `use_auth_token` does not crash.
            try:
                import inspect
                import huggingface_hub
                hf_fn = getattr(huggingface_hub, "hf_hub_download", None)
                if hf_fn is not None:
                    sig = inspect.signature(hf_fn)
                    if "use_auth_token" not in sig.parameters:
                        orig = hf_fn

                        def _hf_hub_download_compat(*args, **kwargs):
                            if "use_auth_token" in kwargs:
                                kwargs["token"] = kwargs.pop("use_auth_token")
                            return orig(*args, **kwargs)

                        huggingface_hub.hf_hub_download = _hf_hub_download_compat

                        # Also patch any already-imported pyannote module reference
                        import sys

                        mod = sys.modules.get("pyannote.audio.core.pipeline")
                        if mod and hasattr(mod, "hf_hub_download"):
                            setattr(mod, "hf_hub_download", _hf_hub_download_compat)
            except Exception:
                # Non-fatal; we'll attempt to load the pipeline regardless
                pass

            from pyannote.audio import Pipeline

            # Call from_pretrained *without* passing `use_auth_token` so the
            # underlying huggingface_hub implementation decides how to use the
            # already-authenticated session/token. This avoids signature
            # mismatches across huggingface_hub versions.
            pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")

            if pipeline is None:
                raise RuntimeError("Pipeline.from_pretrained returned None")

            pipeline.to(self.device)
            self.pipeline = pipeline
            logger.info("pyannote pipeline loaded on device=%s", self.device)
        except Exception as exc:
            raise RuntimeError(f"Failed to load pyannote pipeline: {exc}") from exc

    def diarize(self, file_path: str, num_speakers: int | None = None, progress_callback: Any | None = None) -> dict[str, Any]:
        """Run speaker diarization on an audio file.

        This method lazy-loads the pipeline and uses `soundfile` to read audio
        (avoids relying on optional native torchcodec at import time).

        Args:
            progress_callback: optional callable(progress_percent: float) that
                will be called with progress updates if pyannote exposes them.
        """
        # Ensure pipeline available
        self._ensure_pipeline()

        # Read audio (import locally so module import doesn't require soundfile)
        try:
            import soundfile as sf
        except Exception as exc:
            raise RuntimeError("soundfile is required to read audio files for diarization") from exc

        waveform, sample_rate = sf.read(file_path, dtype="float32")

        # Convert to torch tensor and ensure shape is (channels, samples)
        if torch is None:
            raise RuntimeError("PyannoteClient.diarize requires PyTorch to convert audio to tensors")

        if waveform.ndim == 1:
            waveform = torch.from_numpy(waveform[None, :])
        else:
            waveform = torch.from_numpy(waveform.T)

        audio = {"waveform": waveform, "sample_rate": sample_rate}

        # Use pyannote's progress hook if available
        try:
            from pyannote.audio.pipelines.utils.hook import ProgressHook
        except Exception:
            ProgressHook = None

        # Best-effort: if ProgressHook is available and a caller supplied a
        # progress_callback, spawn a short-lived poller thread that inspects
        # common hook attributes (many pyannote versions expose `progress` as
        # a float between 0.0 and 1.0). This is intentionally defensive so
        # the caller receives live-ish progress without hard dependency on a
        # precise hook API.
        if ProgressHook is not None:
            import threading, time

            stop_event = threading.Event()

            def _start_poller(hook):
                # Poll common attribute names and call the callback when found.
                last_pct = -1.0
                while not stop_event.is_set():
                    val = None
                    for attr in ("progress", "_progress", "current", "n_done", "n_processed"):
                        if hasattr(hook, attr):
                            try:
                                val = getattr(hook, attr)
                                break
                            except Exception:
                                val = None
                    # Some hooks expose a `get_progress()` helper
                    if val is None and hasattr(hook, "get_progress"):
                        try:
                            val = hook.get_progress()
                        except Exception:
                            val = None

                    if val is not None:
                        try:
                            pct = float(val)
                            # normalize 0..1 -> 0..100 if necessary
                            if pct <= 1.0:
                                pct = pct * 100.0
                            # call only when percentage changed meaningfully
                            if progress_callback and abs(pct - last_pct) >= 0.5:
                                try:
                                    progress_callback(pct)
                                except Exception:
                                    pass
                                last_pct = pct
                        except Exception:
                            pass
                    time.sleep(0.10)

            with ProgressHook() as hook:
                # eager notification that processing started
                if progress_callback is not None:
                    try:
                        progress_callback(0.0)
                    except Exception:
                        pass

                poller = None
                if progress_callback is not None:
                    poller = threading.Thread(target=_start_poller, args=(hook,), daemon=True)
                    poller.start()
                try:
                    diarization = self.pipeline(audio, hook=hook, num_speakers=num_speakers)
                finally:
                    if poller is not None:
                        stop_event.set()
                        poller.join(timeout=0.5)

                # best-effort final update
                if progress_callback is not None:
                    try:
                        progress_callback(100.0)
                    except Exception:
                        pass
        else:
            # No hook available — run the pipeline normally
            diarization = self.pipeline(audio, num_speakers=num_speakers)

        # Normalize output from different pyannote versions / return types
        diar = _annotation_to_list(diarization)
        return {"diarization": diar}
