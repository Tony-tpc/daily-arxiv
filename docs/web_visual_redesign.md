# Canva 风格能源研究工作台

实施前回退点：`228613f`（`chore: snapshot frontend before Canva-style redesign`）。
实施分支：`codex/canva-style-ui`。

## 视觉依据

参考 [Canva 演示文稿模板页](https://www.canva.cn/presentations/templates/)，
从其[页面样式](https://static.canva.cn/web/49cb6b99a6fe9f10.ltr.css)提取以下颜色：

| 用途 | 颜色 |
| --- | --- |
| 主按钮 | `#8B3DFF` |
| 悬停 / 按下 | `#7630D7` / `#612DAE` |
| 主文字 | `#0F1015` |
| 背景 | 白色、浅灰、浅紫 |
| 品牌渐变 | `#00C4CC → #7D2AE8` |

渐变来自参考站点的[品牌样式](https://static.canva.cn/web/7e94d84556d9b7ed.ltr.css)。
参考页面以 Canva Sans、Noto Sans 和系统无衬线字体排版；本站自托管
Inter，中文使用苹方、微软雅黑、Noto Sans CJK SC 等系统字体。未分发 Canva 字体或模板作品。
以紫色强调、轻边框、10–12px 控件圆角和清晰留白统一导航、筛选、列表、报告与抽屉，
深色模式分别调整背景、文字和图表色板。

## 页面与资源

- 概览：风电照片横幅、四类资料图片入口，以及原有真实数量、推荐、信号和采集状态。
- 资料目录：左图右文紧凑列表，摘要预览三行，全文和推荐依据继续通过原有展开控件阅读。
- 报告与统计：统一封面、阅读宽度、目录、引用抽屉和图表配色。
- 图片：光伏、风电、电网、储能设备、城市、工业六类本地 WebP，另提供缩略图和本地 SVG 占位图。
  图片明确标注“主题示意”，按标题优先、主题次之、资料类型兜底稳定匹配，不作为原文配图或证据。
  首屏横幅优先加载，其余图片懒加载；所有图片具有尺寸和替代文本。
- 字体：本地 Inter Variable WOFF2，使用 `font-display: swap`。

作者、原始图片页、图片标识符和授权见 [素材说明](../static/images/energy/CREDITS.md)，
字体许可见 [SIL OFL](../static/fonts/Inter-OFL.txt)。

继续使用 Flask/Jinja、原生 JavaScript 和现有 API。未修改数据格式、路由、检索范围或引用行为。
服务端唯一配套调整是注册 WebP/WOFF2 MIME 类型，确保 Windows 静态文件响应正确。
采集数据、日志和临时脚本不包含在本次改版提交中。

## 验收记录（2026-09-29）

```powershell
node --check static/js/main.js
node --test test/web_workspace.test.cjs
python -m unittest discover -s test -p 'test_web*.py'
python -m unittest discover -s test -p 'test_*.py'
python -m pip check
python -m test.manual_visual_review
git diff --check
```

使用项目 `.runtime-venv` Python，并设置 `PYTHONUTF8=1`、`PYTHONIOENCODING=utf-8`。
前端行为测试 **20 项**、Web 单元测试 **33 项**、全量 Python 测试 **209 项**通过；
JavaScript 语法、依赖一致性和差异空白检查通过。

浏览器验收使用隔离的无头 Microsoft Edge。`test/manual_visual_review.py` 是可选手动验收脚本，
需安装 `playwright`；Windows 使用系统 Edge，其他系统需运行 `playwright install chromium`。
脚本使用独立临时端口及现有测试夹具；报告和图表读取本地已有数据，不写业务记录。

- 1440、1024、390px × 浅色 / 深色 × 10 个页面，检查激活页面、可见图片、字体与横向溢出。
- 检查移动导航、焦点恢复、主题切换、报告目录、证据抽屉和 Escape 关闭。
- 检查长标题、展开摘要、搜索、清除筛选、页大小、分页、排序、空结果、接口重试与英文界面。
- 实际中断图片请求，确认自动替换为本地占位图。
- 全部通过，未出现 JavaScript 异常。详细结果与场景截图写入被 Git 忽略的 `data/ui-review/`。

下列截图来自本地应用现有资料，展示本次改版；数量和内容会随采集更新。

| 页面 | 截图 |
| --- | --- |
| 1440px 浅色概览 | [查看](screenshots/canva-style-ui/overview-light.png) |
| 1440px 深色概览 | [查看](screenshots/canva-style-ui/overview-dark.png) |
| 1024px 资料目录 | [查看](screenshots/canva-style-ui/papers-tablet.png) |
| 390px 概览 | [查看](screenshots/canva-style-ui/overview-mobile.png) |
| 390px 深色目录 | [查看](screenshots/canva-style-ui/papers-mobile-dark.png) |
