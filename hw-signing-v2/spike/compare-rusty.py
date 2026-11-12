import sys, json
sys.path.insert(0, '../audit-app')
from audit import chromaprint_fingerprint, compare_fingerprints
ref = {}
for f in ['speech-a.wav','speech-a-aac.m4a','speech-b.wav']:
    ref[f] = chromaprint_fingerprint(f)
for name, reff in [('a','speech-a.wav'),('b','speech-b.wav'),('aac','speech-a-aac.m4a')]:
    rusty = json.load(open(f'rusty-{name}.json'))
    c = compare_fingerprints(rusty, ref[reff])
    print(f'rusty-{name} vs ffmpeg {reff}: items rusty={len(rusty)} ref={len(ref[reff])} BER={c["ber"]} similarity={c["similarity"]} offset={c["offset_items"]} compared={c["compared_items"]}')
# cross checks: rusty-a vs ffmpeg-b, rusty-a vs ffmpeg-aac
for a, b in [('a','speech-b.wav'), ('a','speech-a-aac.m4a'), ('aac','speech-a.wav')]:
    ra = json.load(open(f'rusty-{a}.json'))
    c = compare_fingerprints(ra, ref[b])
    print(f'rusty-{a} vs ffmpeg {b}: BER={c["ber"]} similarity={c["similarity"]} offset={c["offset_items"]}')
