/**
 * Result of one-shot fingerprint: raw u32 array and base64 compressed string.
 */
export class FingerprintFromSamplesResult {
    static __wrap(ptr) {
        ptr = ptr >>> 0;
        const obj = Object.create(FingerprintFromSamplesResult.prototype);
        obj.__wbg_ptr = ptr;
        FingerprintFromSamplesResultFinalization.register(obj, obj.__wbg_ptr, obj);
        return obj;
    }
    __destroy_into_raw() {
        const ptr = this.__wbg_ptr;
        this.__wbg_ptr = 0;
        FingerprintFromSamplesResultFinalization.unregister(this);
        return ptr;
    }
    free() {
        const ptr = this.__destroy_into_raw();
        wasm.__wbg_fingerprintfromsamplesresult_free(ptr, 0);
    }
    /**
     * @returns {string}
     */
    get compressed() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.__wbg_get_fingerprintfromsamplesresult_compressed(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * @returns {Uint32Array}
     */
    get raw() {
        const ret = wasm.__wbg_get_fingerprintfromsamplesresult_raw(this.__wbg_ptr);
        var v1 = getArrayU32FromWasm0(ret[0], ret[1]).slice();
        wasm.__wbindgen_free(ret[0], ret[1] * 4, 4);
        return v1;
    }
    /**
     * @param {string} arg0
     */
    set compressed(arg0) {
        const ptr0 = passStringToWasm0(arg0, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        wasm.__wbg_set_fingerprintfromsamplesresult_compressed(this.__wbg_ptr, ptr0, len0);
    }
    /**
     * @param {Uint32Array} arg0
     */
    set raw(arg0) {
        const ptr0 = passArray32ToWasm0(arg0, wasm.__wbindgen_malloc);
        const len0 = WASM_VECTOR_LEN;
        wasm.__wbg_set_fingerprintfromsamplesresult_raw(this.__wbg_ptr, ptr0, len0);
    }
}
if (Symbol.dispose) FingerprintFromSamplesResult.prototype[Symbol.dispose] = FingerprintFromSamplesResult.prototype.free;

/**
 * Create a new fingerprinter. Uses the default preset (compatible with AcoustID).
 */
export class Fingerprinter {
    __destroy_into_raw() {
        const ptr = this.__wbg_ptr;
        this.__wbg_ptr = 0;
        FingerprinterFinalization.unregister(this);
        return ptr;
    }
    free() {
        const ptr = this.__destroy_into_raw();
        wasm.__wbg_fingerprinter_free(ptr, 0);
    }
    /**
     * Feed interleaved i16 samples (e.g. from decodeAudioData → getChannelData → convert to i16).
     * Pass an Int16Array from JS.
     * @param {Int16Array} samples
     */
    consume(samples) {
        const ptr0 = passArray16ToWasm0(samples, wasm.__wbindgen_malloc);
        const len0 = WASM_VECTOR_LEN;
        wasm.fingerprinter_consume(this.__wbg_ptr, ptr0, len0);
    }
    /**
     * Call when all samples have been fed.
     */
    finish() {
        wasm.fingerprinter_finish(this.__wbg_ptr);
    }
    /**
     * Compressed fingerprint as base64 (AcoustID/fpcalc format). Only valid after finish().
     * @returns {string}
     */
    getCompressedFingerprint() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.fingerprinter_getCompressedFingerprint(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * Raw fingerprint (u32 array). Only valid after finish().
     * @returns {Uint32Array}
     */
    getFingerprint() {
        const ret = wasm.fingerprinter_getFingerprint(this.__wbg_ptr);
        var v1 = getArrayU32FromWasm0(ret[0], ret[1]).slice();
        wasm.__wbindgen_free(ret[0], ret[1] * 4, 4);
        return v1;
    }
    constructor() {
        const ret = wasm.fingerprinter_new();
        if (ret[2]) {
            throw takeFromExternrefTable0(ret[1]);
        }
        this.__wbg_ptr = ret[0] >>> 0;
        FingerprinterFinalization.register(this, this.__wbg_ptr, this);
        return this;
    }
    /**
     * Start fingerprinting. Call with your audio's sample rate (e.g. 44100) and channel count (1 or 2).
     * @param {number} sample_rate
     * @param {number} channels
     */
    start(sample_rate, channels) {
        const ret = wasm.fingerprinter_start(this.__wbg_ptr, sample_rate, channels);
        if (ret[1]) {
            throw takeFromExternrefTable0(ret[0]);
        }
    }
}
if (Symbol.dispose) Fingerprinter.prototype[Symbol.dispose] = Fingerprinter.prototype.free;

/**
 * Result of matching two fingerprints.
 */
export class MatchFingerprintsResult {
    static __wrap(ptr) {
        ptr = ptr >>> 0;
        const obj = Object.create(MatchFingerprintsResult.prototype);
        obj.__wbg_ptr = ptr;
        MatchFingerprintsResultFinalization.register(obj, obj.__wbg_ptr, obj);
        return obj;
    }
    __destroy_into_raw() {
        const ptr = this.__wbg_ptr;
        this.__wbg_ptr = 0;
        MatchFingerprintsResultFinalization.unregister(this);
        return ptr;
    }
    free() {
        const ptr = this.__destroy_into_raw();
        wasm.__wbg_matchfingerprintsresult_free(ptr, 0);
    }
    /**
     * @returns {MatchSegment[]}
     */
    get segments() {
        const ret = wasm.__wbg_get_matchfingerprintsresult_segments(this.__wbg_ptr);
        var v1 = getArrayJsValueFromWasm0(ret[0], ret[1]).slice();
        wasm.__wbindgen_free(ret[0], ret[1] * 4, 4);
        return v1;
    }
    /**
     * @param {MatchSegment[]} arg0
     */
    set segments(arg0) {
        const ptr0 = passArrayJsValueToWasm0(arg0, wasm.__wbindgen_malloc);
        const len0 = WASM_VECTOR_LEN;
        wasm.__wbg_set_matchfingerprintsresult_segments(this.__wbg_ptr, ptr0, len0);
    }
}
if (Symbol.dispose) MatchFingerprintsResult.prototype[Symbol.dispose] = MatchFingerprintsResult.prototype.free;

/**
 * A matched segment between two fingerprints.
 */
export class MatchSegment {
    static __wrap(ptr) {
        ptr = ptr >>> 0;
        const obj = Object.create(MatchSegment.prototype);
        obj.__wbg_ptr = ptr;
        MatchSegmentFinalization.register(obj, obj.__wbg_ptr, obj);
        return obj;
    }
    static __unwrap(jsValue) {
        if (!(jsValue instanceof MatchSegment)) {
            return 0;
        }
        return jsValue.__destroy_into_raw();
    }
    __destroy_into_raw() {
        const ptr = this.__wbg_ptr;
        this.__wbg_ptr = 0;
        MatchSegmentFinalization.unregister(this);
        return ptr;
    }
    free() {
        const ptr = this.__destroy_into_raw();
        wasm.__wbg_matchsegment_free(ptr, 0);
    }
    /**
     * @returns {number}
     */
    get duration() {
        const ret = wasm.matchsegment_duration(this.__wbg_ptr);
        return ret;
    }
    /**
     * @returns {number}
     */
    get end1() {
        const ret = wasm.matchsegment_end1(this.__wbg_ptr);
        return ret;
    }
    /**
     * @returns {number}
     */
    get end2() {
        const ret = wasm.matchsegment_end2(this.__wbg_ptr);
        return ret;
    }
    /**
     * @returns {number}
     */
    get score() {
        const ret = wasm.matchsegment_score(this.__wbg_ptr);
        return ret;
    }
    /**
     * @returns {number}
     */
    get start1() {
        const ret = wasm.matchsegment_start1(this.__wbg_ptr);
        return ret;
    }
    /**
     * @returns {number}
     */
    get start2() {
        const ret = wasm.matchsegment_start2(this.__wbg_ptr);
        return ret;
    }
}
if (Symbol.dispose) MatchSegment.prototype[Symbol.dispose] = MatchSegment.prototype.free;

/**
 * One-shot: compute fingerprint from interleaved i16 samples.
 * @param {number} sample_rate
 * @param {number} channels
 * @param {Int16Array} samples
 * @returns {FingerprintFromSamplesResult}
 */
export function fingerprintFromSamples(sample_rate, channels, samples) {
    const ptr0 = passArray16ToWasm0(samples, wasm.__wbindgen_malloc);
    const len0 = WASM_VECTOR_LEN;
    const ret = wasm.fingerprintFromSamples(sample_rate, channels, ptr0, len0);
    if (ret[2]) {
        throw takeFromExternrefTable0(ret[1]);
    }
    return FingerprintFromSamplesResult.__wrap(ret[0]);
}

/**
 * Match two raw fingerprints (u32 arrays). Returns segments of similar audio.
 * @param {Uint32Array} raw1
 * @param {Uint32Array} raw2
 * @returns {MatchFingerprintsResult}
 */
export function matchFingerprints(raw1, raw2) {
    const ptr0 = passArray32ToWasm0(raw1, wasm.__wbindgen_malloc);
    const len0 = WASM_VECTOR_LEN;
    const ptr1 = passArray32ToWasm0(raw2, wasm.__wbindgen_malloc);
    const len1 = WASM_VECTOR_LEN;
    const ret = wasm.matchFingerprints(ptr0, len0, ptr1, len1);
    if (ret[2]) {
        throw takeFromExternrefTable0(ret[1]);
    }
    return MatchFingerprintsResult.__wrap(ret[0]);
}
export function __wbg_Error_83742b46f01ce22d(arg0, arg1) {
    const ret = Error(getStringFromWasm0(arg0, arg1));
    return ret;
}
export function __wbg___wbindgen_throw_6ddd609b62940d55(arg0, arg1) {
    throw new Error(getStringFromWasm0(arg0, arg1));
}
export function __wbg_matchsegment_new(arg0) {
    const ret = MatchSegment.__wrap(arg0);
    return ret;
}
export function __wbg_matchsegment_unwrap(arg0) {
    const ret = MatchSegment.__unwrap(arg0);
    return ret;
}
export function __wbindgen_init_externref_table() {
    const table = wasm.__wbindgen_externrefs;
    const offset = table.grow(4);
    table.set(0, undefined);
    table.set(offset + 0, undefined);
    table.set(offset + 1, null);
    table.set(offset + 2, true);
    table.set(offset + 3, false);
}
const FingerprintFromSamplesResultFinalization = (typeof FinalizationRegistry === 'undefined')
    ? { register: () => {}, unregister: () => {} }
    : new FinalizationRegistry(ptr => wasm.__wbg_fingerprintfromsamplesresult_free(ptr >>> 0, 1));
const MatchFingerprintsResultFinalization = (typeof FinalizationRegistry === 'undefined')
    ? { register: () => {}, unregister: () => {} }
    : new FinalizationRegistry(ptr => wasm.__wbg_matchfingerprintsresult_free(ptr >>> 0, 1));
const MatchSegmentFinalization = (typeof FinalizationRegistry === 'undefined')
    ? { register: () => {}, unregister: () => {} }
    : new FinalizationRegistry(ptr => wasm.__wbg_matchsegment_free(ptr >>> 0, 1));
const FingerprinterFinalization = (typeof FinalizationRegistry === 'undefined')
    ? { register: () => {}, unregister: () => {} }
    : new FinalizationRegistry(ptr => wasm.__wbg_fingerprinter_free(ptr >>> 0, 1));

function addToExternrefTable0(obj) {
    const idx = wasm.__externref_table_alloc();
    wasm.__wbindgen_externrefs.set(idx, obj);
    return idx;
}

function getArrayJsValueFromWasm0(ptr, len) {
    ptr = ptr >>> 0;
    const mem = getDataViewMemory0();
    const result = [];
    for (let i = ptr; i < ptr + 4 * len; i += 4) {
        result.push(wasm.__wbindgen_externrefs.get(mem.getUint32(i, true)));
    }
    wasm.__externref_drop_slice(ptr, len);
    return result;
}

function getArrayU32FromWasm0(ptr, len) {
    ptr = ptr >>> 0;
    return getUint32ArrayMemory0().subarray(ptr / 4, ptr / 4 + len);
}

let cachedDataViewMemory0 = null;
function getDataViewMemory0() {
    if (cachedDataViewMemory0 === null || cachedDataViewMemory0.buffer.detached === true || (cachedDataViewMemory0.buffer.detached === undefined && cachedDataViewMemory0.buffer !== wasm.memory.buffer)) {
        cachedDataViewMemory0 = new DataView(wasm.memory.buffer);
    }
    return cachedDataViewMemory0;
}

function getStringFromWasm0(ptr, len) {
    ptr = ptr >>> 0;
    return decodeText(ptr, len);
}

let cachedUint16ArrayMemory0 = null;
function getUint16ArrayMemory0() {
    if (cachedUint16ArrayMemory0 === null || cachedUint16ArrayMemory0.byteLength === 0) {
        cachedUint16ArrayMemory0 = new Uint16Array(wasm.memory.buffer);
    }
    return cachedUint16ArrayMemory0;
}

let cachedUint32ArrayMemory0 = null;
function getUint32ArrayMemory0() {
    if (cachedUint32ArrayMemory0 === null || cachedUint32ArrayMemory0.byteLength === 0) {
        cachedUint32ArrayMemory0 = new Uint32Array(wasm.memory.buffer);
    }
    return cachedUint32ArrayMemory0;
}

let cachedUint8ArrayMemory0 = null;
function getUint8ArrayMemory0() {
    if (cachedUint8ArrayMemory0 === null || cachedUint8ArrayMemory0.byteLength === 0) {
        cachedUint8ArrayMemory0 = new Uint8Array(wasm.memory.buffer);
    }
    return cachedUint8ArrayMemory0;
}

function passArray16ToWasm0(arg, malloc) {
    const ptr = malloc(arg.length * 2, 2) >>> 0;
    getUint16ArrayMemory0().set(arg, ptr / 2);
    WASM_VECTOR_LEN = arg.length;
    return ptr;
}

function passArray32ToWasm0(arg, malloc) {
    const ptr = malloc(arg.length * 4, 4) >>> 0;
    getUint32ArrayMemory0().set(arg, ptr / 4);
    WASM_VECTOR_LEN = arg.length;
    return ptr;
}

function passArrayJsValueToWasm0(array, malloc) {
    const ptr = malloc(array.length * 4, 4) >>> 0;
    for (let i = 0; i < array.length; i++) {
        const add = addToExternrefTable0(array[i]);
        getDataViewMemory0().setUint32(ptr + 4 * i, add, true);
    }
    WASM_VECTOR_LEN = array.length;
    return ptr;
}

function passStringToWasm0(arg, malloc, realloc) {
    if (realloc === undefined) {
        const buf = cachedTextEncoder.encode(arg);
        const ptr = malloc(buf.length, 1) >>> 0;
        getUint8ArrayMemory0().subarray(ptr, ptr + buf.length).set(buf);
        WASM_VECTOR_LEN = buf.length;
        return ptr;
    }

    let len = arg.length;
    let ptr = malloc(len, 1) >>> 0;

    const mem = getUint8ArrayMemory0();

    let offset = 0;

    for (; offset < len; offset++) {
        const code = arg.charCodeAt(offset);
        if (code > 0x7F) break;
        mem[ptr + offset] = code;
    }
    if (offset !== len) {
        if (offset !== 0) {
            arg = arg.slice(offset);
        }
        ptr = realloc(ptr, len, len = offset + arg.length * 3, 1) >>> 0;
        const view = getUint8ArrayMemory0().subarray(ptr + offset, ptr + len);
        const ret = cachedTextEncoder.encodeInto(arg, view);

        offset += ret.written;
        ptr = realloc(ptr, len, offset, 1) >>> 0;
    }

    WASM_VECTOR_LEN = offset;
    return ptr;
}

function takeFromExternrefTable0(idx) {
    const value = wasm.__wbindgen_externrefs.get(idx);
    wasm.__externref_table_dealloc(idx);
    return value;
}

let cachedTextDecoder = new TextDecoder('utf-8', { ignoreBOM: true, fatal: true });
cachedTextDecoder.decode();
const MAX_SAFARI_DECODE_BYTES = 2146435072;
let numBytesDecoded = 0;
function decodeText(ptr, len) {
    numBytesDecoded += len;
    if (numBytesDecoded >= MAX_SAFARI_DECODE_BYTES) {
        cachedTextDecoder = new TextDecoder('utf-8', { ignoreBOM: true, fatal: true });
        cachedTextDecoder.decode();
        numBytesDecoded = len;
    }
    return cachedTextDecoder.decode(getUint8ArrayMemory0().subarray(ptr, ptr + len));
}

const cachedTextEncoder = new TextEncoder();

if (!('encodeInto' in cachedTextEncoder)) {
    cachedTextEncoder.encodeInto = function (arg, view) {
        const buf = cachedTextEncoder.encode(arg);
        view.set(buf);
        return {
            read: arg.length,
            written: buf.length
        };
    };
}

let WASM_VECTOR_LEN = 0;


let wasm;
export function __wbg_set_wasm(val) {
    wasm = val;
}
