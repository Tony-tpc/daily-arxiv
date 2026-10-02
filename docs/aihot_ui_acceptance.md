# AIHOT 风格融合验收

2026-10-02，本地 Python/Flask 与原生 JavaScript 实现。参考源码固定为
`KKKKhazix/AIHOT@ddf1c19ef2302863748dce51e4fdcd60d4415fc0`，许可见
[MIT 来源说明](third_party/AIHOT-LICENSE.txt)。当天亦目视核对了用户提供的在线事件详情页；
在线页面可能继续更新，设计变量仍以固定源码及本次方案为准。

## 风格与交互自检

| 项目 | 验收结果 |
| --- | --- |
| 颜色 | 浅色米白 `#faf9f6`、墨色 `#202a30`、青绿 `#176b75`；深色背景 `#13191c`、青色强调。未引入渐变。 |
| 排版 | 系统中文字体，页面标题24px，资料列表14px；保留原项目名称，不使用上游名称或Logo。 |
| 间距 | 以4px倍数为主；控件8px、资料卡片12px、热点面板14px圆角，细边框与轻阴影。 |
| 响应式 | 1440×1100桌面与390×844手机检查；960px以下折叠导航，640px以下单列。手机页面宽度375px（扣除滚动条），内容宽度375px，无横向溢出。 |
| 交互 | 首页进入完整榜单、事件/主题详情、浏览器返回、手机菜单开合、精选翻页、浅深色切换均验证。 |
| 异常 | 空榜显示证据不足/等待任务的原因；503显示重试，重试后恢复。无历史不绘图，采集中断的曲线区间不连线。 |
| 可访问性 | 保留键盘焦点、导航标签、状态播报；详情加载后聚焦标题；减少动态效果偏好继续有效。 |

## 截图

截图由内置浏览器保存，位于 [screenshots/aihot](screenshots/aihot/)。
有数据的热点来自 `python -m test.manual_web_fixtures` 的 `?case=hotspots` 隔离样例；
测试脚本仅拦截当前标签页的读取请求，不写入正式文档或热点SQLite。
资料库截图使用原有本地公开资料，未改动其内容。

- [桌面浅色首页](screenshots/aihot/desktop-light.jpg)
- [手机浅色首页](screenshots/aihot/mobile-light.jpg)
- [学术完整榜单](screenshots/aihot/academic-light.jpg)
- [浅色事件详情](screenshots/aihot/detail-light.jpg)
- [深色事件详情](screenshots/aihot/detail-dark.jpg)
- [手机深色详情](screenshots/aihot/mobile-detail-dark.jpg)
- [手机空榜](screenshots/aihot/mobile-empty.jpg)
- [手机请求失败](screenshots/aihot/mobile-failure.jpg)
- [桌面深色空榜及错误状态](screenshots/aihot/desktop-empty-dark.jpg)
- [原论文库深色样式](screenshots/aihot/library-dark.jpg)

## 自动检查与边界

- 全部 `unittest discover -s test -p "test_*.py"`：233项通过。
- `node --test test/web_workspace.test.cjs test/web_hotspots.test.cjs`：26项通过。
- Python `compileall`、两份JavaScript的 `node --check`、`git diff --check` 通过。
- 当前环境没有安装 `pyright`，未执行该类型检查。

本轮模型与网络回归使用固定时间和替身，没有对正式资料执行付费模型全库重算。
真实热点尚未生成时显示空榜；后续正常采集运行会在50条资料/300次新增调用的上限内初始化窗口数据。
60/65/76门槛仍是待能源样本校准的初始值。学术覆盖局限于本地准入论文，缺乏可比完整历史时不显示增长曲线。
