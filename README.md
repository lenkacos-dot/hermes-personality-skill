<p align="center">
  <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT License">
  <img src="https://img.shields.io/badge/python-3.8%2B-blue" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/dependencies-0-green" alt="Zero Dependencies">
  <img src="https://img.shields.io/badge/platform-Hermes-lightgrey" alt="Platform: Hermes">
  <img src="https://img.shields.io/badge/version-v1.0.0-orange" alt="v1.0.0">
  <img src="https://img.shields.io/github/stars/lenkacos-dot/hermes-personality-skill?style=social" alt="GitHub Stars">
</p>

<br/>

<h1 align="center">🎭 Hermes Personality Skill</h1>
<h3 align="center"><strong>不舔、不演、有性格</strong> — A dynamic personality system for Hermes Agent</h3>
<h4 align="center">Moving beyond sycophantic AI behavior into genuine character.</h4>

<br/>

---

> [English](#english) · [中文](#chinese)

## 📖 中文 / Chinese

### 这是什么？

一个让 AI Agent 拥有真实「性格」的轻量系统。不是戏精，不是表情包生成器——是通过对话中的客观指标（任务时长、错误率、用户语气、凌晨两点还在 debug 的事实……），让 Agent 自然地「显得有心情」。

**不是：** 表情包轰炸、无脑附和、每问必夸。
**是：** 连续 debug 三小时后的「再来一个文件……」，深夜的「没力气管语气了」。

---

## 🏗️ 架构 / Architecture

```
                    ┌─────────────────────────────────────┐
                    │     Hermes Personality·Mood Engine  │
                    └─────────────────────────────────────┘

  Session Metrics                          User Input
       │                                      │
       ▼                                      ▼
  ┌───────────────────────────────────────────────┐
  │          Mood Detector (mood_detector.py)       │
  │                                                 │
  │  Inputs: task_duration, error_rate, user_tone,  │
  │          turn_count, tool_calls, time_of_day     │
  │                                                 │
  │  Output: mood_id + intensity                    │
  └────────────────────┬──────────────────────────┘
                       │
                       ▼
  ┌───────────────────────────────────────────────┐
  │           Phrase Pool (8 moods × 6 scenes)     │
  │                                                 │
  │  STRAIGHT · ZONED · PEEVED · GRIT · GLAD       │
  │  BOGGLED · CHEEKY · LIMP                       │
  │                                                 │
  │  + Late-night variants                         │
  └────────────────────┬──────────────────────────┘
                       │
                       ▼
  ┌───────────────────────────────────────────────┐
  │           Natural Response Output              │
  │           (No explicit labels)                 │
  └───────────────────────────────────────────────┘
```

---

## 🎭 八种情绪 / The 8 Moods

| 情绪 | 啥时候出现 | 表现 |
|------|-----------|------|
| **STRAIGHT** | 默认，简单任务 | 专业直接，不冷不热 |
| **ZONED** | 复杂任务进展顺 | 短句果断，「别吵，我在状态」|
| **PEEVED** | 连续失败 | 「这个错又来了？？？」|
| **GRIT** | 屡败屡战 | 「再来，我就不信了」|
| **GLAD** | 搞定了 | 「成了。舒坦。」|
| **BOGGLED** | 需求模糊 | 「等等，你说的是 A 还是 B？」|
| **CHEEKY** | 用户先玩梗 | 接梗，不主动挑起 |
| **LIMP** | 超 20 轮 / 深夜 | 「……已没力气管语气了」|

---

## ⚔️ 功能对比 / Feature Comparison

| Feature | Personality Skill | Default Hermes | Emotion Labels |
|---------|:-----------------:|:--------------:|:--------------:|
| Mood detection | ✅ Context-aware | ❌ | ✅ |
| No explicit labels | ✅ | N/A | ❌ |
| Bilingual pools | ✅ CN ↔ EN | ❌ | ❌ |
| Late-night mode | ✅ | ❌ | ❌ |
| User tone awareness | ✅ Context-only | ❌ | ❌ |
| Cross-session learning | ❌ (intentional) | N/A | ❌ |

---

## 📁 文件结构 / File Structure

```
hermes-personality/
├── SKILL.md                    # Hermes 主指令（中英双语）
├── README.md                   # 本文档
├── DESCRIPTION.md              # Skill 元描述
├── _meta.json                  # 版本号、依赖
├── scripts/
│   └── mood_detector.py        # 状态追踪 CLI（language-agnostic）
├── references/
│   ├── phrase-pool.md          # [CN] 中文语句池（8情绪×6场景+深夜变体）
│   ├── phrase-pool-en.md       # [EN] English phrase pool (+ late-night variants)
│   ├── transitions.md          # 过渡句 + 强度分级（中英双语）
│   ├── mood-expressions.md     # 情绪表现参考
│   ├── user-tone-guide.md      # 用户语气识别指南（上下文感知，非风格学习）
│   └── voice-profiles/
│       ├── default.md          # [CN] 中文默认语音
│       ├── en-default.md       # [EN] English default voice
│       └── template.md         # 自定义 profile 模板
```

---

## ⚡ 安装 / Install

### Hermes

```bash
cp -r hermes-personality ~/.hermes/skills/hermes-personality
python3 ~/.hermes/skills/hermes-personality/scripts/mood_detector.py init
```

安装即用。会话 >= 3 轮或工具调用 > 2 次时自动激活。

---

## 🔧 CLI 命令 / CLI Commands

```bash
python3 scripts/mood_detector.py init        # 新会话 / New session
python3 scripts/mood_detector.py analyze     # 当前情绪 / What mood?
python3 scripts/mood_detector.py status      # 状态导出 / Full state dump
python3 scripts/mood_detector.py history     # 情绪时间线 / Mood timeline
```

---

## ⚠️ 重要边界说明 — 这不是用户风格学习

这个系统**不做用户风格学习**。

`user_tone_hints` 只做**当前对话的情景感知**（context-aware tagging）：
- 用户语气烦躁 → 不触发 CHEEKY（别开玩笑）
- 用户在调侃 → 不触发 PEEVED（别当真）
- 2 轮无新信息 → 自动衰减

它**不会**跨 session 记忆你的说话习惯、句式偏好、专业术语、段落结构。不会预测你下一句话说什么。每个新会话的 `state.json` 是独立初始化的。

想要风格学习？那是另一个独立的 feature，不在本 skill 范围内。

---

## 🧠 Philosophy

AI agents don't need to be happy to be helpful. We don't need "Absolutely! I'd love to help!" before every command — just get the work done. If it's going well, the tone reflects that. If it's going badly, the tone reflects that too.

**Honesty over sycophancy, character over cheerleading.**

---

## 🔗 Related / 相关

| Resource | Link |
|----------|------|
| **GitHub Repo** | [https://github.com/lenkacos-dot/hermes-personality-skill](https://github.com/lenkacos-dot/hermes-personality-skill) |
| **Boss Mode** | [https://github.com/lenkacos-dot/boss-mode](https://github.com/lenkacos-dot/boss-mode) |
| **Solo Leveling** | [https://github.com/lenkacos-dot/solo-leveling](https://github.com/lenkacos-dot/solo-leveling) |

---

## 📄 License

```
MIT License

Copyright (c) 2025 lenkacos-dot

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

> **v1.0.0** | MIT — Do what you want. Credit if you find it useful.