# AgentZero 覆盖式多语言说明

这个仓库当前采用“覆盖式本地化”方案：

- 上游源码保持不改
- 特定语言版本写入独立 overlay 目录
- 提取与回写通过 Codex skill 完成
- 实际翻译文本由用户在聊天外处理，降低 token 消耗

## 当前结构

- `E:\Agent\AgentZero\agent-zero\`
  上游项目目录，作为英文源组件使用

- `E:\Agent\AgentZero\agent-zero_CN\`
  中文运行入口和中文 overlay 目录

- `E:\Agent\AgentZero\agent-zero_CN\usr\webui\components\`
  中文组件覆盖目录

- `E:\Agent\AgentZero\.Codex\skills\overlay-localization\`
  通用覆盖式本地化 skill

- `E:\Agent\AgentZero\.overlay-localization.json`
  当前仓库的适配器配置

## 设计目标

- 不直接修改上游源码
- 通过 repo-local adapter 适配不同仓库结构
- 用 `linked-missing` 递归发现已接入页面引用到但尚未翻译的二级组件
- 把翻译文本导出到本地文件，让用户离线编辑，避免把大段内容送进对话

## 当前仓库适配器

`E:\Agent\AgentZero\.overlay-localization.json` 已经配置好当前项目：

- 源目录：`agent-zero/webui/components`
- 中文 overlay 目录模板：`agent-zero_{lang}/usr/webui/components`
- 翻译包目录模板：`agent-zero_{lang}/usr/translation`

当前默认语言是 `CN`，因此实际输出会落到：

- `E:\Agent\AgentZero\agent-zero_CN\usr\webui\components\`
- `E:\Agent\AgentZero\agent-zero_CN\usr\translation\`

## 推荐流程

### 1. 导出 JSON + 纯文本翻译包

```powershell
py -3.12 E:\Agent\AgentZero\.Codex\skills\overlay-localization\scripts\export_bundle.py --adapter E:\Agent\AgentZero\.overlay-localization.json --text-output E:\Agent\AgentZero\agent-zero_CN\usr\translation\component-texts-linked-missing.txt
```

这会生成：

- `E:\Agent\AgentZero\agent-zero_CN\usr\translation\component-texts-linked-missing.json`
- `E:\Agent\AgentZero\agent-zero_CN\usr\translation\component-texts-linked-missing.txt`

默认模式是 `linked-missing`，适合当前项目，扫描速度快，也能把一级菜单引用到的二级菜单和子页面一起带出来。

### 2. 用户编辑纯文本翻译包

推荐编辑 `.txt` 文件，只改 `T "..."` 行，不改 `@@` 和 `S` 行。

示例：

```text
@@ settings/a2a/a2a-server.html:text:27
S "A0 A2A Server"
T "A0 A2A 服务器"
```

说明：

- `@@`：条目标识，不能改
- `S`：源文本，不能改
- `T`：目标翻译，只改这一行

如果你更喜欢 JSON，也可以直接编辑每条记录里的 `translation` 字段。

### 3. 导入纯文本翻译包回 JSON

```powershell
py -3.12 E:\Agent\AgentZero\.Codex\skills\overlay-localization\scripts\import_text_bundle.py --bundle E:\Agent\AgentZero\agent-zero_CN\usr\translation\component-texts-linked-missing.json --text-input E:\Agent\AgentZero\agent-zero_CN\usr\translation\component-texts-linked-missing.txt
```

### 4. 回写到中文 overlay

```powershell
py -3.12 E:\Agent\AgentZero\.Codex\skills\overlay-localization\scripts\apply_bundle.py --adapter E:\Agent\AgentZero\.overlay-localization.json
```

回写目标只会是：

- `E:\Agent\AgentZero\agent-zero_CN\usr\webui\components\`

不会修改：

- `E:\Agent\AgentZero\agent-zero\webui\components\`

## 常用命令

### 只导出，不生成纯文本

```powershell
py -3.12 E:\Agent\AgentZero\.Codex\skills\overlay-localization\scripts\export_bundle.py --adapter E:\Agent\AgentZero\.overlay-localization.json
```

### 全量扫描

```powershell
py -3.12 E:\Agent\AgentZero\.Codex\skills\overlay-localization\scripts\export_bundle.py --adapter E:\Agent\AgentZero\.overlay-localization.json --mode all
```

### 先写到测试目录，不直接覆盖正式组件

```powershell
py -3.12 E:\Agent\AgentZero\.Codex\skills\overlay-localization\scripts\apply_bundle.py --adapter E:\Agent\AgentZero\.overlay-localization.json --target-root E:\Agent\AgentZero\agent-zero_CN\usr\translation\test-output --no-backup
```

## 模式说明

- `linked-missing`
  从当前 overlay 中已存在的文件出发，递归追踪引用到但未翻译的子组件。默认推荐。

- `missing`
  扫描上游目录中所有未被 overlay 覆盖的组件。

- `existing`
  导出已经有 overlay 的组件，适合校对和补翻。

- `all`
  全量导出所有组件。

## Token 说明

这个流程的目标是降低对话 token 消耗。

本地脚本做的事情：

- 扫描文件
- 提取文本
- 生成 JSON/TXT 翻译包
- 回写 overlay 文件

这些都发生在本地，不会天然转成对话 token。

真正会消耗大量 token 的情况是：

- 把大段导出内容直接贴进聊天
- 让模型在对话里逐条翻译
- 让模型在对话里做大规模校对

因此当前推荐流程是：

- 本地导出
- 用户本地编辑翻译文件
- 本地导回和回写

## 注意事项

- 不要直接修改 `agent-zero/` 里的上游组件。
- 如果上游组件在导出后发生变化，回写时会因为 hash 校验失败而拒绝覆盖；这时重新导出即可。
- 修改完中文组件后，如果页面还显示旧内容，先关闭弹窗再打开；必要时刷新页面。
- `.Codex\skills\overlay-localization\` 是当前仓库内的通用 skill 位置。
- 根目录无扩展名的 `Readme` 文件仍然保留，主要是维护和提交流程笔记；本文件 `README.md` 负责本地化工作流说明。
