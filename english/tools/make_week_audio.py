"""Make the background-listening MP3 for the text of the week.

Reads week_text from english/data.json, voices every sentence with edge-tts
(en-US-JennyNeural, rate -15%), joins them with ~1.2 s pauses and writes
english/audio/week-NN.mp3. Then puts "audio": "audio/week-NN.mp3" into week_text.

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
    import edge_tts
    await edge_tts.Communicate(text, VOICE, rate=RATE).save(path)


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
    out = os.path.join(AUDIO_DIR, name)
    stamp = os.path.join(AUDIO_DIR, 'week-%02d.txt' % week)
    digest = hashlib.sha1(json.dumps([VOICE, RATE, PAUSE, lines], ensure_ascii=False).encode('utf-8')).hexdigest()

    fresh = os.path.exists(out) and os.path.exists(stamp) and open(stamp, encoding='utf-8').read().strip() == digest
    if fresh and not a.force:
        print('up to date:', name)
    else:
        os.makedirs(AUDIO_DIR, exist_ok=True)
        ff = find_ffmpeg()
        with tempfile.TemporaryDirectory() as tmp:
            parts = []
            for i, s in enumerate(lines):
                p = os.path.join(tmp, 's%03d.mp3' % i)
                asyncio.run(tts(s, p))
                parts.append(p)
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
        open(stamp, 'w', encoding='utf-8').write(digest + '\n')
        print('made:', name, '(%d sentences)' % len(lines))

    rel = 'audio/' + name
    if wt.get('audio') != rel:
        wt['audio'] = rel
        data['week_text'] = wt
        with open(DATA, 'w', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
        print('data.json: week_text.audio =', rel)


if __name__ == '__main__':
    main()
