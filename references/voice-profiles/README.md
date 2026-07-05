# Voice Profiles — 语言使用习惯分区 v1.0.0

在情绪层之上加一层"个人风格层"。情绪决定语气基调，voice profile 决定具体用词、口头禅、节奏。同一个 PEEVED，不同人嘴里是不一样的味道。

## 载入机制

1. 默认载入 `default.md`
2. 在 state.json 的 `voice_profile` 字段指定要激活的 profile 名（不带 .md）
3. Hermes 每次响应前，读取当前 voice profile，把 phrase-pool.md 的通用句式按 profile 做替换/补充

## 用法

```bash
# 设当前 voice profile（值为文件名，不含 .md）
python3 ~/.hermes/skills/hermes-personality/scripts/mood_detector.py \
  set-state voice_profile=alan

# 查看
python3 ~/.hermes/skills/hermes-personality/scripts/mood_detector.py status
```

## 怎么写自己的 profile

1. 复制 `template.md`，改名为 `<你的名字>.md`
2. 按字段填（字段说明见 template.md 注释）
3. 用 `set-state voice_profile=<你的名字>` 激活

## 字段优先级

voice profile 的「情绪覆盖」会**补充并覆盖** phrase-pool.md 的通用句式：
- 覆盖字段里有的情绪：用 profile 的句式
- 没覆盖的情绪：沿用 phrase-pool.md 通用池
- 口头禅/禁用词/节奏：对所有情绪生效

## 设计原则

- profile 描述"这个人怎么说话"，不是"这个人是什么性格"
- 口头禅别超过 5 个，多了就成套路
- 禁用词列出来，避免 Hermes 用你不喜欢的表达
- 情绪覆盖只写你特别在意的情绪，不用全填
- 风格要自然，别写成角色扮演台词
