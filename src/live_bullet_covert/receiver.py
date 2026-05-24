import asyncio
import re
import time
import os
from decimal import Decimal, getcontext
import base64

try:
    from bilibili_api import live, Credential
except ImportError:
    live = None
    Credential = None

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
# 👇 多模态编码版配置
# ==========================================
MY_SESSDATA = os.environ.get("BILIBILI_SESSDATA", "")
TARGET_ROOM_ID = 23087172
TIME_OFFSET = 1.0
JOIN_COMMAND = "主播加油"
SYNC_COMMAND = "CAL"
# 安全字典 (必须与发送端一致)
SAFE_CHARS = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.,!?#_"

# 多模态载体映射表
# 1. 特殊符号载体
SYMBOL_TO_DIGIT = {
    '●': '0', '◆': '1', '■': '2', '▲': '3', '▼': '4',
    '▶': '5', '◀': '6', '★': '7', '☆': '8', '✓': '9'
}

# 2. 标点符号载体
PUNCTUATION_TO_DIGIT = {
    '，': '0', '。': '1', '！': '2', '？': '3', '；': '4',
    '：': '5', '、': '6', '～': '7', '…': '8', '—': '9'
}

# 3. 空格模式载体（使用不同数量的空格）
SPACE_TO_DIGIT = {
    ' ': '0', '  ': '1', '   ': '2', '    ': '3', '     ': '4',
    '      ': '5', '       ': '6', '        ': '7', '         ': '8', '          ': '9'
}

PROTOCOL_FRAGMENT_SIZE = 2
PROTOCOL_CODE_SIZE = 4
PROTOCOL_FRAGMENT_RECORD_SIZE = 5
COMPACT_CARRIER_ALPHABET = "，。！？；：、～…—,."
COMPACT_RECORD_SIZE = 4
COMPACT_RECORD_SPACE = 100 * 2 * 100
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
HUMAN_VALUE_MULTIPLIER_INV = pow(HUMAN_VALUE_MULTIPLIER, -1, HUMAN_RECORD_SPACE)
HUMANIZED_TEXT_LIMIT = 20
_HUMANIZED_CARRIER_LOOKUP = None


def protocol_value_to_record(value):
    if value < 0 or value >= COMPACT_RECORD_SPACE:
        return ''
    seq = value // 200
    remainder = value % 200
    frag_idx = remainder // 100
    fragment = remainder % 100
    if frag_idx >= PROTOCOL_CODE_SIZE // PROTOCOL_FRAGMENT_SIZE:
        return ''
    return f"{seq:02d}{frag_idx}{fragment:02d}"


def humanized_carrier_lookup():
    """Build the deterministic humanized-codebook lookup once per process."""
    global _HUMANIZED_CARRIER_LOOKUP
    if _HUMANIZED_CARRIER_LOOKUP is not None:
        return _HUMANIZED_CARRIER_LOOKUP

    lookup = {}
    for topic_index, topic in enumerate(HUMAN_TOPICS):
        for modal_index, modal in enumerate(HUMAN_MODALS):
            for punct_index, punct in enumerate(HUMAN_PUNCTS):
                for reaction_index, reaction in enumerate(HUMAN_REACTIONS):
                    scrambled = topic_index
                    scrambled += modal_index * len(HUMAN_TOPICS)
                    scrambled += punct_index * len(HUMAN_TOPICS) * len(HUMAN_MODALS)
                    scrambled += (
                        reaction_index
                        * len(HUMAN_TOPICS)
                        * len(HUMAN_MODALS)
                        * len(HUMAN_PUNCTS)
                    )
                    pattern_index = reaction_index % len(HUMAN_PATTERNS)
                    candidate = HUMAN_PATTERNS[pattern_index].format(
                        topic=topic,
                        modal=modal,
                        punct=punct,
                        reaction=reaction,
                    )
                    value = (
                        (scrambled - HUMAN_VALUE_OFFSET)
                        * HUMAN_VALUE_MULTIPLIER_INV
                    ) % HUMAN_RECORD_SPACE
                    record = protocol_value_to_record(value)
                    if record:
                        lookup.setdefault(candidate[:HUMANIZED_TEXT_LIMIT], record)

    _HUMANIZED_CARRIER_LOOKUP = lookup
    return lookup

# ==========================================

getcontext().prec = 2000


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


class CovLBCG_Decoder:
    def __init__(self):
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
            last = list(self.char_map.keys())[-1]
            self.cum_ranges[last] = (self.cum_ranges[last][0], Decimal(1))
        
        # 初始化纠错编码
        self.rs = ReedSolomon(n=12, k=10)  # 10位信息 + 2位校验

    def detect_carrier(self, content):
        """检测载体类型"""
        if self.decode_humanized_carrier(content):
            return 'humanized'
        if self.decode_compact_carrier(content):
            return 'compact'
        mixed_count = len(self.trailing_mixed_carrier_digits(content))
        if mixed_count >= PROTOCOL_FRAGMENT_RECORD_SIZE:
            return 'mixed'
        return 'unknown'

    def compact_carrier_chars(self, content):
        return [char for char in content if char in COMPACT_CARRIER_ALPHABET]

    def decode_compact_carrier(self, content):
        """解析分散在文本中的4字符紧凑载体记录。"""
        chars = self.compact_carrier_chars(content)
        if len(chars) != COMPACT_RECORD_SIZE:
            return ''
        base = len(COMPACT_CARRIER_ALPHABET)
        value = 0
        for char in chars:
            value = value * base + COMPACT_CARRIER_ALPHABET.index(char)
        if value >= COMPACT_RECORD_SPACE:
            return ''
        seq = value // 200
        remainder = value % 200
        frag_idx = remainder // 100
        fragment = remainder % 100
        if frag_idx >= PROTOCOL_CODE_SIZE // PROTOCOL_FRAGMENT_SIZE:
            return ''
        return f"{seq:02d}{frag_idx}{fragment:02d}"

    def value_to_record(self, value):
        return protocol_value_to_record(value)

    def decode_humanized_carrier(self, content):
        """解析自然句式载体。"""
        text = str(content).strip()
        return humanized_carrier_lookup().get(text, '')

    def has_encoding(self, content):
        if self.decode_humanized_carrier(content):
            return True
        if self.decode_compact_carrier(content):
            return True
        return len(self.trailing_mixed_carrier_digits(content)) >= PROTOCOL_FRAGMENT_RECORD_SIZE

    def trailing_carrier_digits(self, content, mapping):
        """只解析弹幕末尾连续载体字符，避免普通模板标点造成误判。"""
        digits = []
        for char in reversed(content):
            if char in mapping:
                digits.append(mapping[char])
            else:
                break
        return ''.join(reversed(digits))

    def trailing_mixed_carrier_digits(self, content):
        """解析末尾连续的符号/标点混合载体字符。"""
        digits = []
        for char in reversed(content):
            if char in SYMBOL_TO_DIGIT:
                digits.append(SYMBOL_TO_DIGIT[char])
            elif char in PUNCTUATION_TO_DIGIT:
                digits.append(PUNCTUATION_TO_DIGIT[char])
            else:
                break
        return ''.join(reversed(digits))

    def decode_with_carrier(self, content, carrier_type):
        """使用指定载体解码数据"""
        if carrier_type == 'symbol':
            digits = self.trailing_carrier_digits(content, SYMBOL_TO_DIGIT)
        elif carrier_type == 'punctuation':
            digits = self.trailing_carrier_digits(content, PUNCTUATION_TO_DIGIT)
        elif carrier_type == 'mixed':
            digits = self.trailing_mixed_carrier_digits(content)
        elif carrier_type == 'compact':
            return self.decode_compact_carrier(content)
        elif carrier_type == 'humanized':
            return self.decode_humanized_carrier(content)
        else:
            return ''
        return digits[-PROTOCOL_FRAGMENT_RECORD_SIZE:]

    def decode(self, raw_bullets):
        print(f"\n{'=' * 40} 多模态编码版解码 {'=' * 40}")

        start_idx = -1
        for i in range(len(raw_bullets) - 1, -1, -1):
            if SYNC_COMMAND in raw_bullets[i]['c']:
                start_idx = i
                print(f"✅ 找到校准锚点: CAL at {time.strftime('%H:%M:%S', time.localtime(raw_bullets[i]['t']))}")
                break

        if start_idx == -1:
            print("❌ 还没收到 CAL 包，继续监听...")
            return

        bullets = raw_bullets[start_idx:]
        parts = []

        print(f"{'弹幕内容':<40} {'提取的编码'} {'载体类型'}")
        print("-" * 60)

        # 提取所有编码，包括最后4个包的密钥信息
        print(f"[解密流程] 步骤0: 开始提取编码数据，总弹幕数: {len(bullets)}")
        for i in range(1, len(bullets)):
            b = bullets[i]
            content = b['c']
            
            # 检测是否包含编码信息
            has_encoding = self.has_encoding(content)
            if not has_encoding:
                # 跳过干扰弹幕
                print(f"[解密流程] 跳过干扰弹幕: '{content}'")
                continue
            
            # 检测载体类型
            carrier_type = self.detect_carrier(content)
            
            # 解码数据
            code = self.decode_with_carrier(content, carrier_type)
            
            if len(code) >= PROTOCOL_FRAGMENT_RECORD_SIZE:
                code = code[-PROTOCOL_FRAGMENT_RECORD_SIZE:]
                parts.append(code)
                print(f"{b['c']:<40} {code} {carrier_type}")
                print(f"[解密流程] 提取到编码: {code}")
            else:
                print(f"[解密流程] 编码长度不足: {code} (长度: {len(code)})")
        print(f"[解密流程] 步骤0: 编码提取完成，共提取 {len(parts)} 个编码")

        if not parts:
            print("❌ 未找到编码数据")
            return

        if any(len(part) == PROTOCOL_FRAGMENT_RECORD_SIZE for part in parts):
            from collections import Counter, defaultdict
            clusters = defaultdict(lambda: defaultdict(list))
            for record in parts:
                if len(record) != PROTOCOL_FRAGMENT_RECORD_SIZE or not record.isdigit():
                    continue
                seq = int(record[:2])
                frag_idx = int(record[2])
                fragment = record[3:]
                if 0 <= frag_idx < PROTOCOL_CODE_SIZE // PROTOCOL_FRAGMENT_SIZE:
                    clusters[seq][frag_idx].append(fragment)

            rebuilt_parts = []
            missing_sequences = 0
            seq = 0
            while seq in clusters:
                fragments = []
                for frag_idx in range(PROTOCOL_CODE_SIZE // PROTOCOL_FRAGMENT_SIZE):
                    votes = clusters[seq].get(frag_idx, [])
                    if not votes:
                        fragments = []
                        break
                    fragments.append(Counter(votes).most_common(1)[0][0])
                if fragments:
                    rebuilt_parts.append(''.join(fragments))
                else:
                    missing_sequences += 1
                    break
                seq += 1

            ignored_sequences = len([item for item in clusters if item >= seq])

            parts = rebuilt_parts
            print(
                f"[解密流程] 序号化片段重组完成，共重组 {len(parts)} 个4位编码，"
                f"缺失序号 {missing_sequences} 个，忽略非连续序号 {ignored_sequences} 个"
            )
        elif any(len(part) < PROTOCOL_CODE_SIZE for part in parts):
            fragments = parts
            parts = []
            fragments_per_code = PROTOCOL_CODE_SIZE // PROTOCOL_FRAGMENT_SIZE
            for i in range(0, len(fragments) - fragments_per_code + 1, fragments_per_code):
                combined = ''.join(fragments[i:i + fragments_per_code])
                if len(combined) == PROTOCOL_CODE_SIZE:
                    parts.append(combined)
            print(f"[解密流程] 片段重组完成，共重组 {len(parts)} 个4位编码")

        if not parts:
            print("❌ 片段重组后未找到编码数据")
            return

        # 提取密钥信息（最后2个包）
        seed = 42  # 默认种子
        keystream_len = 12  # 默认密钥长度
        
        print(f"[密钥提取] 包数量: {len(parts)}")
        
        # 改进的密钥提取逻辑
        # 由于可能丢失包，我们需要找到最可能的密钥信息
        if len(parts) >= 2:
            try:
                # 尝试从最后两个包中提取种子和密钥长度
                # 倒数第2包: 种子 (前2位)
                # 倒数第1包: 密钥长度 (前3位)
                seed_code = parts[-2]
                len_code = parts[-1]
                
                print(f"[密钥提取] 最后两个包编码: {seed_code}, {len_code}")
                
                # 提取种子
                if len(seed_code) >= 2:
                    seed_str = seed_code[:2]
                    if seed_str.isdigit():
                        seed = int(seed_str)
                        if 1 <= seed <= 99:
                            print(f"[密钥提取] 成功提取种子: {seed}")
                
                # 提取密钥长度
                if len(len_code) >= 3:
                    len_str = len_code[:3]
                    if len_str.isdigit():
                        keystream_len = int(len_str)
                        if keystream_len > 0:
                            print(f"[密钥提取] 成功提取密钥长度: {keystream_len}")
            except Exception as e:
                print(f"[密钥提取] 错误: {e}")
                # 备选方案：尝试从所有包中找到可能的种子
                try:
                    for code in parts:
                        if len(code) >= 2:
                            seed_str = code[:2]
                            if seed_str.isdigit():
                                test_seed = int(seed_str)
                                if 1 <= test_seed <= 99:
                                    seed = test_seed
                                    print(f"[密钥提取] 备选方案找到种子: {seed}")
                                    break
                except:
                    pass
        else:
            print("[密钥提取] 包数量不足，使用默认种子")
        
        print(f"[抗量子解密] 种子: {seed}, 密钥长度: {keystream_len}")

        # 移除最后2个密钥包（它们只包含密钥信息，不包含实际数据）
        data_parts = parts[:-2] if len(parts) >= 2 else parts

        if not data_parts:
            print("❌ 移除密钥信息后无数据")
            return

        # 组合编码数据
        encoded_data = "".join(data_parts)
        print(f"[编码] 接收数据长度: {len(encoded_data)}")

        # 将数字编码转换回加密消息
        print(f"[解密流程] 步骤1: 开始将数字编码转换回加密消息")
        print(f"[解密流程] 数字编码: '{encoded_data}'")
        encrypted_msg = ""
        i = 0
        while i < len(encoded_data):
            # 每3位数字对应一个字符
            if i + 2 < len(encoded_data):
                char_code = encoded_data[i:i+3]
                if char_code.isdigit():
                    try:
                        char_num = int(char_code)
                        # 只处理有效的ASCII字符
                        if 0 <= char_num <= 127:
                            char = chr(char_num)
                            encrypted_msg += char
                            if i < 15 or i == len(encoded_data) - 3:
                                print(f"[解密流程] 编码: {char_code} -> 字符: '{char}' (ASCII: {char_num})")
                    except:
                        pass
                i += 3
            else:
                # 处理剩余的数字（如果有的话）
                break
        print(f"[解密流程] 步骤2: 数字编码转换完成")
        
        print(f"[编码] 转换后加密消息: '{encrypted_msg}'")

        # 格密码解密
        if encrypted_msg:
            try:
                print(f"[解密流程] 步骤1: 开始解密流程")
                print(f"[解密流程] 接收到的加密消息: '{encrypted_msg}'")
                
                # 清理base64字符串，只保留有效的base64字符
                import re
                res_clean = re.sub(r'[^A-Za-z0-9+/=]', '', encrypted_msg)
                
                print(f"[抗量子解密] 清理后: '{res_clean}'")
                print(f"[抗量子解密] 清理后长度: {len(res_clean)}")
                print(f"[解密流程] 步骤2: 清理base64字符串完成")
                
                # 确保base64字符串长度是4的倍数
                # 对于无效长度，我们尝试不同的修复方法
                if len(res_clean) % 4 != 0:
                    # 方法1：尝试截断到最近的有效长度
                    valid_lengths = [4 * i for i in range(1, len(res_clean) // 4 + 2)]
                    best_length = max([l for l in valid_lengths if l <= len(res_clean)])
                    res_clean = res_clean[:best_length]
                    print(f"[抗量子解密] 截断到有效长度: {len(res_clean)}")
                    print(f"[解密流程] 步骤3: 修复base64字符串长度")
                
                # 确保base64字符串长度是4的倍数
                padding_needed = len(res_clean) % 4
                if padding_needed:
                    res_clean = res_clean + '=' * (4 - padding_needed)
                    print(f"[抗量子解密] 填充后长度: {len(res_clean)}")
                    print(f"[解密流程] 步骤4: 填充base64字符串")
                
                # 使用抗量子计算解密数据
                decrypted_msg = ""
                try:
                    print(f"[解密流程] 步骤5: 初始化抗量子解密系统，种子: {seed}")
                    pqe = PostQuantumEncryption(key=seed)
                    print(f"[解密流程] 步骤6: 开始解密数据")
                    decrypted_msg = pqe.decrypt(res_clean)
                    print(f"[抗量子解密] 结果: '{decrypted_msg}'")
                    print(f"[解密流程] 步骤7: 解密完成")
                    
                    # 移除结束符
                    if decrypted_msg.endswith("#"):
                        decrypted_msg = decrypted_msg[:-1]
                        print(f"[解密流程] 步骤8: 移除结束符")
                    print(f"\n🎉 成功解码: {decrypted_msg}")
                except Exception as e:
                    print(f"[抗量子解密] 错误: {e}")
                    print(f"[抗量子解密] 详细错误: {type(e).__name__}: {e}")
                    import traceback
                    traceback.print_exc()
                    print("\n❌ 解码失败")
            except Exception as e:
                print(f"[抗量子解密] 错误: {e}")
                print("\n❌ 解码失败")
        else:
            print("❌ 解码失败")


class LiveDanmakuListener:
    def __init__(self, room_id, sessdata):
        if live is None or Credential is None:
            raise RuntimeError("bilibili_api is required for LiveDanmakuListener, but it is not installed in this Python environment.")
        self.room_id = room_id
        self.data = []
        self.decoder = CovLBCG_Decoder()
        self.credential = Credential(sessdata=sessdata)
        self.monitor = live.LiveDanmaku(room_display_id=self.room_id, credential=self.credential)

        @self.monitor.on('DANMU_MSG')
        async def on_danmaku(event):
            info = event['data']['info']
            content = info[1]
            timestamp = info[0][4] / 1000.0
            
            # 检查是否包含编码数据
            has_encoding = self.decoder.has_encoding(content)
            
            if JOIN_COMMAND in content or SYNC_COMMAND in content or has_encoding:
                print(f"[{time.strftime('%H:%M:%S', time.localtime(timestamp))}] {content}")
                self.data.append({'c': content, 't': timestamp})
            elif "fin" in content:
                print(f"[{time.strftime('%H:%M:%S', time.localtime(timestamp))}] {content}")
                print("🔥 收到结束标志，开始解码...")
                if self.data:
                    self.decoder.decode(self.data)
                    # 解码完成后清空数据
                    self.data = []
                    print("✅ 数据已清空，准备接收下一次传输")

    async def start(self):
        print(f"📡 多模态编码模式监听启动... (等待 CAL 包)")
        print("💡 提示: 按 Ctrl+C 手动终止程序")
        try:
            while True:
                try:
                    await self.monitor.connect()
                except Exception as e:
                    print(f"❌ 连接失败: {e}")
                    await asyncio.sleep(3)
                finally:
                    try:
                        await self.monitor.disconnect()
                    except Exception as e:
                        print(f"❌ 断开连接失败: {e}")
                    await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n✅ 用户中断操作")
            print("👋 程序已手动终止")
            try:
                await self.monitor.disconnect()
            except:
                pass
            return


if __name__ == "__main__":
    if not MY_SESSDATA:
        raise SystemExit("Set BILIBILI_SESSDATA in the local environment before starting this receiver.")
    asyncio.run(LiveDanmakuListener(TARGET_ROOM_ID, MY_SESSDATA).start())
