/* Energy hotspot views. AIHOT-inspired hierarchy; no network/model work beyond read-only APIs. */
(() => {
    const versions = {industry: 0, academic: 0, detail: 0};
    const cache = {};
    const text = (zh, en) => LANG === 'zh' ? zh : en;
    const esc = value => escapeHtml(String(value ?? ''));
    const node = id => document.getElementById(id);
    const number = value => Number.isFinite(Number(value)) ? Number(value).toFixed(1) : '—';
    const title = board => board === 'industry' ? text('行业事件', 'Industry events') : text('学术研究', 'Research topics');
    const dateTime = value => value ? esc(String(value).replace('T', ' ').replace(/\.\d+/, '').slice(0, 16)) + ' UTC' : '—';

    function trend(entry) {
        if (entry.kind === 'academic') return `<span class="hot-trend quiet">${text('论文活跃度', 'Paper activity')}</span>`;
        if (entry.is_new) return `<span class="hot-new">${text('新', 'New')}</span>`;
        const labels = {up: text('↑ 上升', '↑ Rising'), down: text('↓ 回落', '↓ Falling'), flat: text('— 持平', '— Stable')};
        return `<span class="hot-trend ${entry.trend === 'up' ? 'rising' : 'quiet'}">${labels[entry.trend] || text('暂无可比趋势', 'No comparable trend')}${entry.trend_pct != null && labels[entry.trend] ? ` ${esc(entry.trend_pct)}%` : ''}</span>`;
    }

    function support(entry) {
        return entry.kind === 'academic'
            ? text(`${Number(entry.paper_count)} 篇论文 · ${Number(entry.institution_count)} 个已知机构`, `${Number(entry.paper_count)} papers · ${Number(entry.institution_count)} known institutions`)
            : text(`${Number(entry.source_count)} 个独立来源 · ${Number(entry.report_count)} 份资料`, `${Number(entry.source_count)} publishers · ${Number(entry.report_count)} records`);
    }

    function row(entry, compact = false) {
        const rank = Math.max(1, Number(entry.rank) || 1);
        return `<article class="${compact ? 'hot-mini-row' : 'hot-event-card'} ${!compact && rank === 1 ? 'hot-lead' : ''}">
            <span class="hot-rank rank-${Math.min(rank, 4)}" aria-label="${text('排名', 'Rank')} ${rank}">${String(rank).padStart(2, '0')}</span>
            <div class="hot-event-copy"><h${compact ? '3' : '2'}><a href="#hotspot/${encodeURIComponent(entry.id)}">${esc(entry.title)}</a></h${compact ? '3' : '2'}>
            ${!compact ? `<p class="hot-summary">${esc(entry.summary)}</p>` : ''}
            <div class="hot-meta"><span>${esc(support(entry))}</span>${trend(entry)}</div></div>
            <div class="hot-value"><strong>${number(entry.score)}</strong><small>${entry.kind === 'academic' ? text('活跃度', 'Activity') : text('热度', 'Heat')}</small></div>
        </article>`;
    }

    function empty(payload, board) {
        const message = payload.reason || payload.empty_reason || text('暂时没有足够证据形成热点。', 'Not enough evidence for a ranking yet.');
        return `<div class="hot-empty"><span class="empty-orbit" aria-hidden="true">○</span><p>${esc(message)}</p><small>${board === 'industry' ? text('持续关注国内能源事件；重复转载不会增加独立来源。', 'Following domestic energy events; repeat reports do not add publishers.') : text('等待更多通过准入审核的近期论文。', 'Waiting for more recent admitted papers.')}</small></div>`;
    }

    function renderBoard(board, payload) {
        const entries = payload.entries || [];
        const compact = node(`home-hot-${board}`);
        const full = node(`hot-${board}-list`);
        if (compact) compact.innerHTML = entries.length ? entries.slice(0, 5).map(entry => row(entry, true)).join('') : empty(payload, board);
        if (full) full.innerHTML = entries.length ? entries.slice(0, 10).map(entry => row(entry)).join('') : empty(payload, board);
        const meta = node(`hot-${board}-meta`);
        if (meta) meta.innerHTML = `<span>${esc(payload.metric || '')}</span><span>${text('更新于', 'Updated')} ${dateTime(payload.computed_at)}${payload.stale ? ` · <strong>${text('数据待更新', 'Update pending')}</strong>` : ''}</span>`;
        if (payload.stale && compact) compact.insertAdjacentHTML('beforeend', `<p class="hot-stale">${text('当前为上次生成结果，等待更新。', 'Showing the previous snapshot; awaiting refresh.')}</p>`);
    }

    async function loadBoard(board, force = false) {
        if (!['industry', 'academic'].includes(board)) return;
        if (cache[board] && !force) { renderBoard(board, cache[board]); return; }
        const version = ++versions[board];
        try {
            const response = await fetch(`/api/hotspots?board=${board}`);
            if (!response.ok) throw new Error('Hotspot request failed');
            const payload = await response.json();
            if (version !== versions[board]) return;
            cache[board] = payload;
            renderBoard(board, payload);
        } catch (error) {
            if (version !== versions[board]) return;
            const errorHtml = `<div class="hot-empty" role="alert"><p>${text('热点暂时无法读取', 'Hotspots could not be loaded')}</p><button type="button" class="btn-paper btn-secondary" data-refresh-hot="${board}">${text('重新加载', 'Retry')}</button></div>`;
            for (const id of [`home-hot-${board}`, `hot-${board}-list`]) if (node(id)) node(id).innerHTML = errorHtml;
        }
    }

    function sparkline(series) {
        const valid = series.filter(point => point.score != null && Number.isFinite(Number(point.score)));
        if (valid.length < 3) return `<p class="hot-placeholder">${text('尚无足够的可比历史，暂不绘制趋势。', 'Not enough comparable history to draw a trend.')}</p>`;
        const maximum = Math.max(1, ...valid.map(point => Number(point.score)));
        const times = series.map(point => Date.parse(point.at));
        if (times.some(time => !Number.isFinite(time))) return '';
        const first = Math.min(...times), span = Math.max(1, Math.max(...times) - first);
        let drawing = '', open = false, previous = null;
        series.forEach((point, index) => {
            if (point.score == null || !Number.isFinite(Number(point.score))) { open = false; previous = null; return; }
            if (previous != null && times[index] - previous > 90 * 60 * 1000) open = false;
            const x = 8 + (times[index] - first) / span * 584;
            const y = 112 - Number(point.score) / maximum * 100;
            drawing += `${open ? 'L' : 'M'}${x.toFixed(2)},${y.toFixed(2)} `;
            open = true;
            previous = times[index];
        });
        return `<svg class="heat-sparkline" viewBox="0 0 600 128" role="img" aria-label="${text('可比时间点的热度变化，缺失区间不连线', 'Comparable heat history; missing intervals are not connected')}"><path class="spark-axis" d="M8 116H592"/><path class="spark-line" d="${drawing}"/></svg><div class="spark-dates"><span>${dateTime(series[0].at)}</span><span>${dateTime(series[series.length - 1].at)}</span></div>`;
    }

    function renderDetail(detail) {
        const board = detail.kind === 'academic' ? 'academic' : 'industry';
        const evidence = detail.evidence || [];
        const timeline = evidence.map(item => `<li><time>${esc(String(item.published_at || '').slice(0, 16).replace('T', ' '))}</time><div><span class="timeline-source">${esc(item.source_name)}</span><h3>${item.url && item.link_status === 'verified' ? sourceLink(item.url, item.display_title || item.title, '') : esc(item.display_title || item.title)}</h3><p>${esc(item.summary)}</p>${item.link_status !== 'verified' ? `<small>${text('原文链接尚未通过核验', 'Original link has not passed verification')}</small>` : ''}${(item.observations || []).length > 1 ? `<details><summary>${text('查看其他来源', 'Other sources')}</summary>${item.observations.map(observation => `<p>${esc(observation.source_name)} · ${esc(observation.published_at)}</p>`).join('')}</details>` : ''}</div></li>`).join('');
        return `<a href="#hot-${board}" data-section="hot-${board}" class="hot-back">← ${title(board)}</a>
            <header class="hot-detail-header"><p class="page-kicker">${board === 'academic' ? 'RESEARCH TOPIC' : 'ENERGY EVENT'}</p><h1 tabindex="-1">${esc(detail.title)}</h1><div class="hot-meta"><span>${esc(support(detail))}</span>${trend(detail)}<span>${text('更新于', 'Updated')} ${dateTime(detail.computed_at)}</span></div></header>
            <div class="hot-detail-grid"><article class="hot-digest"><h2>${detail.summary_kind === 'digest' ? text('事件与研究综述', 'Evidence synthesis') : text('代表资料摘要', 'Representative summary')}</h2><p>${esc(detail.summary)}</p><p class="scope-note">${esc(detail.coverage?.reason || text('以下资料提供原始证据，请结合原文判断。', 'The records below provide the original evidence.'))}</p></article><aside class="hot-measure"><span>${board === 'academic' ? text('30天研究活跃度', '30-day activity') : text('48小时事件热度', '48-hour heat')}</span><strong>${number(detail.score)}</strong><small>${board === 'academic' ? text('去重论文 · 15天半衰期', 'Distinct papers · 15-day half-life') : text('独立机构 · 24小时半衰期', 'Independent publishers · 24-hour half-life')}</small></aside></div>
            <section class="hot-history"><h2>${text('热度记录', 'Recorded activity')}</h2>${sparkline(detail.series || [])}</section>
            <section class="hot-evidence"><h2>${text('证据与进展', 'Evidence and developments')}</h2><ol class="hot-timeline">${timeline}</ol></section>
            ${(detail.background_documents || []).length ? `<section class="hot-background"><h2>${text('相关背景资料', 'Related background')}</h2>${detail.background_documents.map(item => `<p>${esc(item.title)}</p>`).join('')}<small>${text('背景关联不计为事件报道。', 'Background references do not count as event reports.')}</small></section>` : ''}`;
    }

    async function loadDetail(id) {
        const version = ++versions.detail;
        if (!node('hotspot-detail')) return;
        node('hotspot-detail').innerHTML = `<p class="hot-placeholder" role="status">${text('正在读取事件证据…', 'Loading evidence…')}</p>`;
        try {
            const response = await fetch(`/api/hotspots/${encodeURIComponent(id)}`);
            if (version !== versions.detail) return;
            if (response.status === 404) {
                node('hotspot-detail').innerHTML = `<div class="hot-empty"><h1>${text('热点暂无可用证据', 'No current evidence')}</h1><p>${text('该热点可能已过期，或资料不再符合准入条件。', 'The item may have expired or its evidence is no longer admitted.')}</p><a href="#overview" data-section="overview">${text('返回精选', 'Back to selected')}</a></div>`;
                return;
            }
            if (!response.ok) throw new Error('Detail request failed');
            const detail = await response.json();
            if (version !== versions.detail) return;
            node('hotspot-detail').innerHTML = renderDetail(detail);
            node('hotspot-detail').querySelector('h1')?.focus({preventScroll: true});
            updateElement('current-page-label', title(detail.kind));
        } catch (error) {
            if (version !== versions.detail) return;
            node('hotspot-detail').innerHTML = `<div class="hot-empty" role="alert"><p>${text('详情读取失败', 'Detail could not be loaded')}</p><button type="button" class="btn-paper btn-secondary" data-retry-detail="${esc(id)}">${text('重试', 'Retry')}</button></div>`;
        }
    }

    function navigate(section) {
        if (section !== 'hotspot') versions.detail++;
        if (section === 'hot-industry' || section === 'hot-academic') loadBoard(section.slice(4));
        if (section === 'hotspot') {
            const id = window.location.hash.slice('#hotspot/'.length);
            if (/^[\w-]{1,100}$/.test(id)) loadDetail(id);
            else if (node('hotspot-detail')) node('hotspot-detail').innerHTML = emptyState(text('无效热点地址', 'Invalid hotspot address'));
        }
    }

    function renderFeedPagination(payload) {
        const container = node('home-feed-pagination');
        if (!container) return;
        const pages = Math.ceil(Number(payload.total || 0) / 8);
        container.innerHTML = pages > 1 ? `<button type="button" data-feed-page="${state.homePage - 1}" ${state.homePage <= 1 ? 'disabled' : ''}>← ${text('上一页', 'Previous')}</button><span>${state.homePage} / ${pages}</span><button type="button" data-feed-page="${state.homePage + 1}" ${state.homePage >= pages ? 'disabled' : ''}>${text('下一页', 'Next')} →</button>` : '';
    }

    document.addEventListener('DOMContentLoaded', () => {
        loadBoard('industry');
        loadBoard('academic');
        document.addEventListener('click', event => {
            const refresh = event.target.closest('[data-refresh-hot]');
            if (refresh) loadBoard(refresh.dataset.refreshHot, true);
            const retry = event.target.closest('[data-retry-detail]');
            if (retry) loadDetail(retry.dataset.retryDetail);
            const view = event.target.closest('[data-feed-view]');
            if (view) {
                state.homeView = view.dataset.feedView;
                document.querySelectorAll('[data-feed-view]').forEach(button => button.setAttribute('aria-pressed', String(button === view)));
                loadIntelligenceHome();
            }
            const page = event.target.closest('[data-feed-page]');
            if (page && !page.disabled) loadIntelligenceHome(Math.max(1, Number(page.dataset.feedPage)));
        });
    });
    window.EnergyHotspots = {navigate, loadBoard, loadDetail, renderFeedPagination, renderDetail, sparkline};
})();
