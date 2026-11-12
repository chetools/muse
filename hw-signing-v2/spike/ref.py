import sys
sys.path.insert(0, '../audit-app')
from audit import chromaprint_fingerprint, compare_fingerprints
import json
files = ['speech-a.wav','speech-a-aac.m4a','speech-a-opus.opus','speech-b.wav','speech-a-slow.wav','speech-a-fast.wav']
fps = {}
for f in files:
    fp = chromaprint_fingerprint(f)
    fps[f] = fp
    print(f, 'items:', len(fp) if fp else None)
def cmp(a, b):
    c = compare_fingerprints(fps[a], fps[b])
    print(f'{a} vs {b}: BER={c["ber"]} similarity={c["similarity"]} offset_items={c["offset_items"]} compared={c["compared_items"]} thirds={c["thirds"]}')
cmp('speech-a.wav','speech-a.wav')
cmp('speech-a.wav','speech-a-aac.m4a')
cmp('speech-a.wav','speech-a-opus.opus')
cmp('speech-a.wav','speech-b.wav')
cmp('speech-a.wav','speech-a-slow.wav')
cmp('speech-a.wav','speech-a-fast.wav')
