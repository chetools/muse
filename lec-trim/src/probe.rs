use crate::tools::{path_str, run_ok};
use anyhow::{Context, Result};
use serde::Deserialize;
use std::path::{Path, PathBuf};
use std::process::Command;

#[derive(Debug, Clone)]
pub struct AudioTrack {
    /// Absolute stream index in the container (used with `-map 0:<index>`).
    pub stream_index: usize,
    pub codec: String,
    pub sample_rate: u32,
    pub channels: u32,
}

#[derive(Debug, Clone)]
pub struct ClipMeta {
    pub duration: f64,
    pub video_codec: String,
    pub width: u32,
    pub height: u32,
    /// Frame rate, in frames per second (s^-1).
    pub fps: f64,
    pub pix_fmt: String,
    /// True when the video stream carries B-frames. Stream-copy trimming
    /// is not frame-accurate with B-frames (packet presentation times
    /// are out of decode order), so such clips are re-encoded in full.
    pub has_b_frames: bool,
    pub audio: Vec<AudioTrack>,
}

impl ClipMeta {
    /// True when this clip's parameters that affect stream-copy
    /// concatenation match `other`.
    pub fn compatible_with(&self, other: &ClipMeta) -> bool {
        self.video_codec == other.video_codec
            && self.width == other.width
            && self.height == other.height
            && (self.fps - other.fps).abs() < 0.01
            && self.pix_fmt == other.pix_fmt
    }
}

#[derive(Deserialize)]
struct ProbeJson {
    format: Option<FormatJson>,
    streams: Vec<StreamJson>,
}

#[derive(Deserialize)]
struct FormatJson {
    duration: Option<String>,
}

#[derive(Deserialize)]
struct StreamJson {
    index: usize,
    codec_type: String,
    codec_name: String,
    width: Option<u32>,
    height: Option<u32>,
    pix_fmt: Option<String>,
    #[serde(default)]
    has_b_frames: u32,
    avg_frame_rate: Option<String>,
    sample_rate: Option<String>,
    channels: Option<u32>,
    duration: Option<String>,
}

fn parse_rate(s: &str) -> f64 {
    if let Some((a, b)) = s.split_once('/') {
        let den: f64 = b.parse().unwrap_or(1.0);
        if den == 0.0 {
            return 0.0;
        }
        a.parse::<f64>().unwrap_or(0.0) / den
    } else {
        s.parse().unwrap_or(0.0)
    }
}

pub fn probe(ffprobe: &PathBuf, file: &Path) -> Result<ClipMeta> {
    let out = run_ok(
        Command::new(ffprobe).args([
            "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams",
            &path_str(file)?,
        ]),
        "ffprobe",
    )?;
    let parsed: ProbeJson = serde_json::from_slice(&out.stdout).context("parsing ffprobe JSON")?;
    let mut video: Option<&StreamJson> = None;
    let mut audio = Vec::new();
    for s in &parsed.streams {
        match s.codec_type.as_str() {
            "video" if video.is_none() => video = Some(s),
            "audio" => audio.push(AudioTrack {
                stream_index: s.index,
                codec: s.codec_name.clone(),
                sample_rate: s.sample_rate.as_deref().unwrap_or("0").parse().unwrap_or(0),
                channels: s.channels.unwrap_or(0),
            }),
            _ => {}
        }
    }
    let v = video.context("clip has no video stream")?;
    let duration = parsed
        .format
        .and_then(|f| f.duration)
        .or_else(|| v.duration.clone())
        .and_then(|d| d.parse::<f64>().ok())
        .context("clip has no duration")?;
    Ok(ClipMeta {
        duration,
        video_codec: v.codec_name.clone(),
        width: v.width.unwrap_or(0),
        height: v.height.unwrap_or(0),
        fps: parse_rate(v.avg_frame_rate.as_deref().unwrap_or("0")),
        pix_fmt: v.pix_fmt.clone().unwrap_or_default(),
        has_b_frames: v.has_b_frames > 0,
        audio,
    })
}

/// Keyframe presentation times, in seconds (s), ascending.
pub fn keyframes(ffprobe: &PathBuf, file: &Path) -> Result<Vec<f64>> {
    let out = run_ok(
        Command::new(ffprobe).args([
            "-v", "quiet", "-select_streams", "v:0",
            "-show_entries", "packet=pts_time,flags",
            "-of", "csv=p=0",
            &path_str(file)?,
        ]),
        "ffprobe keyframes",
    )?;
    let text = String::from_utf8_lossy(&out.stdout);
    let mut times: Vec<f64> = Vec::new();
    for line in text.lines() {
        // csv order follows the -show_entries order in some builds and is
        // reversed in others; accept a float and a flag field either way.
        let parts: Vec<&str> = line.split(',').collect();
        if parts.len() < 2 {
            continue;
        }
        let (t, flags) = if parts[0].trim().parse::<f64>().is_ok() {
            (parts[0].trim(), parts[1].trim())
        } else {
            (parts[1].trim(), parts[0].trim())
        };
        if flags.contains('K') {
            if let Ok(v) = t.parse::<f64>() {
                times.push(v);
            }
        }
    }
    times.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    times.dedup_by(|a, b| (*a - *b).abs() < 1e-6);
    Ok(times)
}
