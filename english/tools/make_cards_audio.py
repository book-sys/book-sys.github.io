"""Voice the phrases and examples of the word cards (tab «Слова»).

Single words are played from real US recordings (Wikimedia) by the app itself.
This script voices what has no real recording: multi-word phrases (homework words like
"What do you do?", data.json "cards") and every example sentence — with edge-tts
(en-US-JennyNeural, rate -10%). Files: english/audio/cards/<hash>.mp3 and index.json
{"text in lower case": "audio/cards/<hash>.mp3"}. Only missing files are made.

    python english/tools/make_cards_audio.py
"""
import asyncio, hashlib, json, os, re

VOICE = 'en-US-JennyNeural'
RATE = '-10%'
HERE = os.path.dirname(os.path.abspath(__file__))
ENGLISH = os.path.dirname(HERE)
DATA = os.path.join(ENGLISH, 'data.json')
OUT = os.path.join(ENGLISH, 'audio', 'cards')


def texts(data):
    out = []
    for h in data.get('homework') or []:
        for s in h.get('words') or []:
            p = re.split(r'\s+[—–-]\s+', str(s))
            if len(p) < 2:
                continue
            en = re.sub(r'\s*[/\[][^/\]]+[/\]]\s*$', '', p[0].strip()).strip()
            if re.search(r'\s', en):
                out.append(en)
            ex = ' — '.join(p[2:]).strip()
            if ex:
                out.append(ex)
    for c in data.get('cards') or []:
        if str(c.get('en', '')).strip():
            out.append(str(c['en']).strip())
        if str(c.get('ex', '')).strip():
            out.append(str(c['ex']).strip())
    seen, res = set(), []
    for t in out:
        k = t.lower()
        if k not in seen:
            seen.add(k)
            res.append(t)
    return res


async def tts(text, path):
    import edge_tts
    await edge_tts.Communicate(text, VOICE, rate=RATE).save(path)


def main():
    data = json.load(open(DATA, encoding='utf-8'))
    os.makedirs(OUT, exist_ok=True)
    idx_path = os.path.join(OUT, 'index.json')
    idx = json.load(open(idx_path, encoding='utf-8')) if os.path.exists(idx_path) else {}
    made = 0
    for t in texts(data):
        k = t.lower()
        name = hashlib.sha1((VOICE + RATE + t).encode('utf-8')).hexdigest()[:12] + '.mp3'
        if idx.get(k) == 'audio/cards/' + name and os.path.exists(os.path.join(OUT, name)):
            continue
        asyncio.run(tts(t, os.path.join(OUT, name)))
        idx[k] = 'audio/cards/' + name
        made += 1
    with open(idx_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(idx, ensure_ascii=False, indent=1) + '\n')
    print('cards audio: %d new, %d total' % (made, len(idx)))


if __name__ == '__main__':
    main()
