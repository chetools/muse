use clap::{Parser, ValueEnum};
use std::path::PathBuf;

#[derive(Copy, Clone, Debug, PartialEq, Eq, ValueEnum)]
pub enum OutFormat {
    Mp4,
    Mkv,
}

impl OutFormat {
    pub fn extension(&self) -> &'static str {
        match self {
            OutFormat::Mp4 => "mp4",
            OutFormat::Mkv => "mkv",
        }
    }
}

/// Trim OBS clips at spoken cues and stitch them into one lecture video.
#[derive(Parser, Debug, Clone)]
#[command(name = "lec-trim", version, about)]
pub struct Cli {
    /// Folder containing the OBS clips (default: current folder).
    #[arg(value_name = "INPUT_DIR", default_value = ".")]
    pub input: PathBuf,

    /// Output container. MP4 is the default because YouTube and most
    /// learning-management upload pages accept MP4 but not MKV.
    #[arg(long, value_enum, default_value = "mp4")]
    pub format: OutFormat,

    /// Spoken phrase that starts the kept part of each clip.
    #[arg(long, default_value = "start recording")]
    pub start_phrase: String,

    /// Spoken phrase that ends the kept part of each clip.
    #[arg(long, default_value = "stop recording")]
    pub stop_phrase: String,

    /// Seconds of audio examined at the start of each clip.
    #[arg(long, default_value_t = 30.0)]
    pub head_window: f64,

    /// Seconds of audio examined at the end of each clip.
    #[arg(long, default_value_t = 30.0)]
    pub tail_window: f64,

    /// Seconds added after the end of the start phrase.
    #[arg(long, default_value_t = 0.15)]
    pub pad_start: f64,

    /// Seconds removed before the start of the stop phrase.
    #[arg(long, default_value_t = 0.15)]
    pub pad_end: f64,

    /// Detect cues and print the report without writing video.
    #[arg(long)]
    pub dry_run: bool,

    /// Print the report as JSON as well as a table.
    #[arg(long)]
    pub json: bool,

    /// Path to ggml-base.en.bin (searched beside the executable and in
    /// the OS cache folder when omitted).
    #[arg(long)]
    pub model: Option<PathBuf>,

    /// Path to the whisper-cli program (searched beside the executable,
    /// then on PATH, when omitted).
    #[arg(long)]
    pub whisper_cli: Option<PathBuf>,

    /// Path to ffmpeg (searched beside the executable, then on PATH).
    #[arg(long)]
    pub ffmpeg: Option<PathBuf>,

    /// Path to ffprobe (searched beside the executable, then on PATH).
    #[arg(long)]
    pub ffprobe: Option<PathBuf>,

    /// On Windows, wait for Enter before closing (for drag-and-drop use).
    #[arg(long)]
    pub pause_at_end: bool,
}
