use serde::Serialize;

#[derive(Debug, Clone, Serialize)]
pub struct ClipReport {
    pub file: String,
    /// Clip duration, in seconds (s).
    pub duration: f64,
    /// Absolute stream index of the chosen audio track.
    pub audio_stream: usize,
    /// Start of the kept segment, in seconds (s) from the clip start.
    pub inpoint: f64,
    /// End of the kept segment, in seconds (s) from the clip start.
    pub outpoint: f64,
    /// Kept duration, in seconds (s).
    pub kept: f64,
    pub start_cue_found: bool,
    pub stop_cue_found: bool,
    pub mismatched: bool,
    pub warnings: Vec<String>,
}

pub fn print_table(reports: &[ClipReport]) {
    println!(
        "{:<34} {:>5} {:>8} {:>8} {:>8}  notes",
        "file", "track", "in (s)", "out (s)", "kept (s)"
    );
    for r in reports {
        let name = if r.file.len() > 34 {
            format!("...{}", &r.file[r.file.len() - 31..])
        } else {
            r.file.clone()
        };
        println!(
            "{:<34} {:>5} {:>8.2} {:>8.2} {:>8.2}  {}",
            name,
            r.audio_stream,
            r.inpoint,
            r.outpoint,
            r.kept,
            r.warnings.join("; ")
        );
    }
    let total: f64 = reports.iter().map(|r| r.kept).sum();
    println!("total kept: {total:.2} s across {} clip(s)", reports.len());
}
