"""Generates the game's ambience loops, effects and music with ElevenLabs (sound-generation and music APIs)
and packs them into data/amb.json. The key is read from the ELEVEN environment variable. Results are cached
in ./cache so re-running only fetches what is new. Usage: python3 tools/audio_gen.py REPO"""
import os, sys, json, base64, hashlib, urllib.request
REPO = sys.argv[1]; K = os.environ['ELEVEN']
SFX = {  # name: (prompt, seconds, loop)
    'rain_loop': ('steady heavy rain falling on a city street at night, no thunder, no voices', 10, True),
    'city_night': ('quiet downtown city ambience at night, distant traffic hum, faint wind, no voices', 10, True),
    'bar_room': ('dim neighborhood bar room tone, low murmur of a few people, glasses clinking occasionally, no music', 10, True),
    'moto_loop': ('motorcycle engine running at steady cruising speed, mid-size street bike, seamless', 6, True),
    'moto_start': ('motorcycle engine starting up and revving once', 3, False),
    'thunder': ('distant rolling thunder after a lightning strike', 6, False),
    'thunder2': ('single close thunder crack with long rumble tail', 6, False),
    'door_heavy': ('heavy steel jail door buzzing open then slamming shut', 4, False),
    'whoosh_cut': ('soft low cinematic whoosh transition', 2, False),
    'stinger_low': ('dark low cinematic bass hit with reverb tail, tense', 4, False),
    'trunk_open': ('car trunk unlatching and creaking open', 2, False),
    'phone_buzz': ('mobile phone vibrating on a hard surface, two buzzes', 2, False),
    'tires_wet': ('car tires skidding briefly on a wet road', 2, False),
    'glass_set': ('whisky glass set down on a wooden bar', 1, False),
}
MUSIC = {  # name: (prompt, milliseconds)
    'music_menu': ('Instrumental neo-noir crime drama theme. Slow, moody, rain-soaked Pacific Northwest mill town at night. Clean electric guitar with tremolo, upright bass, brushed drums, low synth pad, sparse piano. Melancholy but determined. No vocals.', 60000),
    'music_tense': ('Instrumental tense underscore for a quiet, threatening conversation in a crime drama. Low pulsing synth bass, sparse piano notes, distant percussion, slow build, no melody on top, leaves room for dialogue. No vocals.', 60000),
    'music_ride': ('Instrumental night ride through an empty rainy city. Mid-tempo, driving bass line, muted electric guitar, steady drums, atmospheric synths, noir mood. No vocals.', 60000),
}
os.makedirs('cache', exist_ok=True)
def call(url, body):
    r = urllib.request.Request(url, data=json.dumps(body).encode(), headers={'xi-api-key': K, 'Content-Type': 'application/json'})
    return urllib.request.urlopen(r, timeout=300).read()
def used():
    return json.load(urllib.request.urlopen(urllib.request.Request('https://api.elevenlabs.io/v1/user/subscription', headers={'xi-api-key': K}), timeout=60)).get('character_count')
out = {}; u0 = used(); only = sys.argv[2].split(',') if len(sys.argv) > 2 else None
for name, (prompt, sec, loop) in SFX.items():
    if only and name not in only and 'sfx' not in only: continue
    f = 'cache/%s_%s.mp3' % (name, hashlib.sha1((prompt + str(sec) + str(loop)).encode()).hexdigest()[:10])
    if not os.path.exists(f):
        try: open(f, 'wb').write(call('https://api.elevenlabs.io/v1/sound-generation?output_format=mp3_22050_32', {'text': prompt, 'duration_seconds': sec, 'prompt_influence': 0.4, 'loop': loop, 'model_id': 'eleven_text_to_sound_v2'}))
        except Exception as e: print('FAIL', name, str(e)[:80], (e.read()[:200] if hasattr(e, 'read') else '')); continue
    out[name] = f
print('sfx', len(out), 'credits used so far', used() - u0)
for name, (prompt, ms) in MUSIC.items():
    if only and name not in only and 'music' not in only: continue
    f = 'cache/%s_%s.mp3' % (name, hashlib.sha1((prompt + str(ms)).encode()).hexdigest()[:10])
    if not os.path.exists(f):
        try: open(f, 'wb').write(call('https://api.elevenlabs.io/v1/music?output_format=mp3_22050_32', {'prompt': prompt, 'music_length_ms': ms}))
        except Exception as e: print('FAIL', name, str(e)[:80], (e.read()[:200] if hasattr(e, 'read') else '')); continue
    out[name] = f
    print(name, 'credits used so far', used() - u0)
pk = {}
for f in os.listdir('cache'):
    n = f.rsplit('_', 1)[0]
    if n in SFX or n in MUSIC: pk[n] = base64.b64encode(open('cache/' + f, 'rb').read()).decode()
json.dump(pk, open(REPO + '/data/amb.json', 'w'), separators=(',', ':'))
print('packed', sorted(pk), os.path.getsize(REPO + '/data/amb.json') // 1024, 'KB; total credits', used() - u0)
