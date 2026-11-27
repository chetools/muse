use crate::cli::OutFormat;
use crate::probe::ClipMeta;
use crate::tools::{path_str, run_ok};
use anyhow::Result;
use std::path::{Path, PathBuf};
use std::process::Command;

#[derive(Debug, Clone)]
pub struct Segment {
    pub file: PathBuf,
    pub meta: ClipMeta,
    /// Absolute stream index of the chosen audio track.
    pub audio_stream: usize,
    pub audio_codec: String,
    pub audio_sample_rate: u32,
    pub audio_channels: u32,
    pub inpoint: f64,
    pub outpoint: f64,
    /// True when the clip's parameters differ from the primary clip and
    /// the whole kept segment must be re-encoded to match.
    pub mismatched: bool,
}

/// Plan the parts of one kept segment. Each part is
/// (start in seconds (s), end in seconds (s), stream-copy flag).
/// The head part runs from the inpoint to the first keyframe after it,
/// the middle part between keyframes is stream-copied, and the tail
/// part runs from the last keyframe before the outpoint to the
/// outpoint. Head and tail parts are re-encoded, which makes the cuts
/// accurate to the cue times instead of snapping to keyframes.
pub fn plan_parts(inpoint: f64, outpoint: f64, keyframes: &[f64]) -> Vec<(f64, f64, bool)> {
    let inner: Vec<f64> = keyframes
        .iter()
        .copied()
        .filter(|k| *k > inpoint + 0.001 && *k < outpoint - 0.001)
        .collect();
    if inner.len() < 2 {
        return vec![(inpoint, outpoint, false)];
    }
    let first = inner[0];
    let last = inner[inner.len() - 1];
    if last - first < 0.01 {
        return vec![(inpoint, outpoint, false)];
    }
    vec![
        (inpoint, first, false),
        (first, last, true),
        (last, outpoint, false),
    ]
}

/// Escape a path for an ffconcat manifest: single quotes are wrapped as
/// '\'' and backslashes are converted to forward slashes.
pub fn escape_concat_path(p: &Path) -> String {
    let s = p.to_string_lossy().replace('\\', "/");
    format!("'{}'", s.replace('\'', "'\\''"))
}

struct EncTarget {
    width: u32,
    height: u32,
    fps: f64,
    pix_fmt: String,
    sample_rate: u32,
    channels: u32,
}

#[allow(clippy::too_many_arguments)]
fn make_part(
    ffmpeg: &PathBuf,
    seg: &Segment,
    start: f64,
    end: f64,
    copy_video: bool,
    target: &EncTarget,
    scale_to_target: bool,
    out: &Path,
) -> Result<()> {
    let dur = end - start;
    let mut args: Vec<String> = vec![
        "-y".into(), "-v".into(), "error".into(),
        "-ss".into(), format!("{start:.3}"),
        "-i".into(), path_str(&seg.file)?,
    ];
    if copy_video {
        // An output-side `-ss 0` after the input seek is required:
        // without it, `-t` with stream copy overruns the requested
        // duration by about a keyframe interval (measured 7.23 s for a
        // 6.00 s part on the mock clips); with it the same part is
        // 6.13 s. The input seek already lands on the part's first
        // keyframe, so the output seek discards nothing.
        args.extend(["-ss".into(), "0".into()]);
    }
    args.extend([
        "-t".into(), format!("{dur:.3}"),
        "-map".into(), "0:v:0".into(),
        "-map".into(), format!("0:{}", seg.audio_stream),
    ]);
    if copy_video {
        args.extend(["-c:v".into(), "copy".into()]);
    } else {
        args.extend([
            "-c:v".into(), "libx264".into(),
            "-preset".into(), "veryfast".into(),
            "-crf".into(), "18".into(),
            "-pix_fmt".into(), target.pix_fmt.clone(),
        ]);
        if scale_to_target {
            args.extend([
                "-vf".into(),
                format!("scale={}:{},fps={:.3}", target.width, target.height, target.fps),
            ]);
        } else if target.fps > 0.0 {
            args.extend(["-r".into(), format!("{:.3}", target.fps)]);
        }
    }
    // Audio: copy only in a stream-copied video part, and only when it
    // already matches the target AAC profile. In a re-encoded part the
    // audio is always re-encoded too: copied audio packets overrun the
    // part's end (measured 1.07 s of audio in a 0.57 s head part), while
    // re-encoded audio is trimmed at frame level.
    let audio_copy = copy_video
        && seg.audio_codec == "aac"
        && seg.audio_sample_rate == target.sample_rate
        && seg.audio_channels == target.channels;
    if audio_copy {
        args.extend(["-c:a".into(), "copy".into()]);
    } else {
        args.extend([
            "-c:a".into(), "aac".into(),
            "-b:a".into(), "160k".into(),
            "-ar".into(), target.sample_rate.to_string(),
            "-ac".into(), target.channels.to_string(),
        ]);
    }
    args.extend([
        "-avoid_negative_ts".into(), "make_zero".into(),
        path_str(out)?,
    ]);
    run_ok(Command::new(ffmpeg).args(&args), "ffmpeg part render")?;
    Ok(())
}

/// Render every segment's parts and concatenate them with `-c copy`.
pub fn stitch(
    ffmpeg: &PathBuf,
    ffprobe: &PathBuf,
    segments: &[Segment],
    format: OutFormat,
    output: &Path,
    tmp: &Path,
) -> Result<()> {
    let primary = &segments[0];
    let target = EncTarget {
        width: primary.meta.width,
        height: primary.meta.height,
        fps: if primary.meta.fps > 0.0 { primary.meta.fps } else { 30.0 },
        pix_fmt: if primary.meta.pix_fmt.starts_with("yuv420p") {
            primary.meta.pix_fmt.clone()
        } else {
            "yuv420p".into()
        },
        sample_rate: if primary.audio_sample_rate > 0 { primary.audio_sample_rate } else { 48000 },
        channels: if primary.audio_channels > 0 { primary.audio_channels } else { 2 },
    };
    let mut part_paths: Vec<PathBuf> = Vec::new();
    for (i, seg) in segments.iter().enumerate() {
        // Stream-copy of the middle is only valid when every part of the
        // set shares one video codec. Non-H.264 sources are re-encoded
        // in full to H.264 (OBS records H.264 by default, so this is the
        // uncommon path).
        let force_reencode =
            seg.mismatched || seg.meta.video_codec != "h264" || seg.meta.has_b_frames;
        let parts = if force_reencode {
            vec![(seg.inpoint, seg.outpoint, false)]
        } else {
            let kfs = crate::probe::keyframes(ffprobe, &seg.file)?;
            plan_parts(seg.inpoint, seg.outpoint, &kfs)
        };
        for (j, (start, end, copy)) in parts.iter().enumerate() {
            if end - start < 0.01 {
                continue;
            }
            let part = tmp.join(format!("part_{i:03}_{j}.mkv"));
            make_part(
                ffmpeg, seg, *start, *end,
                *copy && !force_reencode,
                &target, seg.mismatched, &part,
            )?;
            part_paths.push(part);
        }
    }
    let mut manifest = String::from("ffconcat version 1.0\n");
    for p in &part_paths {
        manifest.push_str(&format!("file {}\n", escape_concat_path(p)));
    }
    let manifest_path = tmp.join("list.ffconcat");
    std::fs::write(&manifest_path, manifest)?;
    let mut args: Vec<String> = vec![
        "-y".into(), "-v".into(), "error".into(),
        "-f".into(), "concat".into(), "-safe".into(), "0".into(),
        "-i".into(), path_str(&manifest_path)?,
        "-c".into(), "copy".into(),
    ];
    if format == OutFormat::Mp4 {
        args.extend(["-movflags".into(), "+faststart".into()]);
    }
    args.push(path_str(output)?);
    run_ok(Command::new(ffmpeg).args(&args), "ffmpeg concat")?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn plans_three_parts() {
        let kfs: Vec<f64> = (0..=20).map(|i| i as f64).collect();
        let parts = plan_parts(2.4, 17.6, &kfs);
        assert_eq!(parts.len(), 3);
        assert_eq!(parts[0], (2.4, 3.0, false));
        assert_eq!(parts[1], (3.0, 17.0, true));
        assert_eq!(parts[2], (17.0, 17.6, false));
    }

    #[test]
    fn plans_single_reencode_without_inner_keyframes() {
        let parts = plan_parts(2.4, 2.9, &[0.0, 1.0, 2.0, 3.0]);
        assert_eq!(parts, vec![(2.4, 2.9, false)]);
    }

    #[test]
    fn escapes_paths() {
        assert_eq!(
            escape_concat_path(Path::new("C:\\clips\\it's here.mkv")),
            "'C:/clips/it'\\''s here.mkv'"
        );
    }
}
