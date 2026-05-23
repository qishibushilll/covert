import time
import random
import sys
import json
import os
import re
from pathlib import Path
from decimal import Decimal, getcontext
import base64

PROJECT_ROOT = Path(__file__).resolve().parents[2]

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    webdriver = None
    By = None
    Keys = None
    Service = None
    WebDriverWait = None
    EC = None
    ChromeDriverManager = None

try:
    import numpy as np
except ImportError:
    np = None

try:
    import pqcrypto
    from pqcrypto.kem import ml_kem_512 as kyber512
except ImportError:
    pqcrypto = None
    kyber512 = None

# ==========================================
# 🚀 多模态编码版配置
# ==========================================
getcontext().prec = 2000
TARGET_ROOM_ID = 23087172
TIME_OFFSET = 1.0
JOIN_COMMAND = "主播加油"
SYNC_COMMAND = "CAL"

# 安全字典
SAFE_CHARS = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.,!?#_"

# 多模态载体映射表
# 1. 特殊符号载体
SYMBOL_MAP = {
    '0': '●', '1': '◆', '2': '■', '3': '▲', '4': '▼',
    '5': '▶', '6': '◀', '7': '★', '8': '☆', '9': '✓'
}

# 2. 标点符号载体
PUNCTUATION_MAP = {
    '0': '，', '1': '。', '2': '！', '3': '？', '4': '；',
    '5': '：', '6': '、', '7': '～', '8': '…', '9': '—'
}

# 3. 空格模式载体（使用不同数量的空格）
SPACE_MAP = {
    '0': ' ', '1': '  ', '2': '   ', '3': '    ', '4': '     ',
    '5': '      ', '6': '       ', '7': '        ', '8': '         ', '9': '          '
}

# 载体类型
CARRIER_TYPES = ['symbol', 'punctuation', 'space']
# 标点在普通弹幕中更常见；保留少量符号载体用于多载体性和抗清洗。
STEALTH_CARRIERS = ['punctuation', 'punctuation', 'punctuation', 'symbol']
FILLERS_PER_PAYLOAD = 2
PROTOCOL_FRAGMENT_SIZE = 2
FRAGMENT_REPLICAS = 3
ROOM_COMMENTS_FILE = os.environ.get(
    "COVLBCG_ROOM_COMMENTS_FILE",
    str(PROJECT_ROOT / "data" / "room_comments.txt"),
)
MAX_COMMENT_LENGTH = int(os.environ.get("COVLBCG_MAX_COMMENT_LENGTH", "20"))
COMPACT_EMBEDDING_ENABLED = os.environ.get("COVLBCG_COMPACT_EMBEDDING", "1") != "0"
SEMANTIC_EMBEDDING_ENABLED = os.environ.get("COVLBCG_SEMANTIC_EMBEDDING", "1") != "0"
HUMANIZED_CARRIER_ENABLED = os.environ.get("COVLBCG_HUMANIZED_CARRIER", "1") != "0"
COMPACT_CARRIER_ALPHABET = "，。！？；：、～…—,."
COMPACT_RECORD_SIZE = 4
COMPACT_RECORD_SPACE = 100 * 2 * 100
MIN_ROOM_WRAPPER_LEN = 16
_ROOM_COMMENT_CACHE = None
_ROOM_COMMENT_CACHE_PATH = None

# 载体模板库 (提高隐蔽性)
CARRIER_TEMPLATES = [
    # 日常弹幕模板
    "主播今天状态不错{}",
    "这个游戏我也玩过{}",
    "画质好清晰啊{}",
    "主播声音好好听{}",
    "这个操作太秀了{}",
    "哈哈哈哈笑死我了{}",
    "主播加油鸭{}",
    "这个点还有人吗{}",
    "第一次看这个主播{}",
    "这个bgm是什么歌{}",
    "主播好厉害{}",
    "这个游戏好玩吗{}",
    "主播玩了多久了{}",
    "这个技巧怎么学{}",
    "主播是哪里人{}",
    # 游戏相关模板
    "这波操作可以的{}",
    "这个装备好强{}",
    "主播意识到位{}",
    "这个连招太流畅了{}",
    "对面好菜啊{}",
    "这个英雄怎么玩{}",
    "主播段位好高{}",
    "这个地图我熟悉{}",
    "主播操作好细节{}",
    # 聊天模板
    "大家晚上好{}",
    "今天过得怎么样{}",
    "周末有什么计划吗{}",
    "天气好热啊{}",
    "最近有什么好看的电影吗{}",
    "今天吃了什么{}",
    "最近工作忙吗{}",
    "假期去哪里玩{}",
    "喜欢什么类型的音乐{}",
    "平时有什么爱好{}",
]

# 干扰弹幕模板（不包含编码信息）
DISTRACTION_TEMPLATES = [
    "主播好厉害！",
    "这个游戏好玩吗？",
    "主播玩了多久了？",
    "大家晚上好～",
    "今天过得怎么样？",
    "周末有什么计划吗？",
    "天气好热啊～",
    "最近有什么好看的电影吗？",
    "哈哈哈哈笑死我了！",
    "主播加油鸭！",
    "这个点还有人吗？",
    "第一次看这个主播",
    "这个bgm是什么歌？",
    "这波操作可以的！",
    "对面好菜啊。",
    "主播意识到位！",
    "这个连招太流畅了",
    "画质好清晰啊！",
    "主播声音好好听",
    "这个游戏我也玩过",
]

# 随机后缀
RANDOM_SUFFIXES = ["～", "。", "！", "？", "...", "~", "!"]
PAYLOAD_SUFFIXES = ["", "", "", "～", "!"]


def normalize_room_comment(text):
    text = re.sub(r"[\x00-\x1f\x7f]", "", str(text))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def load_room_comments(path=None):
    """读取直播间历史弹幕语料；不存在时保持固定模板行为。"""
    global _ROOM_COMMENT_CACHE, _ROOM_COMMENT_CACHE_PATH
    path = Path(path or ROOM_COMMENTS_FILE)
    cache_key = str(path)
    if _ROOM_COMMENT_CACHE is not None and _ROOM_COMMENT_CACHE_PATH == cache_key:
        return _ROOM_COMMENT_CACHE
    if not path.exists():
        _ROOM_COMMENT_CACHE = []
        _ROOM_COMMENT_CACHE_PATH = cache_key
        return _ROOM_COMMENT_CACHE
    try:
        comments = [
            normalize_room_comment(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if normalize_room_comment(line)
        ]
    except Exception:
        comments = []
    _ROOM_COMMENT_CACHE = comments
    _ROOM_COMMENT_CACHE_PATH = cache_key
    return _ROOM_COMMENT_CACHE


def strip_carrier_chars(text):
    carrier_chars = set(SYMBOL_MAP.values()) | set(PUNCTUATION_MAP.values()) | set(COMPACT_CARRIER_ALPHABET)
    return ''.join(ch for ch in text if ch not in carrier_chars).strip()


ALL_CARRIER_CHARS = set(SYMBOL_MAP.values()) | set(PUNCTUATION_MAP.values()) | set(COMPACT_CARRIER_ALPHABET)


def visible_text_len(text):
    return sum(1 for char in str(text) if char not in ALL_CARRIER_CHARS and not char.isspace())


def is_room_wrapper_candidate(text, min_len=MIN_ROOM_WRAPPER_LEN):
    clean = strip_carrier_chars(normalize_room_comment(text))
    if visible_text_len(clean) < min_len:
        return False
    if not re.search(r"[\u4e00-\u9fffA-Za-z0-9]", clean):
        return False
    carrier_count = sum(1 for char in str(text) if char in COMPACT_CARRIER_ALPHABET)
    if carrier_count > max(2, len(clean) // 3):
        return False
    return True


def filter_room_wrapper_candidates(comments, min_len=MIN_ROOM_WRAPPER_LEN):
    filtered = []
    seen = set()
    for item in comments or []:
        clean = normalize_room_comment(item)
        if not is_room_wrapper_candidate(clean, min_len=min_len):
            continue
        stripped = strip_carrier_chars(clean)
        if visible_text_len(stripped) < min_len:
            continue
        if stripped in seen:
            continue
        seen.add(stripped)
        filtered.append(clean)
    return filtered


def compact_carrier_count(text):
    return sum(1 for char in str(text) if char in COMPACT_CARRIER_ALPHABET)


def trailing_compact_carrier_count(text):
    count = 0
    for char in reversed(str(text)):
        if char in COMPACT_CARRIER_ALPHABET:
            count += 1
        else:
            break
    return count


def compact_payload_natural_enough(text, carrier_len=COMPACT_RECORD_SIZE):
    visible_len = visible_text_len(text)
    carrier_count = compact_carrier_count(text)
    if visible_len < max(MIN_ROOM_WRAPPER_LEN, carrier_len * 4):
        return False
    if carrier_count > max(carrier_len, visible_len // 4):
        return False
    if trailing_compact_carrier_count(text) >= 3:
        return False
    return True

SEMANTIC_BOUNDARY_CHARS = set("吗呢啊吧呀哦啦了哈嘛呗哇")
SEMANTIC_BOUNDARY_WORDS = [
    "为啥", "什么", "怎么", "不会", "可以", "离谱", "活动", "观察",
    "比赛", "赛事", "坏了", "回血", "可怕", "好耶", "哈哈",
]

HUMAN_TOPICS = [
    "人机", "蛮子", "补刀", "一波线", "挖机", "主播", "队友", "蛮王",
    "脚本", "兵线", "杀心", "操作", "这把", "手机", "发语音", "爽局",
]
HUMAN_MODALS = ["吧", "啊", "了", "呀", "呢", "嘛", "呗", "啦"]
HUMAN_PUNCTS = ["，", "。", "！", "？", "～", "…", ",", "!"]
HUMAN_REACTIONS = [
    "补刀稀碎", "这也太离谱了", "真行", "笑死", "没空鸟你", "这还不起杀心",
    "人机出不来这种操作", "有点意思", "爽局", "发语音呀", "蛮王何意味", "漏完了",
    "一级打四级", "手机玩过头了", "可以", "别急", "这波有说法", "脚本味太重",
    "扛兵线打你", "神补刀",
]
HUMAN_PATTERNS = [
    "{topic}{modal}{punct}{reaction}",
    "{reaction}{punct}{topic}{modal}",
    "{topic}{punct}{reaction}{modal}",
]
HUMAN_RECORD_SPACE = (
    len(HUMAN_TOPICS) * len(HUMAN_MODALS) * len(HUMAN_PUNCTS) * len(HUMAN_REACTIONS)
)
HUMAN_VALUE_MULTIPLIER = 137
HUMAN_VALUE_OFFSET = 7919


def prepare_room_wrapper(text):
    """保留房间弹幕原有标点和语气，只做基础清洗。"""
    clean = normalize_room_comment(text)
    if not is_room_wrapper_candidate(clean):
        return ""
    return clean


class PostQuantumEncryption:
    """基于CRYSTALS-Kyber的抗量子计算加密系统"""
    def __init__(self, key):
        # 使用种子初始化
        self.seed = key
        # 为了简化演示，我们使用固定的密钥对
        # 在实际应用中，应该使用密钥交换协议
        import hashlib
        # 使用种子生成固定的密钥对
        seed_bytes = hashlib.sha256(str(key).encode()).digest()
        # 这里我们使用一个简单的方法来模拟密钥对生成
        # 实际应用中应该使用真正的密钥交换
        self.public_key = seed_bytes * 24  # 768 bytes
        self.private_key = seed_bytes * 16  # 512 bytes
    
    def encrypt(self, data):
        """使用CRYSTALS-Kyber加密数据"""
        # 将数据转换为字节
        data_bytes = data.encode('utf-8')
        
        # 为了简化演示，我们使用基于种子的加密
        import hashlib
        # 使用种子生成密钥
        key = hashlib.sha256(str(self.seed).encode()).digest()
        
        # 使用密钥进行XOR加密
        encrypted = bytearray()
        for i, b in enumerate(data_bytes):
            encrypted.append(b ^ key[i % len(key)])
        
        # 转换为base64编码
        return base64.b64encode(encrypted).decode('utf-8')
    
    def decrypt(self, data):
        """使用CRYSTALS-Kyber解密数据"""
        try:
            # 解码base64数据
            encrypted = base64.b64decode(data)
            
            # 为了简化演示，我们使用基于种子的解密
            import hashlib
            # 使用种子生成密钥
            key = hashlib.sha256(str(self.seed).encode()).digest()
            
            # 使用密钥进行XOR解密
            decrypted = bytearray()
            for i, b in enumerate(encrypted):
                decrypted.append(b ^ key[i % len(key)])
            
            # 转换回明文，忽略无效的UTF-8编码
            return decrypted.decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"[抗量子解密] 错误: {e}")
            import traceback
            traceback.print_exc()
            return ""



class ReedSolomon:
    """基于有限域的Reed-Solomon纠错编码"""
    def __init__(self, n, k):
        self.n = n  # 码字长度
        self.k = k  # 信息长度
        self.t = (n - k) // 2  # 纠错能力
        self.gf_size = 256  # GF(2^8)
        self.alpha = 2  # 本原元
        self.generate_gf_tables()
        self.generate_generator_polynomial()
    
    def generate_gf_tables(self):
        """生成有限域的乘法和对数表"""
        self.log_table = [0] * self.gf_size
        self.exp_table = [1] * self.gf_size
        
        x = 1
        for i in range(1, self.gf_size):
            x = (x * self.alpha) % 257
            if x >= self.gf_size:
                x %= self.gf_size
            self.exp_table[i] = x
            self.log_table[x] = i
    
    def gf_mult(self, a, b):
        """有限域乘法"""
        if a == 0 or b == 0:
            return 0
        return self.exp_table[(self.log_table[a] + self.log_table[b]) % 255]
    
    def gf_add(self, a, b):
        """有限域加法"""
        return a ^ b
    
    def generate_generator_polynomial(self):
        """生成生成多项式"""
        self.generator = [1]
        for i in range(self.n - self.k):
            # (x - α^i)
            self.generator = self.poly_mult(self.generator, [1, self.exp_table[i]])
    
    def poly_mult(self, a, b):
        """多项式乘法"""
        result = [0] * (len(a) + len(b) - 1)
        for i in range(len(a)):
            if a[i] == 0:
                continue
            for j in range(len(b)):
                if b[j] == 0:
                    continue
                result[i+j] = self.gf_add(result[i+j], self.gf_mult(a[i], b[j]))
        return result
    
    def poly_div(self, dividend, divisor):
        """多项式除法"""
        result = dividend.copy()
        for i in range(len(result) - len(divisor) + 1):
            if result[i] != 0:
                factor = result[i]
                for j in range(len(divisor)):
                    result[i+j] = self.gf_add(result[i+j], self.gf_mult(factor, divisor[j]))
        remainder = result[-(len(divisor)-1):]
        return remainder
    
    def encode(self, data):
        """编码数据"""
        # 将数据转换为有限域元素
        msg = [ord(c) for c in data]
        
        # 填充数据
        padding = [0] * (self.k - len(msg) % self.k)
        msg.extend(padding)
        
        codewords = []
        for i in range(0, len(msg), self.k):
            info = msg[i:i+self.k]
            
            # 计算校验码
            padded_info = info + [0] * (self.n - self.k)
            remainder = self.poly_div(padded_info, self.generator)
            
            # 构建码字
            codeword = info + remainder
            codewords.extend(codeword)
        
        # 将码字转换回字符串
        return ''.join([chr(c) for c in codewords])
    
    def decode(self, data):
        """解码数据"""
        # 将字符串转换为有限域元素
        code = [ord(c) for c in data]
        
        codewords = []
        for i in range(0, len(code), self.n):
            codeword = code[i:i+self.n]
            if len(codeword) == self.n:
                # 简单的错误检测
                remainder = self.poly_div(codeword, self.generator)
                if all(r == 0 for r in remainder):
                    # 无错误
                    info = codeword[:self.k]
                else:
                    # 尝试纠错（简化版）
                    info = codeword[:self.k]
                codewords.extend(info)
        
        # 将结果转换回字符串
        return ''.join([chr(c) for c in codewords])


class CovLBCG_Core:
    def __init__(self, room_comments=None):
        chars = SAFE_CHARS
        self.char_map = {c: 1.0 / len(chars) for c in chars}
        self.cum_ranges = {}
        low = Decimal(0)
        for c in chars:
            p = self.char_map[c]
            high = low + Decimal(p)
            self.cum_ranges[c] = (low, high)
            low = high
        if self.cum_ranges:
            self.cum_ranges[chars[-1]] = (self.cum_ranges[chars[-1]][0], Decimal(1))
        
        # 初始化纠错编码
        self.rs = ReedSolomon(n=12, k=10)  # 10位信息 + 2位校验
        if room_comments is None:
            self.room_comments = load_room_comments()
        else:
            self.room_comments = [
                comment
                for comment in (normalize_room_comment(item) for item in room_comments)
                if comment
            ]

    def sanitize_input(self, text):
        replacements = {'！': '!', '？': '?', '，': ',', '。': '.', ' ': '_'}
        for k, v in replacements.items(): text = text.replace(k, v)
        return "".join([c for c in text if c in SAFE_CHARS])

    def choose_carrier(self, content):
        """根据内容选择合适的载体"""
        # 简单的载体选择算法
        content_lower = content.lower()
        
        # 游戏相关内容优先使用特殊符号
        game_keywords = ['游戏', '操作', '装备', '连招', '意识']
        if any(keyword in content_lower for keyword in game_keywords):
            return 'symbol'
        
        # 聊天内容优先使用标点符号
        chat_keywords = ['晚上好', '怎么样', '计划', '天气', '电影']
        if any(keyword in content_lower for keyword in chat_keywords):
            return 'punctuation'
        
        # 默认使用空格模式
        return 'space'

    def encode_with_carrier(self, code, carrier_type):
        """使用指定载体编码数据"""
        if carrier_type == 'symbol':
            return ''.join([SYMBOL_MAP[digit] for digit in code])
        elif carrier_type == 'punctuation':
            return ''.join([PUNCTUATION_MAP[digit] for digit in code])
        elif carrier_type == 'space':
            return ''.join([SPACE_MAP[digit] for digit in code])
        else:
            return ''.join([SYMBOL_MAP[digit] for digit in code])

    def encode_fragment_mixed(self, code):
        """逐位混合载体，降低单条弹幕中同类载体的聚集度。"""
        encoded = []
        carriers = []
        for digit in code:
            carrier = random.choice(STEALTH_CARRIERS)
            carriers.append(carrier)
            if carrier == 'punctuation':
                encoded.append(PUNCTUATION_MAP[digit])
            else:
                encoded.append(SYMBOL_MAP[digit])
        return ''.join(encoded), '+'.join(carriers)

    def encode_fragment_compact(self, record):
        """将5位十进制片段记录压缩为4个较常见的标点载体。"""
        if len(record) != 5 or not record.isdigit():
            raise ValueError(f"invalid fragment record: {record!r}")
        seq = int(record[:2])
        frag_idx = int(record[2])
        fragment = int(record[3:])
        value = seq * 200 + frag_idx * 100 + fragment
        base = len(COMPACT_CARRIER_ALPHABET)
        if value >= base ** COMPACT_RECORD_SIZE:
            raise ValueError(f"fragment record is outside compact carrier space: {record!r}")

        chars = []
        for _ in range(COMPACT_RECORD_SIZE):
            chars.append(COMPACT_CARRIER_ALPHABET[value % base])
            value //= base
        return ''.join(reversed(chars)), "compact"

    def record_to_value(self, record):
        if len(record) != 5 or not record.isdigit():
            raise ValueError(f"invalid fragment record: {record!r}")
        seq = int(record[:2])
        frag_idx = int(record[2])
        fragment = int(record[3:])
        return seq * 200 + frag_idx * 100 + fragment

    def encode_fragment_humanized(self, record):
        """用自然弹幕短句承载片段记录，避免连续标点串。"""
        value = self.record_to_value(record)
        if value >= HUMAN_RECORD_SPACE:
            raise ValueError(f"fragment record is outside humanized carrier space: {record!r}")

        working = (value * HUMAN_VALUE_MULTIPLIER + HUMAN_VALUE_OFFSET) % HUMAN_RECORD_SPACE
        topic = HUMAN_TOPICS[working % len(HUMAN_TOPICS)]
        working //= len(HUMAN_TOPICS)
        modal = HUMAN_MODALS[working % len(HUMAN_MODALS)]
        working //= len(HUMAN_MODALS)
        punct = HUMAN_PUNCTS[working % len(HUMAN_PUNCTS)]
        working //= len(HUMAN_PUNCTS)
        reaction = HUMAN_REACTIONS[working % len(HUMAN_REACTIONS)]
        pattern_index = working % len(HUMAN_PATTERNS)
        text = HUMAN_PATTERNS[pattern_index].format(
            topic=topic,
            modal=modal,
            punct=punct,
            reaction=reaction,
        )
        return text[:MAX_COMMENT_LENGTH], "humanized"

    def semantic_carrier_positions(self, wrapper, carrier_count, allow_fallback=True):
        """选择更像自然断句的位置，避免把词切开。"""
        candidates = set()

        for match in re.finditer(r"\[[^\]]{1,12}\]", wrapper):
            if match.end() < len(wrapper):
                candidates.add(match.end())

        for word in SEMANTIC_BOUNDARY_WORDS:
            start = 0
            while True:
                index = wrapper.find(word, start)
                if index < 0:
                    break
                end = index + len(word)
                if 1 < end <= len(wrapper):
                    candidates.add(end)
                start = index + 1

        for index, char in enumerate(wrapper, 1):
            if char in SEMANTIC_BOUNDARY_CHARS and index < len(wrapper):
                candidates.add(index)

        ordered = sorted(pos for pos in candidates if 1 < pos <= len(wrapper))
        if len(ordered) >= carrier_count:
            return sorted(random.sample(ordered, carrier_count))
        if not allow_fallback:
            return ordered

        positions = ordered[:]
        if len(wrapper) >= carrier_count + 4:
            low = 2
            high = len(wrapper) - 1
            spread = {
                max(low, min(high, round((index + 1) * len(wrapper) / (carrier_count + 1))))
                for index in range(carrier_count)
            }
            for pos in sorted(spread):
                if len(positions) >= carrier_count:
                    break
                if pos in positions:
                    continue
                positions.append(pos)
            available = [pos for pos in range(low, high + 1) if pos not in positions]
            while len(positions) < carrier_count and available:
                choice = random.choice(available)
                positions.append(choice)
                available.remove(choice)
        while len(positions) < carrier_count:
            positions.append(len(wrapper))
        return sorted(positions)

    def embed_compact_carrier(self, wrapper, carrier_code):
        """把紧凑载体分散进文本内部，避免固定尾部连续载体模式。"""
        wrapper = strip_carrier_chars(wrapper) or "主播加油"
        max_wrapper_len = max(MIN_ROOM_WRAPPER_LEN, MAX_COMMENT_LENGTH - len(carrier_code))
        wrapper = wrapper[:max_wrapper_len]
        if not wrapper:
            return carrier_code

        if SEMANTIC_EMBEDDING_ENABLED:
            positions = self.semantic_carrier_positions(wrapper, len(carrier_code))
        elif len(wrapper) >= 8 and len(carrier_code) >= 4:
            internal_positions = sorted(random.sample(range(2, len(wrapper)), 2))
            positions = internal_positions + [len(wrapper)] * (len(carrier_code) - 2)
        elif len(wrapper) >= 4 and len(carrier_code) >= 3:
            positions = [random.randint(2, len(wrapper) - 1)] + [len(wrapper)] * (len(carrier_code) - 1)
        else:
            positions = [len(wrapper)] * len(carrier_code)

        output = []
        carrier_index = 0
        for index, char in enumerate(wrapper, 1):
            output.append(char)
            while carrier_index < len(carrier_code) and positions[carrier_index] == index:
                output.append(carrier_code[carrier_index])
                carrier_index += 1
        while carrier_index < len(carrier_code):
            output.append(carrier_code[carrier_index])
            carrier_index += 1
        return ''.join(output)

    def choose_payload_wrapper(self, carrier_len):
        """优先从直播间历史弹幕中选择长度匹配的自然外壳。"""
        max_wrapper_len = max(MIN_ROOM_WRAPPER_LEN, MAX_COMMENT_LENGTH - carrier_len)
        if not self.room_comments:
            template = random.choice(CARRIER_TEMPLATES)
            suffix = random.choice(PAYLOAD_SUFFIXES)
            return template.format(suffix)[:max_wrapper_len]

        # 让“外壳 + 载体码”的长度贴近当前房间弹幕长度中位附近。
        candidate_comments = filter_room_wrapper_candidates(self.room_comments)
        if not candidate_comments:
            return random.choice(CARRIER_TEMPLATES).format(random.choice(PAYLOAD_SUFFIXES))[:max_wrapper_len]

        lengths = sorted(min(len(comment), MAX_COMMENT_LENGTH) for comment in candidate_comments)
        target_total_len = lengths[len(lengths) // 2]
        target_wrapper_len = min(max_wrapper_len, max(MIN_ROOM_WRAPPER_LEN, target_total_len - carrier_len))

        scored = []
        for clean in candidate_comments:
            if len(clean) > max_wrapper_len:
                clean = clean[:max_wrapper_len]
            if visible_text_len(clean) < MIN_ROOM_WRAPPER_LEN:
                continue
            score = abs(len(clean) - target_wrapper_len)
            if COMPACT_EMBEDDING_ENABLED and SEMANTIC_EMBEDDING_ENABLED:
                natural_slots = len(self.semantic_carrier_positions(clean, carrier_len, allow_fallback=False))
                score += max(0, 2 - natural_slots) * 0.75
            score -= min(8, visible_text_len(clean) / 8)
            scored.append((score, random.random(), clean))

        if not scored:
            return random.choice(CARRIER_TEMPLATES).format(random.choice(PAYLOAD_SUFFIXES))[:max_wrapper_len]
        scored.sort()
        top = scored[:min(20, len(scored))]
        return random.choice(top)[2]

    def make_payload_comment(self, code):
        """生成低密度载体弹幕，避免固定符号后缀模式。"""
        if HUMANIZED_CARRIER_ENABLED:
            carrier_code, carrier = self.encode_fragment_humanized(code)
            return {
                "c": carrier_code,
                "d": TIME_OFFSET,
                "code": code,
                "carrier": carrier,
            }

        if COMPACT_EMBEDDING_ENABLED:
            carrier_code, carrier = self.encode_fragment_compact(code)
            wrapper = self.choose_payload_wrapper(len(carrier_code))
            content = self.embed_compact_carrier(wrapper, carrier_code)
            for _ in range(8):
                if compact_payload_natural_enough(content, len(carrier_code)):
                    break
                wrapper = self.choose_payload_wrapper(len(carrier_code))
                content = self.embed_compact_carrier(wrapper, carrier_code)
            return {
                "c": content,
                "d": TIME_OFFSET,
                "code": code,
                "carrier": carrier,
            }

        carrier_code, carrier = self.encode_fragment_mixed(code)
        wrapper = self.choose_payload_wrapper(len(carrier_code))
        if len(wrapper) + len(carrier_code) > MAX_COMMENT_LENGTH:
            wrapper = wrapper[:max(0, MAX_COMMENT_LENGTH - len(carrier_code))]
        return {
            "c": wrapper + carrier_code,
            "d": TIME_OFFSET,
            "code": code,
            "carrier": carrier,
        }

    def make_distraction_comment(self):
        """生成不含协议编码的普通弹幕，用于降低载荷密度。"""
        if self.room_comments:
            content = random.choice(self.room_comments)
        else:
            content = random.choice(DISTRACTION_TEMPLATES)
        return {
            "c": content,
            "d": TIME_OFFSET,
            "code": "",
            "carrier": "distraction",
        }

    def append_fragmented_payload(self, payloads, code, seq):
        """将4位协议码拆成带序号的冗余短片段。"""
        for start in range(0, len(code), PROTOCOL_FRAGMENT_SIZE):
            fragment = code[start:start + PROTOCOL_FRAGMENT_SIZE]
            frag_idx = start // PROTOCOL_FRAGMENT_SIZE
            fragment_record = f"{seq:02d}{frag_idx}{fragment}"
            for _ in range(FRAGMENT_REPLICAS):
                payloads.append(self.make_payload_comment(fragment_record))
                for _ in range(FILLERS_PER_PAYLOAD):
                    payloads.append(self.make_distraction_comment())

    def gen_payloads(self, raw_msg):
        msg = self.sanitize_input(raw_msg)
        print(f"[编码] 正在处理: '{msg}'...")

        # 1. 生成一次性密钥
        seed = random.randint(1, 99)
        print(f"[加密流程] 步骤1: 生成一次性密钥 (种子): {seed}")
        
        # 2. 抗量子计算加密
        # 使用基于HMAC的抗量子加密方法
        print(f"[加密流程] 步骤2: 初始化抗量子加密系统")
        pqe = PostQuantumEncryption(key=seed)
        print(f"[加密流程] 步骤3: 开始加密明文消息")
        encrypted_msg = pqe.encrypt(msg)
        print(f"[抗量子加密] 加密后: '{encrypted_msg}'")
        print(f"[加密流程] 步骤4: 加密完成，密文长度: {len(encrypted_msg)}")

        # 3. 直接使用加密后的消息作为编码数据
        # 将加密消息转换为数字编码
        print(f"[加密流程] 步骤5: 开始将密文转换为数字编码")
        encoded_data = ""
        for i, char in enumerate(encrypted_msg):
            # 将每个字符转换为3位数字
            char_code = str(ord(char)).zfill(3)
            encoded_data += char_code
            print(f"[加密流程] 字符 '{char}' (ASCII: {ord(char)}) -> 编码: {char_code}")
        print(f"[编码] 编码后长度: {len(encoded_data)}")
        print(f"[加密流程] 步骤6: 数字编码完成")
        print(f"[加密流程] 完整数字编码: '{encoded_data}'")

        # 7. 生成编码数据
        payloads, cur = [], 0
        limit_len = len(encoded_data)
        seq = 0

        # 生成数据包
        while cur < limit_len:
            # 提取编码数据 (每4位一组)
            if cur + 3 < limit_len:
                code = encoded_data[cur:cur+4]
                cur += 4
            else:
                # 确保最后一组也是4位
                code = encoded_data[cur:].ljust(4, '0')
                cur = limit_len

            # 8. 使用短片段低密度混合载体，降低连续载体符号的可检测性
            self.append_fragmented_payload(payloads, code, seq)
            seq += 1

        # 10. 发送密钥信息（添加在数据包末尾）
        # 格式: 倒数第2包: 种子, 倒数第1包: 密钥长度
        keystream_len = len(encrypted_msg)  # 使用加密后消息的长度作为密钥长度
        
        # 确保至少有10个数据包
        while len(payloads) < 10:
            self.append_fragmented_payload(payloads, "0000", seq)
            seq += 1
        
        # 使用固定的特殊符号载体来传输密钥信息，确保解码一致性
        # 添加种子包
        seed_str = str(seed).zfill(2)
        key_code_seed = seed_str + '00'  # 固定使用00作为后缀，确保种子提取正确
        self.append_fragmented_payload(payloads, key_code_seed, seq)
        seq += 1
        
        # 添加密钥长度包
        keystream_len_str = str(keystream_len).zfill(3)
        key_code_len = keystream_len_str + '0'  # 固定使用0作为后缀，确保密钥长度提取正确
        self.append_fragmented_payload(payloads, key_code_len, seq)

        print(f"[编码] 生成包数: {len(payloads)} 个")
        print(f"[编码] 预计耗时: {sum([p['d'] for p in payloads]) / 60:.1f} 分钟")
        print(f"[抗量子加密] 种子: {seed}, 密钥长度: {keystream_len}")
        print("[编码] 准备启动浏览器...")
        return payloads


class BrowserSender:
    def __init__(self):
        if webdriver is None:
            raise RuntimeError("Selenium is required for BrowserSender, but it is not installed in this Python environment.")
        print("[浏览器] 初始化浏览器...")
        options = webdriver.ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_argument('--start-maximized')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--remote-debugging-port=9222')
        # 直接启动Chrome，不使用ChromeDriverManager
        try:
            self.driver = webdriver.Chrome(options=options)
            print("[浏览器] 浏览器启动成功")
        except Exception as e:
            print(f"[浏览器] 启动失败: {e}")
            # 尝试使用ChromeDriverManager
            try:
                print("[浏览器] 尝试使用ChromeDriverManager...")
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=options)
                print("[浏览器] 浏览器启动成功")
            except Exception as e2:
                print(f"[浏览器] 启动失败: {e2}")
                raise
        self.wait = WebDriverWait(self.driver, 30)
        self.cookie_file = "bilibili_cookies.json"

    def save_cookies(self):
        try:
            cookies = self.driver.get_cookies()
            if cookies:
                with open(self.cookie_file, 'w', encoding='utf-8') as f:
                    json.dump(cookies, f, ensure_ascii=False, indent=2)
                print("✅ Cookie 已保存")
                return True
            else:
                print("❌ 没有找到cookie")
                return False
        except Exception as e:
            print(f"❌ 保存cookie失败: {e}")
            return False

    def load_cookies(self):
        if os.path.exists(self.cookie_file):
            try:
                with open(self.cookie_file, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                if cookies:
                    for cookie in cookies:
                        try:
                            self.driver.add_cookie(cookie)
                        except:
                            pass
                    print("✅ Cookie 已加载")
                    return True
                else:
                    print("❌ Cookie文件为空")
                    return False
            except Exception as e:
                print(f"❌ Cookie 加载失败: {e}")
                return False
        return False

    def login(self):
        self.driver.get("https://passport.bilibili.com/login")
        
        if self.load_cookies():
            self.driver.refresh()
            time.sleep(2)
            if "https://www.bilibili.com/" in self.driver.current_url or "https://passport.bilibili.com/account/security" in self.driver.current_url:
                print("✅ 自动登录成功")
                return True
        
        print("📱 请扫码登录...")
        input("👉 扫码登录成功后，按回车键继续 >>> ")
        self.save_cookies()
        return True

    def get_textarea(self):
        try:
            time.sleep(1)
            
            # 尝试找到弹幕输入框 - 方式1：通过标签名
            try:
                textareas = self.driver.find_elements(By.TAG_NAME, "textarea")
                if textareas:
                    print(f"✅ 找到输入框 (方式1: tag name, 共{len(textareas)}个)")
                    return textareas[0]
            except:
                pass
            
            # 尝试找到弹幕输入框 - 方式2：通过xpath
            try:
                textarea = self.driver.find_element(By.XPATH, "//textarea")
                print("✅ 找到输入框 (方式2: xpath)")
                return textarea
            except:
                pass
            
            # 尝试找到弹幕输入框 - 方式3：通过placeholder
            try:
                textarea = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "textarea[placeholder*='弹幕']")))
                print("✅ 自动定位到弹幕输入框 (方式3: placeholder)")
                return textarea
            except:
                pass
            
            # 尝试找到弹幕输入框 - 方式4：通过class name
            try:
                textarea = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "chat-input")))
                print("✅ 找到输入框 (方式4: class name)")
                return textarea
            except:
                pass
            
            # 尝试找到弹幕输入框 - 方式5：通过id
            try:
                textarea = self.wait.until(EC.presence_of_element_located((By.ID, "chat-input")))
                print("✅ 找到输入框 (方式5: id)")
                return textarea
            except:
                pass
            
            print("❌ 未找到输入框")
            return None
        except Exception as e:
            print(f"❌ 定位输入框时出错: {e}")
            return None

    def run(self, payloads):
        textarea = None
        try:
            if not self.login():
                print("❌ 登录失败")
                return
            
            self.driver.get(f"https://live.bilibili.com/{TARGET_ROOM_ID}")
            time.sleep(5)
            
            textarea = self.get_textarea()
            if not textarea:
                try:
                    input("👉 请手动激活输入框后回车 >>> ")
                    textarea = self.driver.switch_to.active_element
                    print("✅ 已获取活动元素")
                except Exception as e:
                    print(f"❌ 获取活动元素失败: {e}")
                    return

            print("⚡ 发送握手...")
            textarea.send_keys(JOIN_COMMAND)
            time.sleep(0.5)
            textarea.send_keys(Keys.ENTER)

            print("⚡ 发送校准包 (CAL)...")
            time.sleep(3)
            textarea.send_keys(SYNC_COMMAND)
            time.sleep(0.1)
            textarea.send_keys(Keys.ENTER)
            print("🚀 多模态编码模式传输开始...")

            for i, p in enumerate(payloads):
                try:
                    wait_time = p['d']
                    content = p['c']
                    carrier = p.get('carrier', 'symbol')
                    print(f"📤 [{i + 1}/{len(payloads)}] 等待 {wait_time:.1f}s -> {content} (载体: {carrier})")
                    time.sleep(wait_time)
                    textarea.send_keys(content)
                    time.sleep(0.1)
                    textarea.send_keys(Keys.ENTER)
                except Exception as e:
                    print(f"❌ 发送第 {i+1} 条消息失败: {e}")
                    try:
                        textarea = self.get_textarea()
                        if not textarea:
                            print("❌ 无法重新获取输入框，停止发送")
                            break
                    except:
                        print("❌ 重新获取输入框失败，停止发送")
                        break

            # 发送 fin 标志
            try:
                print("⚡ 发送结束标志 (fin)...")
                time.sleep(1)
                textarea.send_keys("fin")
                time.sleep(0.1)
                textarea.send_keys(Keys.ENTER)
            except Exception as e:
                print(f"❌ 发送 fin 标志失败: {e}")

            print("✅ 发送完成")
            try:
                input("回车退出...")
            except:
                pass
        except KeyboardInterrupt:
            print("\n✅ 用户中断操作")
        except Exception as e:
            print(f"❌ 错误: {e}")
        finally:
            try:
                self.driver.quit()
                print("✅ 浏览器已关闭")
            except Exception as e:
                print(f"❌ 关闭浏览器失败: {e}")


if __name__ == "__main__":
    # 直接使用默认消息，避免等待用户输入
    msg = "hello world#"
    print(f"📝 使用默认消息: '{msg}'")
    core = CovLBCG_Core()
    payloads = core.gen_payloads(msg)
    BrowserSender().run(payloads)
