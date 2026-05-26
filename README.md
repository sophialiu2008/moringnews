# A股每日盘前情报简报系统

这是一个面向 A股交易研究的每日盘前自动化简报系统。系统通过 GitHub Actions 定时运行 Python 脚本，调用阿里云百炼 DashScope / 通义千问联网搜索最近 24 小时的 A股相关信息，生成 Markdown 简报，并可选调用 DeepSeek 做二次压缩、风险强化和微信摘要生成。

本项目只做信息收集、研究辅助和风险提示，不做自动交易。

## 功能列表

- 周一到周五北京时间 06:50 自动生成盘前简报
- 阿里百炼 OpenAI 兼容模式调用，默认模型 `qwen-max`
- 百炼主模型优先启用 `enable_search`
- `enable_search` 失败时自动降级普通模型调用
- 支持多阶段研究：资料收集、信号过滤、最终简报
- 支持简报质量检查，不达标时自动修订一次
- DeepSeek 可选二次优化，默认模型 `deepseek-chat`
- 自动生成 Markdown 文件到 `briefings/`
- 自动记录运行日志到 `logs/`
- 可选 Server酱 或 WxPusher 推送微信摘要
- 默认生成 10 分钟可读的盘前简报，微信摘要控制在 1000 字以内
- 支持本地手动运行和 GitHub Actions 手动触发
- 可选接入 AKShare，本地行情失败不影响主流程

## 目录结构

```text
a_stock_morning_brief/
  README.md
  requirements.txt
  .env.example
  config/
    settings.yaml
    research_context.md
    watchlist.yaml
    sources.yaml
  prompts/
    research_collection_prompt.txt
    signal_filter_prompt.txt
    morning_brief_prompt.txt
    deepseek_refine_prompt.txt
    quality_fix_prompt.txt
    wechat_summary_prompt.txt
  src/
    main.py
    llm_client.py
    bailian_client.py
    deepseek_client.py
    market_data.py
    brief_generator.py
    quality_checker.py
    file_writer.py
    notifier.py
    utils.py
  briefings/
    .gitkeep
  logs/
    .gitkeep
  .github/
    workflows/
      morning_brief.yml
```

## 配置阿里百炼 API Key

1. 登录阿里云百炼控制台。
2. 开通 DashScope / 通义千问模型服务。
3. 创建 API Key。
4. 本地运行时复制 `.env.example` 为 `.env`，填写：

```env
DASHSCOPE_API_KEY=your_dashscope_api_key
```

GitHub Actions 运行时，请把同名变量配置到 GitHub Secrets。

## 配置 DeepSeek API Key

DeepSeek 是可选项，用于二次优化简报和生成微信摘要。

```env
DEEPSEEK_API_KEY=your_deepseek_api_key
```

如果不配置 `DEEPSEEK_API_KEY`，系统会自动跳过 DeepSeek，不会中断主流程。

## 配置 Server酱微信推送

1. 登录 Server酱。
2. 获取 SendKey。
3. 配置环境变量：

```env
SERVERCHAN_SENDKEY=your_serverchan_sendkey
```

默认推送优先级为 Server酱优先。

## 配置 WxPusher

1. 创建 WxPusher 应用。
2. 获取 App Token。
3. 关注应用并获取 UID。
4. 配置环境变量：

```env
WXPUSHER_APP_TOKEN=your_wxpusher_app_token
WXPUSHER_UID=your_wxpusher_uid
```

## 配置 GitHub Secrets

进入仓库页面：

`Settings` -> `Secrets and variables` -> `Actions` -> `New repository secret`

建议配置：

- `DASHSCOPE_API_KEY`：必填
- `DEEPSEEK_API_KEY`：可选
- `SERVERCHAN_SENDKEY`：可选
- `WXPUSHER_APP_TOKEN`：可选
- `WXPUSHER_UID`：可选

## 本地手动运行

```powershell
cd E:\早信息推送\a_stock_morning_brief
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

编辑 `.env` 后运行：

```powershell
python src/main.py
```

生成结果在 `briefings/YYYY-MM-DD-A股盘前简报.md`。

## GitHub Actions 定时运行

工作流文件位于 `.github/workflows/morning_brief.yml`。

当前配置：

```yaml
schedule:
  - cron: "50 6 * * 1-5"
    timezone: "Asia/Shanghai"
```

GitHub 官方文档已支持 `timezone` 字段，因此这里直接使用北京时间。若你的仓库所在 GitHub 环境暂不支持该字段，可改成 UTC：

```yaml
schedule:
  - cron: "50 22 * * 0-4"
```

`22:50 UTC` 对应次日北京时间 `06:50`，所以周日到周四 UTC 运行，对应北京时间周一到周五早上。

## 手动触发 GitHub Actions

进入 GitHub 仓库：

1. 点击 `Actions`
2. 选择 `A股每日盘前简报`
3. 点击 `Run workflow`
4. 等待任务完成

任务成功后会自动提交 `briefings/` 和 `logs/` 中的新文件。

## 修改持仓列表

编辑 `config/watchlist.yaml`：

```yaml
holdings:
  - code: "301510"
    name: "固高科技"
    note: "当前持仓，重点检查减持、机器人板块退潮、技术破位风险"
```

持仓会进入盘前风险检查。

## 修改关注板块和股票

同样编辑 `config/watchlist.yaml`：

```yaml
watch_sectors:
  - AI算力
  - 半导体

watch_stocks:
  - code: "300308"
    name: "中际旭创"
```

这些内容会被拼接进主 Prompt，作为百炼联网搜索和简报生成的重点上下文。

## 修改模型名称

编辑 `config/settings.yaml`：

```yaml
llm:
  primary_model: qwen-max
  secondary_model: deepseek-chat
```

阿里百炼使用 OpenAI 兼容地址：

```text
https://dashscope.aliyuncs.com/compatible-mode/v1
```

DeepSeek 使用：

```text
https://api.deepseek.com
```

## 多阶段研究流程

默认启用多阶段研究，配置在 `config/settings.yaml`：

```yaml
search:
  enable_multistage_research: true
```

运行顺序：

1. `research_collection_prompt.txt`：按外围、政策、板块、公告、资金和持仓收集事实。
2. `signal_filter_prompt.txt`：剔除旧消息、弱相关消息和无来源消息。
3. `morning_brief_prompt.txt`：基于过滤后的信号生成最终简报。
4. `quality_checker.py`：检查栏目、板块数量、外围市场表格、持仓覆盖、来源数量和违规词。
5. `quality_fix_prompt.txt`：如果不达标，自动修订一次。

## 简报质量检查配置

编辑 `config/settings.yaml`：

```yaml
quality:
  enable_quality_check: true
  auto_fix: true
  max_fix_attempts: 1
  min_sections: 9
  min_global_market_rows: 8
  min_sector_count: 5
  min_source_count: 5
```

如果简报不足 5 个板块、未覆盖持仓股、来源太少或出现确定性投资表述，系统会自动尝试修订。

## 关闭 DeepSeek 二次优化

编辑 `config/settings.yaml`：

```yaml
llm:
  enable_deepseek_refine: false
```

关闭后系统直接使用阿里百炼生成的简报。

## 关闭微信推送

编辑 `config/settings.yaml`：

```yaml
notification:
  enable_wechat: false
```

关闭后仍会生成 Markdown 文件和日志。

## 可选启用 AKShare

默认不强制安装 AKShare。若你希望尝试本地行情补充：

```powershell
pip install akshare
```

并修改 `config/settings.yaml`：

```yaml
market:
  enable_akshare: true
```

AKShare 获取失败不会中断主流程，简报中允许写“暂未获取到可靠数据”。

## 常见问题

### 1. 提示缺少 DASHSCOPE_API_KEY

本项目主模型依赖阿里百炼。请确认本地 `.env` 或 GitHub Secrets 中已配置 `DASHSCOPE_API_KEY`。

### 2. DeepSeek 未配置会不会失败

不会。未配置 `DEEPSEEK_API_KEY` 时，系统自动跳过二次优化。

### 3. 微信推送失败会不会影响简报生成

不会。推送失败只写日志，不影响 Markdown 文件保存。

### 4. 百炼联网搜索失败怎么办

系统会记录 `enable_search` 的错误，并自动降级为普通模型调用。若普通模型调用也失败，主流程会失败退出。

### 5. 为什么有些数据写“暂未获取到可靠数据”

这是项目约束。没有可靠来源或模型无法验证时，必须明确说明，禁止编造。

### 6. GitHub Actions 没有自动提交

检查仓库 `Settings` -> `Actions` -> `General` 中的 workflow 权限，确保允许 `Read and write permissions`。本项目 workflow 已设置：

```yaml
permissions:
  contents: write
```

## 风险声明

本项目仅用于信息收集、研究辅助和风险提示，不构成任何投资建议。

本项目不提供自动交易功能。

用户应自行判断交易风险并独立决策。

所有股票、板块和方向只作为观察对象，不构成买入、卖出或持有建议。系统不会输出“必涨、必买、稳赚”等确定性投资表述。
