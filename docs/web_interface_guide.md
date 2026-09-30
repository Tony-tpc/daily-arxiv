# 企业能源情报工作台使用指南

面向能源企业管理层、研究和战略团队，首页呈现重点资料与趋势信号，资料页提供筛选、比较和证据回查。界面支持中文与英文，沿用配置中的产品名称和语言设置。

## 启动与技术栈

使用项目可用的 Python 环境安装依赖后，运行 `python src/web/app.py`，访问 `http://localhost:5000/`。Windows 终端建议设置 `PYTHONUTF8=1` 和 `PYTHONIOENCODING=utf-8`。服务地址和端口由 `config/config.yaml` 的 `web` 配置决定。

后端为 Flask/Jinja；前端为原生 JavaScript、Bootstrap 5 和 Chart.js。线性图标使用本地 `static/css/icons.css` 内的 SVG，不依赖图标字体 CDN。模板位于 `src/web/templates/index.html`，浏览器资源位于仓库根目录 `static/`。

## 页面与操作

- **概览**：四类来源的数量对应当前已应用的首页筛选；最多展示 8 条重点信息。分析生成时间来自分析产物，与每条资料的发布日期分别展示。重点列表优先展示资料摘要，完整摘要和推荐依据按需展开；趋势依据使用同一证据抽屉。来源数量入口可进入对应目录。
- **论文列表**：类别筛选使用服务端能力；标题／作者／关键词搜索、优先级与排序作用于当前加载页，页头会注明总量和本页匹配数。每页可选择 10、20 或 50 篇。
- **中国政策、国内新闻、行业报告**：搜索、主题、日期、优先级、排序通过原有目录 API 执行；每页 20 条，支持上一页／下一页。常用搜索和排序直接显示，主题、日期与优先级可展开；已应用条件在收起后仍可见。结果分别列出总数、匹配数和本页数量。
- **资料详情**：点击“展开资料与分析依据”查看完整摘要、评分、结构化知识和关联信息。原文和有效的独立全文地址在新标签打开；与原文相同的 PDF 地址不重复展示。没有地址时不生成占位链接。评分为 0–100 分的阅读排序依据；缺失评分不显示成零。
- **论文研究报告**（`#paper-report`）：独立分析论文的研究问题、方法差异、实验依据、局限和可验证的研究想法。
- **政策分析**（`#policy-analysis`）：只使用国内政策证据，分析目标、适用边界、执行机制以及对研究设计的影响，区分政策规定与技术推论。
- **趋势分析**（`#analysis`）：结合论文、政策、新闻与行业报告，论证技术演进、来源间分歧和未来研究方向。三类正文均采用连续段落，并保留逐条证据回查。
- **汇总报告**（`#reports`）：完整流程同时保存周报和阶段报告，汇集上述三类正文和来源附录。周期内资料数量与正文历史证据范围分别说明。

- **统计数据**：比较标签出现次数、有记录日期的资料分布、来源与实体提及，以及方法矩阵和文献对比。标签可重复计数，不转换成占比；时间线只列出有记录日期，不对缺失日期补零或插值。图表明确范围和单位。矩阵和对比表使用当前加载的论文页，字段不截断；宽表仅在表格容器内部滚动。词云是检索辅助，不代表战略重要性。

先运行 `python main.py` 才会完成采集、总结、知识抽取、三类正文写作和报告保存；只启动 Flask 不会调用模型生成正文。页面刷新读取最新结果，不会把已生成的正文替换为离线模板。没有当前分析产物时显示“临时证据整理稿”，生成失败原因另行显示，不能把整理稿算作正式成文分析。

正文证据只使用已取得的原始摘要或正文，系统生成的旧摘要不作为事实来源。仅有简短发布信息的行业报告保留题录并标记正文不足，获取附件前不推断报告中的统计数据。2026-09-29 的完整运行、正文审校与页面验证见 [报告恢复验收](report_restoration_2026-09-29.md)。

十个页面使用 `#overview`、`#papers`、`#policies`、`#news`、`#industry-reports`、`#paper-report`、`#policy-analysis`、`#analysis`、`#reports`、`#statistics` 地址，可直接打开、刷新和前进后退。同一会话中切换页面不会清除筛选；“清除筛选”按钮恢复当前页面的默认条件。重新刷新页面会重置筛选条件。

## 主题、键盘与响应式

默认使用 Notion 风格浅色主题：米色（`#f7f6f3`）侧栏与资料块、白色阅读区、深灰（`#37352f`）正文及细边框。桌面侧栏宽 240px；视口小于 1024px 时使用导航抽屉，小于 768px 时筛选与资料纵向排列。顶栏面包屑跟随当前页面；主题按钮可切换中性深色并保存在浏览器中。

按钮使用透明底色，悬停背景为 `#efedea`，按下背景为 `#e3e1db`，过渡为 150ms；没有位移、缩放、渐变或悬停阴影。资料块悬停或内部控件获得焦点时显示 `⋮⋮`，仅作为装饰提示，不支持拖动排序。正文最大行宽为 72ch；键盘焦点保留清晰轮廓，减少动态效果偏好下关闭过渡。

所有主要操作可通过键盘完成。证据抽屉和移动导航支持 Escape 关闭、Tab 焦点约束及关闭后返回触发控件；趋势选项卡支持左右方向键。移动端目录默认折叠。请求失败可重试，尚无数据、无匹配结果和加载失败分别展示；论文类别或结构化知识不可用时保留已加载资料并单独提供重试。

## 回归验证

```bash
python -m unittest discover -s test -p "test_*.py"
node --test test/web_workspace.test.cjs
node --check static/js/main.js
git diff --check
```

前端行为测试覆盖 hash 导航、筛选保留、目录分页、过期请求、评分缺失、外链与转义、报告证据及统计口径。实际浏览器验收记录与截图见 [2026-09-29 界面验收](ui_review_2026-09-29.md)。

隔离边界页可用 `python -m test.manual_web_fixtures` 在 5002 端口启动，支持 `?case=fail-once`、`?case=sparse`、`?case=many`、`?case=empty` 和 `&language=en`。模拟数据仅在该标签页内存中存在，绝不写入资料库；该脚本不用于生产部署。

## API 端点

### 基础信息

#### GET `/`
返回主页 HTML

#### GET `/api/stats`
返回统计信息

**响应示例**:
```json
{
  "papers_count": 20,
  "summaries_count": 20,
  "categories_count": 5,
  "keywords_count": 50,
  "last_update": "2024-01-15"
}
```

### 分析相关

#### GET `/api/analysis`
返回趋势分析数据

**响应示例**:
```json
{
  "keywords": [
    {"word": "transformer", "score": 0.85},
    {"word": "attention", "score": 0.72}
  ],
  "topics": [
    {"id": 1, "words": ["model", "training"], "score": 0.65}
  ],
  "llm_analysis": {
    "analysis_summary": "<h2>分析总结</h2><p>...</p>",
    "hotspots": "<h2>研究热点</h2><p>...</p>",
    "trends": "<h2>技术趋势</h2><p>...</p>",
    "future_directions": "<h2>未来方向</h2><p>...</p>",
    "research_ideas": "<h2>研究思路</h2><p>...</p>"
  },
  "statistics": {...}
}
```

#### GET `/api/wordcloud`
返回词云图 URL

**响应示例**:
```json
{
  "url": "/images/wordcloud_2024-01-15.png",
  "path": "data/analysis/wordcloud_2024-01-15.png"
}
```

### 论文相关

#### GET `/api/papers`
获取论文列表（支持分页和筛选）

**查询参数**:
- `page` (int): 页码，默认 1
- `per_page` (int): 每页数量，默认 20
- `category` (str): 类别筛选，可选

**响应示例**:
```json
{
  "papers": [...],
  "total": 20,
  "page": 1,
  "per_page": 10,
  "total_pages": 2
}
```

#### GET `/api/papers/<paper_id>`
获取单篇论文详情（包含总结）

**响应示例**:
```json
{
  "id": "2401.12345",
  "title": "论文标题",
  "authors": ["作者1", "作者2"],
  "abstract": "摘要...",
  "summary": "AI 生成的总结...",
  ...
}
```

#### GET `/api/summaries`
获取所有论文总结

**响应示例**:
```json
{
  "summaries": {
    "2401.12345": "论文总结...",
    ...
  }
}
```

#### GET `/api/categories`
获取所有类别及论文数量

**响应示例**:
```json
[
  {"name": "cs.AI", "count": 15},
  {"name": "cs.LG", "count": 12}
]
```

### 资源文件

#### GET `/images/<filename>`
获取图片文件（词云图等）

## 自定义配置

### 修改端口

编辑 `src/web/app.py`:

```python
if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=8080,  # 修改端口
        debug=True
    )
```

### 修改数据路径

编辑 `src/web/app.py` 中的路径常量：

```python
DATA_DIR = Path('data')
PAPERS_DIR = DATA_DIR / 'papers'
SUMMARIES_DIR = DATA_DIR / 'summaries'
ANALYSIS_DIR = DATA_DIR / 'analysis'
```

### 修改分页设置

编辑 `src/web/app.py` 中的 `get_papers` 函数：

```python
per_page = request.args.get('per_page', 20, type=int)  # 默认每页 20 篇
```

## 测试

运行测试脚本验证所有 API 端点：

```bash
# 先启动 Web 服务
python src/web/app.py

# 在另一个终端运行测试
python -m unittest discover -s test -p "test_web*.py"
```

测试项目：
1. ✅ 主页加载
2. ✅ 统计信息 API
3. ✅ 趋势分析 API
4. ✅ 论文列表 API
5. ✅ 类别列表 API
6. ✅ 词云图 API

## 部署

### 生产环境部署

使用 Gunicorn:

```bash
pip install gunicorn

gunicorn -w 4 -b 0.0.0.0:5000 src.web.app:app
```

使用 uWSGI:

```bash
pip install uwsgi

uwsgi --http 0.0.0.0:5000 --module src.web.app:app --processes 4
```

### Nginx 反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /images/ {
        alias /path/to/daily-arxiv/data/analysis/;
    }
}
```

## 常见问题

### Q: 页面显示 "数据加载失败"

**A**: 检查以下几点：
1. 确保已运行论文抓取: `python main.py`
2. 确保 `data/papers/latest.json` 存在
3. 检查浏览器控制台错误信息
4. 查看 Flask 服务器日志

### Q: 词云图不显示

**A**: 
1. 确保已运行趋势分析: `python test_analyzer.py`
2. 检查 `data/analysis/` 目录是否有 `wordcloud_*.png` 文件
3. 确认 `/api/wordcloud` 端点返回正确 URL

### Q: 论文总结不显示

**A**:
1. 确保已运行总结生成: `python test_summarizer.py`
2. 检查 `data/summaries/latest.json` 是否存在
3. 确认论文 ID 匹配

### Q: 如何修改界面样式

**A**: 
- 修改 `static/css/style.css` 中对应的变量、布局、组件或页面规则。
- 模板结构在 `src/web/templates/index.html`；避免静态内联样式和末尾重复覆盖。

### Q: 如何添加新的 API 端点

**A**: 在 `src/web/app.py` 中添加新的路由:

```python
@app.route('/api/new-endpoint')
def new_endpoint():
    return jsonify({"data": "your data"})
```

## 支持

如有问题，请查看：
- [Flask 文档](https://flask.palletsprojects.com/)
- [Bootstrap 文档](https://getbootstrap.com/)
- [Chart.js 文档](https://www.chartjs.org/)
