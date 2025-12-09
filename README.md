# Notion 时间记录小工具

一个极简的命令行计时器：本地点击/运行 `start` 开始计时，`stop` 时自动把项目、任务、起止时间和耗时写入你的 Notion 数据库。适合做番茄/专注计时并按时间顺序在 Notion 留档统计。

## 前置准备
1. 在 Notion 创建一个数据库，包含以下属性（可按需重命名，但需要与脚本中的属性对应）：
   - **Task**：`Title`
   - **Project**：`Select`
   - **Start**：`Date`
   - **End**：`Date`
   - **Duration (minutes)**：`Number`
2. 在 [Notion Integrations](https://www.notion.so/my-integrations) 创建一个集成，复制集成密钥。
3. 将数据库与该集成共享（右上角 “分享” → “邀请” → 选择集成）。
4. 在本地设置环境变量（推荐写入 `.env` 或 shell 配置）：
   ```bash
   export NOTION_TOKEN="secret_xxx"      # 集成密钥
   export NOTION_DATABASE_ID="xxxxxxxx"  # 数据库 ID（URL 中的中间一段）
   ```

## 安装
```bash
pip install -r requirements.txt
```

## 不用命令行：桌面小窗口
1. 保证已设置 `NOTION_TOKEN` 和 `NOTION_DATABASE_ID` 环境变量（同上）。
2. 运行桌面窗口（使用系统自带的 Tk，无需额外安装）：
   ```bash
   python notion_tray.py
   ```
3. 在窗口里填写 “项目”“任务” 后点 **开始计时**，完成时点 **停止并写入 Notion**。
   - “刷新状态” 按钮可同步当前是否有在计时（会读取 `.notion_timer_state.json`）。
   - 成功后会弹窗提示并清空状态，记录会写入同一个 Notion 数据库。

## 使用（快速上手）
1. **进入项目目录**：
   ```bash
   cd notion-
   ```

2. **确保环境变量已设置**（或在命令里传入 `--token` / `--database-id`）：
   ```bash
   echo $NOTION_TOKEN        # 应该能看到以 secret_ 开头的一段字符串
   echo $NOTION_DATABASE_ID  # 应该能看到一串 UUID
   ```

3. **开始一段计时**（映射到「图1」里你点击的项目/事项）：
   ```bash
   python notion_timer.py start "项目名称" "具体事项"
   # 例：python notion_timer.py start "写周报" "整理本周亮点"
   ```

4. **查看当前状态**（可选）：
   ```bash
   python notion_timer.py status
   ```

5. **停止计时并写入 Notion**：
   ```bash
   python notion_timer.py stop
   ```

6. **在 Notion 里查看记录**：数据库会多出一行，按时间顺序展示「开始/结束/耗时/项目/事项」，可在 Notion 里创建视图和 rollup 做总计统计（对应「图2」）。

> 小提示
> - 项目名称会写入 `Project` 选择属性；如不存在，Notion 会自动创建新的选项。
> - 任务名称写入 `Task` 标题属性。
> - `Start/End` 使用本地带时区的时间戳。
> - `Duration (minutes)` 为分钟数（保留两位小数），可在 Notion 里使用 rollup/公式做总计统计。

## 常见问题
- **提示缺少 token 或 database id**：确认环境变量是否设置，或使用 `--token`、`--database-id` 参数显式传入。
- **Notion 返回属性名错误**：确保数据库的属性名称与脚本中的默认名称一致，或在 Notion 中创建对应属性。
- **正在计时却又想重来**：删除当前目录下的 `.notion_timer_state.json` 后重新 `start`。

## 与图示的对应
- “时间流”中的每个按钮可映射为 `Project`，具体事项写在 `Task`。
- 每次 `start` → `stop` 会在 Notion 数据库生成一行，按时间顺序排列，方便做总计视图或仪表盘。
