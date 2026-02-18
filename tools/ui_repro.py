"""Headless UI repro: upload an audio file, open websocket for the returned file_id,
trigger /api/transcribe and print incoming WS messages.

Usage: python tools/ui_repro.py
"""
import asyncio
import json
import time
import sys
import requests
import websockets

SERVER_HTTP = "http://127.0.0.1:8000"
SERVER_WS = "ws://127.0.0.1:8000"
AUDIO_PATH = "storage/audio/47.wav"


def do_upload():
    with open(AUDIO_PATH, "rb") as f:
        files = {"file": ("23.wav", f, "audio/wav")}
        data = {"language": "en", "speakers": "2"}
        r = requests.post(f"{SERVER_HTTP}/api/queue", files=files, data=data, timeout=30)
        r.raise_for_status()
        return r.json()["id"]


async def ws_listener(file_id: int, stop_after: float = 120.0):
    uri = f"{SERVER_WS}/api/ws/progress/{file_id}"
    print(f"[ws] connecting to {uri}")
    try:
        async with websockets.connect(uri, max_size=None) as ws:
            print("[ws] connected")
            start = time.time()
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=stop_after)
                    print("[ws] recv:", msg)
                    # stop early if we get completion
                    try:
                        j = json.loads(msg)
                        if j.get("status") == "complete" or j.get("progress") == 100:
                            print("[ws] received completion message, exiting listener")
                            return
                    except Exception:
                        pass
                    if time.time() - start > stop_after:
                        print("[ws] listener timeout")
                        return
                except asyncio.TimeoutError:
                    print("[ws] recv timeout")
                    return
    except Exception as e:
        print("[ws] connection error:", type(e).__name__, e)


async def main():
    print("Uploading audio...", AUDIO_PATH)
    try:
        file_id = do_upload()
    except Exception as e:
        print("Upload failed:", e)
        sys.exit(1)

    print("Uploaded, file_id=", file_id)

    # start ws listener
    listener = asyncio.create_task(ws_listener(file_id, stop_after=180.0))

    # give WS a moment to connect
    await asyncio.sleep(1.0)

    # trigger transcription
    print("Triggering /api/transcribe")
    try:
        r = requests.post(f"{SERVER_HTTP}/api/transcribe", timeout=30)
        print("/api/transcribe ->", r.status_code, r.text)
    except Exception as e:
        print("Failed to trigger transcribe:", e)

    # wait for listener to finish
    try:
        await asyncio.wait_for(listener, timeout=180.0)
    except asyncio.TimeoutError:
        print("Timed out waiting for WS messages")


if __name__ == "__main__":
    asyncio.run(main())
