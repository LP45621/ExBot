# ExBot 技术架构白皮书

## 1. 四层提示词架构 (L1→L4 注入顺序)

```
┌──────────────────────────────────┐
│ L1 灵魂层 (SOUL_LAYER)          │ 永久注入 ~300 tokens
│ 核心哲学 + 六原型 + 四条铁律     │
│ + 深层法则 + 情绪托底技术        │
├──────────────────────────────────┤
│ L2 性格层 (build_personality)   │ 会话级 ~30 tokens
│ 8维参数 (温柔/活泼/傲娇/        │
│ 主动/话量/撒娇/吐槽/成熟)        │
├──────────────────────────────────┤
│ L3 记忆层 (HumanLikeMemory)     │ 动态 ~50 tokens
│ Ebbinghaus遗忘曲线 + 话题匹配    │
│ Top-K 检索 (K=3)                │
├──────────────────────────────────┤
│ L4 上下文层 (get_history)       │ 滑动窗口 ~200 tokens
│ 最近 N 轮对话 (N≤20)            │
│ 超出阈值触发异步压缩              │
└──────────────────────────────────┘
```

## 2. 节奏控制器算法

### 2.1 会话阶段检测
```
Phase = f(轮次, 会话时长):
  warming:  r ≤ 2                          → 温和，不追问
  engaged:  r > 2 且 session < 30min       → 自然变化
  deep:     30min ≤ session < 90min        → 更投入
  winding:  session ≥ 90min                → 简短收尾
```

### 2.2 回复长度分布模型
```
base_len ~ Uniform(base_min, base_max)
  warming:  (5, 15)
  engaged:  (6, 18)  
  deep:     (8, 22)
  winding:  (4, 12)
  cold:     (2, 6)      // 用户冷淡→极短
  sad≥2:    (12, 25)    // 情绪低落→托底更长

noise_factor = max(0.7, min(1.3, Gaussian(μ=1.0, σ=0.15)))
target_len = base_mid * noise_factor

P(极简回复) = 0.15   (is_cold ∧ ¬sad ∧ ¬angry)
P(长回复)   = 0.08   (phase=deep)
P(追问)     = 0.40   (phase=deep ∧ ¬cold ∧ ¬late)
            = 0.20   (phase=engaged ∧ ¬cold)
            = 0.30   (sad≥2)
```

### 2.3 时间感知修正
```
late_night  (22:00-06:00): max_len = min(max_len, 14), quiet mode
morning     (06:00-09:00): max_len += 2, warm greeting tone
```

## 3. 情绪托底五步法

```
Step 1: 定调 (Acknowledge Depth)
  "不是普通的累对吧" vs "好好休息"
  技术: 使用修饰词(普通/一般/表面)暗示已感知到超常状态

Step 2: 给许可 (Permission to Stay)
  "不用马上好起来" vs "你要振作"
  技术: 解除社会期望压力, 降低防御机制

Step 3: 具体化 (Precision Mirroring)
  "是那种连话都懒得说的累对不对" vs "辛苦了"
  技术: 身体感受+情绪标签的双重映射

Step 4: 当容器 (Be the Container)
  "多难听的话都可以倒给我"
  技术: 无条件接纳信号, 释放表达安全区

Step 5: 轻推不强迫 (Gentle Nudge)
  "你想从最难受的那件开始说 还是先安静待一会儿"
  技术: 二选一降低回复成本, 不给开放式压力
```

## 4. 记忆系统算法

### 4.1 Ebbinghaus 遗忘曲线
```
score = query_sim × 0.4 + (importance/10) × 0.3 + decay × 0.2 + reinforce × 0.1

decay = exp(-age_days / half_life)
half_life = importance × 5          // 重要性越高, 半衰期越长
reinforce = ln(recall_count + 1) × 0.15  // 回忆次数强化
```

### 4.2 话题匹配检索
```
sim(memory, query):
  if query ∈ memory.content:  sim = 0.9
  elif any(word ∈ memory.content for word in query):  sim = 0.5
  else:  sim = 0.3
```

## 5. 性格指令系统

### 5.1 8维参数空间
```
温柔 ∈ [-1,1]    活泼 ∈ [-1,1]    傲娇 ∈ [-1,1]    主动 ∈ [-1,1]
话量 ∈ [-1,1]    撒娇 ∈ [-1,1]    吐槽 ∈ [-1,1]    成熟 ∈ [-1,1]
```

### 5.2 自然语言→参数映射
```
"更傲娇一点" → 傲娇 += 0.25
"话少点"     → 话量 -= 0.2
"恢复"       → reset()
```

## 6. DeepSeek API 参数

```
model:       deepseek-chat
temperature: 0.85
max_tokens:  40
timeout:     8s (client), 4.9s (passive reply deadline)
```
