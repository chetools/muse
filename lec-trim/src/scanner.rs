use anyhow::Result;
use std::path::{Path, PathBuf};

pub const EXTENSIONS: [&str; 7] = ["mkv", "mp4", "mov", "flv", "ts", "webm", "m4v"];

fn is_output_name(name: &str) -> bool {
    let lower = name.to_ascii_lowercase();
    lower.starts_with("stitched_lecture_v")
}

/// Extract an OBS-style timestamp key `YYYYMMDDHHMMSS` from a file name
/// such as `2026-11-27 09-00-00.mkv`, when present.
pub fn obs_timestamp_key(name: &str) -> Option<String> {
    let digits: String = name.chars().take(19).filter(|c| c.is_ascii_digit()).collect();
    if digits.len() >= 14 {
        Some(digits[..14].to_string())
    } else {
        None
    }
}

fn sort_key(p: &Path) -> (String, String) {
    let name = p.file_name().map(|n| n.to_string_lossy().to_string()).unwrap_or_default();
    let ts = obs_timestamp_key(&name).unwrap_or_else(|| "99999999999999".to_string());
    (ts, name.to_ascii_lowercase())
}

/// Discover clips in `dir`, sorted chronologically (OBS timestamp in the
/// file name first, then file name). Previous lec-trim outputs and
/// temporary files are excluded.
pub fn discover(dir: &Path) -> Result<Vec<PathBuf>> {
    let mut clips = Vec::new();
    for entry in std::fs::read_dir(dir)? {
        let entry = entry?;
        let path = entry.path();
        if !path.is_file() {
            continue;
        }
        let name = path.file_name().unwrap_or_default().to_string_lossy().to_string();
        if name.starts_with('.') || name.ends_with(".part") || is_output_name(&name) {
            continue;
        }
        let ext = path
            .extension()
            .map(|e| e.to_string_lossy().to_ascii_lowercase())
            .unwrap_or_default();
        if EXTENSIONS.contains(&ext.as_str()) {
            clips.push(path);
        }
    }
    clips.sort_by_key(|p| sort_key(p));
    Ok(clips)
}

/// First unused versioned output path in `dir`:
/// `stitched_lecture_v01.<ext>`, `v02`, and so on.
pub fn next_output_path(dir: &Path, ext: &str) -> PathBuf {
    for n in 1..1000u32 {
        let cand = dir.join(format!("stitched_lecture_v{n:02}.{ext}"));
        if !cand.exists() {
            return cand;
        }
    }
    dir.join(format!("stitched_lecture_v1000.{ext}"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn obs_key_parsed() {
        assert_eq!(
            obs_timestamp_key("2026-11-27 09-00-00.mkv").as_deref(),
            Some("20261127090000")
        );
        assert_eq!(obs_timestamp_key("lecture one.mp4"), None);
    }

    #[test]
    fn sort_obs_before_renamed() {
        let mut v = vec![
            PathBuf::from("zzz renamed.mp4"),
            PathBuf::from("2026-11-27 09-04-12.mkv"),
            PathBuf::from("2026-11-27 09-00-00.mkv"),
        ];
        v.sort_by_key(|p| sort_key(p));
        assert!(v[0].to_string_lossy().contains("09-00-00"));
        assert!(v[1].to_string_lossy().contains("09-04-12"));
    }

    #[test]
    fn version_increments_and_never_overwrites() {
        let dir = std::env::temp_dir().join(format!("lec-trim-scan-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let first = next_output_path(&dir, "mp4");
        assert!(first.ends_with("stitched_lecture_v01.mp4"));
        std::fs::write(&first, b"x").unwrap();
        let second = next_output_path(&dir, "mp4");
        assert!(second.ends_with("stitched_lecture_v02.mp4"));
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn output_names_recognised() {
        assert!(is_output_name("stitched_lecture_v01.mp4"));
        assert!(!is_output_name("2026-11-27 09-00-00.mkv"));
    }
}
