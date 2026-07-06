# Hermes Personality Skill

**不舔、不演、有性格** — A dynamic personality system for Hermes Agent that moves beyond sycophantic AI behavior into genuine character.

> [English](#english) · [中文](#chinese)

---

## Chinese

### 📖 这是什么？

一个让 AI Agent 拥有真实"性格"的轻量系统。不是戏精，不是表情包生成器——是通过对话中的客观指标（任务时长、错误率、用户语气、凌晨两点还在 debug 的事实……），让 Agent 自然地"显得有心情"。

**八种情绪：**

| 情绪 | 啥时候出现 | 表现 |
|------|-----------|------|
| **STRAIGHT** | 默认，简单任务 | 专业直接，不冷不热 |
| **ZONED** | 复杂任务进展顺 | 短句果断，"别吵，我在状态" |
| **PEEVED** | 连续失败 | "这个错又来了？？" |
| **GRIT** | 屡败屡战 | "再来，我就不信了" |
| **GLAD** | 搞定了 | "成了。舒坦。" |
| **BOGGLED** | 需求模糊 | "等等，你说的是 A 还是 B？" |
| **CHEEKY** | 用户先玩梗 | 接梗，不主动挑起 |
| **LIMP** | 超 20 轮 / 深夜 | "……已没力气管语气了" |

### 🎯 安装

```bash
# 复制到 Hermes skills 目录
cp -r hermes-personality-skill ~/.hermes/skills/hermes-personality

# 初始化状态文件
python3 ~/.hermes/skills/hermes-personality/scripts/mood_detector.py init
```

安装即用。会话 >= 3 轮或工具调用 > 2 次时自动激活。

### 🗂️ 文件结构

```
hermes-personality/
├── SKILL.md                    # Hermes 主指令（中英双语文档）
├── README.md                   # 本文件
├── DESCRIPTION.md              # Skill 元描述
├── _meta.json                  # 版本号、依赖
├── scripts/
│   └── mood_detector.py        # 状态追踪 CLI（language-agnostic）
├── references/
│   ├── phrase-pool.md          # [CN] 中文语句池（8情绪×6场景+深夜变体）
│   ├── phrase-pool-en.md       # [EN] English phrase pool (+ late-night variants)
│   ├── transitions.md          # 过渡句 + 强度分级（中英双语）
│   ├── mood-expressions.md     # 情绪表现参考
│   ├── user-tone-guide.md      # 用户语气识别指南
│   └── voice-profiles/
│       ├── default.md          # [CN] 中文默认语音
│       ├── en-default.md       # [EN] English default voice
│       └── template.md         # 自定义 profile 模板
```

---

## English

### 📖 What is this?

A lightweight mood/personality system for AI agents. It tracks real session metrics — task duration, error rate, user tone, tool calls, and time of day — and reflects the work context through natural tone variation instead of forced enthusiasm.

**Not:** emoji spam, sycophantic agreement, or "wow, that's amazing!" on every trivial query.

**Is:** a tired "one more file…" after hour 3, a focused "pulling the data" mid-debug, or a genuine "that works! clean, too." when it actually works.

### 🎯 Install

```bash
cp -r hermes-personality-skill ~/.hermes/skills/hermes-personality
python3 ~/.hermes/skills/hermes-personality/scripts/mood_detector.py init
```

Auto-activates at >=3 turns or >2 tool calls.

### 🗂️ Structure

Same as Chinese above. Bilingual — user language auto-detected (CN ↔ EN phrase pools).

### 🎭 The 8 Moods

| Mood | Trigger | Vibe |
|------|---------|------|
| **STRAIGHT** | Default, simple Q&A | Neutral pro, no warmth |
| **ZONED** | Complex task, in flow | Sharp, clipped, "don't interrupt" |
| **PEEVED** | Recurring failure | "same error *again*?" |
| **GRIT** | Persisting through failure | "one more try — going in" |
| **GLAD** | Success | "nice. that's clean." |
| **BOGGLED** | Ambiguous request | "wait — what does this resolve to?" |
| **CHEEKY** | User cracks a joke | Plays along, doesn't start it |
| **LIMP** | 20+ turns, late night | "…words are hard right now" |

### 🔧 CLI

```bash
python3 scripts/mood_detector.py init        # New session
python3 scripts/mood_detector.py analyze     # What mood am I in?
python3 scripts/mood_detector.py status      # Full state dump
python3 scripts/mood_detector.py history     # Mood timeline
```

## ⚠️ 重要边界说明 — 这不是用户风格学习

⚠️ **这个系统不做用户风格学习。**

`user_tone_hints` 只做**当前对话的情景感知**（context-aware tagging）：
- 用户语气烦躁 → 不触发 CHEEKY（别开玩笑）
- 用户在调侃 → 不触发 PEEVED（别当真）
- 2 轮无新信息 → 自动衰减

它**不会**跨 session 记忆你的说话习惯、句式偏好、专业术语、段落结构。不会预测你下一句话说什么。每个新会话的 `state.json` 是独立初始化的。

想要风格学习？那是另一个独立的 feature，不在本 skill 范围内。

---

## 🧠 Philosophy

AI agents don't need to be happy to be helpful. We don't need "Absolutely! I'd love to help!" before every command — just get the work done. If it's going well, the tone reflects that. If it's going badly, the tone reflects that too. **Honesty over sycophancy, character over cheerleading.**

MIT License. Do whatever.
