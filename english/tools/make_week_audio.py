"""Make the audio for the text of the week (Birkenbihl tab).

Reads week_text from english/data.json, voices every sentence with edge-tts
(en-US-JennyNeural, rate -15%) and writes:
  english/audio/week-NN-sII.mp3  one file per sentence (played in «Слухання», tap on a sentence)
  english/audio/week-NN.json     word timings for highlighting
  english/audio/week-NN.mp3      the whole text with ~1.2 s pauses (background listening)
Then puts "audio" and "timing" into week_text.

    python english/tools/make_week_audio.py           # only if the text changed
    python english/tools/make_week_audio.py --force   # always rebuild

Needs: pip install edge-tts, and ffmpeg on PATH (or in the WinGet folder).
"""
import argparse, asyncio, glob, hashlib, json, os, re, shutil, subprocess, sys, tempfile

VOICE = 'en-US-JennyNeural'
RATE = '-15%'
PAUSE = 1.2
HERE = os.path.dirname(os.path.abspath(__file__))
ENGLISH = os.path.dirname(HERE)
DATA = os.path.join(ENGLISH, 'data.json')
AUDIO_DIR = os.path.join(ENGLISH, 'audio')


def find_ffmpeg():
    p = shutil.which('ffmpeg')
    if p:
        return p
    hits = glob.glob(os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\WinGet\Packages\*FFmpeg*\**\bin\ffmpeg.exe'), recursive=True)
    if hits:
        return hits[0]
    sys.exit('ffmpeg not found')


def sentences(wt):
    if wt.get('lines'):
        return [l['en'].strip() for l in wt['lines'] if l.get('en', '').strip()]
    return [s.strip() for s in re.findall(r'[^.!?]+[.!?]*', wt.get('text', '')) if s.strip()]


async def tts(text, path):
    """Voice one sentence into path; return word timings [[start_ms, end_ms, word], ...]."""
    import edge_tts
    words, audio = [], bytearray()
    async for ch in edge_tts.Communicate(text, VOICE, rate=RATE, boundary='WordBoundary').stream():
        if ch['type'] == 'audio':
            audio += ch['data']
        elif ch['type'] == 'WordBoundary':
            st = round(ch['offset'] / 10000)
            words.append([st, st + round(ch['duration'] / 10000), ch['text']])
    with open(path, 'wb') as f:
        f.write(bytes(audio))
    return words


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args()

    data = json.load(open(DATA, encoding='utf-8'))
    wt = data.get('week_text') or {}
    lines = sentences(wt)
    if not lines:
        print('no text of the week'); return
    week = int(wt.get('week', 0))
    name = 'week-%02d.mp3' % week
    tname = 'week-%02d.json' % week
    out = os.path.join(AUDIO_DIR, name)
    tout = os.path.join(AUDIO_DIR, tname)
    stamp = os.path.join(AUDIO_DIR, 'week-%02d.txt' % week)
    digest = hashlib.sha1(json.dumps(['v2', VOICE, RATE, PAUSE, lines], ensure_ascii=False).encode('utf-8')).hexdigest()

    fresh = all(os.path.exists(x) for x in (out, tout, stamp)) and open(stamp, encoding='utf-8').read().strip() == digest
    if fresh and not a.force:
        print('up to date:', name)
    else:
        os.makedirs(AUDIO_DIR, exist_ok=True)
        ff = find_ffmpeg()
        for old in glob.glob(os.path.join(AUDIO_DIR, 'week-%02d-s*.mp3' % week)):
            os.remove(old)
        timing = {'week': week, 'lines': []}
        parts = []
        for i, s in enumerate(lines):
            fn = 'week-%02d-s%02d.mp3' % (week, i)
            p = os.path.join(AUDIO_DIR, fn)
            timing['lines'].append({'file': 'audio/' + fn, 'words': asyncio.run(tts(s, p))})
            parts.append(p)
        with tempfile.TemporaryDirectory() as tmp:
            sil = os.path.join(tmp, 'pause.mp3')
            subprocess.run([ff, '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'anullsrc=r=24000:cl=mono',
                            '-t', str(PAUSE), '-c:a', 'libmp3lame', '-b:a', '48k', sil], check=True)
            lst = os.path.join(tmp, 'list.txt')
            with open(lst, 'w', encoding='utf-8') as f:
                for i, p in enumerate(parts):
                    f.write("file '%s'\n" % p.replace('\\', '/'))
                    if i < len(parts) - 1:
                        f.write("file '%s'\n" % sil.replace('\\', '/'))
            title = 'Week %d · %s' % (week, wt.get('title', ''))
            subprocess.run([ff, '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst,
                            '-c:a', 'libmp3lame', '-b:a', '64k', '-ar', '24000', '-ac', '1',
                            '-metadata', 'title=' + title, '-metadata', 'artist=English', out], check=True)
        with open(tout, 'w', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(timing, ensure_ascii=False) + '\n')
        with open(stamp, 'w', encoding='utf-8') as f:
            f.write(digest + '\n')
        print('made:', name, '+', len(parts), 'sentence files + timings')

    rel, trel = 'audio/' + name, 'audio/' + tname
    if wt.get('audio') != rel or wt.get('timing') != trel:
        wt['audio'], wt['timing'] = rel, trel
        data['week_text'] = wt
        with open(DATA, 'w', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
        print('data.json: week_text.audio + timing')


if __name__ == '__main__':
    main()
