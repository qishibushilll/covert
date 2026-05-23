from pathlib import Path
import contextlib
import io
import json
import random

from live_bullet_covert import sender

OUT_DIR = Path('figures')
OUT_DIR.mkdir(exist_ok=True)


def generate(mode):
    original = {
        'humanized': sender.HUMANIZED_CARRIER_ENABLED,
        'compact': sender.COMPACT_EMBEDDING_ENABLED,
        'semantic': sender.SEMANTIC_EMBEDDING_ENABLED,
        'replicas': sender.FRAGMENT_REPLICAS,
        'fillers': sender.FILLERS_PER_PAYLOAD,
        'room_file': sender.ROOM_COMMENTS_FILE,
        'cache': sender._ROOM_COMMENT_CACHE,
        'cache_path': sender._ROOM_COMMENT_CACHE_PATH,
    }
    sender.FRAGMENT_REPLICAS = 1
    sender.FILLERS_PER_PAYLOAD = 0
    sender.ROOM_COMMENTS_FILE = '__no_room_comments__.txt'
    sender._ROOM_COMMENT_CACHE = None
    sender._ROOM_COMMENT_CACHE_PATH = None
    if mode == 'legacy':
        sender.HUMANIZED_CARRIER_ENABLED = False
        sender.COMPACT_EMBEDDING_ENABLED = False
        sender.SEMANTIC_EMBEDDING_ENABLED = False
    elif mode == 'humanized':
        sender.HUMANIZED_CARRIER_ENABLED = True
        sender.COMPACT_EMBEDDING_ENABLED = True
        sender.SEMANTIC_EMBEDDING_ENABLED = True
    else:
        raise ValueError(mode)
    try:
        random.seed(20260519)
        core = sender.CovLBCG_Core()
        core.room_comments = []
        with contextlib.redirect_stdout(io.StringIO()):
            payloads = core.gen_payloads('hi#')
        return [p['c'] for p in payloads if p.get('code')]
    finally:
        sender.HUMANIZED_CARRIER_ENABLED = original['humanized']
        sender.COMPACT_EMBEDDING_ENABLED = original['compact']
        sender.SEMANTIC_EMBEDDING_ENABLED = original['semantic']
        sender.FRAGMENT_REPLICAS = original['replicas']
        sender.FILLERS_PER_PAYLOAD = original['fillers']
        sender.ROOM_COMMENTS_FILE = original['room_file']
        sender._ROOM_COMMENT_CACHE = original['cache']
        sender._ROOM_COMMENT_CACHE_PATH = original['cache_path']

legacy = generate('legacy')
humanized = generate('humanized')
print('legacy_count', len(legacy))
print('humanized_count', len(humanized))
for i, (old, new) in enumerate(zip(legacy, humanized), 1):
    print(f'{i:02d} OLD {old}')
    print(f'{i:02d} NEW {new}')

(OUT_DIR / 'danmaku_before_after_samples.json').write_text(
    json.dumps({'legacy_mixed_suffix': legacy, 'humanized_phrase_carrier': humanized}, ensure_ascii=False, indent=2),
    encoding='utf-8'
)
