"""Measure faster-whisper transcription speed on this machine (CPU only).

Run from the repo root:
    .\\.venv\\Scripts\\python.exe scripts\\bench_whisper.py PATH_TO_AUDIO --label "what this clip is"

Only numbers and the label are saved to eval/whisper_benchmark.json. The audio path and the
transcript are never written to disk, so a storyteller's words stay out of the repo.
The transcript is printed to the console so you can eyeball accuracy (it is not scored here).
"""
import argparse
import json
import os
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

import ctranslate2
import faster_whisper
from faster_whisper import WhisperModel, download_model

REPO_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = REPO_ROOT / "models"
RESULTS_PATH = REPO_ROOT / "eval" / "whisper_benchmark.json"


def transcribe_once(model, audio_path, vad):
    """Time one full transcription. transcribe() returns a lazy generator, so the work
    only happens when we iterate it; the clock must cover the iteration."""
    start = time.perf_counter()
    segments, info = model.transcribe(
        str(audio_path), language="en", word_timestamps=True, vad_filter=vad
    )
    segments = list(segments)
    elapsed = time.perf_counter() - start
    word_count = sum(len(s.words or []) for s in segments)
    text = " ".join(s.text.strip() for s in segments)
    return elapsed, info.duration, len(segments), word_count, text


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("audio", type=Path)
    parser.add_argument("--label", required=True, help="What the clip is, e.g. 'my own voice, 1 min'")
    parser.add_argument("--machine", default="", help="Optional CPU name to record, e.g. 'Ryzen 9 9950X3D'")
    parser.add_argument("--models", nargs="+", default=["base", "small"])
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--vad", action="store_true", help="Enable voice-activity filter (off by default)")
    args = parser.parse_args()

    if not args.audio.is_file():
        sys.exit(f"Audio file not found: {args.audio}")

    MODELS_DIR.mkdir(exist_ok=True)
    results = []
    for size in args.models:
        print(f"\n=== model: {size} ({args.compute_type}, cpu) ===")

        t0 = time.perf_counter()
        model_path = download_model(size, cache_dir=str(MODELS_DIR))
        fetch_seconds = time.perf_counter() - t0
        print(f"fetch/cache check: {fetch_seconds:.1f} s (slow only the first time: it downloads weights)")

        t0 = time.perf_counter()
        model = WhisperModel(model_path, device="cpu", compute_type=args.compute_type)
        load_seconds = time.perf_counter() - t0
        print(f"model load: {load_seconds:.1f} s")

        run_seconds, audio_seconds, segment_count, word_count, text = [], 0.0, 0, 0, ""
        for i in range(args.repeats):
            elapsed, audio_seconds, segment_count, word_count, text = transcribe_once(
                model, args.audio, args.vad
            )
            run_seconds.append(round(elapsed, 2))
            print(f"run {i + 1}: {elapsed:.1f} s for {audio_seconds:.1f} s of audio "
                  f"(real-time factor {elapsed / audio_seconds:.2f}; below 1.0 = faster than real time)")

        print(f"segments: {segment_count}, words: {word_count}")
        print(f"transcript ({size}): {text}")

        results.append({
            "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "label": args.label,
            "machine": args.machine,
            "logical_cpus": os.cpu_count(),
            "os": platform.platform(),
            "python": platform.python_version(),
            "faster_whisper": faster_whisper.__version__,
            "ctranslate2": ctranslate2.__version__,
            "model": size,
            "device": "cpu",
            "compute_type": args.compute_type,
            "vad_filter": args.vad,
            "audio_seconds": round(audio_seconds, 2),
            "fetch_seconds": round(fetch_seconds, 2),
            "load_seconds": round(load_seconds, 2),
            "run_seconds": run_seconds,
            "real_time_factor_per_run": [round(s / audio_seconds, 3) for s in run_seconds],
            "segments": segment_count,
            "words": word_count,
        })

    RESULTS_PATH.parent.mkdir(exist_ok=True)
    existing = json.loads(RESULTS_PATH.read_text(encoding="utf-8")) if RESULTS_PATH.exists() else []
    RESULTS_PATH.write_text(json.dumps(existing + results, indent=2), encoding="utf-8")
    print(f"\nSaved {len(results)} result(s) to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
