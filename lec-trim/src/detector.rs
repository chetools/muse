use crate::tools::{path_str, run_ok};
use anyhow::{Context, Result};
use serde::Deserialize;
use std::path::{Path, PathBuf};
use std::process::Command;

/// One recognised word with its time span, in seconds (s), within the
/// audio window that was transcribed.
#[derive(Debug, Clone, PartialEq)]
pub struct Word {
    pub text: String,
    pub start: f64,
    pub end: f64,
    /// Mean token probability assigned by the recogniser, 0 to 1.
    pub prob: f64,
}

/// Normalise a token for phrase matching: lower-case, keep letters,
/// digits and apostrophes only.
pub fn normalise(token: &str) -> String {
    token
        .to_lowercase()
        .chars()
        .filter(|c| c.is_alphanumeric() || *c == '\'')
        .collect()
}

/// Find the first (or, when `last` is set, the last) occurrence of a
/// phrase given as space-separated words. Returns the start time, in
/// seconds (s), of the first word, the end time of the last word, and
/// the mean token probability over the phrase.
pub fn find_phrase(words: &[Word], phrase: &str, last: bool) -> Option<(f64, f64, f64)> {
    let want: Vec<String> = phrase.split_whitespace().map(normalise).collect();
    if want.is_empty() || words.len() < want.len() {
        return None;
    }
    let mut found: Option<(f64, f64, f64)> = None;
    for i in 0..=(words.len() - want.len()) {
        if words[i..i + want.len()].iter().map(|w| w.text.clone()).collect::<Vec<_>>() == want {
            let span = &words[i..i + want.len()];
            let prob = span.iter().map(|w| w.prob).sum::<f64>() / span.len() as f64;
            found = Some((span[0].start, span[span.len() - 1].end, prob));
            if !last {
                break;
            }
        }
    }
    found
}

#[derive(Deserialize)]
struct WhisperJson {
    transcription: Vec<Segment>,
}

#[derive(Deserialize)]
struct Segment {
    tokens: Vec<Token>,
}

#[derive(Deserialize)]
struct Token {
    text: String,
    offsets: Offsets,
    #[serde(default)]
    p: f64,
}

#[derive(Deserialize)]
struct Offsets {
    from: i64,
    to: i64,
}

/// Parse the full JSON written by `whisper-cli -ojf` into words.
/// Offsets in that JSON are in milliseconds (ms) and are converted to
/// seconds (s). The segment-start token `[_BEG_]` is dropped.
pub fn parse_whisper_json(text: &str) -> Result<Vec<Word>> {
    let parsed: WhisperJson = serde_json::from_str(text).context("parsing whisper-cli JSON")?;
    let mut words = Vec::new();
    for seg in parsed.transcription {
        for tok in seg.tokens {
            let t = normalise(&tok.text);
            if t.is_empty() || tok.text.contains("[_") {
                continue;
            }
            words.push(Word {
                text: t,
                start: tok.offsets.from as f64 / 1000.0,
                end: tok.offsets.to as f64 / 1000.0,
                prob: tok.p,
            });
        }
    }
    Ok(words)
}

/// Run whisper-cli on one WAV file and return its words.
pub fn transcribe(
    whisper_cli: &PathBuf,
    model: &Path,
    wav: &Path,
    out_prefix: &Path,
) -> Result<Vec<Word>> {
    run_ok(
        Command::new(whisper_cli).args([
            "-m", &path_str(model)?,
            "-f", &path_str(wav)?,
            "-ojf",
            "-of", &path_str(out_prefix)?,
            "--no-prints",
        ]),
        "whisper-cli",
    )?;
    let json_path = out_prefix.with_extension("json");
    let text = std::fs::read_to_string(&json_path)
        .with_context(|| format!("whisper-cli wrote no JSON at {}", json_path.display()))?;
    parse_whisper_json(&text)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn w(text: &str, start: f64, end: f64) -> Word {
        Word { text: text.into(), start, end, prob: 0.9 }
    }

    #[test]
    fn finds_first_and_last() {
        let words = vec![
            w("start", 1.0, 1.3), w("recording", 1.3, 1.9),
            w("some", 2.0, 2.3), w("teaching", 2.3, 2.9),
            w("stop", 8.0, 8.3), w("recording", 8.3, 8.9),
            w("stop", 9.5, 9.8), w("recording", 9.8, 10.4),
        ];
        let (s, e, _) = find_phrase(&words, "start recording", false).unwrap();
        assert!((s - 1.0).abs() < 1e-9 && (e - 1.9).abs() < 1e-9);
        let (s, _, _) = find_phrase(&words, "stop recording", true).unwrap();
        assert!((s - 9.5).abs() < 1e-9);
        assert!(find_phrase(&words, "begin recording", false).is_none());
    }

    #[test]
    fn normalises_case_and_punctuation() {
        assert_eq!(normalise(" Recording,"), "recording");
        assert_eq!(normalise("STOP."), "stop");
    }

    #[test]
    fn parses_whisper_json() {
        let j = r#"{"transcription":[{"tokens":[
          {"text":"[_BEG_]","offsets":{"from":0,"to":0},"p":1.0},
          {"text":" Start","offsets":{"from":100,"to":400},"p":0.98},
          {"text":" recording","offsets":{"from":400,"to":900},"p":0.97},
          {"text":".","offsets":{"from":900,"to":900},"p":0.5}
        ]}]}"#;
        let words = parse_whisper_json(j).unwrap();
        assert_eq!(words.len(), 2);
        assert_eq!(words[0].text, "start");
        assert!((words[1].end - 0.9).abs() < 1e-9);
    }
}
