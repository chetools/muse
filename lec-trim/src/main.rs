mod audio;
mod cli;
mod detector;
mod probe;
mod report;
mod scanner;
mod stitcher;
mod tools;

use anyhow::{bail, Context, Result};
use clap::Parser;
use cli::Cli;
use rayon::prelude::*;
use report::ClipReport;
use std::path::{Path, PathBuf};
use stitcher::Segment;

struct TrackDetection {
    stream_index: usize,
    start: Option<(f64, f64, f64)>, // (start, end, prob) in head-window time
    stop: Option<(f64, f64, f64)>,  // (start, end, prob) in tail-window time
    prob_sum: f64,
    rms: f64,
}

fn detect_clip(
    args: &Cli,
    ffmpeg: &PathBuf,
    whisper: &PathBuf,
    model: &Path,
    file: &Path,
    meta: &probe::ClipMeta,
    clip_idx: usize,
    tmp: &Path,
) -> Result<(Segment, ClipReport)> {
    let name = file.file_name().unwrap_or_default().to_string_lossy().to_string();
    if meta.audio.is_empty() {
        bail!("{name}: clip has no audio track");
    }
    let tail_len = args.tail_window.min(meta.duration);
    let tail_start = meta.duration - tail_len;

    // Extract every track's windows first and measure their levels.
    // A near-silent track is not transcribed when another track carries
    // sound: transcribing silence is the slowest wasted work in the
    // pipeline, and OBS clips often carry a silent second track.
    let mut extracted: Vec<(usize, std::path::PathBuf, std::path::PathBuf, f64)> = Vec::new();
    for (t, track) in meta.audio.iter().enumerate() {
        let head_wav = tmp.join(format!("c{clip_idx}_t{t}_head.wav"));
        let tail_wav = tmp.join(format!("c{clip_idx}_t{t}_tail.wav"));
        audio::extract_head(ffmpeg, file, track.stream_index, args.head_window, &head_wav)?;
        audio::extract_tail(ffmpeg, file, track.stream_index, args.tail_window, meta.duration, &tail_wav)?;
        let rms = audio::rms_level(&head_wav).max(audio::rms_level(&tail_wav));
        extracted.push((t, head_wav, tail_wav, rms));
    }
    let any_audible = extracted.iter().any(|x| x.3 >= 0.002);

    let mut tracks: Vec<TrackDetection> = Vec::new();
    for (t, head_wav, tail_wav, rms) in &extracted {
        let track = &meta.audio[*t];
        if any_audible && *rms < 0.002 {
            tracks.push(TrackDetection {
                stream_index: track.stream_index,
                start: None,
                stop: None,
                prob_sum: 0.0,
                rms: *rms,
            });
            continue;
        }
        let head_words = detector::transcribe(whisper, model, head_wav, &tmp.join(format!("c{clip_idx}_t{t}_head")))?;
        let tail_words = detector::transcribe(whisper, model, tail_wav, &tmp.join(format!("c{clip_idx}_t{t}_tail")))?;
        let start = detector::find_phrase(&head_words, &args.start_phrase, false);
        let stop = detector::find_phrase(&tail_words, &args.stop_phrase, true);
        let prob_sum = start.map(|x| x.2).unwrap_or(0.0) + stop.map(|x| x.2).unwrap_or(0.0);
        tracks.push(TrackDetection {
            stream_index: track.stream_index,
            start,
            stop,
            prob_sum,
            rms: *rms,
        });
    }

    // Most robust track: both cues found, then highest mean token
    // probability; when no track has both cues, the loudest head window.
    let chosen = tracks
        .iter()
        .filter(|t| t.start.is_some() && t.stop.is_some())
        .max_by(|a, b| a.prob_sum.partial_cmp(&b.prob_sum).unwrap_or(std::cmp::Ordering::Equal))
        .or_else(|| {
            tracks.iter().max_by(|a, b| a.rms.partial_cmp(&b.rms).unwrap_or(std::cmp::Ordering::Equal))
        })
        .context("no audio track could be examined")?;

    let track_meta = meta
        .audio
        .iter()
        .find(|t| t.stream_index == chosen.stream_index)
        .context("chosen audio track missing from probe data")?;

    let mut warnings: Vec<String> = Vec::new();
    let mut inpoint = 0.0f64;
    let mut outpoint = meta.duration;
    let start_found = chosen.start.is_some();
    let stop_found = chosen.stop.is_some();
    if let Some((_, end, _)) = chosen.start {
        inpoint = end + args.pad_start;
    } else {
        warnings.push(format!(
            "WARNING {name}: '{}' not found in the first {:.0} s; keeping from 0 s",
            args.start_phrase, args.head_window
        ));
    }
    if let Some((start, _, _)) = chosen.stop {
        outpoint = tail_start + start - args.pad_end;
    } else {
        warnings.push(format!(
            "WARNING {name}: '{}' not found in the last {:.0} s; keeping to the end",
            args.stop_phrase, args.tail_window
        ));
    }
    if outpoint - inpoint < 2.0 {
        warnings.push(format!(
            "WARNING {name}: kept segment would be under 2.0 s; keeping the whole clip"
        ));
        inpoint = 0.0;
        outpoint = meta.duration;
    }
    inpoint = inpoint.clamp(0.0, meta.duration);
    outpoint = outpoint.clamp(0.0, meta.duration);

    let seg = Segment {
        file: file.to_path_buf(),
        meta: meta.clone(),
        audio_stream: chosen.stream_index,
        audio_codec: track_meta.codec.clone(),
        audio_sample_rate: track_meta.sample_rate,
        audio_channels: track_meta.channels,
        inpoint,
        outpoint,
        mismatched: false, // set by the caller against the primary clip
    };
    let rep = ClipReport {
        file: name,
        duration: meta.duration,
        audio_stream: chosen.stream_index,
        inpoint,
        outpoint,
        kept: outpoint - inpoint,
        start_cue_found: start_found,
        stop_cue_found: stop_found,
        mismatched: false,
        warnings,
    };
    Ok((seg, rep))
}

fn run() -> Result<()> {
    let args = Cli::parse();
    let ffmpeg = tools::find_tool("ffmpeg", &args.ffmpeg)?;
    let ffprobe = tools::find_tool("ffprobe", &args.ffprobe)?;
    let whisper = tools::find_tool("whisper-cli", &args.whisper_cli)?;
    let model = tools::find_model(&args.model)?;

    let clips = scanner::discover(&args.input)?;
    if clips.is_empty() {
        bail!("no video clips found in {}", args.input.display());
    }
    println!("found {} clip(s) in {}", clips.len(), args.input.display());

    let tmp = std::env::temp_dir().join(format!("lec-trim-{}", std::process::id()));
    std::fs::create_dir_all(&tmp)?;
    let result = run_pipeline(&args, &ffmpeg, &ffprobe, &whisper, &model, &clips, &tmp);
    if std::env::var_os("LEC_TRIM_KEEP_TMP").is_some() {
        eprintln!("keeping temporary folder {}", tmp.display());
    } else {
        let _ = std::fs::remove_dir_all(&tmp);
    }
    result
}

fn run_pipeline(
    args: &Cli,
    ffmpeg: &PathBuf,
    ffprobe: &PathBuf,
    whisper: &PathBuf,
    model: &Path,
    clips: &[PathBuf],
    tmp: &Path,
) -> Result<()> {
    let mut metas = Vec::new();
    for c in clips {
        metas.push(probe::probe(ffprobe, c)?);
    }
    let primary = metas[0].clone();

    let mut pairs: Vec<(Segment, ClipReport)> = clips
        .par_iter()
        .zip(metas.par_iter())
        .enumerate()
        .map(|(i, (file, meta))| detect_clip(args, ffmpeg, whisper, model, file, meta, i, tmp))
        .collect::<Result<Vec<_>>>()?;
    pairs.sort_by_key(|(_, r)| r.file.clone());
    // Restore chronological clip order (discovery order), not file-name
    // order of the report sort above: re-sort by discovery index.
    let order: std::collections::HashMap<String, usize> = clips
        .iter()
        .enumerate()
        .map(|(i, p)| {
            (
                p.file_name().unwrap_or_default().to_string_lossy().to_string(),
                i,
            )
        })
        .collect();
    pairs.sort_by_key(|(_, r)| order.get(&r.file).copied().unwrap_or(usize::MAX));

    let mut segments = Vec::new();
    let mut reports = Vec::new();
    for (mut seg, mut rep) in pairs {
        seg.mismatched = !seg.meta.compatible_with(&primary);
        rep.mismatched = seg.mismatched;
        if seg.mismatched {
            rep.warnings.push(format!(
                "WARNING {}: stream parameters differ from the first clip; this clip will be re-encoded in full",
                rep.file
            ));
        }
        if seg.meta.has_b_frames {
            rep.warnings.push(format!(
                "WARNING {}: clip has B-frames; it will be re-encoded in full so the cuts stay accurate (set Max B-frames to 0 in OBS to avoid this)",
                rep.file
            ));
        }
        segments.push(seg);
        reports.push(rep);
    }

    report::print_table(&reports);
    for r in &reports {
        for w in &r.warnings {
            eprintln!("{w}");
        }
    }
    if args.json {
        println!("{}", serde_json::to_string_pretty(&reports)?);
    }
    if args.dry_run {
        println!("dry run: no video written");
        return Ok(());
    }

    let output = scanner::next_output_path(&args.input, args.format.extension());
    stitcher::stitch(ffmpeg, ffprobe, &segments, args.format, &output, tmp)?;
    let out_meta = probe::probe(ffprobe, &output)?;
    println!(
        "wrote {} (duration {:.2} s)",
        output.display(),
        out_meta.duration
    );
    Ok(())
}

fn main() {
    let pause = std::env::args().any(|a| a == "--pause-at-end");
    match run() {
        Ok(()) => {}
        Err(e) => {
            eprintln!("error: {e:#}");
            if pause {
                wait_for_enter();
            }
            std::process::exit(1);
        }
    }
    if pause {
        wait_for_enter();
    }
}

fn wait_for_enter() {
    eprintln!("press Enter to close");
    let mut line = String::new();
    let _ = std::io::stdin().read_line(&mut line);
}
