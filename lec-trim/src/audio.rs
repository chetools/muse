use crate::tools::{path_str, run_ok};
use anyhow::Result;
use std::path::{Path, PathBuf};
use std::process::Command;

/// Extract the head window of one audio track as 16 kHz mono WAV.
/// The sample rate 16000 Hz and mono layout are what whisper-cli expects.
pub fn extract_head(
    ffmpeg: &PathBuf,
    file: &Path,
    stream_index: usize,
    window: f64,
    out: &Path,
) -> Result<()> {
    run_ok(
        Command::new(ffmpeg).args([
            "-y", "-v", "error",
            "-i", &path_str(file)?,
            "-map", &format!("0:{stream_index}"),
            "-t", &format!("{window:.3}"),
            "-vn", "-ac", "1", "-ar", "16000",
            &path_str(out)?,
        ]),
        "ffmpeg head extraction",
    )?;
    Ok(())
}

/// Extract the tail window of one audio track as 16 kHz mono WAV.
/// `-sseof` seeks from the end of the file, so the middle is not read.
pub fn extract_tail(
    ffmpeg: &PathBuf,
    file: &Path,
    stream_index: usize,
    window: f64,
    duration: f64,
    out: &Path,
) -> Result<()> {
    let w = window.min(duration);
    run_ok(
        Command::new(ffmpeg).args([
            "-y", "-v", "error",
            "-sseof", &format!("-{w:.3}"),
            "-i", &path_str(file)?,
            "-map", &format!("0:{stream_index}"),
            "-vn", "-ac", "1", "-ar", "16000",
            &path_str(out)?,
        ]),
        "ffmpeg tail extraction",
    )?;
    Ok(())
}

/// Root-mean-square level of a 16 kHz mono WAV file's samples, used only
/// to rank audio tracks when no track yields both cues. WAV files written
/// by ffmpeg here are 16-bit PCM.
pub fn rms_level(wav: &Path) -> f64 {
    let bytes = match std::fs::read(wav) {
        Ok(b) => b,
        Err(_) => return 0.0,
    };
    // Skip the WAV header (44 bytes for the files ffmpeg writes here).
    let data = if bytes.len() > 44 { &bytes[44..] } else { &bytes[..] };
    if data.len() < 2 {
        return 0.0;
    }
    let mut sum = 0.0f64;
    let mut n = 0u64;
    for pair in data.chunks_exact(2) {
        let s = i16::from_le_bytes([pair[0], pair[1]]) as f64 / 32768.0;
        sum += s * s;
        n += 1;
    }
    if n == 0 {
        0.0
    } else {
        (sum / n as f64).sqrt()
    }
}
