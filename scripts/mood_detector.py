#!/usr/bin/env python3
"""
hermes-personality: 情绪状态追踪器 v1.1.0

管理 state.json 的读写，提供情绪分析和状态报告功能。

用法:
  python3 mood_detector.py init                # 初始化新 session 的 state.json
  python3 mood_detector.py analyze             # 分析当前状态，输出情绪建议 + 原因
  python3 mood_detector.py status              # 查看完整状态
  python3 mood_detector.py set-state [k=v...]  # 批量设置字段，如 failures_this_session=2
  python3 mood_detector.py history             # 查看情绪变化历史

v1.1.0 更新:
  - GRIT 优先级提升到 PEEVED 之上（GRIT 终于能实际触发）
  - 强度分级计算 (mild/normal/strong)
  - phrase-pool 选择追踪 (last_phrase / last_scene)
  - user_tone_hints 自动衰减（2 轮无更新则清除）
  - 时间感知（深夜自动偏斜 LIMP）
  - avg_task_duration_sec 自动计算
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SKILL_DIR = Path.home() / ".hermes" / "skills" / "hermes-personality"
STATE_FILE = SKILL_DIR / "state.json"
DEFAULT_STATE = {
    "session_id": "",
    "session_start": "",
    "turns": 0,
    "tasks_this_session": 0,
    "retries": 0,
    "failures_this_session": 0,
    "user_tone_hints": [],
    "user_interruptions": 0,
    "avg_task_duration_sec": 0,
    "current_mood": "STRAIGHT",
    "mood_history": [],
    "complex_tasks": 0,
    "repetitive_tasks": 0,
    "voice_profile": "default",
    # v1.1.0 新增字段
    "intensity": "normal",
    "last_phrase": "",
    "last_scene": "",
    "last_active": "",
    "tone_update_turn": 0,
    "_task_start_ts": 0.0,  # 内部字段：任务开始时间戳
}

MOOD_ORDER = ["STRAIGHT", "ZONED", "GLAD", "PEEVED", "GRIT", "BOGGLED", "CHEEKY", "LIMP"]

# ─── 情绪转移规则 ──────────────────────────────────────────
# v1.1.0: GRIT priority > PEEVED（GRIT 代表"还在战"，PEEVED 代表"不想战了"）
# v1.1.0: PEEVED 新增 "failures>=2 AND retries==0" 条件
# v1.1.0: 深夜时间偏斜（hour 条件在 evaluate_condition 中可用）

MOOD_TRIGGERS: Dict[str, List[Dict[str, Any]]] = {
    "STRAIGHT": [
        {"reason": "默认状态", "priority": 0},
    ],
    "ZONED": [
        {"condition": "complex_tasks >= 1 and failures_this_session == 0 and turns >= 3",
         "reason": "深度工作中，进展顺利", "priority": 7},
        {"condition": "turns >= 3 and retries <= 1 and tasks_this_session >= 1",
         "reason": "专注执行中", "priority": 6},
    ],
    "GLAD": [
        {"condition": "tasks_this_session >= 1 and failures_this_session == 0 and 'appreciative' in user_tone_hints",
         "reason": "任务完成 + 用户认可", "priority": 8},
        {"condition": "tasks_this_session >= 3 and failures_this_session <= 1",
         "reason": "连续完成多个任务", "priority": 7},
        {"condition": "tasks_this_session >= 2 and failures_this_session == 0",
         "reason": "顺利完成任务", "priority": 6},
    ],
    # v1.1.0: GRIT 优先级 (9/8) > PEEVED (6/5/4)
    # 只要有 retries>0，GRIT 就压住 PEEVED
    "GRIT": [
        {"condition": "retries >= 2 and failures_this_session >= 1",
         "reason": "屡败屡战，不放弃", "priority": 9},
        {"condition": "complex_tasks >= 1 and retries >= 2",
         "reason": "复杂问题卡住了还在推", "priority": 8},
    ],
    # v1.1.0: PEEVED 只在不重试时触发，或重试过度到耐心耗尽
    "PEEVED": [
        {"condition": "failures_this_session >= 2 and retries == 0",
         "reason": "连续失败且无后续尝试", "priority": 6},
        {"condition": "retries >= 5",
         "reason": "反复重试耐心耗尽", "priority": 5},
        {"condition": "user_interruptions >= 3",
         "reason": "用户频繁打断", "priority": 5},
        {"condition": "user_interruptions >= 2",
         "reason": "被中途打断", "priority": 4},
    ],
    "BOGGLED": [
        {"condition": "turns >= 1 and turns <= 5 and tasks_this_session == 0 and retries == 0",
         "reason": "初期需求不明确", "priority": 5},
        {"condition": "'vague' in user_tone_hints",
         "reason": "用户输入模糊", "priority": 7},
    ],
    "CHEEKY": [
        {"condition": "tasks_this_session >= 2 and failures_this_session == 0 and turns >= 5",
         "reason": "进展顺利，氛围轻松", "priority": 6},
        {"condition": "'playful' in user_tone_hints",
         "reason": "用户先玩梗", "priority": 7},
    ],
    # v1.1.0: turns >= 25 才触发（之前 20 太频繁），增加夜间偏斜
    "LIMP": [
        {"condition": "turns >= 25",
         "reason": "对话太长，精力下降", "priority": 7},
        {"condition": "repetitive_tasks >= 3",
         "reason": "重复性任务过多", "priority": 6},
        {"condition": "hour >= 23 or hour <= 6",
         "reason": "深夜了，精力不济", "priority": 5},
    ],
}


# ─── 辅助函数 ──────────────────────────────────────────────


def load_state() -> Dict[str, Any]:
    """加载 state.json，不存在则返回默认值"""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            print("⚠️  state.json 损坏，使用默认值", file=sys.stderr)
    return dict(DEFAULT_STATE)


def save_state(state: Dict[str, Any]) -> None:
    """写入 state.json"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    print(f"✅ 状态已保存 → {STATE_FILE}")


def generate_session_id() -> str:
    """生成简短 session ID"""
    import hashlib, random
    raw = f"{time.time()}{random.random()}"
    return hashlib.md5(raw.encode()).hexdigest()[:8]


def evaluate_condition(condition: str, state: Dict[str, Any]) -> bool:
    """安全评估条件字符串——仅支持字段名 + int/float/str 比较 + list membership。

    v1.1.0: 新增 hour 变量（当前小时 0-23）用于夜间偏斜判断

    支持的语法:
      field >= N       — 数值比较
      field <= N       — 数值比较
      field >= N and ... — and 组合
      'x' in field     — list/str membership
      'x' not in field — list/str non-membership
      hour >= 23       — 时间比较（自动注入当前小时）
    """
    s = condition.strip()
    local_vars = dict(state)
    local_vars["user_tone_hints"] = state.get("user_tone_hints", [])
    local_vars["hour"] = datetime.now().hour  # v1.1.0: 注入当前小时

    def _get_val(name: str):
        name = name.strip()
        if name in local_vars:
            return local_vars[name]
        try:
            return json.loads(name)
        except (json.JSONDecodeError, TypeError):
            return name.strip("'\"")

    def _eval_simple(expr: str) -> bool:
        expr = expr.strip()
        # 'x' in field / 'x' not in field
        import re
        m = re.match(r"""('[^']*'|"[^"]*")\s+(not\s+)?in\s+(\w+)""", expr)
        if m:
            val = _get_val(m.group(1))
            negate = bool(m.group(2))
            container = _get_val(m.group(3))
            if isinstance(container, (list, str)):
                result = val in container
                return not result if negate else result
            return False

        # field op value
        m = re.match(r"""(\w+)\s*(>=|<=|==|!=|>|<)\s*(.+)""", expr)
        if m:
            field, op, raw_val = m.group(1), m.group(2), m.group(3).strip()
            actual = _get_val(field)
            expected = _get_val(raw_val)
            try:
                if op == ">=": return actual >= expected
                elif op == "<=": return actual <= expected
                elif op == "==": return actual == expected
                elif op == "!=": return actual != expected
                elif op == ">":  return actual > expected
                elif op == "<":  return actual < expected
            except TypeError:
                return False

        return False

    # 支持 and 组合
    parts = [p.strip() for p in s.split(" and ")]
    return all(_eval_simple(p) for p in parts)


# ─── v1.1.0 新增: 强度分级 ─────────────────────────────────


def calculate_intensity(mood: str, state: Dict[str, Any]) -> str:
    """根据情绪和状态计算强度级别 mild / normal / strong"""
    t = state.get("tasks_this_session", 0)
    f = state.get("failures_this_session", 0)
    r = state.get("retries", 0)
    c = state.get("complex_tasks", 0)
    tn = state.get("turns", 0)
    hints = state.get("user_tone_hints", [])
    rep = state.get("repetitive_tasks", 0)

    if mood == "GLAD":
        if t >= 3 and f == 0: return "strong"
        if t >= 2: return "normal"
        return "mild"
    elif mood == "PEEVED":
        if f >= 3 or r >= 8: return "strong"
        if f >= 2 or r >= 5: return "normal"
        return "mild"
    elif mood == "GRIT":
        if r >= 4 and f >= 2: return "strong"
        if r >= 2 and f >= 1: return "normal"
        return "mild"
    elif mood == "ZONED":
        if c >= 2: return "strong"
        if c >= 1: return "normal"
        return "mild"
    elif mood == "BOGGLED":
        if tn <= 2: return "strong"
        if "vague" in hints: return "normal"
        return "mild"
    elif mood == "CHEEKY":
        if "playful" in hints and t >= 3: return "strong"
        if "playful" in hints: return "normal"
        return "mild"
    elif mood == "LIMP":
        if tn >= 35: return "strong"
        if tn >= 25 or rep >= 5: return "normal"
        return "mild"
    return "normal"


# ─── v1.1.0 新增: 用户语气衰减 ────────────────────────────


def decay_tone_hints(state: Dict[str, Any]) -> bool:
    """如果过去 2 轮内没有更新用户语气，清空 hints。返回是否清除了。"""
    tone_update = state.get("tone_update_turn", 0)
    current_turns = state.get("turns", 0)
    hints = state.get("user_tone_hints", [])

    if not hints:
        return False

    if current_turns - tone_update >= 2:
        state["user_tone_hints"] = []
        return True
    return False


# ─── 情绪分析核心 ────────────────────────────────────────


def suggest_mood(state: Dict[str, Any]) -> Tuple[str, str]:
    """根据当前状态计算最合适的情绪"""
    candidates: List[Tuple[int, str, str]] = []  # (priority, mood, reason)

    for mood, triggers in MOOD_TRIGGERS.items():
        for trigger in triggers:
            if "condition" in trigger:
                if evaluate_condition(trigger["condition"], state):
                    candidates.append((trigger["priority"], mood, trigger["reason"]))
            else:
                # 无条件触发（STRAIGHT）
                candidates.append((trigger["priority"], mood, trigger["reason"]))

    if not candidates:
        return ("STRAIGHT", "默认状态（无触发条件）")

    # 按优先级排序
    candidates.sort(key=lambda x: x[0], reverse=True)
    return (candidates[0][1], candidates[0][2])


def check_mood_jump(current: str, suggested: str) -> Tuple[bool, str]:
    """检查情绪跳转是否合理（不能跳太多级）"""
    if current == suggested:
        return (True, "")

    # 特殊规则：STRAIGHT 可以转任何情绪
    if current == "STRAIGHT":
        return (True, "")

    get_idx = lambda m: MOOD_ORDER.index(m) if m in MOOD_ORDER else -1
    ci, si = get_idx(current), get_idx(suggested)
    if ci < 0 or si < 0:
        return (True, "")

    delta = abs(si - ci)
    if delta > 2:
        return (False, f"⚠️  情绪跳跃过大（{current}→{suggested}，跨度{delta}级），降级为 STRAIGHT（规则：每次最多移2级）")

    if delta > 1:
        return (True, f"ℹ️  情绪跨度较大（{current}→{suggested}，跨{delta}级）")

    return (True, "")


# ─── v1.1.0 新增: 检查旧 session ─────────────────────────


def check_stale_session(state: Dict[str, Any]) -> Optional[str]:
    """检查是否可能是旧 session 残留。返回提示信息或 None。"""
    if not state.get("session_id"):
        return None
    last_active = state.get("last_active", "")
    if not last_active:
        return None
    try:
        last_dt = datetime.fromisoformat(last_active)
        delta = datetime.now() - last_dt
        if delta.total_seconds() > 1800:  # 30 min
            return f"⚠️  Session 上次活跃在 {delta.seconds // 60} 分钟前。如果是新对话，请运行 init 重置状态。"
    except (ValueError, TypeError):
        pass
    return None


# ─── CLI 命令 ──────────────────────────────────────────────


def cmd_init() -> None:
    """初始化新 session 的 state.json"""
    state = dict(DEFAULT_STATE)
    state["session_id"] = generate_session_id()
    state["session_start"] = datetime.now().isoformat()
    state["current_mood"] = "STRAIGHT"
    state["mood_history"] = [{"turn": 0, "mood": "STRAIGHT", "trigger": "session_start"}]
    state["last_active"] = datetime.now().isoformat()
    save_state(state)
    print(f"🆕 Session {state['session_id']} 已初始化")
    print(f"📅 {state['session_start']}")
    print(f"🎭 初始情绪: STRAIGHT")
    print(f"📊 强度: normal | 时间: {datetime.now().hour}:00")


def cmd_analyze() -> None:
    """分析当前状态并输出情绪建议（v1.1.0: 含强度分级、Stale Session 检查、语气衰减）"""
    state = load_state()
    if not state.get("session_id"):
        print("❌ 状态未初始化，先运行 init")
        return

    # 语气衰减
    decayed = decay_tone_hints(state)
    if decayed:
        print("🧹 用户语气已衰减（2 轮无更新）")
        save_state(state)

    # 旧 session 检查
    stale_msg = check_stale_session(state)

    current_mood = state.get("current_mood", "STRAIGHT")
    suggested_mood, reason = suggest_mood(state)
    ok, msg = check_mood_jump(current_mood, suggested_mood)

    final_mood = suggested_mood if ok else "STRAIGHT"
    final_reason = reason if ok else "（因跳跃过大降级）"
    intensity = calculate_intensity(final_mood, state)

    time_str = f"{datetime.now().hour}:{datetime.now().minute:02d}"

    result = {
        "session_id": state["session_id"],
        "turns": state["turns"],
        "tasks": state["tasks_this_session"],
        "failures": state["failures_this_session"],
        "retries": state["retries"],
        "current_mood": current_mood,
        "suggested_mood": suggested_mood if ok else "STRAIGHT",
        "suggestion_reason": final_reason,
        "mood_jump_check": msg if msg else "ok",
        "final_mood": final_mood,
        "intensity": intensity,  # v1.1.0
        "time": time_str,  # v1.1.0
        "voice_profile": state.get("voice_profile", "default"),
        "user_tone_hints": state.get("user_tone_hints", []),
        "tone_decayed": decayed,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if stale_msg:
        print(stale_msg, file=sys.stderr)


def cmd_status() -> None:
    """查看完整状态（v1.1.0: 新增字段）"""
    state = load_state()
    if not state.get("session_id"):
        print("❌ 状态未初始化")
        return

    print(f"📋 Session: {state['session_id']}")
    print(f"📅 开始: {state['session_start']}")
    print(f"🔄 轮次: {state['turns']}")
    print(f"✅ 完成任务: {state['tasks_this_session']}（平均时长: {state['avg_task_duration_sec']}s）")
    print(f"❌ 失败: {state['failures_this_session']}")
    print(f"🔁 重试: {state['retries']}")
    print(f"🎭 当前情绪: {state['current_mood']}")
    print(f"📊 强度: {state.get('intensity', 'normal')}")  # v1.1.0
    print(f"🎬 情绪历史: {len(state['mood_history'])} 次变化")
    print(f"📊 复杂任务: {state['complex_tasks']} | 重复任务: {state['repetitive_tasks']}")
    print(f"📝 用户语气记录: {state['user_tone_hints']}（上次更新: 第{state.get('tone_update_turn', 0)}轮）")
    print(f"🎙️ 语言习惯: {state.get('voice_profile', 'default')}")
    print(f"🗣️ 上次选用短语: {state.get('last_phrase', '无')}（场景: {state.get('last_scene', '无')}）")  # v1.1.0
    print(f"⏱️ 最后活跃: {state.get('last_active', '无')}")  # v1.1.0
    print(f"🕐 当前时间: {datetime.now().hour}:{datetime.now().minute:02d}")

    if state["mood_history"]:
        print(f"\n  情绪变化时间线:")
        for entry in state["mood_history"]:
            print(f"    第{entry['turn']}轮: {entry['mood']} ← {entry['trigger']}")


def cmd_set_state(kvs: List[str]) -> None:
    """设置状态字段（v1.1.0: 自动更新 last_active / tone_update_turn / avg_task_duration_sec）"""
    state = load_state()
    current_mood = state.get("current_mood", "STRAIGHT")
    mood_changed = False

    for kv in kvs:
        if "=" not in kv:
            print(f"⚠️  跳过 {kv}（格式应为 key=value）")
            continue
        key, val = kv.split("=", 1)
        key = key.strip()
        if key not in DEFAULT_STATE and key != "current_mood":
            print(f"⚠️  未知字段: {key}，仍将写入")

        # 类型推断
        LIST_FIELDS = {"user_tone_hints"}
        FLOAT_FIELDS = {"avg_task_duration_sec"}

        old_val = state.get(key)

        if key in LIST_FIELDS:
            val = [v.strip() for v in val.split(",") if v.strip()]
        elif key in FLOAT_FIELDS:
            try:
                val = float(val)
            except ValueError:
                val = 0.0
        else:
            try:
                if "." in val:
                    val = float(val)
                else:
                    val = int(val)
            except ValueError:
                if val.lower() in ("true", "false"):
                    val = val.lower() == "true"
                else:
                    pass  # 保持字符串

        state[key] = val
        print(f"  {key}: {old_val} → {val}")

    # v1.1.0: 如果更新了 user_tone_hints，记录当前轮次
    tone_keys = [kv.split("=", 1)[0].strip() for kv in kvs]
    if "user_tone_hints" in tone_keys:
        state["tone_update_turn"] = state.get("turns", 0)
        print(f"  📝 tone_update_turn → {state['tone_update_turn']}")

    # v1.1.0: 如果更新了 tasks_this_session（任务完成），计算 avg_task_duration_sec
    if "tasks_this_session" in tone_keys:
        task_start = state.get("_task_start_ts", 0.0)
        if task_start > 0:
            duration = time.time() - task_start
            tasks_done = state.get("tasks_this_session", 1)
            old_avg = state.get("avg_task_duration_sec", 0.0)
            # 滚动平均
            if tasks_done > 1:
                new_avg = ((old_avg * (tasks_done - 1)) + duration) / tasks_done
            else:
                new_avg = duration
            state["avg_task_duration_sec"] = round(new_avg, 1)
            state["_task_start_ts"] = 0.0  # 重置
            print(f"  ⏱️ 任务耗时: {duration:.1f}s → avg_task_duration_sec: {new_avg:.1f}s")

    # 更新 last_active
    state["last_active"] = datetime.now().isoformat()

    # 自动重算情绪
    if "current_mood" not in tone_keys:
        suggested_mood, reason = suggest_mood(state)
        ok, msg = check_mood_jump(current_mood, suggested_mood)
        final_mood = suggested_mood if ok else "STRAIGHT"
        if final_mood != current_mood:
            state["current_mood"] = final_mood
            state["mood_history"].append({
                "turn": state.get("turns", 0),
                "mood": final_mood,
                "trigger": reason,
            })
            # v1.1.0: 情绪变化时自动计算强度
            state["intensity"] = calculate_intensity(final_mood, state)
            print(f"🎭 情绪变化: {current_mood} → {final_mood}（{reason}）")
            print(f"📊 强度: {state['intensity']}")
            mood_changed = True

    save_state(state)
    if not mood_changed:
        print("🎭 情绪无变化")


def cmd_history() -> None:
    """查看情绪变化历史"""
    state = load_state()
    if not state.get("mood_history"):
        print("📭 没有情绪变化记录")
        return

    print(f"📜 情绪变化历史 ({len(state['mood_history'])} 次):")
    for entry in state["mood_history"]:
        trigger = entry.get("trigger", "")
        print(f"  第{entry['turn']}轮: {entry['mood']} ← {trigger}")


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]
    args = sys.argv[2:]

    commands = {
        "init": cmd_init,
        "analyze": cmd_analyze,
        "status": cmd_status,
        "history": cmd_history,
        "set-state": lambda: cmd_set_state(args),
    }

    if cmd in commands:
        commands[cmd]()
    else:
        print(f"❌ 未知命令: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
