# Codex Context Checkpoint

更新时间：2026-05-18 21:55

## 当前结论

`Error running remote compact task: stream disconnected before completion` 不是 CovLBCG 项目代码错误，而是 Codex/ChatGPT 在执行远程上下文压缩时，到 `https://chatgpt.com/backend-api/codex/responses/compact` 的流式请求中断。

已确认：

- 本机可连到该 endpoint；`HEAD` 请求返回 `405 Method Not Allowed`，说明 DNS/TLS/基础网络链路可用。
- 当前 WinHTTP 未配置代理：`Direct access (no proxy server)`。
- 环境变量中没有发现 `HTTP_PROXY`、`HTTPS_PROXY`、`ALL_PROXY`、`NO_PROXY`。
- VS Code 中已经安装新版 ChatGPT/Codex 扩展 `openai.chatgpt-26.513.21555-win32-x64`。
- 当前运行日志仍显示旧版扩展路径 `openai.chatgpt-26.506.31421`，建议重载 VS Code 让会话切到新版扩展。

## 建议修复步骤

1. 在 VS Code 执行 `Developer: Reload Window`，让 ChatGPT/Codex 扩展切换到新版。
2. 如果仍复现，退出 VS Code 后重新打开项目 `D:\Study\CovLBCG`。
3. 如果仍复现，重新登录 ChatGPT 插件账号。
4. 如果仍复现，切换网络或代理/VPN；该错误通常由长连接流式请求被中途断开造成。
5. 保留本文件作为本地上下文恢复点，避免远程 compact 失败导致研究上下文丢失。

## CovLBCG 当前研究状态

以这两个文件为主：

- `CovLBCG_Sender_5_multimodal.py`
- `CovLBCG_Receiver_5_multimodal.py`

已经完成：

- 真实 B 站直播间 `6963590` 弹幕抓取，生成 `room_comments.txt`。
- Sender 支持从 `room_comments.txt` 学习直播间已有弹幕作为 wrapper/filler，降低固定模板痕迹。
- Receiver 支持混合 symbol/punctuation carrier 解析与按序号冗余重组。
- 完成离线鲁棒性实验、检测实验、对比实验、带宽-隐蔽性 tradeoff 实验、room-adaptive 隐蔽性实验。
- 完成一次真实 B 站端到端最小链路测试：
  - room：`6963590`
  - message：`hi#`
  - 参数：`replicas=1`, `fillers=0`
  - 发送评论数：17 条
  - B 站 HTTP API 返回：全部 `code=0`
  - Receiver 最终解码结果：`成功解码: hi`

关键文档：

- `中文_审稿实验与回复说明.md`
- `MANUSCRIPT_REVISION_TEXT.md`
- `REVIEWER_RESPONSE_DRAFT.md`
- `SECTION_II_REVISION.md`
- `REVIEW_RESPONSE_PLAN.md`
- `RESEARCH_BASELINE.md`

建议下一步：

- 不建议在公开直播间跑高冗余大流量实验。
- 可把真实 B 站测试写成 feasibility validation。
- 正式论文表格仍以离线可重复实验和检测实验为主。
