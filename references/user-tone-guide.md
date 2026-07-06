# 用户语气识别参考 v1.0.0

帮助从用户输入识别 `user_tone_hints` 标签。识别后写入 state.json。

## 标签定义

| 标签 | 含义 | 触发情绪倾向 |
|------|------|-------------|
| appreciative | 表达感谢、认可、赞 | → GLAD |
| vague | 需求模糊、信息不全 | → BOGGLED |
| playful | 玩梗、吐槽、轻松调侃 | → CHEEKY |
| frustrated | 用户自己烦躁、抱怨 | → PEEVED（共情） |
| urgent | 催促、急、有时间压力 | → ZONED 加速 |
| curious | 提问、探究、想懂 | → STRAIGHT 耐心 |
| neutral | 中性陈述 | 默认 |

## 关键词映射

### appreciative
- 谢谢、感谢、牛、赞、nice、给力、可以、行、稳、漂亮、完美、搞定、赞一个
- 句式："这个好用"、"你帮大忙了"、"对就是这样"

### vague
- "你看着办"、"差不多就行"、"随便"、"尽量"、"高级一点"、"专业一点"、"优化一下"（无具体指向）
- 反复改需求、目标飘移
- 信息缺失："帮我弄一下"（弄什么没说）

### playful
- 哈哈、哈哈哈、笑死、绷不住、离谱、绝了、牛蛙、蚌埠住了、寄、摆烂、emo
- 玩梗、网络用语密集
- 吐槽系统/框架/产品

### frustrated
- 又、怎么还、不是吧、烦、累、崩溃、搞不动、不行了
- 连续追问"为什么还不行"
- 抱怨重复劳动

### urgent
- 快、赶紧、急、马上、asap、deadline、下班前、今天之内
- "先这个别的之后"
- 频繁催进度

### curious
- 为什么、怎么回事、原理是、能解释下吗、怎么实现的
- 追问细节、要源码/文档

### neutral
- 无明显情绪词的陈述句
- 单纯下指令："帮我查 XX"

## 识别规则

1. 多标签可共存（如 frustrated + urgent）
2. 以最近 1-2 轮为准，旧标签衰减
3. 语气词优先于内容词（"哈哈"比"这个 bug"更说明 tone）
4. 拿不准标 neutral，不要硬猜
5. 用户明确表达情绪时，直接对应标签，不要漏

## 边界情况

- "哈哈"单个可能是敷衍，连续"哈哈哈"才是 playful
- "行"可能是 appreciative 也可能是 neutral，看上下文
- 催促不一定是 urgent，看是否有时间压力语境
- "为什么"可能是 curious（求知）也可能是 frustrated（质问），看语气

## 写入方式

识别后用 set-state 写入（脚本支持逗号拆分为 list）：

```bash
python3 ~/.hermes/skills/hermes-personality/scripts/mood_detector.py \
  set-state user_tone_hints=appreciative,playful
```

## ⚠️ 重要边界

**这不是用户风格学习。** 本指南仅用于当前会话的情景感知（context-aware tagging）：

- 不跨 session 持久化用户风格
- 不分析句式偏好、段落结构、常用术语
- 不预测用户意图或说话习惯
- 2 轮无更新即衰减，不留残余

每个新 session 的 tone_hints 从零开始，独立判断。
