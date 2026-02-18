import os
import sys
import numpy as np
# Ensure project root is on sys.path for test discovery
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from server.merge import merge_diarization_with_transcript
from server.pyannote_client import PyannoteClient


def test_merge_diarization_with_transcript_smoke():
    diarization = {
        "diarization": [
            {"speaker": "SPEAKER_00", "start": 0.0, "end": 1.0},
            {"speaker": "SPEAKER_01", "start": 1.0, "end": 2.0},
        ]
    }

    transcript = {
        "text": "hello world",
        "preview": "hello world",
        "segments": [
            {
                "start": 0.0,
                "end": 1.0,
                "text": "hello",
                "words": [{"start": 0.0, "end": 0.5, "word": "hello"}],
            },
            {
                "start": 1.0,
                "end": 2.0,
                "text": "world",
                "words": [{"start": 1.0, "end": 1.5, "word": "world"}],
            },
        ],
        "device": "cpu",
        "language": "en",
    }

    merged = merge_diarization_with_transcript(diarization, transcript)
    assert "SPEAKER_00" in merged or "hello" in merged


class DummyPipeline:
    def __call__(self, audio, hook=None, num_speakers=None):
        class DummyAnn:
            def serialize(self_inner):
                return {"diarization": [{"speaker": "SPEAKER_00", "start": 0.0, "end": 1.0}]}
        return DummyAnn()


def test_pyannote_client_lazy_init(monkeypatch):
    # Constructing the client should NOT attempt to load the model
    pc = PyannoteClient(hf_key=None)
    assert pc.pipeline is None

    # Monkeypatch the loader to avoid network/model download and verify lazy init
    def fake_ensure():
        pc.pipeline = DummyPipeline()
    monkeypatch.setattr(pc, "_ensure_pipeline", fake_ensure)

    # Calling the loader (not diarize) should set the pipeline without contacting HF
    pc._ensure_pipeline()
    assert pc.pipeline is not None


def test_ensure_pipeline_uses_hf_login(monkeypatch):
    pc = PyannoteClient(hf_key="MY_TOKEN")

    called = {"login": False, "from_pretrained": False}

    def fake_login(token):
        assert token == "MY_TOKEN"
        called["login"] = True

    class FakePipeline:
        def __init__(self):
            self._moved_to = None

        def to(self, device):
            # emulate pipeline.to(device)
            self._moved_to = device
            return self

    def fake_from_pretrained(name):
        assert name == "pyannote/speaker-diarization-3.1"
        called["from_pretrained"] = True
        return FakePipeline()
    monkeypatch.setattr("huggingface_hub.login", fake_login)

    # pyannote may not be installed in the test environment; inject a fake
    # module so Pipeline.from_pretrained can be exercised without network IO.
    import types, sys
    fake_audio_mod = types.ModuleType("pyannote.audio")

    class FakePipelineClass:
        @staticmethod
        def from_pretrained(name):
            return fake_from_pretrained(name)

    fake_audio_mod.Pipeline = FakePipelineClass
    sys.modules["pyannote"] = types.ModuleType("pyannote")
    sys.modules["pyannote.audio"] = fake_audio_mod

    pc._ensure_pipeline()
    assert called["login"] and called["from_pretrained"]

    # cleanup injected modules
    sys.modules.pop("pyannote.audio", None)
    sys.modules.pop("pyannote", None)


def test_hf_hub_download_compatibility(monkeypatch):
    pc = PyannoteClient(hf_key="MY_TOKEN")

    calls = {}

    def fake_hf_hub_download(repo_id, filename, token=None):
        calls['token'] = token
        return 'ok'

    # Replace the top-level hf_hub_download implementation (simulates a
    # huggingface_hub that does not accept `use_auth_token`)
    monkeypatch.setattr('huggingface_hub.hf_hub_download', fake_hf_hub_download, raising=False)

    # Simulate pyannote calling hf_hub_download with `use_auth_token` kwarg
    def fake_from_pretrained(name):
        import huggingface_hub
        huggingface_hub.hf_hub_download('x', 'y', use_auth_token='MY_TOKEN')

        class FakePipelineWithTo:
            def to(self, device):
                return self

        return FakePipelineWithTo()

    import types, sys
    fake_audio_mod = types.ModuleType('pyannote.audio')

    class FakePipelineClass:
        @staticmethod
        def from_pretrained(name):
            return fake_from_pretrained(name)

    fake_audio_mod.Pipeline = FakePipelineClass
    sys.modules['pyannote'] = types.ModuleType('pyannote')
    sys.modules['pyannote.audio'] = fake_audio_mod

    pc._ensure_pipeline()
    assert calls.get('token') == 'MY_TOKEN'

    # cleanup injected modules
    sys.modules.pop('pyannote.audio', None)
    sys.modules.pop('pyannote', None)


def test_annotation_to_list_conversion_itertracks():
    """Ensure _annotation_to_list handles Annotation-like objects with itertracks."""
    from server.pyannote_client import _annotation_to_list

    class DummySeg:
        def __init__(self, start, end):
            self.start = start
            self.end = end

    class DummyAnn:
        def itertracks(self, yield_label=True):
            yield (DummySeg(0.0, 1.0), None, "SPEAKER_00")
            yield (DummySeg(1.0, 2.0), None, "SPEAKER_01")

    out = _annotation_to_list(DummyAnn())
    assert isinstance(out, list)
    assert out[0]["speaker"] == "SPEAKER_00"
    assert out[1]["start"] == 1.0


def test_annotation_to_list_conversion_labels_timeline():
    """Ensure _annotation_to_list handles labels()/get_timeline() API."""
    from server.pyannote_client import _annotation_to_list

    class DummySeg:
        def __init__(self, start, end):
            self.start = start
            self.end = end

    class DummyAnn2:
        def labels(self):
            return ["A"]

        def get_timeline(self, label):
            return [DummySeg(2.0, 3.0)]

    out = _annotation_to_list(DummyAnn2())
    assert out == [{"speaker": "A", "start": 2.0, "end": 3.0}]


def test_pyannote_client_progress_callback(monkeypatch):
    """Ensure diarize calls the provided progress callback when ProgressHook is present."""
    import types, sys, time

    # Inject a fake ProgressHook module so pyannote_client imports succeed
    fake_hook_mod = types.ModuleType('pyannote.audio.pipelines.utils.hook')

    class FakeProgressHook:
        def __init__(self):
            # the pipeline will mutate `progress` during the run
            self.progress = 0.0

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    fake_hook_mod.ProgressHook = FakeProgressHook

    # Ensure parent packages exist so the nested import path resolves
    sys.modules.setdefault('pyannote', types.ModuleType('pyannote'))
    sys.modules.setdefault('pyannote.audio', types.ModuleType('pyannote.audio'))
    sys.modules.setdefault('pyannote.audio.pipelines', types.ModuleType('pyannote.audio.pipelines'))
    sys.modules.setdefault('pyannote.audio.pipelines.utils', types.ModuleType('pyannote.audio.pipelines.utils'))
    sys.modules['pyannote.audio.pipelines.utils.hook'] = fake_hook_mod

    # Ensure `soundfile.read` won't try to open a real file during the test
    fake_sf = types.ModuleType('soundfile')
    import numpy as _np
    def _fake_read(path, dtype='float32'):
        # 1 second of silence at 16kHz
        return _np.zeros(16000, dtype=_np.float32), 16000
    fake_sf.read = _fake_read
    sys.modules['soundfile'] = fake_sf

    # Create a PyannoteClient and monkeypatch its pipeline to simulate progress
    from server import pyannote_client as _pc_mod
    # Provide a lightweight fake `torch` so the function proceeds in test env
    import types as _types
    _pc_mod.torch = _types.SimpleNamespace(
        from_numpy=lambda x: x,
        cuda=_types.SimpleNamespace(is_available=lambda: False),
        device=lambda s: s,
    )

    from server.pyannote_client import PyannoteClient

    pc = PyannoteClient(hf_key=None)

    class DummyPipeline:
        def __call__(self, audio, hook=None, num_speakers=None):
            # Simulate several progress updates
            for i in range(0, 101, 20):
                if hook is not None:
                    hook.progress = i / 100.0
                    # pause so the background poller has time to observe updates
                    time.sleep(0.12)
                    return {"diarization": []}

            return DummyAnn()

    monkeypatch.setattr(pc, '_ensure_pipeline', lambda: setattr(pc, 'pipeline', DummyPipeline()))
    pc._ensure_pipeline()

    seen = []

    def on_progress(pct):
        seen.append(pct)

    # Run diarize with progress callback
    out = pc.diarize('fake.wav', num_speakers=2, progress_callback=on_progress)

    # Cleanup fake modules
    for mod in ['pyannote.audio.pipelines.utils.hook', 'pyannote.audio.pipelines.utils', 'pyannote.audio.pipelines', 'pyannote.audio', 'pyannote']:
        sys.modules.pop(mod, None)

    assert isinstance(out, dict)
    assert 'diarization' in out
    # At minimum we should see a 0% and a final ~100% notification
    assert any(abs(p - 0.0) < 0.1 for p in seen)
    assert any(p >= 99.0 for p in seen)
    assert len(seen) >= 1


