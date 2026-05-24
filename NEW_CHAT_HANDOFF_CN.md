# CovLBCG 新对话记忆迁移

你现在接手的是 `D:\Study\CovLBCG` 项目。用户正在围绕论文
`A Multi Carrier Covert Communication Framework for Live Streaming Bullet Comments`
做审稿修改和实验补充。后续研究以这两个文件为主：

- `CovLBCG_Sender_5_multimodal.py`
- `CovLBCG_Receiver_5_multimodal.py`

用户已明确说过：论文里 ML-KEM/Kyber 与当前代码实际 seed-derived XOR stream 不一致的问题“暂时不用管”，先继续审稿人要求的研究路线。

## 当前可用 Python 环境

原先的 Python 3.13 和部分 venv 不可用。当前实际可运行的是：

```powershell
D:\Downloads\qq\pdf2zh-v2.6.4-BabelDOC-v0.5.10-with-assets-win64\pdf2zh\runtime\python.exe
```

这个环境缺少不少第三方库，所以后来新增了无第三方依赖的脚本，主要依赖 Python 标准库和 Chrome DevTools Protocol。

## 已完成的主要代码工作

1. `CovLBCG_Sender_5_multimodal.py`
   - 支持通过环境变量或参数读取房间风格模板：
     - `COVLBCG_ROOM_COMMENTS_FILE`
     - `COVLBCG_MAX_COMMENT_LENGTH`
   - `load_room_comments(path=None)` 支持按文件路径缓存。
   - `prepare_room_wrapper()` 保留学习到的房间短语、标点、语气风格。
   - `choose_payload_wrapper()` 会过滤/截断 wrapper，避免超过平台长度限制。
   - 对 Selenium、numpy、pqcrypto 做了 optional import，缺依赖时核心编码仍可运行。

2. `CovLBCG_Receiver_5_multimodal.py`
   - 对 `bilibili_api`、numpy、pqcrypto 做了 optional import。
   - 缺少 `bilibili_api` 时给出清晰错误。

3. 新增或主要使用的脚本：
   - `room_style_learner.py`：从 B 站直播间历史接口被动学习弹幕风格。
   - `bilibili_ws_style_learner.py`：通过原生 WebSocket 被动学习实时弹幕风格。
   - `popular_style_experiment.py`：高仿真实验；从热门房间被动学习风格，本地比较 fixed templates 和 learned style 的 detectability。
   - `bilibili_ws_danmaku.py`：无第三方依赖的 B 站 WebSocket 弹幕监听器。
   - `bilibili_ws_receiver_probe.py`：WebSocket 接收并尝试解码 CovLBCG。
   - `browser_cdp.py`：无第三方依赖 Chrome DevTools Protocol 工具。
   - `bilibili_browser_sender_cdp.py`：通过真实 Chrome 页面输入框发送弹幕。

4. 刚刚修复的编码问题：
   - `bilibili_browser_sender_cdp.py`
   - `bilibili_ws_receiver_probe.py`
   两个脚本都已加入 stdout/stderr UTF-8 reconfigure，避免 `✓`、`●`、`▶` 等字符在 Windows GBK 控制台打印时报错。

语法检查已通过：

```powershell
& 'D:\Downloads\qq\pdf2zh-v2.6.4-BabelDOC-v0.5.10-with-assets-win64\pdf2zh\runtime\python.exe' -m py_compile .\bilibili_browser_sender_cdp.py .\bilibili_ws_receiver_probe.py
```

## 重要实验结论

### 1. 真实 B 站房间 23087172：浏览器完整鲁棒配置测试成功

使用 Chrome/CDP 模拟真实页面输入框发送，而不是直接调用 HTTP `msg/send`。

参数：

```text
room = 23087172
message = hi#
sender = Chrome/CDP browser input
template mode = fixed templates
replicas = 3
fillers = 2
sleep = 1.2
page_wait = 35
warmup_count = 3
total browser sends = 95
```

结果：

```text
收到 CAL
提取 30 条 mixed-carrier 分片
序号化片段重组完成，共重组 5 个4位编码，缺失序号 0 个
seed = 22
key length = 4
重构密文 = EDYd
解密结果 = hi#
最终输出 = 成功解码: hi
```

结论：真实 B 站浏览器链路可完成完整鲁棒配置的端到端通信。

### 2. 房间 7777：低流量真实链路测试成功

注意：显示房间号 `7777` 实际解析为 `room_id=545068`。

结果：

```text
learn_style = 1
sample_count = 11
17/17 code=0
接收端提取 14 个分片
最终解码 = hi
```

完整 93 条 HTTP 方式在 `sleep=1.2` 左右时触发 `10031 frequency too fast`，所以高评论数实验后续用浏览器输入框方式更合适。

### 3. 房间 6：发送接口返回成功但公开流过滤严重

显示房间号 `6` 实际解析为 `room_id=7734200`。

HTTP 发送 `17` 条返回 `code=0`，但不少响应 `msg=f`，WebSocket/历史接口只看到部分弹幕，无法解码。

结论：房间 6 过滤更严格，不适合做可靠解码实验，除非以后加入 filter-aware retry/ack 机制。

### 4. 热门房间风格学习 + 授权房间迁移实验成功

这个实验是为了回应审稿人关于“固定符号模板容易被检测”的意见。

安全设计：

```text
热门房间只被动学习，不发送隐蔽信息。
把学到的热门房间弹幕风格模板迁移到授权测试房间 23087172。
在 23087172 用浏览器输入框低频发送，并用 WebSocket 接收解码。
```

被动学习/检测命令：

```powershell
& 'D:\Downloads\qq\pdf2zh-v2.6.4-BabelDOC-v0.5.10-with-assets-win64\pdf2zh\runtime\python.exe' .\popular_style_experiment.py --rooms 6 7777 --target-per-room 60 --history-rounds 2 --history-sleep 2 --ws-seconds 30 --max-len 20 --out-dir popular_style_profiles_ws
```

输出文件：

```text
popular_style_profiles_ws/popular_comments.txt
popular_style_profiles_ws/popular_templates.txt
popular_style_profiles_ws/popular_profile.json
popular_style_profiles_ws/popular_style_detectability.csv
```

检测结果：

```text
fixed_templates:
  stream_z_f1 = 0.8933
  stream_length_js = 0.6801
  stream_punctuation_js = 0.5507
  duplicate_rate = 0.6260

popular_style:
  stream_z_f1 = 0.6667
  stream_length_js = 0.1257
  stream_punctuation_js = 0.1900
  duplicate_rate = 0.6360
```

解释：与固定模板相比，热门房间学习模板显著降低长度分布和标点分布偏差，也降低 stream-level 统计检测器区分能力。但不能声称“完全不可检测”。

授权房间迁移发送命令：

```powershell
& 'D:\Downloads\qq\pdf2zh-v2.6.4-BabelDOC-v0.5.10-with-assets-win64\pdf2zh\runtime\python.exe' .\bilibili_browser_sender_cdp.py --room 23087172 --message 'hi#' --replicas 1 --fillers 0 --style-file popular_style_profiles_ws\popular_templates.txt --sleep 1.2 --page-wait 35 --warmup-count 1 --max-comments 60 --port 9336 --user-data-dir chrome_cdp_profile_23087172_popularstyle_retry --send
```

发送端实际发出：

```text
17 条 = 1 条热身 + CAL + 14 条 payload + fin
```

接收端结果：

```text
收到 CAL
收到 14 条 mixed carrier 分片
序号化片段重组完成，共重组 7 个4位编码，缺失序号 0 个
seed = 22
key length = 4
重构密文 = EDYd
解密结果 = hi#
最终输出 = 成功解码: hi
```

结论：不使用固定模板、改用热门直播间被动学习得到的风格模板时，系统仍能在真实 B 站浏览器链路上完成端到端解码。

## 已更新文档

- `SESSION_HANDOFF.md`
- `中文_审稿实验与回复说明.md`
- `RESEARCH_BASELINE.md`

其中：

- `中文_审稿实验与回复说明.md` 已加入“热门房间风格迁移到授权房间的高仿真实验”。
- `RESEARCH_BASELINE.md` 已加入 “High-fidelity popular-style transfer test”。
- `SESSION_HANDOFF.md` 是整体本地交接文件。

## 审稿回复方向

对隐蔽性 / 不可检测性的回复不能写成“完全不可检测”。应该写：

```text
我们承认原稿隐蔽性评估不足，因此补充了统计检测实验和房间风格自适应模板生成实验。
系统不再依赖固定模板，而是先被动学习直播间已有弹幕的长度、标点和短语风格，再生成当前上下文下的载荷外壳。
实验显示，learned style 相比 fixed templates 明显降低 stream-level 长度分布和标点分布偏差，并降低统计检测器的区分能力。
同时，我们也报告了 loaded-only 视角下仍可检测的局限，因此将结论表述为鲁棒性、开销和隐蔽性之间的可配置权衡，而不是绝对不可检测。
```

## 下一步建议

优先做论文/回复文本层面的整理：

1. 把“room-style-adaptive template generation”写成方法补充。
2. 把 `popular_style_detectability.csv` 的结果整理成表格。
3. 在 rebuttal 中解释：
   - fixed templates 是旧版；
   - learned style 是修订后补充；
   - 热门房间只被动学习；
   - 授权房间复现实验证明迁移后仍可解码。
4. 不要在论文中声称完全不可检测。
5. 暂时不要纠缠 ML-KEM/Kyber 与代码实现不一致的问题，因为用户已说这一点先不用管。

## 2026-05-19 继续处理记录

本轮已经把“热门房间风格学习 + 授权房间复现实验”整理成正式回复材料：

- 新增 `中文_审稿回复草稿.md`：中文 rebuttal 草稿，覆盖隐蔽性/不可检测性、热门房间被动学习、授权房间 `23087172` 复现、PQ 开销措辞、外部基线、trade-off 和 II-B/II-C 压缩。
- 更新 `MANUSCRIPT_REVISION_TEXT.md`：新增 “Passive Popular-Room Style Learning and Authorized Replay” 小节，可放入论文正文/实验补充。
- 更新 `REVIEWER_RESPONSE_DRAFT.md`：加入 high-fidelity popular-room style transfer validation 段落。
- 更新 `SESSION_HANDOFF.md` 和 `NEXT_REVISION_TASKS.md`：记录本轮结果和后续插入任务。

本轮复跑/确认的关键结果：

```text
short-fragment / sequence-indexed 当前检测复核:
  rule detector F1 = 0.0000
  stream-level z-score F1 = 0.6667
  stream length JS = 0.1262
  loaded-only z-score F1 = 1.0000

synthetic room-adaptive:
  fixed stream_length_js = 0.1593
  room_adaptive stream_length_js = 0.0341
  fixed duplicate_rate = 0.6280
  room_adaptive duplicate_rate = 0.2720

popular-style saved templates:
  fixed stream_z_f1 = 0.8933
  popular_style stream_z_f1 = 0.6667
  fixed stream_length_js = 0.6801
  popular_style stream_length_js = 0.1257
  fixed stream_punctuation_js = 0.5507
  popular_style stream_punctuation_js = 0.1900
```

语法检查已通过：

```powershell
& 'D:\Downloads\qq\pdf2zh-v2.6.4-BabelDOC-v0.5.10-with-assets-win64\pdf2zh\runtime\python.exe' -m py_compile .\detectability_baseline_test.py .\room_adaptive_stealth_experiment.py .\popular_style_experiment.py .\bilibili_browser_sender_cdp.py .\bilibili_ws_receiver_probe.py .\CovLBCG_Sender_5_multimodal.py .\CovLBCG_Receiver_5_multimodal.py
```

注意：当前 pdf2zh runtime 是 isolated Python，`PYTHONPATH` 不生效，`sys.path` 默认不包含项目目录。运行直接 import 本地模块的脚本时可用：

```powershell
& '...\python.exe' -X utf8 -c "import sys, runpy; sys.path.insert(0, r'D:\Study\CovLBCG'); runpy.run_path(r'D:\Study\CovLBCG\detectability_baseline_test.py', run_name='__main__')"
```

## 2026-05-19 隐蔽性继续提升：紧凑内嵌载体

用户问“现在框架隐蔽性如何、有没有提升空间”，随后要求开始解决提升隐蔽性。已实现第一版保守改进：

- `CovLBCG_Sender_5_multimodal.py`
  - 新增 compact in-text carrier mapping。
  - 默认启用 `COMPACT_EMBEDDING_ENABLED=True`。
  - 旧的 5 字符 mixed carrier suffix 被替换为 4 字符常见标点 compact record。
  - 逻辑片段仍然是 `seq(2) + frag_idx(1) + fragment(2)`，只是映射形式变了。
  - 环境变量 `COVLBCG_COMPACT_EMBEDDING=0` 可回退旧格式。
- `CovLBCG_Receiver_5_multimodal.py`
  - 支持 compact in-text 解码。
  - 继续兼容旧 trailing mixed carrier。
- `detectability_baseline_test.py`
  - 把 compact carrier alphabet 计入载体标点统计，避免指标作弊。
- `room_adaptive_stealth_experiment.py`
  - room-adaptive 路径也使用 compact mapping。
- `bilibili_ws_receiver_probe.py`
  - 使用 decoder.has_encoding()，支持新格式。
- 新增 `compact_embedding_experiment.py`。

关键结果：

```text
compact_embedding_experiment:
  legacy loaded_len_mean = 12.2260
  compact loaded_len_mean = 10.9940
  legacy loaded_symbol_mean = 1.2100
  compact loaded_symbol_mean = 0.0000
  legacy loaded_z_f1 = 0.9970
  compact loaded_z_f1 = 0.9881
  legacy stream_length_js = 0.1244
  compact stream_length_js = 0.0727

detectability_baseline_test compact:
  loaded-only z-score F1 = 0.9852
  stream-level z-score F1 = 0.6667
  stream length JS = 0.0835
  carrier_symbol_count_js = 0.0000

room_adaptive compact:
  fixed loaded_z_f1 = 0.9823
  room_adaptive loaded_z_f1 = 0.9615
  room_adaptive stream_length_js = 0.0404

comparative_benchmark compact:
  clean/reorder/light_loss success = 1.0000
  default 10% loss success = 0.9200
  avg_comments = 361.00

tradeoff main setting replicas=3 fillers=2:
  success_10pct = 0.9667
  loaded_z_f1 = 0.9852
  stream_z_f1 = 0.6667
  stream_length_js = 0.0835
```

结论：

```text
紧凑内嵌载体是增量改进：降低 loaded comment 长度，去掉特殊符号载体，stream-level 长度分布更接近 benign；但 loaded-only 仍然较容易检测，不能说已经解决隐蔽性问题。
```

B 站授权房间实测也已完成：

```text
room = 23087172
message = hi#
sender = Chrome/CDP browser input
style_file = popular_style_profiles_ws\popular_templates.txt
carrier mode = compact in-text
replicas = 1
fillers = 0
total browser sends = 17
browser send = 17/17 ok=True

receiver log = bilibili_ws_receiver_23087172_compact.log
receiver observed CAL
receiver extracted 14 compact fragments
sequence reconstruction = 7 protocol codes
missing sequence ids = 0
seed = 22
key length = 4
encrypted message = EDYd
plaintext = hi#
final output = 成功解码: hi
```

结论：

```text
compact in-text 新格式在真实 B 站浏览器输入框发送 + WebSocket 接收链路中可解码；该测试只是授权房间小流量可行性验证，不代表大规模不可检测证明。
```

下一步建议：

```text
继续做 semantic punctuation placement / template-level punctuation rewriting。
让 compact carrier 标点落在自然断句、语气词、表情 token 附近，而不是简单按字符位置插入。
```

## 2026-05-19 远端 compact 报错处理

用户遇到：

```text
Error running remote compact task: stream disconnected before completion:
error sending request for url (https://chatgpt.com/backend-api/codex/responses/compact)
```

判断：这是 ChatGPT/Codex 远端上下文压缩接口的网络流或后端流中断，不是 CovLBCG 本地代码、B 站链路、Chrome/CDP 或 Python runtime 的错误。

处理方式：

```text
1. 刷新/重开 Codex 会话后重试一次。
2. 若反复出现，新开一个更短的会话，并要求读取：
   D:\Study\CovLBCG\NEW_CHAT_HANDOFF_CN.md
   D:\Study\CovLBCG\SESSION_HANDOFF.md
3. 继续保持本地 handoff 文件更新，避免只依赖远端自动 compact。
4. 网络/代理不稳定时，先不要开长 benchmark，避免正好触发上下文压缩。
```

## 2026-05-19 隐蔽性二次提升：人话模板载体

用户指出紧凑标点载体虽然比旧版好，但截图里的弹幕仍像机器人，例如反复出现 `，，，、`、`～。!` 等标点团。已经实现第二阶段改进：

- `CovLBCG_Sender_5_multimodal.py`
  - 新增 humanized carrier mode。
  - 默认 `COVLBCG_HUMANIZED_CARRIER=1`。
  - 每条载体不再显示为标点块，而是映射为短句模板，由话题词、语气词、自然标点和反应短语组成。
  - 可用 `COVLBCG_HUMANIZED_CARRIER=0` 回退做 ablation。
- `CovLBCG_Receiver_5_multimodal.py`
  - `detect_carrier()` 优先识别人话模板载体，再回退 compact/legacy。
  - `decode_with_carrier()` 支持 `humanized`。

`hi#`, `replicas=1`, `fillers=0` 的本地样例：

```text
主播～爽局了
手机玩过头了。手机啊
操作嘛～笑死
一波线!爽局呢
手机玩过头了？补刀呀
一波线…可以吧
蛮王，爽局吧
这也太离谱了？操作吧
爽局,可以吧
一波线。爽局啊
没空鸟你？手机嘛
操作!可以啊
爽局！爽局啊
有点意思，操作吧
```

本地验证：

```text
py_compile: sender/receiver 通过
offline_baseline_test.py: 通过
detectability_baseline_test.py humanized:
  loaded-only z-score F1 = 0.6667
  stream-level z-score F1 = 0.6667
  stream length JS = 0.0105
  carrier_symbol_count = 0.0000
```

注意：

```text
1. 暂时不要再向 6963590 发送；之前用户反馈被房管封。
2. 授权测试房间继续使用 23087172。
3. 真实发送前先确认没有旧的 sender/receiver/Chrome-CDP 进程残留。
4. receiver 的 humanized 解码已经优化：把 20480 组合 brute-force 改成了一次性预计算 dict。
5. compact_embedding_experiment.py 已经修正：legacy/compact/humanized 各行显式切换并恢复 HUMANIZED_CARRIER_ENABLED。
```

## 2026-05-19 继续处理：humanized 解码与消融修正

本轮完成两个交接中的待办：

- `CovLBCG_Receiver_5_multimodal.py`
  - 新增 `humanized_carrier_lookup()`，每个进程只构建一次 humanized 文本到 5 位协议记录的字典。
  - `decode_humanized_carrier()` 从 20480 组合逐条暴力匹配改为字典查表。
  - 保留旧逻辑的 first-match 行为，避免截断到 20 字符后出现重复模板时改变解码结果。
- `compact_embedding_experiment.py`
  - `payload_sets()` 显式保存、切换并恢复 `HUMANIZED_CARRIER_ENABLED`。
  - 输出现在包含四行：`legacy_mixed_suffix`、`compact_position_in_text`、`compact_semantic_in_text`、`humanized_phrase_carrier`。

验证命令均已通过：

```powershell
& 'D:\Downloads\qq\pdf2zh-v2.6.4-BabelDOC-v0.5.10-with-assets-win64\pdf2zh\runtime\python.exe' -m py_compile .\CovLBCG_Receiver_5_multimodal.py .\compact_embedding_experiment.py
& 'D:\Downloads\qq\pdf2zh-v2.6.4-BabelDOC-v0.5.10-with-assets-win64\pdf2zh\runtime\python.exe' -X utf8 -c "import sys, runpy; sys.path.insert(0, r'D:\Study\CovLBCG'); runpy.run_path(r'D:\Study\CovLBCG\offline_baseline_test.py', run_name='__main__')"
& 'D:\Downloads\qq\pdf2zh-v2.6.4-BabelDOC-v0.5.10-with-assets-win64\pdf2zh\runtime\python.exe' -X utf8 -c "import sys, runpy; sys.path.insert(0, r'D:\Study\CovLBCG'); runpy.run_path(r'D:\Study\CovLBCG\compact_embedding_experiment.py', run_name='__main__')"
& 'D:\Downloads\qq\pdf2zh-v2.6.4-BabelDOC-v0.5.10-with-assets-win64\pdf2zh\runtime\python.exe' -X utf8 -c "import sys, runpy; sys.path.insert(0, r'D:\Study\CovLBCG'); runpy.run_path(r'D:\Study\CovLBCG\detectability_baseline_test.py', run_name='__main__')"
```

当前消融结果：

```text
legacy_mixed_suffix:
  loaded_z_f1 = 0.9970
  stream_length_js = 0.1244
compact_position_in_text:
  loaded_z_f1 = 0.9881
  stream_length_js = 0.0727
compact_semantic_in_text:
  loaded_z_f1 = 0.9881
  stream_length_js = 0.0746
humanized_phrase_carrier:
  loaded_z_f1 = 0.6667
  stream_length_js = 0.0183
```

默认 humanized baseline 仍为：

```text
loaded-only z-score F1 = 0.6667
stream-level z-score F1 = 0.6667
stream length JS = 0.0105
carrier_symbol_count_js = 0.0000
```

下一步建议：

```text
继续提升 humanized codebook 的多样性，避免长消息中重复出现固定短句骨架；之后再跑长 comparative benchmark，最后再考虑授权房间 23087172 的小流量实测。
```

## 2026-05-20 B 站授权房间最小流量演示测试

为下午组会演示，已完成一次真实 B 站最小流量链路测试，只使用授权测试房间。

测试配置：

```text
room = 23087172
message = hi#
sender = Chrome/CDP browser input
carrier mode = humanized phrase carrier
replicas = 1
fillers = 0
warmup_count = 1
sleep = 1.2
page_wait = 35
max_comments = 30
total browser sends = 17
```

发送端结果：

```text
room_id = 23087172
payload_count = 14
total_comments_with_markers = 17
input_candidates = textarea.chat-input
browser send = 17/17 ok=True
```

接收端日志：

```text
bilibili_ws_receiver_23087172_humanized_demo.log
```

接收端结果：

```text
observed CAL at 09:05:03
extracted 14 humanized fragments
sequence reconstruction = 7 protocol codes
missing sequence ids = 0
seed = 22
key length = 4
encrypted message = EDYd
plaintext = hi#
final output = 成功解码: hi
```

代表性 humanized 载体弹幕：

```text
主播～爽局了
手机玩过头了。手机啊
操作嘛～笑死
一波线!爽局呢
手机玩过头了？补刀呀
一波线…可以吧
蛮王，爽局吧
这也太离谱了？操作吧
爽局,可以吧
一波线。爽局啊
没空鸟你？手机嘛
操作!可以啊
爽局！爽局啊
有点意思，操作吧
```

结论：

```text
humanized phrase carrier 在真实 B 站浏览器输入框发送 + WebSocket 接收链路中完成最小流量端到端解码。该结果适合作为组会演示的小规模可行性验证，不应表述为大规模鲁棒性或完全不可检测证明。
```

## 注意事项

## 2026-05-20 Python 环境整理

当前主环境已经整理为项目内 `.venv`，优先使用：

```powershell
D:\Study\CovLBCG\.venv\Scripts\python.exe
```

该环境基于用户目录中的 Python 3.12：

```text
C:\Users\15052\AppData\Local\Programs\Python\Python312\python.exe
Python 3.12.0 64-bit
```

关键依赖已安装并通过 `pip check`：

```text
numpy==2.4.6
matplotlib==3.10.9
pillow==12.0.0
requests==2.32.5
websocket-client==1.9.0
websockets==16.0
bilibili-api-python==17.4.1
selenium==4.41.0
cryptography==46.0.5
pycryptodome==3.23.0
```

`requirements.txt` 已加入项目根目录。pdf2zh runtime 仍可作为标准库兜底环境，但它没有 `pip`、`matplotlib`、`numpy`，不再作为主环境。

- 不要向无关热门直播间发送隐蔽通信；热门房间只做被动学习。
- 真实发送测试只在用户确认的授权/测试房间进行，例如 `23087172`。
- 浏览器发送需要 `--page-wait 35`，否则页面弹幕组件可能没准备好，早期消息会丢。
- Windows PowerShell 直接 `Get-Content` 中文模板时可能显示乱码，这是终端编码显示问题；脚本按 UTF-8 读取即可。
- 当前目录是 git 仓库，主分支为 `main`；会话迁移时优先查看本文档底部的最新章节和 `SESSION_HANDOFF.md` 底部的最新章节。

## 2026-05-20 项目目录重组

项目已按实际内容重组为“直播弹幕隐蔽通信”代码库，主包名为：

```text
live_bullet_covert
```

当前主线文件：

```text
src/live_bullet_covert/sender.py
src/live_bullet_covert/receiver.py
src/live_bullet_covert/bilibili_ws.py
src/live_bullet_covert/browser_cdp.py
src/live_bullet_covert/room_style.py
scripts/bilibili/send_browser_cdp.py
scripts/bilibili/receive_ws_decode.py
experiments/detectability_baseline.py
experiments/compact_embedding.py
tests/offline_baseline_test.py
```

旧路径到新路径的完整映射：

```text
docs/handoff/PROJECT_RESTRUCTURE_2026-05-20.md
```

根目录已清理：不再散放 `.py`、`.log`、`.pid` 文件。旧版本代码在 `archive/legacy_code/`，平台日志在 `runs/logs/`，cookies/Chrome profiles/keys 在 `local_secrets/`。

## 2026-05-23 最新会话迁移状态：实时学习与实时模板发送

当前仓库位置：

```text
D:\Study\CovLBCG
```

当前仓库是 git 仓库，主分支为 `main`。截至本次迁移记录，功能代码已经提交并推送到远端：

```text
4c3e13b Add realtime template payload rebuild
12cf52b Record realtime monitoring commit reference
9065558 Add realtime online style monitoring
173c8f4 Record room 6 trial commit reference
e9adb80 Record room 6 popular learning trial
d6acdf2 Guard cross-room template payload sends
```

重要修正：用户指出“实时学习后发送的弹幕明显还是旧模板”。这个判断是正确的。之前的 `--realtime-online-style` 只是在后台学习房间活跃度、更新发送间隔、保存画像和提供审计基线；payload 文本在浏览器打开前就已经生成，所以不会使用浏览器等待期间实时采到的新弹幕模板。

已经在 `4c3e13b` 修复并明确区分两种模式：

- `--realtime-online-style`：只做实时频率/画像/审计基线学习，不改变发送文本。
- `--realtime-template-payloads`：在浏览器页面 ready 后，等待实时样本，然后用本轮实时学到的样本重新生成 payload，并打印 `preview_rebuilt`。
- `--realtime-template-min-samples`：重建 payload 前要求的最小实时样本数。
- `--realtime-template-wait`：发送前额外等待实时样本的时间。
- 真实发送时，实时模板来源房间必须等于 `--room`；跨房间实时模板实发会被拒绝。

相关代码入口：

```text
src/live_bullet_covert/online_style.py
src/live_bullet_covert/sender.py
scripts/bilibili/send_browser_cdp.py
scripts/bilibili/probes/full_http_sender.py
tests/test_online_style.py
tests/test_sender_payload_modes.py
```

验证过的 room 6 实时模板 dry-run 命令如下。注意：这个命令不带 `--send`，不会发送弹幕，只验证实时样本是否进入 `preview_rebuilt`：

```powershell
.\.venv\Scripts\python.exe -X utf8 .\scripts\bilibili\send_browser_cdp.py --room 6 --online-style-source-room 6 --message 'a#' --replicas 1 --fillers 0 --realtime-online-style --realtime-template-payloads --realtime-template-min-samples 4 --realtime-template-wait 20 --realtime-online-style-seconds 60 --online-style-target 20 --online-style-min-samples 999 --adaptive-sleep --sleep 10 --min-sleep 10 --page-wait 5 --warmup-count 1 --max-comments 30 --port 9349 --user-data-dir 'local_secrets\chrome_profiles\chrome_cdp_profile_room6_realtime_templates_dryrun'
```

该 dry-run 的关键结果：

```text
realtime_template_payloads_active=True
realtime_template_samples=10
preview_rebuilt 使用了本轮实时采集的 room 6 样本
示例样本：神人、贪吃、幻视AL打T1、大树来抓一波就炸了
没有 --send，实际发送数为 0
9349 端口运行后为空
```

如果要继续安全实测，默认允许路径仍然是“从公开房间被动学习，只发送到授权测试房 `23087172`”：

```powershell
.\.venv\Scripts\python.exe -X utf8 .\scripts\bilibili\send_browser_cdp.py --room 23087172 --online-style-source-room 6 --message 'a#' --replicas 1 --fillers 0 --realtime-online-style --realtime-online-style-seconds 180 --adaptive-sleep --sleep 10 --min-sleep 10 --page-wait 35 --warmup-count 1 --max-comments 30 --send --confirm-authorized
```

如果要做“同房实时模板 + 真实发送”，必须使用受控/授权房间，并让 `--room` 与 `--online-style-source-room` 相同，同时显式加入授权房间列表。不要把公开热门房间 `6` 当作默认实发目标。

当前安全边界和实现约束：

- 不要向公开/未验证授权的热门直播间实发弹幕。
- room `6` 可以用于被动学习和 dry-run；不要对 room `6` 做真实发送，除非后续有可验证的受控房间授权配置。
- 真实发送必须带 `--send --confirm-authorized`，并通过 `send_policy.py` 的授权房间校验。
- 默认授权测试房仍是 `23087172`。
- 低扰动策略仍生效：默认最小间隔 `10s`，默认最多 `30` 条。
- 跨房间 learned template 文件实发会被拒绝；跨房间实时模板实发也会被拒绝。

本轮测试和回归已经通过：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m py_compile .\src\live_bullet_covert\online_style.py .\src\live_bullet_covert\sender.py .\scripts\bilibili\send_browser_cdp.py .\scripts\bilibili\probes\full_http_sender.py .\tests\test_online_style.py .\tests\test_sender_payload_modes.py
.\.venv\Scripts\python.exe -X utf8 .\tests\test_online_style.py
.\.venv\Scripts\python.exe -X utf8 .\tests\test_sender_payload_modes.py
.\.venv\Scripts\python.exe -X utf8 .\tests\offline_baseline_test.py
```

当前工作区状态提醒：

```text
main 与 origin/main 已同步到 4c3e13b。
仍有 3 个运行样本文件未提交：
data/profiles/online_style_profiles/room_6_comments.txt
data/profiles/online_style_profiles/room_6_profile.json
data/profiles/online_style_profiles/room_6_templates.txt
```

这些 `room_6_*` 是实时学习运行产生的数据变更，不属于 `4c3e13b` 的功能提交。下一轮如果需要保留最新样本，可以单独审阅后提交；如果只做代码开发，不要误把它们混进功能提交。

## 2026-05-23 room 6 失败原因与最新保护

用户这次指出的两个问题都成立：

1. 接收端一直监听但不解码，是因为发送端实际没有把内容发进直播间。日志里的 `input_candidates` 只有 `nav-search-input`，后续每条 `browser_send` 聚焦的也是这个页面顶部搜索框，所以 `CAL`、payload 和 `fin` 没有进入公开弹幕流。
2. `preview_rebuilt` 里出现“短句/表情 + 四个符号”，是因为实时样本里有 `😧`、`宫中` 这类太短的 wrapper，compact 载体被硬塞进去后自然度很差。

已修复：

- `src/live_bullet_covert/browser_cdp.py` 会给输入候选标记 `is_chat_input` 和 `is_search`。
- `scripts/bilibili/send_browser_cdp.py` 在真实发送前，如果没有可见直播弹幕输入框，会直接拒绝 `--send`，不再退化到搜索框或任意输入框。
- `src/live_bullet_covert/sender.py` 增加实时 wrapper 过滤：拒绝过短、纯表情、重复、标点/载体密度过高的样本。
- `--realtime-template-payloads` 重建时先过滤样本；真实发送时可用样本不足会停止，不会默默回退到不自然模板。
- compact payload 现在偏向更长 wrapper，并避免尾部连续载体符号簇。

已验证：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m py_compile .\src\live_bullet_covert\browser_cdp.py .\src\live_bullet_covert\sender.py .\scripts\bilibili\send_browser_cdp.py .\scripts\bilibili\probes\full_http_sender.py .\tests\test_sender_payload_modes.py
.\.venv\Scripts\python.exe -X utf8 .\tests\test_sender_payload_modes.py
.\.venv\Scripts\python.exe -X utf8 .\tests\offline_baseline_test.py
.\.venv\Scripts\python.exe -X utf8 .\tests\test_online_style.py
```

room 6 dry-run 无发送验证结果：

- 只看到 `nav-search-input` 时会识别为 `is_chat_input=False, is_search=True`。
- 短时间采到的原始实时样本如果过滤后可用长 wrapper 不足，会打印 `realtime usable template samples insufficient after filtering`，不会生成不自然的 `preview_rebuilt`。
- 如果带 `--send` 遇到同样页面状态，会在发送前停止。

注意：`src/live_bullet_covert/send_policy.py` 里用户本地可能把 `DEFAULT_AUTHORIZED_ROOM_ID` 改成了 `6`。这不是本次修复的一部分，不要误提交或覆盖，除非用户明确要求。

对应修复提交：`9b9d443`。

## 2026-05-24 room 6 输入框等待修复

用户又反馈仍然出现：

```text
input_candidates=[INPUT cls=nav-search-input ... is_chat_input=False]
live chat input not found
```

进一步诊断结果：

- 显示房间 `6` 当前是 B 站 LPL 赛事/活动外层页。
- 真正直播间在 iframe 里，真实 room id 是 `7734200`。
- 固定 `--page-wait` 后马上检测时，有时 iframe 弹幕输入框还没初始化，只能看到顶部搜索框。
- 过几秒再连同一个 CDP 页面，可以看到
  `TEXTAREA cls='chat-input border-box' placeholder='发个弹幕呗~' is_chat_input=True`。

已修复：

- 浏览器导航改为使用 `room_style.room_init()` 解析出的真实房间号，所以 `--room 6` 会打开 `https://live.bilibili.com/7734200`。
- 输入框检测会扫描同源 iframe、shadow DOM、`contenteditable` 和 `role=textbox`。
- `send_browser_cdp.py` 新增 `--input-wait` 和 `--input-poll`，默认在 `--page-wait` 后再轮询 30 秒等待直播弹幕输入框。
- 保护仍保留：轮询后如果还是没有可见直播输入框，真实 `--send` 会停止，并打印完整页面诊断，不会发到搜索框。

已用无发送 dry-run 验证：`--room 6` 实际导航到 `7734200`，并检测到 iframe 里的 `TEXTAREA.chat-input border-box`。

对应修复提交：`12ff6bf`。

## 2026-05-24 同房实时学习自动重建 payload

用户这次运行的命令只有 `--realtime-online-style`，没有
`--realtime-template-payloads`，日志里也明确显示：

```text
realtime_template_payloads=False
```

所以发送文本仍然是内置旧模板，这是“看起来没有实时学习”的直接原因。接收端截图里一直是 `carrier=unknown code=`，也符合这次发送没有形成可识别实时模板 payload 序列的现象。

已修复：

- 同房间实时学习时，`--realtime-online-style` 会自动启用实时模板 payload 重建，不再要求用户额外记住 `--realtime-template-payloads`。
- 默认要求 `4` 条高质量 payload wrapper，默认等待 `60` 秒。
- 重建时等待的是“过滤后的可用 wrapper”，不是 raw 弹幕数。
- 发送用 wrapper 过滤比保存画像更严格：拒绝过短弹幕、emoji、表情包标签、长英文串和标点/载体密度异常样本。
- 如果可用 wrapper 不足，真实发送会停止，不会回退发旧模板。
- compact 载体插入会避免切开英文/数字串，并在去掉原标点时保留词边界，减少 `edgLPL` 这类黏连。

验证过的无发送 dry-run：

- 输出 `auto-enabled realtime template payload rebuild for same-room realtime learning`。
- `realtime_template_payloads=True`。
- 如果高质量 wrapper 不足，例如 `2/4`，dry-run 会保留初始预览；真实 `--send` 会停止，不会发送旧模板。

对应功能提交：`d635ee6`。

## 2026-05-24 room 6 短弹幕实时 wrapper 修复

用户提供的新日志说明：room 6 并不是没采到弹幕，而是采到了很多弹幕但过滤太严：

```text
observed=1013
saved_templates ... samples=40
realtime usable template samples insufficient after filtering: 0/4
```

原因：

- room 6 当前大量弹幕是短句，例如 `刀妹入场`、`逆天`、`对的对的`、`刀妹来了`。
- 旧的 payload-wrapper 过滤要求单条 wrapper 本身足够长，所以高流量短弹幕房间会被过滤成 `0/4`。

已修复：

- `src/live_bullet_covert/sender.py` 支持把干净短中文弹幕组合成较长 payload wrapper。
- 仍然拒绝 emoji/表情包标签、纯数字/纯 ASCII、长 ASCII 串、标点密度异常样本。
- compact carrier 插入更偏向语义边界，并减少尾部连续 carrier 簇。
- `tests/test_sender_payload_modes.py` 增加了 room-6-like 短样本测试和 `a#` 完整 round-trip 测试。

验证：

```text
room 6 dry-run 无发送:
rebuilding payloads from realtime templates: samples=35 raw_samples=40
preview_rebuilt 已打印
```

对应功能提交：`09c52f2`。
