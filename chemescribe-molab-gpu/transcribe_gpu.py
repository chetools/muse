# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "onnx-asr",
#     "onnxruntime-gpu",
# ]
# ///

"""ChemEScribe on a MoLab GPU: Parakeet transcription with a session log.

Transcribes one uploaded audio file with NVIDIA Parakeet TDT 0.6B v2
through onnx-asr, on the session GPU when the CUDA provider is present.
Every step writes a structured session log (environment probe, installs,
per-chunk timings, provider actually used), downloadable at the end
together with the raw transcript. The raw transcript is the record; the
chemical-engineering glossary correction stages run later, outside this
notebook, on the returned raw text.

Self-contained: no sibling files are imported.
"""

import marimo

app = marimo.App()


@app.cell
def _():
    # Telemetry off before onnxruntime is imported anywhere in the kernel:
    # ONNX Runtime sends telemetry to Microsoft by default.
    import os

    os.environ["ORT_DISABLE_TELEMETRY"] = "1"

    import json
    import shutil
    import subprocess
    import sys
    import tempfile
    import time
    import wave

    import marimo as mo
    import numpy as np

    def chunk_bounds(audio, sr):
        """Cut points in s at the lowest-energy 0.1 s window near each target.

        audio is the waveform as a float array with samples in [-1, 1];
        sr is the sample rate in samples per s. The target chunk length
        is 25 s with a 4 s search either side, the same chunking as the
        local ChemEScribe runner, so transcripts are comparable.
        """
        target = 25.0
        search = 4.0
        dur = len(audio) / sr
        if dur <= target + 8.0:
            return [0.0, dur]
        win = int(0.1 * sr)
        rms = np.array(
            [
                np.sqrt(np.mean(audio[i : i + win] ** 2))
                for i in range(0, len(audio) - win, win)
            ]
        )
        cuts = [0.0]
        t = target
        while t < dur - 8.0:
            lo, hi = int((t - search) * 10), int((t + search) * 10)
            cuts.append((lo + int(np.argmin(rms[lo:hi]))) / 10.0)
            t = cuts[-1] + target
        cuts.append(dur)
        return cuts

    def format_ts(seconds):
        """Format a time in s as [mm:ss] ([h:mm:ss] past one hour)."""
        s = int(round(seconds))
        if s >= 3600:
            return f"{s // 3600}:{(s % 3600) // 60:02d}:{s % 60:02d}"
        return f"{s // 60:02d}:{s % 60:02d}"

    return (
        chunk_bounds,
        format_ts,
        json,
        mo,
        np,
        os,
        shutil,
        subprocess,
        sys,
        tempfile,
        time,
        wave,
    )


@app.cell
def _(mo):
    _out = mo.md(
        r"""
        # ChemEScribe transcription on a MoLab GPU

        This notebook transcribes one audio file with the NVIDIA Parakeet
        TDT 0.6B v2 speech recogniser, run through the `onnx-asr` library
        on the graphics processing unit (GPU) attached to this session
        when one is available.

        Terms used below, defined at first use: a **provider** is the
        ONNX Runtime execution back end that runs the model; the CUDA
        provider runs on an NVIDIA GPU and the CPU provider runs on the
        central processing unit. **CUDA** is NVIDIA's GPU computing
        platform. Memory sizes are in gigabytes (GB), file sizes in
        megabytes (MB), times in seconds (s), and the sample rate in
        samples per s. The **real-time factor** is the audio duration
        in s divided by the transcription time in s, so a factor of
        10 means ten seconds of audio transcribed per second of compute.

        Order of work: run all cells once with the notebook-level Run
        control. Read the environment probe in the next section: it must
        name the RTX PRO 6000 and list the CUDA provider before a GPU
        transcription is possible. If a package is missing, click the
        install button. Then upload an audio file, optionally request
        timestamps (one time range per chunk of about 25 s), and click
        Transcribe. At the end, download the raw transcript and the
        session log; both are the record of the run.
        """
    )
    # NOTE: marimo renders only the cell's last expression, so end on _out
    _out
    return


@app.cell
def _(json, mo, shutil, subprocess, sys, time):
    import platform

    _t0 = time.time()
    probe_log = {
        "started_unix_s": round(_t0, 3),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "ffmpeg": shutil.which("ffmpeg"),
    }
    try:
        import torch

        probe_log["torch"] = torch.__version__
        probe_log["torch_cuda_available"] = bool(torch.cuda.is_available())
        if torch.cuda.is_available():
            probe_log["gpu_name"] = torch.cuda.get_device_name(0)
            probe_log["gpu_memory_gb"] = round(
                torch.cuda.get_device_properties(0).total_memory / 1e9, 2
            )
            probe_log["cuda_version_torch"] = torch.version.cuda
        else:
            probe_log["gpu_name"] = None
            probe_log["gpu_memory_gb"] = None
    except Exception as _e:
        torch = None
        probe_log["torch"] = None
        probe_log["torch_error"] = f"{type(_e).__name__}: {_e}"
    try:
        _smi = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
             "--format=csv,noheader"],
            capture_output=True, text=True, timeout=30,
        )
        probe_log["nvidia_smi"] = _smi.stdout.strip() or None
    except Exception as _e:
        probe_log["nvidia_smi"] = None
        probe_log["nvidia_smi_error"] = f"{type(_e).__name__}: {_e}"
    try:
        import onnxruntime as ort

        ort.disable_telemetry_events()
        probe_log["onnxruntime"] = ort.__version__
        probe_log["providers_available"] = ort.get_available_providers()
    except Exception as _e:
        ort = None
        probe_log["onnxruntime"] = None
        probe_log["providers_available"] = []
        probe_log["onnxruntime_error"] = f"{type(_e).__name__}: {_e}"
    probe_log["probe_seconds"] = round(time.time() - _t0, 3)
    _gpu_line = (
        f"{probe_log.get('gpu_name')} "
        f"({probe_log.get('gpu_memory_gb')} GB)"
        if probe_log.get("gpu_name")
        else "none attached — attach the RTX PRO 6000 under "
        "Configure Resources, then reload this notebook"
    )
    _out = mo.md(
        "## Environment probe\n\n"
        f"- GPU: **{_gpu_line}**\n"
        f"- nvidia-smi: `{probe_log.get('nvidia_smi')}`\n"
        f"- torch: `{probe_log.get('torch')}`, "
        f"CUDA available: `{probe_log.get('torch_cuda_available')}`\n"
        f"- ONNX Runtime: `{probe_log.get('onnxruntime')}`, "
        f"providers: `{probe_log.get('providers_available')}`\n"
        f"- ffmpeg: `{probe_log.get('ffmpeg')}`\n"
        f"- Python: `{probe_log.get('python')}` on "
        f"`{probe_log.get('platform')}`\n\n"
        "A GPU transcription needs the GPU line to name the RTX PRO 6000 "
        "and the providers list to contain `CUDAExecutionProvider`. "
        "If the CUDA provider is missing, use the install button in the "
        "next section; if the GPU itself is missing, no install can fix "
        "that — attach it and start a fresh session.\n\n"
        f"Probe record (saved into the session log):\n\n"
        f"```json\n{json.dumps(probe_log, indent=2)}\n```"
    )
    # NOTE: marimo renders only the cell's last expression, so end on _out
    _out
    return ort, probe_log, torch


@app.cell
def _(mo):
    install_btn = mo.ui.run_button(
        label="Install missing packages (onnx-asr; GPU ONNX Runtime if needed)"
    )
    _out = mo.vstack(
        [
            mo.md(
                "## Install\n\n"
                "The header of this notebook declares `onnx-asr` and "
                "`onnxruntime-gpu`, but MoLab does not always install "
                "header packages at session start. This button installs "
                "only what the probe found missing, and logs each "
                "command, its duration in s, and its result."
            ),
            install_btn,
        ]
    )
    # NOTE: marimo renders only the cell's last expression, so end on _out
    _out
    return (install_btn,)


@app.cell
def _(install_btn, mo, probe_log, subprocess, sys, time):
    import importlib.util

    install_log = {"status": "not run", "steps": []}
    if not install_btn.value:
        _out = mo.md(
            "Install not run. If the probe above already lists "
            "`CUDAExecutionProvider` and the transcription cell reports "
            "no missing package, no install is needed."
        )
    else:
        _providers = probe_log.get("providers_available") or []
        _cmds = []
        if importlib.util.find_spec("onnx_asr") is None:
            _cmds.append([sys.executable, "-m", "pip", "install", "onnx-asr"])
        if "CUDAExecutionProvider" not in _providers:
            _cmds.append(
                [sys.executable, "-m", "pip", "install", "onnxruntime-gpu"]
            )
        if not _cmds:
            install_log["status"] = "nothing missing"
            _out = mo.md(
                "Nothing to install: `onnx-asr` is importable and the "
                "CUDA provider is already listed."
            )
        else:
            _lines = []
            for _cmd in _cmds:
                _t0 = time.time()
                _r = subprocess.run(
                    _cmd, capture_output=True, text=True, timeout=1200
                )
                _step = {
                    "command": " ".join(_cmd),
                    "returncode": _r.returncode,
                    "seconds": round(time.time() - _t0, 3),
                    "stdout_tail": _r.stdout.strip().splitlines()[-3:],
                    "stderr_tail": _r.stderr.strip().splitlines()[-3:],
                }
                install_log["steps"].append(_step)
                _lines.append(
                    f"- `{' '.join(_cmd[3:])}`: return code "
                    f"{_r.returncode} in {_step['seconds']} s"
                )
            install_log["status"] = "ran"
            install_log["restart_recommended"] = True
            _out = mo.md(
                "## Install result\n\n"
                + "\n".join(_lines)
                + "\n\nONNX Runtime was already imported by the probe "
                "cell, so a newly installed GPU build takes effect only "
                "after a kernel restart: use the notebook menu to "
                "restart the kernel, then run all cells again and check "
                "that the probe now lists `CUDAExecutionProvider`."
            )
    # NOTE: marimo renders only the cell's last expression, so end on _out
    _out
    return (install_log,)


@app.cell
def _(mo):
    audio_file = mo.ui.file(
        filetypes=[".wav", ".mp3", ".m4a", ".webm", ".ogg", ".mp4", ".flac"],
        kind="area",
        label="Drop one audio file here, or click to choose it",
    )
    timestamps_cb = mo.ui.checkbox(
        label="Timestamps: prefix each chunk (about 25 s) with its time range",
        value=False,
    )
    _out = mo.vstack(
        [
            mo.md(
                "## Audio\n\n"
                "One file per run. The file stays in this session; "
                "nothing is sent anywhere else by this notebook."
            ),
            audio_file,
            timestamps_cb,
        ]
    )
    # NOTE: marimo renders only the cell's last expression, so end on _out
    _out
    return audio_file, timestamps_cb


@app.cell
def _(mo):
    transcribe_btn = mo.ui.run_button(label="Transcribe")
    _out = mo.vstack(
        [
            mo.md(
                "## Transcribe\n\n"
                "The model (about 670 MB in its int8 form; the "
                "unquantized form used on the GPU is larger) downloads "
                "on the first run and is cached in the session. Words "
                "appear chunk by chunk in the progress bar while the "
                "run proceeds."
            ),
            transcribe_btn,
        ]
    )
    # NOTE: marimo renders only the cell's last expression, so end on _out
    _out
    return (transcribe_btn,)


@app.cell
def _(
    audio_file,
    chunk_bounds,
    format_ts,
    install_log,
    mo,
    np,
    ort,
    probe_log,
    shutil,
    subprocess,
    tempfile,
    time,
    timestamps_cb,
    transcribe_btn,
    wave,
):
    transcript_text = ""
    run_log = {"status": "not run"}
    _val = audio_file.value
    if isinstance(_val, (list, tuple)):
        _val = _val[0] if _val else None
    if _val is None:
        _out = mo.md("No audio file uploaded yet.")
    elif not transcribe_btn.value:
        _out = mo.md(
            f"File ready: **{_val.name}** "
            f"({round(_val.size / 1e6, 2)} MB). Click Transcribe to run."
        )
    elif ort is None:
        run_log = {
            "status": "blocked",
            "error": "onnxruntime is not imported; run the install "
            "step, restart the kernel, and run all cells again.",
        }
        _out = mo.md(f"**Cannot transcribe.** {run_log['error']}")
    else:
        _t_all = time.time()
        run_log = {
            "status": "running",
            "file_name": _val.name,
            "file_size_mb": round(_val.size / 1e6, 3),
            "timestamps": bool(timestamps_cb.value),
            "install_status": install_log.get("status"),
        }
        try:
            import onnx_asr

            with tempfile.TemporaryDirectory() as _tmp:
                _raw_path = f"{_tmp}/input"
                with open(_raw_path, "wb") as _f:
                    _f.write(_val.contents)
                _wav_path = _raw_path
                _is_wav = False
                try:
                    with wave.open(_raw_path, "rb") as _w:
                        _is_wav = (
                            _w.getframerate(),
                            _w.getnchannels(),
                            _w.getsampwidth(),
                        ) == (16000, 1, 2)
                except Exception:
                    _is_wav = False
                if not _is_wav:
                    if shutil.which("ffmpeg") is None:
                        raise RuntimeError(
                            "ffmpeg is not on the path and the file is "
                            "not already a 16 kHz mono WAV file"
                        )
                    _wav_path = f"{_tmp}/input.16k.wav"
                    subprocess.run(
                        [
                            "ffmpeg", "-y", "-v", "error", "-i", _raw_path,
                            "-ar", "16000", "-ac", "1",
                            "-sample_fmt", "s16", _wav_path,
                        ],
                        check=True,
                    )
                with wave.open(_wav_path, "rb") as _w:
                    _n = _w.getnframes()
                    _audio = (
                        np.frombuffer(_w.readframes(_n), dtype=np.int16)
                        .astype(np.float32)
                        / 32768.0
                    )
                _sr = 16000
                _cuts = chunk_bounds(_audio, _sr)
                run_log["duration_s"] = round(len(_audio) / _sr, 2)
                run_log["chunks"] = len(_cuts) - 1
                _providers = ort.get_available_providers()
                run_log["providers_available"] = _providers
                _on_gpu = "CUDAExecutionProvider" in _providers
                run_log["engine"] = "gpu" if _on_gpu else "cpu-fallback"
                run_log["providers_requested"] = (
                    ["CUDAExecutionProvider", "CPUExecutionProvider"]
                    if _on_gpu
                    else ["CPUExecutionProvider"]
                )
                run_log["quantization"] = None if _on_gpu else "int8"
                _t0 = time.time()
                _load_kwargs = {"providers": run_log["providers_requested"]}
                if not _on_gpu:
                    _so = ort.SessionOptions()
                    _so.intra_op_num_threads = 1
                    _so.inter_op_num_threads = 1
                    _load_kwargs["sess_options"] = _so
                if run_log["quantization"]:
                    _load_kwargs["quantization"] = run_log["quantization"]
                _model = onnx_asr.load_model(
                    "nemo-parakeet-tdt-0.6b-v2", **_load_kwargs
                )
                run_log["model_load_s"] = round(time.time() - _t0, 3)
                _parts = []
                _chunk_log = []
                _t_tr = time.time()
                with mo.status.progress_bar(
                    total=len(_cuts) - 1,
                    title="Transcribing",
                    remove_on_exit=False,
                ) as _bar:
                    for _i in range(len(_cuts) - 1):
                        _tc = time.time()
                        _seg = _audio[
                            int(_cuts[_i] * _sr) : int(_cuts[_i + 1] * _sr)
                        ]
                        _text = _model.recognize(_seg, sample_rate=_sr)
                        if not isinstance(_text, str):
                            _text = _text.text
                        _text = _text.strip()
                        _parts.append(_text)
                        _chunk_log.append(
                            {
                                "chunk": _i + 1,
                                "start_s": round(_cuts[_i], 2),
                                "end_s": round(_cuts[_i + 1], 2),
                                "seconds": round(time.time() - _tc, 3),
                                "words": len(_text.split()),
                            }
                        )
                        _bar.update(
                            increment=1,
                            subtitle=(
                                f"chunk {_i + 1} of {len(_cuts) - 1}: "
                                f"{_text[:110]}"
                            ),
                        )
                run_log["transcribe_s"] = round(time.time() - _t_tr, 3)
                run_log["chunk_log"] = _chunk_log
                if timestamps_cb.value:
                    transcript_text = "\n".join(
                        f"[{format_ts(_cuts[_j])}-{format_ts(_cuts[_j + 1])}] "
                        f"{_parts[_j]}"
                        for _j in range(len(_parts))
                        if _parts[_j]
                    )
                else:
                    transcript_text = " ".join(p for p in _parts if p)
                run_log["word_count"] = len(transcript_text.split())
                run_log["total_s"] = round(time.time() - _t_all, 3)
                run_log["real_time_factor"] = round(
                    run_log["duration_s"] / max(run_log["transcribe_s"], 1e-9),
                    2,
                )
                run_log["status"] = "done"
            _warn = (
                ""
                if run_log["engine"] == "gpu"
                else "\n\n**Warning: the CUDA provider was not available, "
                "so this run used the CPU.** The log records this; the "
                "transcript is still valid, but it is not a GPU result."
            )
            _out = mo.md(
                f"Transcription done on the **{run_log['engine']}**: "
                f"{run_log['duration_s']} s of audio in "
                f"{run_log['transcribe_s']} s of transcription "
                f"(real-time factor {run_log['real_time_factor']}), "
                f"{run_log['chunks']} chunks, "
                f"{run_log['word_count']} words. Model load took "
                f"{run_log['model_load_s']} s.{_warn}"
            )
        except Exception as _e:
            run_log["status"] = "error"
            run_log["error"] = f"{type(_e).__name__}: {_e}"
            run_log["total_s"] = round(time.time() - _t_all, 3)
            _out = mo.md(
                f"**Transcription failed.** {run_log['error']}\n\n"
                "The failure is recorded in the session log below; "
                "download it and return it with the transcript."
            )
    # NOTE: marimo renders only the cell's last expression, so end on _out
    _out
    return run_log, transcript_text


@app.cell
def _(mo, run_log, transcript_text):
    import html

    if not transcript_text:
        _out = mo.md(
            "## Raw transcript\n\n"
            "No transcript yet. The raw transcript is the record of "
            "the run: the glossary correction stages are applied to "
            "this text later, outside this notebook, and never change "
            "this file."
        )
    else:
        _out = mo.vstack(
            [
                mo.md("## Raw transcript"),
                mo.Html(
                    "<pre style='white-space:pre-wrap; "
                    "font-size:0.85em; max-height:480px; "
                    "overflow:auto'>"
                    + html.escape(transcript_text)
                    + "</pre>"
                ),
                mo.download(
                    data=transcript_text.encode("utf-8"),
                    filename="transcript-gpu.raw.txt",
                    mimetype="text/plain",
                    label="Download raw transcript (.txt)",
                ),
            ]
        )
    # NOTE: marimo renders only the cell's last expression, so end on _out
    _out
    return


@app.cell
def _(
    audio_file,
    install_log,
    json,
    mo,
    probe_log,
    run_log,
    time,
    timestamps_cb,
):
    _val = audio_file.value
    if isinstance(_val, (list, tuple)):
        _val = _val[0] if _val else None
    session_log = {
        "notebook": "chemescribe-molab-gpu/transcribe_gpu.py",
        "assembled_unix_s": round(time.time(), 3),
        "probe": probe_log,
        "install": install_log,
        "ui": {
            "timestamps": bool(timestamps_cb.value),
            "file_name": _val.name if _val is not None else None,
            "file_size_mb": (
                round(_val.size / 1e6, 3) if _val is not None else None
            ),
        },
        "transcription": run_log,
    }
    _log_text = json.dumps(session_log, indent=2)
    _out = mo.vstack(
        [
            mo.md(
                "## Session log\n\n"
                "The log records the environment probe (GPU name and "
                "memory in GB, providers, package versions), every "
                "install command with its duration in s and return "
                "code, the control settings, and the transcription "
                "record (engine actually used, model load time in s, "
                "per-chunk times in s, word counts, errors). Download "
                "it and return it together with the raw transcript; "
                "that pair is what the next correction and the lessons "
                "from this run are based on.\n\n"
                f"Transcription status in this log: "
                f"**{run_log.get('status')}**"
            ),
            mo.download(
                data=_log_text.encode("utf-8"),
                filename="molab-gpu-session-log.json",
                mimetype="application/json",
                label="Download session log (.json)",
            ),
            mo.Html(
                "<pre style='white-space:pre-wrap; "
                "font-size:0.8em; max-height:360px; overflow:auto'>"
                + _log_text.replace("<", "&lt;")
                + "</pre>"
            ),
        ]
    )
    # NOTE: marimo renders only the cell's last expression, so end on _out
    _out
    return (session_log,)


if __name__ == "__main__":
    app.run()
