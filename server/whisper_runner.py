from pathlib import Path

# Import torch lazily / gracefully so the app can start in test/dev
# environments where PyTorch is not installed.
try:
    import torch
except Exception:  # pragma: no cover - tests may run without torch installed
    torch = None

from server import config


def select_device() -> str:
    """Select device based on config. 
    
    - "cuda": Force CUDA (error if not available)
    - "cpu": Force CPU
    - "auto": Use CUDA if available, fall back to CPU
    """
    device = config.WHISPER_DEVICE.lower()
    
    # If the environment does not have torch, treat as CPU unless the
    # user explicitly requested CUDA (in which case raise a clear error).
    if torch is None:
        if device == "cuda":
            raise RuntimeError(
                "CUDA requested (WHISPER_DEVICE=cuda) but PyTorch is not installed."
            )
        return "cpu"

    if device == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError(
                "CUDA is required (WHISPER_DEVICE=cuda) but not available. "
                "Please install PyTorch with CUDA support or set WHISPER_DEVICE=cpu"
            )
        return "cuda"

    if device == "cpu":
        return "cpu"

    # Auto mode: use CUDA if available, otherwise CPU
    if device == "auto":
        if torch.cuda.is_available():
            return "cuda"
        return "cpu"

    # Default: auto
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def select_compute_type(device: str) -> str:
    """Select optimal compute type based on device and config."""
    if config.WHISPER_COMPUTE_TYPE.lower() != "auto":
        return config.WHISPER_COMPUTE_TYPE.lower()
    
    # Auto-select based on device (float16 for CUDA, int8 for CPU)
    if device == "cuda":
        return "float16"
    return "int8"


class WhisperService:
    def __init__(self, model_name: str | None = None, device: str | None = None) -> None:
        # Defer device selection until model initialization so the app can
        # start even when CUDA/PyTorch are not available at startup.
        self.model_name = model_name or config.WHISPER_MODEL
        self.device = device  # may be None; resolved in _get_model()
        self.compute_type = None
        self._model = None

    def _get_model(self):
        if self._model is None:
            # Resolve device/compute lazily so server startup doesn't require
            # torch/faster-whisper to be available.
            if not self.device:
                self.device = select_device()
            if not self.compute_type:
                self.compute_type = select_compute_type(self.device)

            try:
                from faster_whisper import WhisperModel
            except Exception as imp_exc:
                raise RuntimeError(
                    "faster-whisper import failed. Ensure faster-whisper is installed and native dependencies are available"
                ) from imp_exc

            device_index = int(config.WHISPER_DEVICE_INDEX) if config.WHISPER_DEVICE_INDEX else 0

            try:
                self._model = WhisperModel(
                    self.model_name,
                    device=self.device,
                    compute_type=self.compute_type,
                    device_index=device_index,
                )
            except OSError as os_exc:
                raise RuntimeError(
                    "Failed to initialize WhisperModel - native extension error (ctranslate2/ffi). "
                    "Try setting WHISPER_DEVICE=cpu or reinstalling faster-whisper/ctranslate2."
                ) from os_exc
        return self._model

    def transcribe(self, audio_path: Path, language: str, progress_callback=None) -> dict:
        """Transcribe audio and return text with segments.
        
        Args:
            audio_path: Path to audio file
            language: Language code
            progress_callback: Optional callable(processed_seconds, total_seconds)
        """
        model = self._get_model()
        
        segments, info = model.transcribe(
            str(audio_path),
            language=language,
            beam_size=5,
            word_timestamps=True,
        )
        
        # Get total duration
        total_duration = info.duration if hasattr(info, 'duration') else 0
        
        # Collect segments
        all_segments = []
        full_text = []
        
        for segment in segments:
            seg_dict = {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
                "words": [
                    {
                        "start": word.start,
                        "end": word.end,
                        "word": word.word,
                        "probability": word.probability,
                    }
                    for word in (segment.words or [])
                ],
            }
            all_segments.append(seg_dict)
            full_text.append(segment.text)
            
            # Report progress
            if progress_callback and total_duration > 0:
                progress_percent = (segment.end / total_duration) * 100
                progress_callback(progress_percent)
        
        text = " ".join(full_text)
        preview = text[:200] + "..." if len(text) > 200 else text
        
        return {
            "text": text,
            "preview": preview,
            "segments": all_segments,
            "device": self.device,
            "language": info.language,
        }
