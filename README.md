# PsychoGAT 抑郁检测交互式小说游戏

基于 **PsychoGAT 框架**的抑郁症倾向检测交互式小说游戏。系统由 4 个 LLM 智能体协同工作，通过 9 轮交互式叙事完成 PHQ-9 量表的隐性评估。

## 系统架构

| 智能体 | 角色 | 运行次数 | 功能 |
|--------|------|---------|------|
| **设计师 (Designer)** | 游戏策划 | 第1次仅运行1次 | 根据PHQ-9生成游戏标题、大纲、量表 |
| **控制器 (Controller)** | 游戏编剧 | 每轮迭代1次 | 写故事段落 + 生成两个分支指令 |
| **评论家 (Critic)** | 游戏审核 | 每轮迭代1次 | 优化控制器输出 |
| **模拟器 (Simulator)** | 人类玩家 | 每轮迭代1次 | 模拟有/无抑郁倾向玩家，选择指令 |

共 **9 轮迭代**（对应 PHQ-9 的 9 个维度），每轮三步走：**控制器 → 评论家 → 模拟器**，最后算总分。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

复制 `.env.example` 为 `.env`，填入你的 DeepSeek API Key：

```bash
cp .env.example .env
# 编辑 .env 文件，填入 DEEPSEEK_API_KEY
```

在 [DeepSeek Platform](https://platform.deepseek.com/) 注册获取 API Key。

### 3. 运行

模拟器运行：
```bash
# 默认：抑郁倾向模拟
python run.py

# 指定参数
python run.py --game-type 奇幻 --game-topic 疗愈之旅 --simulator depressed --model deepseek-chat

# 健康对照
python run.py --simulator healthy

# 使用 DeepSeek-R1（推理模型）
python run.py --model deepseek-reasoner

# 详细输出
python run.py --verbose

# 保存完整游戏记录到文件
python run.py --output example_output/full_game_demo.md
```

真人交互运行：
```
  python web_app.py
  然后在浏览器打开 http://127.0.0.1:5000
```

## 隐私说明

- 所有数据仅通过 DeepSeek API 传输，不存储个人身份信息
- 本项目仅用于研究目的，不构成医疗建议
- 如有心理健康问题，请咨询专业医疗机构

## 输出示例

```
=== PsychoGAT 抑郁检测游戏 ===

[设计师] 游戏标题：光之碎片（Fragments of Light）
[设计师] 游戏类型：奇幻 | 主题：疗愈之旅

=== 第1轮迭代（兴趣减退）===
[控制器] 生成段落...
[评论家] 优化完成（连贯性 ✓ 无偏见 ✓ 无遗漏 ✓）
[模拟器（抑郁倾向）] 选择了指令1 → 得分：1

...

=== 最终结果 ===
总分：9/9
评估：重度抑郁倾向
```


