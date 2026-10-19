//! Minimal JSON parser for the parity-test fixtures.
//!
//! Supports the fixture subset: objects, arrays, numbers, strings (with the
//! common escapes), `true`/`false`/`null`, and insignificant whitespace.
//! Numbers parse via `f64::from_str`, which accepts the shortest-round-trip
//! format the Python generators write.

#[derive(Debug, Clone)]
pub enum Json {
    Null,
    Bool(bool),
    Num(f64),
    Str(String),
    Arr(Vec<Json>),
    Obj(Vec<(String, Json)>),
}

impl Json {
    /// Fetch an object member; panics with the key name when absent.
    pub fn get(&self, key: &str) -> &Json {
        match self {
            Json::Obj(members) => members
                .iter()
                .find(|(k, _)| k == key)
                .map(|(_, v)| v)
                .unwrap_or_else(|| panic!("missing key '{}'", key)),
            _ => panic!("get('{}') on non-object", key),
        }
    }

    /// Borrow as an array; panics on other types.
    pub fn arr(&self) -> &Vec<Json> {
        match self {
            Json::Arr(items) => items,
            _ => panic!("arr() on non-array"),
        }
    }

    /// Read as `f64`; panics on other types.
    pub fn f64(&self) -> f64 {
        match self {
            Json::Num(v) => *v,
            _ => panic!("f64() on non-number"),
        }
    }

    /// Read as `Vec<f64>`; panics on other types.
    pub fn vec_f64(&self) -> Vec<f64> {
        self.arr().iter().map(|v| v.f64()).collect()
    }

    /// Read as a nested `Vec<Vec<f64>>`; panics on other types.
    pub fn mat_f64(&self) -> Vec<Vec<f64>> {
        self.arr().iter().map(|v| v.vec_f64()).collect()
    }

    /// Read an optional `f64` (`null` maps to `None`).
    pub fn opt_f64(&self) -> Option<f64> {
        match self {
            Json::Null => None,
            Json::Num(v) => Some(*v),
            _ => panic!("opt_f64() on non-number/non-null"),
        }
    }
}

struct Parser<'a> {
    b: &'a [u8],
    i: usize,
}

impl<'a> Parser<'a> {
    fn skip_ws(&mut self) {
        while self.i < self.b.len()
            && (self.b[self.i] as char).is_whitespace()
        {
            self.i += 1;
        }
    }

    fn peek(&self) -> Option<u8> {
        self.b.get(self.i).copied()
    }

    fn expect_byte(&mut self, c: u8) -> Result<(), String> {
        if self.peek() == Some(c) {
            self.i += 1;
            Ok(())
        } else {
            Err(format!(
                "expected '{}' at byte {}",
                c as char, self.i
            ))
        }
    }

    fn literal(&mut self, word: &str, v: Json) -> Result<Json, String> {
        if self.b[self.i..].starts_with(word.as_bytes()) {
            self.i += word.len();
            Ok(v)
        } else {
            Err(format!("bad literal at byte {}", self.i))
        }
    }

    fn string(&mut self) -> Result<String, String> {
        self.expect_byte(b'"')?;
        let mut s = String::new();
        loop {
            match self.peek() {
                None => return Err("unterminated string".to_string()),
                Some(b'"') => {
                    self.i += 1;
                    return Ok(s);
                }
                Some(b'\\') => {
                    self.i += 1;
                    match self.peek() {
                        Some(b'"') => s.push('"'),
                        Some(b'\\') => s.push('\\'),
                        Some(b'/') => s.push('/'),
                        Some(b'n') => s.push('\n'),
                        Some(b't') => s.push('\t'),
                        Some(b'r') => s.push('\r'),
                        Some(b'u') => {
                            if self.i + 5 > self.b.len() {
                                return Err("bad \\u escape".to_string());
                            }
                            let hex = std::str::from_utf8(
                                &self.b[self.i + 1..self.i + 5],
                            )
                            .map_err(|_| "bad \\u escape".to_string())?;
                            let cp = u32::from_str_radix(hex, 16)
                                .map_err(|_| "bad \\u escape".to_string())?;
                            s.push(
                                char::from_u32(cp)
                                    .ok_or("bad \\u escape".to_string())?,
                            );
                            self.i += 5;
                            continue;
                        }
                        _ => return Err("bad escape".to_string()),
                    }
                    self.i += 1;
                }
                Some(c) => {
                    s.push(c as char);
                    self.i += 1;
                }
            }
        }
    }

    fn number(&mut self) -> Result<Json, String> {
        let start = self.i;
        if self.peek() == Some(b'-') {
            self.i += 1;
        }
        while matches!(self.peek(), Some(c) if c.is_ascii_digit()) {
            self.i += 1;
        }
        if self.peek() == Some(b'.') {
            self.i += 1;
            while matches!(self.peek(), Some(c) if c.is_ascii_digit()) {
                self.i += 1;
            }
        }
        if matches!(self.peek(), Some(b'e') | Some(b'E')) {
            self.i += 1;
            if matches!(self.peek(), Some(b'+') | Some(b'-')) {
                self.i += 1;
            }
            while matches!(self.peek(), Some(c) if c.is_ascii_digit()) {
                self.i += 1;
            }
        }
        let tok = std::str::from_utf8(&self.b[start..self.i])
            .map_err(|_| "bad number".to_string())?;
        tok.parse::<f64>()
            .map(Json::Num)
            .map_err(|_| format!("bad number '{}'", tok))
    }

    fn array(&mut self) -> Result<Json, String> {
        self.expect_byte(b'[')?;
        let mut items = Vec::new();
        self.skip_ws();
        if self.peek() == Some(b']') {
            self.i += 1;
            return Ok(Json::Arr(items));
        }
        loop {
            self.skip_ws();
            items.push(self.value()?);
            self.skip_ws();
            match self.peek() {
                Some(b',') => {
                    self.i += 1;
                }
                Some(b']') => {
                    self.i += 1;
                    return Ok(Json::Arr(items));
                }
                _ => return Err(format!("bad array at byte {}", self.i)),
            }
        }
    }

    fn object(&mut self) -> Result<Json, String> {
        self.expect_byte(b'{')?;
        let mut members = Vec::new();
        self.skip_ws();
        if self.peek() == Some(b'}') {
            self.i += 1;
            return Ok(Json::Obj(members));
        }
        loop {
            self.skip_ws();
            let key = self.string()?;
            self.skip_ws();
            self.expect_byte(b':')?;
            self.skip_ws();
            let v = self.value()?;
            members.push((key, v));
            self.skip_ws();
            match self.peek() {
                Some(b',') => {
                    self.i += 1;
                }
                Some(b'}') => {
                    self.i += 1;
                    return Ok(Json::Obj(members));
                }
                _ => return Err(format!("bad object at byte {}", self.i)),
            }
        }
    }

    fn value(&mut self) -> Result<Json, String> {
        self.skip_ws();
        match self.peek() {
            Some(b'{') => self.object(),
            Some(b'[') => self.array(),
            Some(b'"') => self.string().map(Json::Str),
            Some(b't') => self.literal("true", Json::Bool(true)),
            Some(b'f') => self.literal("false", Json::Bool(false)),
            Some(b'n') => self.literal("null", Json::Null),
            Some(c) if c == b'-' || c.is_ascii_digit() => self.number(),
            _ => Err(format!("unexpected byte at {}", self.i)),
        }
    }
}

/// Parse a JSON document into [`Json`].
pub fn parse(s: &str) -> Result<Json, String> {
    let mut p = Parser {
        b: s.as_bytes(),
        i: 0,
    };
    p.skip_ws();
    let v = p.value()?;
    p.skip_ws();
    if p.i != p.b.len() {
        return Err("trailing characters".to_string());
    }
    Ok(v)
}

/// Mixed absolute-relative deviation used by the parity tests:
/// `|a - b| / max(1, |a|, |b|)`. The `max(1, ...)` floor keeps the check
/// meaningful for quantities near zero.
pub fn rel_dev(a: f64, b: f64) -> f64 {
    (a - b).abs() / 1.0f64.max(a.abs()).max(b.abs())
}
