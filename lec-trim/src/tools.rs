use anyhow::{bail, Context, Result};
use std::path::{Path, PathBuf};
use std::process::Command;

/// Locate an external program: explicit path first, then beside the
/// lec-trim executable (the bundled layout), then on PATH.
pub fn find_tool(name: &str, explicit: &Option<PathBuf>) -> Result<PathBuf> {
    if let Some(p) = explicit {
        if p.exists() {
            return Ok(p.clone());
        }
        bail!("{} not found at {}", name, p.display());
    }
    let exe_name = if cfg!(windows) {
        format!("{name}.exe")
    } else {
        name.to_string()
    };
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            for cand in [dir.join(&exe_name), dir.join("tools").join(&exe_name)] {
                if cand.exists() {
                    return Ok(cand);
                }
            }
        }
    }
    // Fall back to PATH lookup by name.
    Ok(PathBuf::from(name))
}

/// Locate ggml-base.en.bin: explicit path, beside the executable, in a
/// `models` folder beside the executable, or in the OS cache folder.
pub fn find_model(explicit: &Option<PathBuf>) -> Result<PathBuf> {
    const MODEL_FILE: &str = "ggml-base.en.bin";
    if let Some(p) = explicit {
        if p.exists() {
            return Ok(p.clone());
        }
        bail!("model not found at {}", p.display());
    }
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            for cand in [dir.join(MODEL_FILE), dir.join("models").join(MODEL_FILE)] {
                if cand.exists() {
                    return Ok(cand);
                }
            }
        }
    }
    if let Some(home) = std::env::var_os("HOME") {
        let cand = PathBuf::from(home).join(".cache").join("lec-trim").join(MODEL_FILE);
        if cand.exists() {
            return Ok(cand);
        }
    }
    if let Some(local) = std::env::var_os("LOCALAPPDATA") {
        let cand = PathBuf::from(local).join("lec-trim").join(MODEL_FILE);
        if cand.exists() {
            return Ok(cand);
        }
    }
    bail!(
        "{MODEL_FILE} not found. Put it beside lec-trim, in a models folder beside it, \
         or pass --model <path>. The release zip bundles the model."
    )
}

pub fn run_ok(cmd: &mut Command, what: &str) -> Result<std::process::Output> {
    let out = cmd
        .output()
        .with_context(|| format!("failed to start {what}"))?;
    if !out.status.success() {
        bail!(
            "{} failed ({}): {}",
            what,
            out.status,
            String::from_utf8_lossy(&out.stderr).trim()
        );
    }
    Ok(out)
}

pub fn path_str(p: &Path) -> Result<String> {
    p.to_str()
        .map(|s| s.to_string())
        .with_context(|| format!("path is not valid UTF-8: {}", p.display()))
}
