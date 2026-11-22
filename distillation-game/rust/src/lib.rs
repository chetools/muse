//! Distillation game simulation engine (Rust, compiled to WebAssembly
//! for play; the Python reference in ../python is the development-time
//! standard it must match — see the parity tests in ../tests).

pub mod api;
pub mod autopilot;
pub mod column;
pub mod feed;
pub mod mixtures;
pub mod overhead;
pub mod plant;
