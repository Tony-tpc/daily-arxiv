/**
 * Daily arXiv - Modern Frontend JavaScript
 */

const LANG = window.APP_LANGUAGE === 'en' ? 'en' : 'zh';
const I18N = {
    zh: {
        monthNames: ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'],
        weekDays: ['日', '一', '二', '三', '四', '五', '六'],
        loading: '加载中...',
        loadingPapers: '加载论文中...',
        loadAnalysisFailed: '加载分析失败',
        noWordcloud: '暂无词云数据',
        wordcloudLoadFailed: '词云加载失败',
        noPaperData: '暂无论文数据',
        unknown: '未提供',
        authorLabel: '作者',
        sourceLabel: '来源',
        priorityLabel: '优先级',
        recommendationLabel: '建议动作',
        scoreLabel: '综合分',
        scoreBreakdown: '查看五维评分',
        relevanceReason: '推荐依据',
        relatedTopicsLabel: '相关主题',
        citationsLabel: '引用次数',
        journalLabel: '期刊',
        whitelistQuartileLabel: '白名单分区',
        primaryTopicLabel: 'OpenAlex 主主题',
        institutionsLabel: '机构',
        referencesLabel: '参考文献数',
        noAbstract: '暂无摘要',
        problem: '研究问题',
        method: '核心方法',
        scenario: '应用场景',
        constraint: '关键约束',
        metric: '评价指标',
        contribution: '主要贡献',
        structuredInsight: '结构化论文洞察',
        evidence: '展开证据句',
        adaptiveFacets: '主题自适应标签',
        confidence: '置信度',
        viewPdf: '查看PDF',
        viewDetail: '查看详情',
        noPapers: '暂无论文',
        noCategories: '暂无类别',
        allCategories: '全部类别',
        noData: '暂无数据',
        timelineHint: '按日期展示论文数量，并突出每期高频研究关键词',
        paperCount: '论文数量',
        categoryCount: '类别数量',
        methodScenario: '方法/场景',
        mechanism: '机制',
        relatedPapers: '相关论文',
        comparisonPaper: '论文',
        comparisonProblem: '研究问题',
        comparisonMethod: '方法',
        comparisonScenario: '场景',
        comparisonMetric: '指标',
        comparisonContribution: '贡献',
        originalSource: '查看原文',
        emptyPolicyTitle: '暂无中国政策数据',
        emptyPolicyHint: '采集任务运行后，国家能源局和国家发展改革委政策将在此展示。',
        emptyNewsTitle: '暂无国内新闻数据',
        emptyNewsHint: '采集任务运行后，国内能源新闻将在此展示。',
        emptyReportTitle: '暂无行业报告数据',
        emptyReportHint: '配置国内行业报告来源并运行采集任务后，报告将在此展示。',
        relatedIntelligence: '关联信息',
        duplicateSources: '已合并来源',
        reportLoadFailed: '报告加载失败',
        reportEmpty: '本周期暂无可展示条目',
        reportOriginal: '查看原始来源',
        reportPeriod: '报告周期',
        reportGenerated: '生成于',
        noIntelligence: '尚无可展示的科研资料',
        signalInsufficient: '历史信号不足，运行多源采集后将在此展示',
        schedulerPending: '待运行',
        schedulerEmpty: '本轮无新增',
        schedulerFailed: '失败',
        schedulerSucceeded: '成功',
        schedulerPartial: '部分成功',
        schedulerDisabled: '自动调度未启用',
        schedulerLoadFailed: '任务状态加载失败'
    },
    en: {
        monthNames: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
        weekDays: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
        loading: 'Loading...',
        loadingPapers: 'Loading papers...',
        loadAnalysisFailed: 'Failed to load analysis',
        noWordcloud: 'No word cloud data',
        wordcloudLoadFailed: 'Failed to load word cloud',
        noPaperData: 'No paper data',
        unknown: 'Unknown',
        authorLabel: 'Authors',
        sourceLabel: 'Source',
        priorityLabel: 'Priority',
        recommendationLabel: 'Recommended action',
        scoreLabel: 'Score',
        scoreBreakdown: 'View score breakdown',
        relevanceReason: 'Rationale',
        relatedTopicsLabel: 'Related topics',
        citationsLabel: 'Citations',
        journalLabel: 'Journal',
        whitelistQuartileLabel: 'Whitelist quartile',
        primaryTopicLabel: 'OpenAlex primary topic',
        institutionsLabel: 'Institutions',
        referencesLabel: 'Referenced works',
        noAbstract: 'No abstract',
        problem: 'Problem',
        method: 'Method',
        scenario: 'Scenario',
        constraint: 'Constraint',
        metric: 'Metric',
        contribution: 'Contribution',
        structuredInsight: 'Structured insight',
        evidence: 'Evidence',
        adaptiveFacets: 'Adaptive facets',
        confidence: 'Confidence',
        viewPdf: 'View PDF',
        viewDetail: 'View details',
        noPapers: 'No papers available',
        noCategories: 'No categories',
        allCategories: 'All categories',
        noData: 'No data',
        timelineHint: 'Shows paper volume by date and highlights frequent research keywords',
        paperCount: 'Papers',
        categoryCount: 'Categories',
        methodScenario: 'Method / Scenario',
        mechanism: 'Mechanism',
        relatedPapers: 'Related papers',
        comparisonPaper: 'Paper',
        comparisonProblem: 'Problem',
        comparisonMethod: 'Method',
        comparisonScenario: 'Scenario',
        comparisonMetric: 'Metric',
        comparisonContribution: 'Contribution',
        originalSource: 'Open source',
        emptyPolicyTitle: 'No China policy data',
        emptyPolicyHint: 'Policies will appear after the collection job runs.',
        emptyNewsTitle: 'No China news data',
        emptyNewsHint: 'News will appear after the collection job runs.',
        emptyReportTitle: 'No industry report data',
        emptyReportHint: 'Reports will appear after sources are configured and collected.',
        relatedIntelligence: 'Related information',
        duplicateSources: 'Merged sources',
        reportLoadFailed: 'Failed to load report',
        reportEmpty: 'No items in this period',
        reportOriginal: 'Open source',
        reportPeriod: 'Period',
        reportGenerated: 'Generated',
        noIntelligence: 'No research information is available yet',
        signalInsufficient: 'Run multi-source collection to build historical signals',
        schedulerPending: 'Pending',
        schedulerEmpty: 'No new records',
        schedulerFailed: 'Failed',
        schedulerSucceeded: 'Succeeded',
        schedulerPartial: 'Partial',
        schedulerDisabled: 'Scheduler disabled',
        schedulerLoadFailed: 'Failed to load job status'
    }
};

const FACET_LABELS_ZH = {
    interaction_type: '交互类型',
    market_structure: '市场结构',
    objective: '优化目标',
    decision_horizon: '决策周期',
    solution_approach: '求解方法',
    uncertainty_modeling: '不确定性建模',
    scalability_aspect: '可扩展性',
    game_type: '博弈类型',
    method_family: '方法族',
    application_context: '应用背景',
    mechanism_or_process: '机制/过程',
    constraint_or_risk: '约束/风险',
    evaluation_signal: '评价信号'
};

function t(key) {
    return I18N[LANG][key] || key;
}

// ===================  全局状态 ==================== //
const state = {
    currentSection: 'overview',
    currentPage: 1,
    papersPerPage: 20,
    selectedCategory: '',
    selectedPriority: '',
    searchQuery: '',
    allPapers: [],
    directories: {
        policy: {documents: [], total: 0, search: '', topic: '', priority: '', dateFrom: '', dateTo: '', sort: 'relevance', page: 1, totalPages: 0},
        news: {documents: [], total: 0, search: '', topic: '', priority: '', dateFrom: '', dateTo: '', sort: 'relevance', page: 1, totalPages: 0},
        industry_report: {documents: [], total: 0, search: '', topic: '', priority: '', dateFrom: '', dateTo: '', sort: 'relevance', page: 1, totalPages: 0}
    },
    homeFilters: {sourceType: 'all', topic: '', priority: '', dateFrom: '', dateTo: ''},
    allCategories: [],
    analysis: null,
    narrative: null,
    narrativeView: 'paper',
    forecast: null,
    forecastTaxonomy: [],
    forecastFilters: {horizon: 'all', topic: '', confidence: ''},
    report: null,
    history: [],
    knowledgeByPaperId: {},
    facetSchema: [],
    categoryChart: null,
    trendChart: null,
    sourceComparisonChart: null,
    entityTrendChart: null,
    forecastChart: null,
    paperTotal: 0,
    papersLoaded: false,
    knowledgeFailed: false,
    categoriesFailed: false,
    paperSort: 'relevance',
    requestVersions: {},
    theme: localStorage.getItem('theme') || 'light'
};

// ==================== 初始化 ==================== //
document.addEventListener('DOMContentLoaded', async function() {
    initTheme();
    initNavigation();
    initMobileMenu();
    initScrollBehavior();
    initWorkspaceControls();
    initReaderToc();
    initEventListeners();
    
    // 加载数据
    await loadAllData();
    

});

// ==================== 主题切换 ==================== //
function initTheme() {
    const html = document.documentElement;
    html.setAttribute('data-theme', state.theme);
    
    const themeToggle = document.getElementById('theme-toggle');
    const icon = themeToggle.querySelector('i');
    icon.className = state.theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    themeToggle.setAttribute('aria-pressed', String(state.theme === 'dark'));
    configureChartTheme();
}

function toggleTheme() {
    state.theme = state.theme === 'light' ? 'dark' : 'light';
    localStorage.setItem('theme', state.theme);
    initTheme();
    renderResearchTrendModules();
}

// ==================== 导航 ==================== //

const SECTIONS = ['overview', 'papers', 'policies', 'news', 'industry-reports', 'reports', 'analysis', 'statistics'];
let evidenceReturnFocus = null;
let menuReturnFocus = null;

function initNavigation() {
    document.addEventListener('click', event => {
        const link = event.target.closest('[data-section]');
        if (!link || !SECTIONS.includes(link.dataset.section)) return;
        event.preventDefault();
        navigateToSection(link.dataset.section);
    });
    const restoreRoute = () => {
        const section = window.location.hash.slice(1);
        if (SECTIONS.includes(section)) navigateToSection(section, false);
        else if (!section) navigateToSection('overview', false);
    };
    window.addEventListener('hashchange', restoreRoute);
    window.addEventListener('popstate', restoreRoute);
    restoreRoute();
    document.addEventListener('click', event => {
        const anchor = event.target.closest('#narrative-toc a, #report-toc a');
        if (!anchor) return;
        const target = document.getElementById(anchor.getAttribute('href').slice(1));
        if (target) {
            event.preventDefault();
            target.scrollIntoView({behavior: 'auto', block: 'start'});
            target.setAttribute('tabindex', '-1');
            target.focus({preventScroll: true});
        }
    });
}

function navigateToSection(sectionName, updateHistory = true) {
    if (!SECTIONS.includes(sectionName)) return;
    state.currentSection = sectionName;
    if (updateHistory && window.location.hash !== '#' + sectionName) history.pushState(null, '', '#' + sectionName);
    closeNarrativeEvidence();
    closeMobileMenu();
    document.querySelectorAll('.nav-item').forEach(item => {
        const active = item.dataset.section === sectionName;
        item.classList.toggle('active', active);
        if (active) item.setAttribute('aria-current', 'page');
        else item.removeAttribute('aria-current');
    });
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.toggle('active', section.id === sectionName + '-section');
    });
    if (sectionName === 'statistics') requestAnimationFrame(() => renderResearchTrendModules());
    window.scrollTo({top: 0, behavior: 'auto'});
}

function initMobileMenu() {
    document.getElementById('mobile-menu-btn').addEventListener('click', toggleMobileMenu);
    document.getElementById('sidebar-toggle-btn').addEventListener('click', closeMobileMenu);
    document.getElementById('sidebar-backdrop').addEventListener('click', closeMobileMenu);
    window.matchMedia('(min-width: 1024px)').addEventListener('change', closeMobileMenu);
    document.addEventListener('keydown', event => {
        const drawer = document.getElementById('narrative-evidence-drawer');
        const sidebar = document.getElementById('sidebar');
        const modal = drawer.classList.contains('open') ? drawer : sidebar.classList.contains('open') ? sidebar : null;
        if (!modal) return;
        if (event.key === 'Escape') {
            if (modal === drawer) closeNarrativeEvidence();
            else closeMobileMenu();
        } else if (event.key === 'Tab') trapFocus(event, modal);
    });
}

function trapFocus(event, root) {
    const items = [...root.querySelectorAll('a[href], button:not([disabled]), input, select, summary, [tabindex="0"]')]
        .filter(item => item.getClientRects().length);
    if (!items.length) return;
    const first = items[0], last = items[items.length - 1];
    if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
    }
}

function toggleMobileMenu() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar.classList.contains('open')) return closeMobileMenu();
    menuReturnFocus = document.activeElement;
    sidebar.classList.add('open');
    sidebar.setAttribute('role', 'dialog');
    sidebar.setAttribute('aria-modal', 'true');
    sidebar.setAttribute('aria-label', LANG === 'zh' ? '主导航' : 'Main navigation');
    document.getElementById('sidebar-backdrop').hidden = false;
    document.getElementById('mobile-menu-btn').setAttribute('aria-expanded', 'true');
    document.getElementById('main-content').inert = true;
    document.querySelector('.top-navbar').inert = true;
    document.body.classList.add('menu-open');
    document.getElementById('sidebar-toggle-btn').focus();
}

function closeMobileMenu() {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar.classList.contains('open')) return;
    sidebar.classList.remove('open');
    sidebar.removeAttribute('role');
    sidebar.removeAttribute('aria-modal');
    document.getElementById('sidebar-backdrop').hidden = true;
    document.getElementById('mobile-menu-btn').setAttribute('aria-expanded', 'false');
    document.getElementById('main-content').inert = false;
    document.querySelector('.top-navbar').inert = false;
    document.body.classList.remove('menu-open');
    menuReturnFocus?.focus();
}

function configureChartTheme() {
    if (typeof Chart === 'undefined') return;
    const style = getComputedStyle(document.documentElement);
    Chart.defaults.color = style.getPropertyValue('--text-secondary').trim();
    Chart.defaults.borderColor = style.getPropertyValue('--border-color').trim();
    Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
    Chart.defaults.font.size = 11;
    Chart.defaults.maintainAspectRatio = false;
    Chart.defaults.plugins.legend.labels.boxWidth = 10;
    Chart.defaults.plugins.legend.labels.padding = 16;
    Chart.defaults.animation = false;
}

// Each view owns its filters. Navigation does not reload or reset them.
function initWorkspaceControls() {
    document.getElementById('paper-filter-clear').addEventListener('click', () => {
        state.searchQuery = '';
        state.selectedCategory = '';
        state.selectedPriority = '';
        state.paperSort = 'relevance';
        document.getElementById('search-input').value = '';
        document.getElementById('paper-category-filter').value = '';
        document.getElementById('paper-priority-filter').value = '';
        document.getElementById('paper-sort').value = 'relevance';
        loadPapers(1);
    });
    document.getElementById('home-filter-clear').addEventListener('click', () => {
        state.homeFilters = {sourceType: 'all', topic: '', priority: '', dateFrom: '', dateTo: ''};
        document.querySelectorAll('.intelligence-filter-grid input').forEach(input => { input.value = ''; });
        document.getElementById('home-source-filter').value = 'all';
        document.getElementById('home-priority-filter').value = '';
        loadIntelligenceHome();
    });
    document.querySelectorAll('[data-directory-clear]').forEach(button => {
        button.addEventListener('click', () => {
            const type = button.dataset.directoryClear;
            Object.assign(state.directories[type], {search: '', topic: '', priority: '', dateFrom: '', dateTo: '', sort: 'relevance'});
            const toolbar = button.closest('.filter-bar');
            toolbar.querySelectorAll('input').forEach(input => { input.value = ''; });
            toolbar.querySelector('[data-directory-priority]').value = '';
            toolbar.querySelector('[data-directory-sort]').value = 'relevance';
            loadDirectory(type);
        });
    });
    document.querySelectorAll('.intelligence-filter-grid input').forEach(input => {
        input.addEventListener('keydown', event => {
            if (event.key === 'Enter') document.getElementById('home-filter-apply').click();
        });
    });
    document.querySelector('.narrative-tabs').addEventListener('keydown', event => {
        if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
        const tabs = [...document.querySelectorAll('[data-narrative-view]')];
        const index = tabs.indexOf(document.activeElement);
        const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1
            : (index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
        event.preventDefault();
        tabs[next].click();
        tabs[next].focus();
    });
}

function initReaderToc() {
    const media = window.matchMedia('(max-width: 767px)');
    const sync = () => document.querySelectorAll('.reader-toc').forEach(toc => { toc.open = !media.matches; });
    media.addEventListener('change', sync);
    sync();
}

function wrapReadingTables(root) {
    root.querySelectorAll('table').forEach(table => {
        if (table.parentElement.classList.contains('table-scroll')) return;
        const wrapper = document.createElement('div');
        wrapper.className = 'table-scroll';
        wrapper.tabIndex = 0;
        wrapper.setAttribute('role', 'region');
        wrapper.setAttribute('aria-label', LANG === 'zh' ? '数据表，可横向滚动' : 'Data table, scroll horizontally');
        table.replaceWith(wrapper);
        wrapper.append(table);
    });
}

function renderPager(container, page, totalPages, onPage) {
    if (!container) return;
    if (!totalPages) { container.innerHTML = ''; return; }
    const previous = LANG === 'zh' ? '上一页' : 'Previous';
    const next = LANG === 'zh' ? '下一页' : 'Next';
    const start = Math.max(1, Math.min(page - 2, totalPages - 4));
    const numbers = Array.from({length: Math.min(5, totalPages)}, (_, offset) => start + offset);
    container.innerHTML = `<span>${LANG === 'zh' ? `第 ${page} / ${totalPages} 页` : `Page ${page} of ${totalPages}`}</span>
        <button type="button" class="page-link" data-page="${page - 1}" ${page <= 1 ? 'disabled' : ''}>${previous}</button>
        ${numbers.map(number => `<button type="button" class="page-link" data-page="${number}" aria-label="${LANG === 'zh' ? `第 ${number} 页` : `Page ${number}`}" ${number === page ? 'aria-current="page"' : ''}>${number}</button>`).join('')}
        <button type="button" class="page-link" data-page="${page + 1}" ${page >= totalPages ? 'disabled' : ''}>${next}</button>`;
    container.querySelectorAll('button').forEach(button => button.addEventListener('click', () => {
        const selected = Number(button.dataset.page);
        if (selected >= 1 && selected <= totalPages) onPage(selected);
    }));
}

function renderDirectoryPagination(sourceType) {
    const directory = state.directories[sourceType];
    const prefix = sourceType === 'industry_report' ? 'industry-report' : sourceType;
    renderPager(document.getElementById(prefix + '-pagination'), directory.page, directory.totalPages,
        page => loadDirectory(sourceType, page));
}

// ==================== 数据加载 ==================== //
async function loadAllData() {
    try {
        await Promise.all([
            loadAnalysis(),
            loadNarrative(),
            loadHistory(),
            loadKnowledge(),
            loadPapers(),
            loadCategories(),
            loadDirectory('policy'),
            loadDirectory('news'),
            loadDirectory('industry_report'),
            loadReport(),
            loadIntelligenceHome(),
            loadSchedulerStatus()
        ]);
        if (state.papersLoaded) {
            renderPapers(filterPapers(state.allPapers));
            renderFeaturedPapers(state.allPapers.slice(0, 5));
        }
        renderResearchTrendModules();
        renderResearchMatrix();
        renderComparisonTable();
        renderHomeTrendSignals();
    } catch (error) {
        console.error('加载数据失败:', error);
    }
}

async function loadKnowledge() {
    try {
        const response = await fetch('/api/knowledge');
        if (!response.ok && response.status !== 404) throw new Error('Knowledge unavailable');
        state.knowledgeFailed = false;
        if (response.status === 404) {
            state.knowledgeByPaperId = {};
            state.facetSchema = [];
            return;
        }

        const knowledge = await response.json();
        state.facetSchema = knowledge.facet_schema || [];
        state.knowledgeByPaperId = (knowledge.papers || []).reduce((index, paper) => {
            if (paper.id) index[paper.id] = paper.knowledge || {};
            return index;
        }, {});
    } catch (error) {
        state.knowledgeFailed = true;
        console.warn('加载结构化知识失败:', error);
        state.knowledgeByPaperId = {};
        state.facetSchema = [];
    }
    renderPaperSupportStatus();
}

async function loadHistory() {
    try {
        const response = await fetch('/api/history');
        if (!response.ok) {
            state.history = [];
            return;
        }

        const history = await response.json();
        state.history = history.snapshots || [];
    } catch (error) {
        console.warn('加载历史趋势失败:', error);
        state.history = [];
    }
}



async function loadAnalysis() {
    const version = (state.requestVersions.analysis || 0) + 1;
    state.requestVersions.analysis = version;
    try {
        const response = await fetch('/api/analysis');
        if (!response.ok) throw new Error('Failed to load analysis');
        
        const analysis = await response.json();
        if (state.requestVersions.analysis !== version) return;
        state.analysis = analysis;
        const dataDate = analysis.generated_at || analysis.date || '';
        const dateLabel = dataDate ? formatReportTime(dataDate) : (LANG === 'zh' ? '未记录' : 'Not recorded');
        updateElement('workspace-data-date', (analysis.generated_at ? (LANG === 'zh' ? '分析生成时间：' : 'Analysis generated: ') : (LANG === 'zh' ? '分析产物日期：' : 'Analysis date: ')) + dateLabel);
        updateElement('last-update-time', dateLabel);
        document.getElementById('statistics-error').hidden = true;
        
        // 加载词云
        await loadWordcloud();
        
        if (analysis.trend_forecast && !state.forecast) {
            state.forecast = analysis.trend_forecast;
            state.forecastTaxonomy = analysis.trend_forecast.taxonomy || [];
        }
        renderResearchTrendModules();
        renderHomeTrendSignals();
        
    } catch (error) {
        if (state.requestVersions.analysis !== version) return;
        console.error('加载分析数据失败:', error);
        updateElement('workspace-data-date', LANG === 'zh' ? '分析数据暂不可用' : 'Analysis unavailable');
        document.getElementById('statistics-error').hidden = false;
        showError('statistics-error', t('loadAnalysisFailed'));
    }
}

async function loadNarrative(options = {}) {
    const version = (state.requestVersions.narrative || 0) + 1;
    state.requestVersions.narrative = version;
    document.getElementById('narrative-opportunity-section').hidden = true;
    document.getElementById('narrative-chain-section').hidden = true;
    updateElement('narrative-generated', t('loading'));
    document.getElementById('narrative-coverage').innerHTML = '';
    document.getElementById('narrative-toc').innerHTML = '';
    const content = document.getElementById('narrative-content');
    if (content) {
        content.innerHTML = `<div class="loading"><div class="spinner"></div><p>${LANG === 'zh' ? '正在读取长篇分析…' : 'Loading long-form analysis…'}</p></div>`;
    }
    const params = new URLSearchParams({view: state.narrativeView});
    if (options.refresh) params.set('refresh', '1');
    try {
        const response = await fetch(`/api/trends/narrative?${params.toString()}`);
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.error || 'Failed to load narrative');
        }
        const payload = await response.json();
        if (state.requestVersions.narrative !== version) return;
        state.narrative = payload;
        renderNarrative();
    } catch (error) {
        if (state.requestVersions.narrative !== version) return;
        console.error('加载长篇趋势分析失败:', error);
        updateElement('narrative-generated', LANG === 'zh' ? '分析暂不可用' : 'Analysis unavailable');
        document.getElementById('narrative-coverage').innerHTML = '';
        document.getElementById('narrative-toc').innerHTML = '';
        showError('narrative-content', LANG === 'zh' ? `长篇分析加载失败：${error.message}` : `Narrative failed: ${error.message}`);
    }
}

function renderNarrative() {
    const payload = state.narrative;
    if (!payload) return;
    renderNarrativeCoverage(payload);
    renderNarrativeArticle(payload);
    renderNarrativeOpportunities(payload);
    renderNarrativeChains(payload);
    const generated = document.getElementById('narrative-generated');
    if (generated) {
        const timestamp = formatReportTime(payload.generated_at);
        generated.textContent = LANG === 'zh'
            ? `生成时间 ${timestamp || '未记录'} · 正文 ${Number(payload.char_count || 0).toLocaleString()} 字`
            : `Generated ${timestamp || 'unknown'} · ${Number(payload.char_count || 0).toLocaleString()} characters`;
    }
}

function renderNarrativeCoverage(payload) {
    const container = document.getElementById('narrative-coverage');
    if (!container) return;
    const coverage = payload.coverage || {};
    const sourceLabels = LANG === 'zh'
        ? {paper: '论文', policy: '中国政策', news: '国内新闻', industry_report: '行业报告'}
        : {paper: 'Papers', policy: 'China policies', news: 'China news', industry_report: 'Industry reports'};
    const selectedCounts = coverage.selected_source_counts || {};
    const corpusCounts = coverage.source_counts || {};
    const chips = payload.view === 'paper'
        ? `<span class="narrative-source-chip"><strong>${escapeHtml(sourceLabels.paper)}</strong>${Number(coverage.selected_evidence_count || 0)} ${LANG === 'zh' ? '条引用证据' : 'cited items'} / ${Number(corpusCounts.paper || coverage.document_count || 0)} ${LANG === 'zh' ? '条语料' : 'corpus items'}</span>`
        : Object.entries(selectedCounts).map(([source, count]) =>
            `<span class="narrative-source-chip"><strong>${escapeHtml(sourceLabels[source] || source)}</strong>${Number(count || 0)} ${LANG === 'zh' ? '条引用证据' : 'cited items'}</span>`
        ).join('');
    const partial = coverage.status === 'partial';
    const gaps = [...(coverage.gaps || []), ...(payload.limitations || []).filter(item => !(coverage.gaps || []).includes(item))];
    container.innerHTML = `<div class="narrative-coverage-summary">
        <span class="narrative-status ${partial ? 'partial' : ''}">${partial ? (LANG === 'zh' ? '部分覆盖' : 'Partial coverage') : (LANG === 'zh' ? '来源覆盖' : 'Source coverage')}</span>
        <span>${escapeHtml(coverage.period_start || '')}${coverage.period_end ? ` — ${escapeHtml(coverage.period_end)}` : ''}</span>
        <span>${Number(coverage.month_count || 0)} ${LANG === 'zh' ? '个自然月' : 'months'}</span>
    </div><div class="narrative-source-row">${chips}</div>
    ${gaps.length ? `<details class="narrative-limitations"><summary>${LANG === 'zh' ? `结论边界与数据缺口（${gaps.length}）` : `Limitations (${gaps.length})`}</summary><ul>${gaps.map(gap => `<li>${escapeHtml(gap)}</li>`).join('')}</ul></details>` : ''}`;
}

function renderNarrativeArticle(payload) {
    const article = document.getElementById('narrative-content');
    const toc = document.getElementById('narrative-toc');
    if (!article || !toc) return;
    const sections = payload.sections || [];
    toc.innerHTML = sections.map((section, index) =>
        `<a href="#narrative-section-${escapeHtml(section.id)}"><span>${String(index + 1).padStart(2, '0')}</span>${escapeHtml(section.title)}</a>`
    ).join('');
    article.innerHTML = sections.length ? sections.map((section, index) => `<section id="narrative-section-${escapeHtml(section.id)}" class="narrative-section">
        <h2>${escapeHtml(section.title)}</h2>
        <div class="narrative-prose">${decorateNarrativeCitations(section.html || '')}</div>
    </section>`).join('') : `<p class="trend-note">${LANG === 'zh' ? '当前没有可展示的正文。' : 'No narrative is available.'}</p>`;
    bindNarrativeEvidenceButtons(article);
    wrapReadingTables(article);
}

function decorateNarrativeCitations(html) {
    return String(html || '').replace(/\[((?:POL|P|N|R)\d{2})\]/g, (_, id) =>
        `<button type="button" class="narrative-citation" data-evidence-id="${id}" aria-label="${LANG === 'zh' ? '查看证据' : 'Open evidence'} ${id}">${id}</button>`
    );
}

function renderNarrativeOpportunities(payload) {
    const section = document.getElementById('narrative-opportunity-section');
    const container = document.getElementById('narrative-opportunities');
    if (!section || !container) return;
    section.hidden = state.narrativeView !== 'paper';
    if (section.hidden) return;
    const opportunities = payload.opportunities || [];
    container.innerHTML = opportunities.length ? `<table class="narrative-opportunity-table"><thead><tr>
        <th>${LANG === 'zh' ? '研究问题' : 'Research question'}</th><th>${LANG === 'zh' ? '候选方法' : 'Method'}</th><th>${LANG === 'zh' ? '对比基线' : 'Baseline'}</th><th>${LANG === 'zh' ? '验证环境' : 'Validation'}</th><th>${LANG === 'zh' ? '核心指标' : 'Metrics'}</th><th>${LANG === 'zh' ? '支撑论文' : 'Evidence'}</th>
    </tr></thead><tbody>${opportunities.map(item => `<tr>
        <td><strong>${escapeHtml(item.title || '')}</strong><span>${escapeHtml(item.question || '')}</span></td>
        <td>${escapeHtml(item.method || '')}</td><td>${escapeHtml(item.baseline || '')}</td><td>${escapeHtml(item.validation || '')}</td>
        <td>${(item.metrics || []).map(metric => `<span class="narrative-metric">${escapeHtml(metric)}</span>`).join('')}</td>
        <td><button type="button" class="narrative-evidence-link" data-evidence-ids="${escapeHtml((item.evidence_ids || []).join(','))}">${(item.evidence_ids || []).length} ${LANG === 'zh' ? '篇' : 'items'}</button></td>
    </tr>`).join('')}</tbody></table>` : `<p class="trend-note">${LANG === 'zh' ? '当前没有实验机会条目。' : 'No experiment opportunities.'}</p>`;
    bindNarrativeEvidenceButtons(container);
}

function renderNarrativeChains(payload) {
    const section = document.getElementById('narrative-chain-section');
    const container = document.getElementById('narrative-chains');
    if (!section || !container) return;
    section.hidden = state.narrativeView !== 'multi_source';
    if (section.hidden) return;
    const chains = payload.evidence_chains || [];
    container.innerHTML = chains.length ? chains.map(chain => `<article class="narrative-chain-card">
        <div class="narrative-chain-heading"><div><small>${LANG === 'zh' ? '研究问题' : 'Research question'}</small><h3>${escapeHtml(chain.topic || '')}</h3></div><p>${escapeHtml(chain.question || '')}</p></div>
        <div class="narrative-chain-track">${(chain.nodes || []).map((node, index) => `${index ? '<i class="fas fa-arrow-right narrative-chain-arrow"></i>' : ''}<button type="button" class="narrative-chain-node ${node.status === 'missing' ? 'missing' : ''}" data-evidence-ids="${escapeHtml((node.evidence_ids || []).join(','))}" ${node.status === 'missing' ? 'disabled' : ''}>
            <span>${escapeHtml(node.label || '')}</span><strong>${node.status === 'missing' ? (LANG === 'zh' ? '证据缺口' : 'Evidence gap') : `${(node.evidence_ids || []).length} ${LANG === 'zh' ? '条' : 'items'}`}</strong><small>${escapeHtml(node.summary || '')}</small>
        </button>`).join('')}<i class="fas fa-arrow-right narrative-chain-arrow"></i><div class="narrative-chain-experiment"><span>${LANG === 'zh' ? '可执行实验' : 'Executable experiment'}</span><strong>${escapeHtml(chain.experiment?.title || '')}</strong><small>${escapeHtml(chain.experiment?.validation || '')}</small></div></div>
        <p class="narrative-causality-note"><i class="fas fa-shield-halved"></i>${escapeHtml(chain.causality_note || '')}</p>
    </article>`).join('') : `<p class="trend-note">${LANG === 'zh' ? '当前没有可展示的证据链。' : 'No evidence chains.'}</p>`;
    bindNarrativeEvidenceButtons(container);
}

function bindNarrativeEvidenceButtons(root) {
    root.querySelectorAll('.narrative-citation').forEach(button => button.addEventListener('click', () => openNarrativeEvidence([button.dataset.evidenceId])));
    root.querySelectorAll('[data-evidence-ids]').forEach(button => button.addEventListener('click', () => openNarrativeEvidence(String(button.dataset.evidenceIds || '').split(',').filter(Boolean))));
}

function openNarrativeEvidence(evidenceIds, evidenceIndex = null) {
    const drawer = document.getElementById('narrative-evidence-drawer');
    const backdrop = document.getElementById('narrative-drawer-backdrop');
    const body = document.getElementById('narrative-evidence-body');
    const title = document.getElementById('narrative-evidence-title');
    if (!drawer || !backdrop || !body) return;
    const index = evidenceIndex || state.narrative?.evidence_index || {};
    const ids = [...new Set(evidenceIds || [])].filter(id => index[id]);
    if (title) title.textContent = LANG === 'zh' ? `证据详情 · ${ids.length} 条` : `Evidence · ${ids.length}`;
    body.innerHTML = ids.length ? ids.map(id => {
        const item = index[id] || {};
        const safeUrl = /^https?:\/\//i.test(item.url || '') ? item.url : '';
        const auditNote = item.link_status && item.link_status !== 'verified'
            ? `<span class="narrative-no-link">${LANG === 'zh' ? `近期链接核验状态：${escapeHtml(item.link_status)}。${safeUrl ? '该站点可能限制自动访问，请打开后核对标题。' : '为避免跳转到无关或失效页面，已禁止跳转。'}` : `Recent link verification status: ${escapeHtml(item.link_status)}.${safeUrl ? ' The host may limit automated access; verify the title after opening.' : ' Navigation is disabled to avoid an unrelated or unavailable page.'}`}</span>`
            : '';
        return `<article class="narrative-evidence-item"><div class="narrative-evidence-meta"><code>${escapeHtml(id)}</code><span>${escapeHtml(item.source_name || item.source_type || '')}</span><time>${escapeHtml(item.event_date || '')}</time></div>
            <h3>${escapeHtml(item.title || '')}</h3><p>${escapeHtml(item.excerpt || '')}</p>
            ${safeUrl ? `<a href="${escapeHtml(safeUrl)}" target="_blank" rel="noopener noreferrer">${LANG === 'zh' ? '打开原始材料' : 'Open source'} <i class="fas fa-arrow-up-right-from-square"></i></a>${auditNote}` : `${auditNote || `<span class="narrative-no-link">${LANG === 'zh' ? '当前记录未提供原文链接' : 'No source URL'}</span>`}`}</article>`;
    }).join('') : `<p class="trend-note">${LANG === 'zh' ? '未找到对应证据。' : 'Evidence not found.'}</p>`;
    evidenceReturnFocus = document.activeElement;
    backdrop.hidden = false;
    drawer.inert = false;
    document.querySelector('.main-wrapper').inert = true;
    document.querySelector('.top-navbar').inert = true;
    drawer.classList.add('open');
    drawer.setAttribute('aria-hidden', 'false');
    document.body.classList.add('drawer-open');
    document.getElementById('narrative-drawer-close').focus();
}

function closeNarrativeEvidence() {
    const drawer = document.getElementById('narrative-evidence-drawer');
    const backdrop = document.getElementById('narrative-drawer-backdrop');
    if (!drawer || !backdrop || !drawer.classList.contains('open')) return;
    drawer.inert = true;
    document.querySelector('.main-wrapper').inert = false;
    document.querySelector('.top-navbar').inert = false;
    drawer.classList.remove('open');
    drawer.setAttribute('aria-hidden', 'true');
    backdrop.hidden = true;
    document.body.classList.remove('drawer-open');
    evidenceReturnFocus?.focus({preventScroll: true});
}

async function loadForecast() {
    const filters = state.forecastFilters;
    const params = new URLSearchParams();
    params.set('horizon', filters.horizon || 'all');
    if (filters.topic) params.set('topic', filters.topic);
    if (filters.confidence) params.set('confidence', filters.confidence);
    try {
        const response = await fetch(`/api/trends/forecast?${params.toString()}`);
        if (!response.ok) throw new Error('Failed to load forecast');
        const payload = await response.json();
        state.forecast = payload;
        if ((payload.taxonomy || []).length > state.forecastTaxonomy.length) {
            state.forecastTaxonomy = payload.taxonomy;
        }
        populateForecastTopics();
        renderForecastDashboard();
    } catch (error) {
        console.error('加载未来趋势失败:', error);
        showError('forecast-topic-cards', LANG === 'zh' ? '未来趋势加载失败' : 'Failed to load future trends');
    }
}

function populateForecastTopics() {
    const select = document.getElementById('forecast-topic');
    if (!select) return;
    const selected = state.forecastFilters.topic;
    const allLabel = LANG === 'zh' ? '全部六类主题' : 'All six topics';
    select.innerHTML = `<option value="">${allLabel}</option>` + state.forecastTaxonomy.map(item =>
        `<option value="${escapeHtml(item.id)}">${escapeHtml(item.label)}</option>`
    ).join('');
    select.value = selected;
}

async function loadWordcloud() {
    try {
        const response = await fetch('/api/wordcloud');
        if (response.status === 404) {
            document.getElementById('wordcloud-container').innerHTML = emptyState(t('noWordcloud'));
            return;
        }
        if (!response.ok) throw new Error('Failed to load wordcloud');
        
        const data = await response.json();
        const container = document.getElementById('wordcloud-container');
        
        if (data.url) {
            container.innerHTML = `<img src="${escapeHtml(data.url)}" alt="${LANG === 'zh' ? '研究热点词云' : 'Research word cloud'}">`;
            container.querySelector('img').addEventListener('error', () => showError('wordcloud-container', t('wordcloudLoadFailed')));
        } else {
            container.innerHTML = `<p>${t('noWordcloud')}</p>`;
        }
    } catch (error) {
        console.error('加载词云失败:', error);
        showError('wordcloud-container', t('wordcloudLoadFailed'));
    }
}

async function loadPapers(page = 1) {
    const version = (state.requestVersions.papers || 0) + 1;
    state.requestVersions.papers = version;
    state.currentPage = page;
    state.papersLoaded = false;
    renderPagination(0, page);
    try {
        showLoading('papers-list');
        
        const params = new URLSearchParams({
            page: page,
            per_page: state.papersPerPage,
            category: state.selectedCategory
        });
        
        const response = await fetch(`/api/papers?${params}`);
        if (!response.ok && response.status !== 404) throw new Error('Failed to load papers');
        const data = response.status === 404 ? {papers: [], total: 0, total_pages: 0} : await response.json();
        if (state.requestVersions.papers !== version) return;
        renderCollectionQuality(data.collection_quality || {});
        state.papersLoaded = true;
        state.allPapers = data.papers || [];
        state.currentPage = page;
        state.paperTotal = Number(data.total || 0);
        sortPapers(state.paperSort);
        
        // 渲染论文列表
        renderPapers(filterPapers(state.allPapers));
        
        // 渲染分页
        renderPagination(data.total_pages, page);
        
        // 渲染热门论文（概览页）
        renderFeaturedPapers(state.allPapers.slice(0, 5));
        renderResearchMatrix();
        renderComparisonTable();
        
    } catch (error) {
        if (state.requestVersions.papers !== version) return;
        console.error('加载论文失败:', error);
        showError('papers-list', LANG === 'en' ? 'Failed to load papers' : '加载论文失败');
        showError('featured-papers', LANG === 'en' ? 'Failed to load papers' : '加载论文失败');
        updateElement('papers-result-count', '—');
    }
}

function renderCollectionQuality(report) {
    const node = document.getElementById('paper-collection-quality');
    if (!node) return;
    const unavailable = report.unavailable_sources || [];
    const percent = report.abstract_completeness == null ? '—' : (report.abstract_completeness * 100).toFixed(1) + '%';
    const parts = report.raw_count == null ? [] : [
        `累计原始记录 ${report.raw_count} · 去重后 ${report.unique_count} · 合格 ${report.admitted_count} · 摘要完整率 ${percent}`,
        `中科院分区版本 ${(report.cas_editions || []).join(' / ') || '待核验'} · 未完成分片 ${report.incomplete_count || 0}`
    ];
    if (unavailable.length) parts.push('未接通来源：' + unavailable.join(' / '));
    node.textContent = parts.join('。');
}

async function loadCategories() {
    try {
        const response = await fetch('/api/categories');
        if (!response.ok) throw new Error('Failed to load categories');
        
        const categories = await response.json();
        state.categoriesFailed = false;
        state.allCategories = categories;
        
        
        // 渲染类别筛选（论文列表页）
        renderCategoryFilter(categories);
        
    } catch (error) {
        state.categoriesFailed = true;
        console.error('加载类别失败:', error);
    }
    renderPaperSupportStatus();
}

// ==================== 渲染函数 ==================== //
function renderPaperSupportStatus() {
    const container = document.getElementById('paper-support-status');
    if (!container) return;
    const failed = [state.knowledgeFailed ? (LANG === 'zh' ? '结构化知识' : 'Structured knowledge') : '', state.categoriesFailed ? (LANG === 'zh' ? '论文类别' : 'Paper categories') : ''].filter(Boolean);
    container.hidden = !failed.length;
    if (failed.length) showError('paper-support-status', LANG === 'zh' ? `${failed.join('、')}暂不可用，已加载资料仍可阅读。` : `${failed.join(', ')} unavailable; loaded documents remain readable.`);
}

function renderPapers(papers) {
    const container = document.getElementById('papers-list');
    updateElement('papers-result-count', LANG === 'zh'
        ? `类别范围共 ${state.paperTotal} 篇 · 本页匹配 ${papers.length} 篇，共加载 ${state.allPapers.length} 篇`
        : `${state.paperTotal} in category scope · ${papers.length} matches / ${state.allPapers.length} loaded on this page`);
    updateElement('paper-applied-filters', filterDescription({search: state.searchQuery, topic: state.selectedCategory, priority: state.selectedPriority}));
    container.innerHTML = papers.length
        ? papers.map(paper => renderDocumentRow(paper, 'paper')).join('')
        : emptyState(state.searchQuery || state.selectedPriority || state.selectedCategory
            ? (LANG === 'zh' ? '没有匹配的论文，请调整或清除筛选。' : 'No matching papers. Adjust or clear filters.')
            : t('noPapers'));
}

function sourceLink(url, label, className = 'btn-paper btn-secondary') {
    return /^https?:\/\//i.test(url || '')
        ? `<a href="${escapeHtml(url)}" class="${className}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)} <i class="fas fa-arrow-up-right-from-square" aria-hidden="true"></i></a>`
        : '';
}

function renderDocumentRow(document, sourceType) {
    const card = document.web_card || document;
    const links = card.links || {};
    const suggestion = card.reading_suggestion || {};
    const title = card.title || document.title || '';
    const url = links.source_url || links.primary_url || document.url || document.entry_url || '';
    const date = card.published_at || document.published_at || document.published || '';
    const organization = card.author_line || card.source_name || document.source_name || (document.authors || []).slice(0, 3).join(', ');
    const specificSource = {paper: card.source_metadata?.journal_name || document.journal_name,
        policy: document.issuing_body, news: document.media_name, industry_report: document.institution}[sourceType];
    const sourceName = specificSource || card.source_name || document.source_name;
    const summary = card.summary || card.description || document.summary || document.abstract || document.raw_text || t('noAbstract');
    const badges = [...new Set([...(card.badges || document.categories || document.tags || []), ...(suggestion.related_topics || [])])];
    const knowledge = sourceType === 'paper' ? state.knowledgeByPaperId[document.id] : null;
    const pdf = links.pdf_url || document.pdf_url;
    const citationCount = card.source_metadata?.citation_count ?? document.citation_count;
    const facts = sourceType === 'policy' ? [
        [LANG === 'zh' ? '地域' : 'Region', document.region],
        [LANG === 'zh' ? '生效日期' : 'Effective date', document.effective_date]
    ] : sourceType === 'industry_report' ? [
        [LANG === 'zh' ? '主题' : 'Topics', (document.themes || []).join('、')]
    ] : [];
    return `<article class="document-row">
        <div class="document-heading">
            <div><h3>${sourceLink(url, title, '') || escapeHtml(title)}</h3>
                <div class="paper-meta">${sourceName ? `<span>${escapeHtml(sourceName)}</span>` : ''}${organization && organization !== sourceName ? `<span>${escapeHtml(organization)}</span>` : ''}<time>${escapeHtml(String(date).slice(0, 10) || (LANG === 'zh' ? '发布日期未提供' : 'Publication date unavailable'))}</time>${sourceType === 'paper' && citationCount != null ? `<span>${LANG === 'zh' ? '引用' : 'Citations'} ${Number(citationCount)}</span>` : ''}${facts.filter(([, value]) => value).map(([label, value]) => `<span>${label}：${escapeHtml(value)}</span>`).join('')}</div>
            </div>${renderRankingPanel(card, true)}
        </div>
        <p class="document-summary clamp-two">${escapeHtml(summary)}</p>
        <div class="document-actions">
            <details class="document-details"><summary>${LANG === 'zh' ? '展开资料与分析依据' : 'Expand document and analysis'}</summary>
                <div class="document-details-body">
                    <h4>${LANG === 'zh' ? '系统摘要' : 'System summary'}</h4><p class="paper-abstract">${escapeHtml(summary)}</p>
                    ${sourceType === 'paper' && (document.authors || card.authors_or_orgs || []).length ? `<p class="paper-meta">${LANG === 'zh' ? '作者' : 'Authors'}：${escapeHtml((document.authors || card.authors_or_orgs).join(', '))}</p>` : ''}
                    ${document.abstract && document.abstract !== summary ? `<h4>${LANG === 'zh' ? '原始摘要' : 'Original abstract'}</h4><p class="paper-abstract">${escapeHtml(document.abstract)}</p>` : ''}
                    <div class="paper-meta">${renderCompactInfoBar(card, document)}</div>
                    ${renderRankingPanel({...card, ranking_applicable_dimensions: document.ranking_applicable_dimensions})}
                    ${renderKnowledgePanel(knowledge)}
                    ${renderRelatedDocuments(card)}
                    <div class="paper-categories">${badges.map(tag => `<span class="category-badge">${escapeHtml(tag)}</span>`).join('')}</div>
                </div>
            </details>
            <div class="paper-actions">${pdf && pdf !== url ? sourceLink(pdf, /\.pdf(?:[?#]|$)|\/pdf\//i.test(pdf) ? 'PDF' : (LANG === 'zh' ? '全文入口' : 'Full text')) : ''}${sourceLink(url, t('originalSource'))}</div>
        </div>
    </article>`;
}

async function loadIntelligenceHome() {
    const version = (state.requestVersions.home || 0) + 1;
    state.requestVersions.home = version;
    showLoading('today-recommendations');
    const filters = state.homeFilters;
    const params = new URLSearchParams({
        source_type: filters.sourceType,
        topic: filters.topic,
        priority: filters.priority,
        date_from: filters.dateFrom,
        date_to: filters.dateTo,
        sort: 'relevance',
        per_page: 8
    });
    try {
        const response = await fetch(`/api/research-information?${params}`);
        if (!response.ok) throw new Error('Failed to load research information');
        const payload = await response.json();
        if (state.requestVersions.home !== version) return;
        updateElement('intelligence-result-count', LANG === 'zh'
            ? `匹配 ${payload.total || 0} 条 · 展示 ${(payload.documents || []).length} 条`
            : `${payload.total || 0} matches · ${(payload.documents || []).length} shown`);
        updateElement('home-applied-filters', filterDescription(filters));
        renderTodayRecommendations(payload.documents || []);
        renderSourceSnapshot(payload.source_counts || {});
    } catch (error) {
        if (state.requestVersions.home !== version) return;
        console.error('加载科研信息首页失败:', error);
        showError('today-recommendations', LANG === 'zh' ? '重点信息加载失败' : 'Failed to load priority information');
        updateElement('intelligence-result-count', '—');
        document.getElementById('source-snapshot').innerHTML = emptyState(LANG === 'zh' ? '来源数量暂不可用' : 'Source counts unavailable');
    }
}

function renderTodayRecommendations(documents) {
    const container = document.getElementById('today-recommendations');
    if (!container) return;
    if (!documents.length) {
        container.innerHTML = emptyState(hasFilters(state.homeFilters)
            ? (LANG === 'zh' ? '没有符合当前条件的资料，可清除筛选后重新查看。' : 'No matches. Clear filters to see available sources.') : t('noIntelligence'));
        return;
    }
    const labels = LANG === 'zh'
        ? {paper: '论文', policy: '政策', news: '新闻', industry_report: '行业报告'}
        : {paper: 'Paper', policy: 'Policy', news: 'News', industry_report: 'Industry report'};
    container.innerHTML = documents.map(document => {
        const card = document.web_card || document;
        const suggestion = card.reading_suggestion || document.reading_suggestion || {};
        const url = card.links?.source_url || card.links?.primary_url || document.url || document.entry_url || '';
        const sourceType = card.source_type || document.source_type || 'paper';
        const summary = card.summary || card.description || document.summary || document.abstract || '';
        return `<article class="recommendation-card">
            <h3>${sourceLink(url, card.title || document.title || '', '') || escapeHtml(card.title || document.title || '')}</h3>
            <div class="recommendation-meta"><span>${labels[sourceType] || escapeHtml(sourceType)}</span><span>${escapeHtml(card.source_name || document.source_name || '')}</span><time>${escapeHtml(String(card.published_at || document.published_at || document.published || '').slice(0, 10) || (LANG === 'zh' ? '发布日期未提供' : 'Publication date unavailable'))}</time></div>
            <p class="clamp-two">${escapeHtml(summary)}</p>
            <footer>${renderRankingPanel(card, true)}<details class="recommendation-details"><summary>${LANG === 'zh' ? '摘要与推荐依据' : 'Summary and rationale'}</summary><div><p><small>${LANG === 'zh' ? '系统摘要' : 'System summary'}</small><br>${escapeHtml(summary)}</p>${suggestion.why_relevant ? `<p><small>${t('relevanceReason')}</small><br>${escapeHtml(suggestion.why_relevant)}</p>` : ''}${sourceLink(url, t('originalSource'))}</div></details></footer>
        </article>`;
    }).join('');
}

function renderSourceSnapshot(counts) {
    const container = document.getElementById('source-snapshot');
    if (!container) return;
    const items = [
        ['paper', 'papers', 'fa-file-lines', LANG === 'zh' ? '论文' : 'Papers'],
        ['policy', 'policies', 'fa-landmark', LANG === 'zh' ? '中国政策' : 'China policies'],
        ['news', 'news', 'fa-newspaper', LANG === 'zh' ? '国内新闻' : 'China news'],
        ['industry_report', 'industry-reports', 'fa-industry', LANG === 'zh' ? '行业报告' : 'Industry reports']
    ];
    container.innerHTML = items.map(([type, section, icon, label]) => `<button type="button" class="source-snapshot-item" data-home-section="${section}" title="${LANG === 'zh' ? '打开资料目录（保留该页条件）' : 'Open directory with its own filters'}"><span>${label}</span><strong>${Number(counts[type] || 0)}</strong></button>`).join('');
    container.querySelectorAll('[data-home-section]').forEach(button => {
        button.addEventListener('click', () => navigateToSection(button.dataset.homeSection));
    });
}

function renderHomeTrendSignals() {
    const container = document.getElementById('home-trend-signals');
    if (!container) return;
    const forecastSignals = (state.forecast?.forecasts || []).slice(0, 3).map(item => {
        const metrics = item.metrics || {};
        const mode = item.mode === 'quantitative'
            ? (LANG === 'zh' ? '定量预测' : 'Quantitative')
            : (LANG === 'zh' ? '低置信情景' : 'Low-confidence scenario');
        return {
            title: item.topic || item.topic_id,
            body: `${trajectoryLabel(item.trajectory)} · ${confidenceLabel(item.confidence)} · ${mode}`,
            gaps: (item.data_gaps || []).join('；'),
            evidenceIds: item.evidence_ids || []
        };
    });
    if (forecastSignals.length) {
        container.innerHTML = `<p class="signal-scope">${LANG === 'zh' ? '系统预测 · 截至' : 'System forecast · As of'} ${escapeHtml(state.forecast.as_of || '—')}</p>` + forecastSignals.map((item, index) => `<div class="home-trend-signal"><strong>${escapeHtml(item.title)}</strong><span>${escapeHtml(item.body)}</span>${item.gaps ? `<span>${escapeHtml(item.gaps)}</span>` : ''}${item.evidenceIds.length ? `<button class="narrative-evidence-link" type="button" data-signal-index="${index}">${LANG === 'zh' ? '查看依据' : 'View evidence'} · ${item.evidenceIds.length}</button>` : ''}</div>`).join('');
        container.querySelectorAll('[data-signal-index]').forEach(button => button.addEventListener('click', () => {
            const ids = forecastSignals[Number(button.dataset.signalIndex)].evidenceIds;
            openNarrativeEvidence(ids, documentEvidenceIndex(ids));
        }));
        return;
    }
    // Compatibility fallback for analysis artifacts created before schema 2.0.
    const sevenDay = state.analysis?.temporal_trends?.windows?.['7'] || {};
    const rising = (sevenDay.topic_momentum || []).filter(item => ['new', 'rising'].includes(item.status)).slice(0, 3);
    const directions = (state.analysis?.cross_source_analysis?.directions || []).slice(0, 2);
    const signals = rising.map(item => ({
        title: item.name,
        body: `${LANG === 'zh' ? '近 7 天变化' : '7-day change'} ${Number(item.delta || 0) >= 0 ? '+' : ''}${Number(item.delta || 0)}`
    })).concat(directions.map(item => ({title: item.direction, body: item.judgment || item.rationale || ''})));
    container.innerHTML = signals.length
        ? signals.map(item => `<div class="home-trend-signal"><strong>${escapeHtml(item.title)}</strong><span>${escapeHtml(item.body)}</span></div>`).join('')
        : `<p class="trend-note">${t('signalInsufficient')}</p>`;
}

async function loadSchedulerStatus() {
    const container = document.getElementById('scheduler-job-status');
    if (!container) return;
    const version = (state.requestVersions.scheduler || 0) + 1;
    state.requestVersions.scheduler = version;
    try {
        const response = await fetch('/api/scheduler/status');
        if (!response.ok) throw new Error('Failed to load scheduler status');
        const payload = await response.json();
        if (state.requestVersions.scheduler !== version) return;
        if (!payload.enabled) {
            container.innerHTML = `<p class="trend-note">${t('schedulerDisabled')}</p>`;
            return;
        }
        const labels = {
            pending: t('schedulerPending'),
            running: LANG === 'zh' ? '运行中' : 'Running',
            empty: t('schedulerEmpty'),
            failed: t('schedulerFailed'),
            succeeded: t('schedulerSucceeded'),
            partial: t('schedulerPartial')
        };
        container.innerHTML = (payload.jobs || []).map(job => {
            const status = job.status || 'pending';
            const finished = job.last_finished_at || job.finished_at || '';
            return `<article class="scheduler-job-item scheduler-job-${escapeHtml(status)}">
                <div><strong>${escapeHtml(job.name || job.id || '')}</strong><span>${escapeHtml(job.schedule || '')}</span></div>
                <span class="scheduler-status-badge">${escapeHtml(labels[status] || status)}</span>
                <small>${finished ? formatReportTime(finished) : `${(job.sources || []).length} ${LANG === 'zh' ? '个来源' : 'sources'}`}</small>
            </article>`;
        }).join('') || `<p class="trend-note">${t('schedulerPending')}</p>`;
    } catch (error) {
        if (state.requestVersions.scheduler !== version) return;
        console.warn('加载调度状态失败:', error);
        showError('scheduler-job-status', t('schedulerLoadFailed'));
    }
}

async function loadReport(reportType) {
    const version = (state.requestVersions.report || 0) + 1;
    state.requestVersions.report = version;
    const selectedType = reportType || document.getElementById('report-type')?.value || 'weekly';
    showLoading('intelligence-report');
    updateElement('report-period', t('loading'));
    document.getElementById('report-limitations').innerHTML = '';
    document.getElementById('report-toc').innerHTML = '';
    ['document', 'paper', 'policy', 'industry'].forEach(key => updateElement('report-' + key + '-count', '—'));
    try {
        const response = await fetch(`/api/reports/latest?report_type=${encodeURIComponent(selectedType)}`);
        if (!response.ok) throw new Error('Failed to load report');
        const payload = await response.json();
        if (state.requestVersions.report !== version) return;
        state.report = payload;
        renderIntelligenceReport(state.report);
    } catch (error) {
        if (state.requestVersions.report !== version) return;
        console.error('加载研究报告失败:', error);
        updateElement('report-title', LANG === 'zh' ? '研究报告' : 'Research report');
        showError('home-report-entry', t('reportLoadFailed'));
        updateElement('report-period', t('reportLoadFailed'));
        ['document', 'paper', 'policy', 'industry'].forEach(key => updateElement('report-' + key + '-count', '—'));
        document.getElementById('report-toc').innerHTML = '';
        showError('intelligence-report', t('reportLoadFailed'));
    }
}

function renderIntelligenceReport(report) {
    const home = document.getElementById('home-report-entry');
    if (home) home.innerHTML = `<a href="#reports" data-section="reports">${escapeHtml(report.title || '')}</a><p>${escapeHtml(report.period_start || '—')} — ${escapeHtml(report.period_end || '—')}</p><p>${t('reportGenerated')} ${escapeHtml(formatReportTime(report.generated_at))}</p><p>${LANG === 'zh' ? '本期收录' : 'Period sample'} ${Number(report.document_count || 0)} ${LANG === 'zh' ? '条资料' : 'documents'}</p>`;
    updateElement('report-title', report.title || '');
    updateElement(
        'report-period',
        `${t('reportPeriod')}：${report.period_start || '—'} — ${report.period_end || '—'} · ${t('reportGenerated')} ${formatReportTime(report.generated_at)}`
    );
    const sourceCounts = report.source_counts || {};
    const quality = report.data_quality || {};
    const limitations = document.getElementById('report-limitations');
    if (limitations) limitations.innerHTML = `<p>${LANG === 'zh' ? '正文历史证据范围' : 'Historical evidence window'}：${escapeHtml(quality.period_start || '—')} — ${escapeHtml(quality.period_end || '—')} · ${quality.document_count ?? '—'} ${LANG === 'zh' ? '条语料' : 'corpus items'} · ${quality.selected_evidence_count ?? '—'} ${LANG === 'zh' ? '条引用证据' : 'cited items'}</p>${(quality.gaps || []).length ? `<details><summary>${LANG === 'zh' ? '数据缺口与结论边界' : 'Data gaps and limitations'} (${quality.gaps.length})</summary><ul>${quality.gaps.map(gap => `<li>${escapeHtml(gap)}</li>`).join('')}</ul></details>` : ''}`;
    updateElement('report-document-count', Number(report.document_count || 0));
    updateElement('report-paper-count', Number(sourceCounts.paper || 0));
    updateElement('report-policy-count', Number(sourceCounts.policy || 0));
    updateElement(
        'report-industry-count',
        Number(sourceCounts.news || 0) + Number(sourceCounts.industry_report || 0)
    );

    const container = document.getElementById('intelligence-report');
    if (!container) return;
    const sections = report.sections || [];
    document.getElementById('report-toc').innerHTML = sections.map((section, index) =>
        '<a href="#report-section-' + index + '"><span>' + String(index + 1).padStart(2, '0') + '</span>' + escapeHtml(section.title || '') + '</a>'
    ).join('');
    if (!sections.length) {
        container.innerHTML = `<div class="report-empty">${t('reportEmpty')}</div>`;
        return;
    }
    container.innerHTML = sections.map((section, index) => {
        const items = section.items || [];
        const isNarrative = section.kind === 'narrative';
        return `<article id="report-section-${index}" class="report-section-card ${isNarrative ? 'report-section-narrative' : ''} report-section-${escapeHtml(section.key || '')}">
            <header>
                <span class="report-section-index">${String(index + 1).padStart(2, '0')}</span>
                <h2>${escapeHtml(section.title || '')}</h2>
                <span class="report-section-count">${isNarrative ? `${Number(section.char_count || 0).toLocaleString()} ${LANG === 'zh' ? '字' : 'chars'}` : items.length}</span>
            </header>
            <div class="${isNarrative ? 'report-narrative-body analysis-content' : 'report-section-items'}" ${isNarrative ? `data-report-view="${escapeHtml(section.view || '')}"` : ''}>
                ${isNarrative ? decorateNarrativeCitations(section.html || '') : (items.length ? items.map(item => renderReportItem(item, section.key)).join('') : `<p class="report-empty">${t('reportEmpty')}</p>`)}
            </div>
        </article>`;
    }).join('');
    wrapReadingTables(container);
    container.querySelectorAll('.report-narrative-body').forEach(section => {
        const evidenceIndex = report.evidence_indexes?.[section.dataset.reportView] || {};
        section.querySelectorAll('.narrative-citation').forEach(button => {
            button.addEventListener('click', () => openNarrativeEvidence([button.dataset.evidenceId], evidenceIndex));
        });
    });
}

function renderReportItem(item, sectionKey = '') {
    const score = Number(item.importance_score || 0);
    const isAppendix = String(sectionKey).startsWith('appendix_');
    const sourceUrl = /^https?:\/\//i.test(item.url || '') ? item.url : '';
    const sourceTypeLabel = {
        paper: LANG === 'zh' ? '论文' : 'Paper',
        policy: LANG === 'zh' ? '政策' : 'Policy',
        news: LANG === 'zh' ? '新闻' : 'News',
        industry_report: LANG === 'zh' ? '行业报告' : 'Industry report'
    }[item.source_type] || '';
    return `<div class="report-item">
        <div class="report-item-heading">
            <h3>${escapeHtml(item.heading || '')}</h3>
            ${sourceTypeLabel ? `<span class="report-source-chip">${sourceTypeLabel}</span>` : ''}
            ${isAppendix && score > 0 ? `<span class="report-score">${score.toFixed(1)}</span>` : ''}
        </div>
        ${item.body ? `<p>${escapeHtml(item.body)}</p>` : ''}
        ${renderReportEvidence(item)}
        <div class="report-item-footer">
            ${item.meta ? `<span>${escapeHtml(item.meta)}</span>` : '<span></span>'}
            ${sourceUrl ? `<a href="${escapeHtml(sourceUrl)}" target="_blank" rel="noopener noreferrer">${t('reportOriginal')}<i class="fas fa-arrow-up-right-from-square"></i></a>` : ''}
        </div>
    </div>`;
}

function renderReportEvidence(item) {
    const evidenceIds = item.evidence_ids || [];
    const counterSignals = item.counter_signals || [];
    const watchIndicators = item.watch_indicators || [];
    if (!evidenceIds.length && !counterSignals.length && !watchIndicators.length) return '';
    return `<details class="report-evidence">
        <summary>${LANG === 'zh' ? '查看证据、反证与监测项' : 'Evidence, counter-signals and monitoring'}</summary>
        ${evidenceIds.length ? `<div><strong>${LANG === 'zh' ? '证据ID' : 'Evidence IDs'}</strong>${evidenceIds.map(value => `<code>${escapeHtml(value)}</code>`).join('')}</div>` : ''}
        ${counterSignals.length ? `<div><strong>${LANG === 'zh' ? '反证条件' : 'Counter-signals'}</strong>${counterSignals.map(value => `<span>${escapeHtml(value)}</span>`).join('')}</div>` : ''}
        ${watchIndicators.length ? `<div><strong>${LANG === 'zh' ? '监测指标' : 'Watch indicators'}</strong>${watchIndicators.map(value => `<span>${escapeHtml(value)}</span>`).join('')}</div>` : ''}
    </details>`;
}

function formatReportTime(value) {
    const parsed = new Date(value || '');
    if (Number.isNaN(parsed.getTime())) return value || '—';
    return new Intl.DateTimeFormat(LANG === 'zh' ? 'zh-CN' : 'en', {
        year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
    }).format(parsed);
}

async function loadDirectory(sourceType, page = 1) {
    const directory = state.directories[sourceType];
    if (!directory) return;
    const ids = directoryIds(sourceType);
    directory.page = page;
    const version = (state.requestVersions[sourceType] || 0) + 1;
    state.requestVersions[sourceType] = version;
    showLoading(ids.list);
    document.getElementById((sourceType === 'industry_report' ? 'industry-report' : sourceType) + '-pagination').innerHTML = '';
    const params = new URLSearchParams({
        source_type: sourceType,
        page: page,
        per_page: 20,
        search: directory.search,
        topic: directory.topic,
        priority: directory.priority,
        date_from: directory.dateFrom,
        date_to: directory.dateTo,
        sort: directory.sort
    });
    try {
        const response = await fetch(`/api/documents?${params}`);
        if (!response.ok) throw new Error('Failed to load directory');
        const payload = await response.json();
        if (state.requestVersions[sourceType] !== version) return;
        directory.totalPages = Number(payload.total_pages || 0);
        directory.documents = payload.documents || [];
        directory.total = Number(payload.total || 0);
        if (!hasFilters(directory)) {
            directory.unfilteredTotal = directory.total;
            updateElement(ids.navCount, directory.total);
        }
        updateElement(ids.total, LANG === 'zh'
            ? `资料总数 ${directory.unfilteredTotal ?? '—'} · 匹配 ${directory.total} · 本页 ${directory.documents.length}`
            : `${directory.unfilteredTotal ?? '—'} total · ${directory.total} matched · ${directory.documents.length} on page`);
        updateElement((sourceType === 'industry_report' ? 'industry-report' : sourceType) + '-applied-filters', filterDescription(directory));
        renderDirectoryPagination(sourceType);
        renderDirectoryDocuments(sourceType, directory.documents);
    } catch (error) {
        if (state.requestVersions[sourceType] !== version) return;
        console.error(`加载 ${sourceType} 目录失败:`, error);
        updateElement(ids.total, '—');
        showError(ids.list, LANG === 'zh' ? '目录加载失败' : 'Failed to load directory');
    }
}

function directoryIds(sourceType) {
    const prefix = sourceType === 'industry_report' ? 'industry-report' : sourceType;
    return {list: `${prefix}-list`, total: `${prefix}-total`, navCount: `${prefix}-nav-count`};
}

function renderDirectoryDocuments(sourceType, documents) {
    const container = document.getElementById(directoryIds(sourceType).list);
    if (!container) return;
    const filters = state.directories[sourceType];
    const filtered = filters.search || filters.topic || filters.priority || filters.dateFrom || filters.dateTo;
    const labels = {policy: t('emptyPolicyTitle'), news: t('emptyNewsTitle'), industry_report: t('emptyReportTitle')};
    container.innerHTML = documents.length
        ? documents.map(document => renderDocumentRow(document, sourceType)).join('')
        : emptyState(filtered ? (LANG === 'zh' ? '没有匹配资料，请调整或清除筛选。' : 'No matches. Adjust or clear filters.') : labels[sourceType]);
}

function renderRelatedDocuments(card) {
    const related = card.related_documents || [];
    const duplicateSources = card.duplicate_sources || [];
    if (!related.length && duplicateSources.length < 2) return '';
    const typeLabels = LANG === 'zh'
        ? {paper: '论文', policy: '政策', news: '新闻', industry_report: '行业报告'}
        : {paper: 'Paper', policy: 'Policy', news: 'News', industry_report: 'Industry report'};
    const links = related.map(item => `<div class="related-document">
        <span class="related-type">${typeLabels[item.source_type] || escapeHtml(item.source_type)}</span>
        <span class="related-title">${sourceLink(item.url, item.title, '') || escapeHtml(item.title)}</span>
        <span>${item.score != null ? `${LANG === 'zh' ? '关联分' : 'Relation score'} ${Math.round(Number(item.score) * 100)}` : ''}</span>
        <small>${escapeHtml(item.reason || '')}</small>
    </div>`).join('');
    const merged = duplicateSources.length > 1
        ? `<div class="merged-sources"><i class="fas fa-code-merge"></i>${t('duplicateSources')}：${duplicateSources.map(escapeHtml).join('、')}</div>`
        : '';
    return `<details class="related-panel">
        <summary><i class="fas fa-link"></i>${t('relatedIntelligence')} <span>${related.length}</span></summary>
        ${merged}<div class="related-list">${links}</div>
    </details>`;
}

function renderWebSuggestionPanel(card) {
    const suggestion = card.reading_suggestion || {};
    const sourceName = card.source_name || '';
    const blocks = [];

    if (sourceName) {
        blocks.push(`<span><strong>${t('sourceLabel')}:</strong> ${escapeHtml(sourceName)}</span>`);
    }
    if (suggestion.read_priority) {
        blocks.push(`<span><strong>${t('priorityLabel')}:</strong> ${escapeHtml(suggestion.read_priority)}</span>`);
    }
    if (suggestion.recommended_action) {
        blocks.push(`<span><strong>${t('recommendationLabel')}:</strong> ${escapeHtml(suggestion.recommended_action)}</span>`);
    }
    if (suggestion.related_topics && suggestion.related_topics.length) {
        blocks.push(`<span><strong>${t('relatedTopicsLabel')}:</strong> ${escapeHtml(suggestion.related_topics.join(', '))}</span>`);
    }

    if (!blocks.length) return '';
    return `<div class="paper-authors">${blocks.join(' · ')}</div>`;
}

function renderRankingPanel(card, compact = false) {
    const suggestion = card.reading_suggestion || {};
    const rawPriority = card.read_priority || suggestion.read_priority;
    const priority = ['high', 'medium', 'low'].includes(rawPriority) ? rawPriority : '';
    const action = card.recommended_action || suggestion.recommended_action || '';
    const score = card.importance_score == null || card.importance_score === '' ? NaN : Number(card.importance_score);
    const breakdown = card.ranking_score_breakdown || {};
    const reason = suggestion.why_relevant || '';
    const labels = {
        topic_relevance: LANG === 'zh' ? '主题相关性' : 'Topic relevance',
        novelty: LANG === 'zh' ? '新颖性' : 'Novelty',
        policy_importance: LANG === 'zh' ? '政策重要性' : 'Policy importance',
        industry_relevance: LANG === 'zh' ? '行业相关性' : 'Industry relevance',
        source_credibility: LANG === 'zh' ? '来源可信度' : 'Source credibility'
    };
    const rows = Object.entries(labels)
        .filter(([key]) => Object.prototype.hasOwnProperty.call(breakdown, key) && (!card.ranking_applicable_dimensions || card.ranking_applicable_dimensions.includes(key)))
        .map(([key, label]) => {
            const value = Math.max(0, Math.min(100, Number(breakdown[key]) || 0));
            return `<div class="score-row">
                <span>${label}</span>
                <progress max="100" value="${value}" aria-label="${label}"></progress>
                <strong>${Math.round(value)}</strong>
            </div>`;
        }).join('');

    return `<div class="ranking-panel ranking-${priority}">
        <div class="ranking-summary">
            ${priority ? `<span class="priority-pill priority-${priority}">${priorityLabel(priority)}</span>` : ''}
            ${!compact && action ? `<span class="action-pill">${escapeHtml(action)}</span>` : ''}
            ${Number.isFinite(score) ? `<span class="score-pill">${t('scoreLabel')} <strong>${score.toFixed(1)}</strong></span>` : ''}
        </div>
        ${!compact && (rows || reason) ? `<details class="ranking-details">
            <summary>${t('scoreBreakdown')}</summary>
            <div class="score-grid">${rows}</div>
            <p>${LANG === 'zh' ? '综合评分与适用维度均为 0–100 分，用于安排阅读顺序，不代表准确率或商业价值。' : 'Overall and applicable dimension scores use a 0–100 scale for reading priority, not accuracy or commercial value.'}</p>
            ${reason ? `<p><strong>${t('relevanceReason')}：</strong>${escapeHtml(reason)}</p>` : ''}
        </details>` : ''}
    </div>`;
}

function normalizePriority(value) {
    return ['high', 'medium', 'low'].includes(value) ? value : 'low';
}

function priorityLabel(priority) {
    if (LANG === 'en') return {high: 'High', medium: 'Medium', low: 'Low'}[priority];
    return {high: '高优先级', medium: '中优先级', low: '低优先级'}[priority];
}

function renderOpenAlexPanel(card) {
    const meta = card.source_metadata || {};
    const items = [];

    if (meta.journal_name) {
        items.push(`<span><strong>${t('journalLabel')}:</strong> ${escapeHtml(meta.journal_name)}</span>`);
    }
    if (meta.cas_partition) items.push(`<span>中科院 ${escapeHtml(String(meta.cas_edition_year))} · ${escapeHtml(meta.cas_major_category || '')} ${escapeHtml(String(meta.cas_partition))} 区</span>`);
    if (meta.abstract_status === 'missing') items.push('<span>摘要待补齐</span>');
    if (meta.discovered_via?.length) items.push(`<span>${escapeHtml(meta.discovered_via.join(' / '))}</span>`);
    if (meta.citation_count !== undefined && meta.citation_count !== null) {
        items.push(`<span><strong>${t('citationsLabel')}:</strong> ${escapeHtml(String(meta.citation_count))}</span>`);
    }
    if (meta.openalex_primary_topic) {
        items.push(`<span><strong>${t('primaryTopicLabel')}:</strong> ${escapeHtml(meta.openalex_primary_topic)}</span>`);
    }
    if (meta.openalex_institutions && meta.openalex_institutions.length) {
        items.push(`<span><strong>${t('institutionsLabel')}:</strong> ${escapeHtml(meta.openalex_institutions.slice(0, 3).join(', '))}</span>`);
    }
    if (meta.openalex_referenced_works_count !== undefined && meta.openalex_referenced_works_count !== null) {
        items.push(`<span><strong>${t('referencesLabel')}:</strong> ${escapeHtml(String(meta.openalex_referenced_works_count))}</span>`);
    }

    if (!items.length) return '';
    return `<div class="paper-authors">${items.join(' · ')}</div>`;
}

function renderCompactInfoBar(card, paper) {
    const meta = card.source_metadata || {};
    const parts = [];
    if (meta.journal_name) parts.push(meta.journal_name);
    if (meta.citation_count != null) parts.push(t('citationsLabel') + ' ' + meta.citation_count);
    if (meta.cas_partition) parts.push(`中科院 ${meta.cas_edition_year} · ${meta.cas_partition} 区`);
    if (meta.abstract_status === 'missing') parts.push('摘要待补齐');
    if (meta.openalex_primary_topic) parts.push(meta.openalex_primary_topic);
    if (meta.openalex_institutions?.length) parts.push(meta.openalex_institutions.slice(0, 2).join(', '));
    return parts.map(value => `<span>${escapeHtml(String(value))}</span>`).join('');
}

function renderKnowledgePanel(knowledge) {
    if (!knowledge || !knowledge.generic) return '';

    const fields = [
        ['problem', 'fa-circle-question', true],
        ['method', 'fa-diagram-project', true],
        ['scenario', 'fa-location-dot', false],
        ['constraint', 'fa-shield-halved', false],
        ['metric', 'fa-gauge-high', false],
        ['contribution', 'fa-lightbulb', true]
    ];

    const highlights = fields
        .map(([field, icon, isMajor]) => renderKnowledgeField(field, knowledge.generic[field], icon, isMajor))
        .filter(Boolean)
        .join('');

    const facets = (knowledge.adaptive_facets || [])
        .filter(item => item.value)
        .slice(0, 8);

    const facetBadges = facets.map(item => `
        <span class="facet-chip" title="${escapeHtml(item.evidence || '')}">
            <span class="facet-name">${formatFacetName(item.facet)}</span>
            <span class="facet-value">${escapeHtml(item.value)}</span>
        </span>
    `).join('');

    const evidenceRows = fields
        .map(([field]) => renderEvidenceRow(field, knowledge.generic[field]))
        .filter(Boolean)
        .join('');


    return `<details class="knowledge-panel">
        <summary>${t('structuredInsight')}</summary>
        ${facetBadges ? `<div class="facet-strip">${facetBadges}</div>` : ''}
        <div class="knowledge-grid">${highlights}</div>
        ${evidenceRows ? `<details class="knowledge-evidence"><summary>${t('evidence')}</summary><div class="evidence-list">${evidenceRows}</div></details>` : ''}
    </details>`;
}

function renderKnowledgeField(field, item, icon, isMajor = false) {
    if (!item || !item.value) return '';
    const confidence = typeof item.confidence === 'number' ? Math.round(item.confidence * 100) : null;
    return `
        <div class="knowledge-field ${isMajor ? 'knowledge-field-major' : ''}">
            <div class="knowledge-field-label">
                <i class="fas ${icon}"></i>
                <span>${t(field)}</span>
                ${confidence !== null ? `<span class="confidence-pill">${confidence}%</span>` : ''}
            </div>
            <div class="knowledge-field-value">${escapeHtml(item.value)}</div>
        </div>
    `;
}

function renderEvidenceRow(field, item) {
    if (!item || !item.evidence) return '';
    return `
        <div class="evidence-row">
            <div class="evidence-label">${t(field)}</div>
            <div class="evidence-text">${escapeHtml(item.evidence)}</div>
        </div>
    `;
}

function formatFacetName(name) {
    if (!name) return '';
    if (LANG === 'zh' && FACET_LABELS_ZH[name]) {
        return FACET_LABELS_ZH[name];
    }
    return escapeHtml(name.replaceAll('_', ' '));
}

function renderFeaturedPapers(papers) {
    const container = document.getElementById('featured-papers');
    if (!container) return;
    container.innerHTML = papers.length ? papers.slice(0, 3).map(paper => {
        const card = paper.web_card || {};
        return `<article class="featured-paper-item">
            <h4>${sourceLink(card.links?.primary_url || paper.entry_url, card.title || paper.title, '') || escapeHtml(card.title || paper.title)}</h4>
            <p class="document-summary clamp-two">${escapeHtml(card.summary || paper.summary || paper.abstract || '')}</p>
            <div class="paper-meta">${renderCompactInfoBar(card, paper)}</div>
        </article>`;
    }).join('') : emptyState(t('noPapers'));
}

function renderCategoryFilter(categories) {
    const select = document.getElementById('paper-category-filter');
    if (!select) return;
    
    select.innerHTML = `<option value="">${t('allCategories')}</option>` +
        categories.map(cat => 
            `<option value="${escapeHtml(cat.name)}">${escapeHtml(cat.name)} (${cat.count})</option>`
        ).join('');
}

function renderPagination(totalPages, currentPage) {
    renderPager(document.getElementById('pagination'), currentPage, totalPages, page => loadPapers(page));
}

function renderAnalysisContent(elementId, content) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    if (content) {
        element.innerHTML = content;
    } else {
        element.innerHTML = `<p>${t('noData')}</p>`;
    }
}

function renderResearchTrendModules() {
    if (typeof Chart === 'undefined') {
        for (const id of ['category-chart', 'trend-chart', 'source-comparison-chart', 'entity-trend-chart']) {
            setChartAvailability(document.getElementById(id), false,
                LANG === 'zh' ? '图表组件暂不可用，请刷新页面重试。' : 'Charts unavailable. Reload the page to retry.');
        }
        return;
    }
    renderCategoryChart();
    renderTrendTimeline();
    renderSourceComparisonChart();
    renderEntityTrendChart();
}

function setChartAvailability(canvas, available, message = t('noData')) {
    if (!canvas) return;
    canvas.parentElement.hidden = !available;
    const status = document.getElementById(canvas.id + '-status');
    if (status) {
        status.textContent = available ? '' : message;
        status.hidden = available;
    }
}

function renderForecastDashboard() {
    if (!state.forecast) return;
    renderForecastQuality();
    renderForecastChart();
    renderForecastTopicCards();
    renderForecastTransmission();
    renderForecastScenarios();
    renderForecastMonitoring();
}

function renderForecastQuality() {
    const container = document.getElementById('forecast-data-quality');
    if (!container) return;
    const quality = state.forecast?.data_quality || {};
    const sourceLabels = LANG === 'zh'
        ? {paper: '论文', policy: '中国政策', news: '国内新闻', industry_report: '行业报告'}
        : {paper: 'Papers', policy: 'China policies', news: 'China news', industry_report: 'Industry reports'};
    const sources = Object.entries(quality.source_counts || {}).map(([source, count]) =>
        `<span class="quality-chip"><i class="fas fa-database"></i>${escapeHtml(sourceLabels[source] || source)} ${Number(count || 0)}</span>`
    ).join('');
    const coverage = quality.coverage_status_counts || {};
    const coverageText = LANG === 'zh'
        ? `完整 ${Number(coverage.complete || 0)} · 部分 ${Number(coverage.partial || 0)} · 不可用 ${Number(coverage.unavailable || 0)}`
        : `Complete ${Number(coverage.complete || 0)} · Partial ${Number(coverage.partial || 0)} · Unavailable ${Number(coverage.unavailable || 0)}`;
    const gaps = quality.gaps || [];
    container.innerHTML = `<div class="quality-summary">
        <div><span>${LANG === 'zh' ? '有效历史' : 'Usable history'}</span><strong>${Number(quality.history_month_count || 0)} / 24</strong><small>${LANG === 'zh' ? '个月' : 'months'}</small></div>
        <div><span>${LANG === 'zh' ? '事件定期资料' : 'Event-dated records'}</span><strong>${Number(quality.document_count || 0)}</strong><small>${escapeHtml(quality.period_start || '')} — ${escapeHtml(quality.period_end || '')}</small></div>
        <div><span>${LANG === 'zh' ? '来源覆盖' : 'Coverage'}</span><strong>${escapeHtml(coverageText)}</strong><small>${LANG === 'zh' ? '缺口不按零值计算' : 'Missing coverage is not treated as zero'}</small></div>
    </div>
    <div class="quality-source-row">${sources || `<span class="quality-chip warning">${LANG === 'zh' ? '暂无来源统计' : 'No source totals'}</span>`}</div>
    ${gaps.length ? `<div class="quality-warning"><i class="fas fa-triangle-exclamation"></i><div><strong>${LANG === 'zh' ? '结论边界' : 'Limitations'}</strong>${gaps.map(gap => `<p>${escapeHtml(gap)}</p>`).join('')}</div></div>` : ''}`;
}

function renderForecastChart() {
    const canvas = document.getElementById('forecast-chart');
    const note = document.getElementById('forecast-chart-note');
    const topicLabel = document.getElementById('forecast-chart-topic');
    if (!canvas || typeof Chart === 'undefined') return;
    const forecasts = state.forecast?.forecasts || [];
    const taxonomy = state.forecast?.taxonomy || state.forecastTaxonomy;
    const topicId = state.forecastFilters.topic || forecasts[0]?.topic_id || taxonomy[0]?.id;
    const definition = taxonomy.find(item => item.id === topicId) || state.forecastTaxonomy.find(item => item.id === topicId) || {};
    const series = state.forecast?.topic_series?.[topicId] || [];
    const forecast = forecasts.find(item => item.topic_id === topicId);
    if (topicLabel) topicLabel.textContent = definition.label || forecast?.topic || '';
    if (!series.length) {
        if (note) note.textContent = LANG === 'zh' ? '当前筛选下没有可用时间序列。' : 'No time series for the current filters.';
        if (state.forecastChart) state.forecastChart.destroy();
        state.forecastChart = null;
        return;
    }
    const labels = series.map(point => point.month);
    const futureLabels = [1, 2, 3].map(offset => addMonth(labels[labels.length - 1], offset));
    const allLabels = [...labels, ...futureLabels];
    const historyData = [...series.map(point => point.available ? Number(point.share || 0) * 100 : null), null, null, null];
    const lastActual = [...historyData.slice(0, labels.length)].reverse().find(value => value !== null);
    const projection = Array(allLabels.length).fill(null);
    const lower = Array(allLabels.length).fill(null);
    const upper = Array(allLabels.length).fill(null);
    if (lastActual !== undefined) projection[labels.length - 1] = lastActual;
    (forecast?.projections || []).forEach(point => {
        const index = labels.length - 1 + Number(point.months_ahead || 0);
        projection[index] = Number(point.share || 0) * 100;
        lower[index] = Number(point.lower || 0) * 100;
        upper[index] = Number(point.upper || 0) * 100;
    });
    if (state.forecastChart) state.forecastChart.destroy();
    state.forecastChart = new Chart(canvas, {
        type: 'line',
        data: {
            labels: allLabels,
            datasets: [
                {label: LANG === 'zh' ? '历史主题占比' : 'Historical topic share', data: historyData, borderColor: '#426a96', backgroundColor: 'rgba(79,70,229,.1)', fill: true, tension: .3, spanGaps: false},
                {label: LANG === 'zh' ? '预测中位线' : 'Forecast', data: projection, borderColor: '#b0976d', borderDash: [7, 5], tension: .25, spanGaps: true},
                {label: LANG === 'zh' ? '80%区间下界' : '80% lower', data: lower, borderColor: 'rgba(245,158,11,.15)', pointRadius: 0, spanGaps: true},
                {label: LANG === 'zh' ? '80%预测区间' : '80% interval', data: upper, borderColor: 'rgba(245,158,11,.15)', backgroundColor: 'rgba(245,158,11,.18)', pointRadius: 0, fill: '-1', spanGaps: true}
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {mode: 'index', intersect: false},
            scales: {y: {beginAtZero: true, ticks: {callback: value => `${value}%`}}},
            plugins: {legend: {position: 'bottom'}}
        }
    });
    if (note) note.textContent = forecast?.mode === 'quantitative'
        ? (LANG === 'zh' ? '虚线为 Theil–Sen 稳健预测，阴影为80%区间；预测不是确定事实。' : 'Dashed line is a robust forecast with an 80% interval.')
        : (LANG === 'zh' ? `数据未达到定量门槛：${(forecast?.data_gaps || []).join('；') || '当前仅展示历史证据'}` : 'Quantitative threshold not met; history only.');
}

function renderForecastTopicCards() {
    const container = document.getElementById('forecast-topic-cards');
    if (!container) return;
    const forecasts = state.forecast?.forecasts || [];
    if (!forecasts.length) {
        container.innerHTML = `<p class="trend-note">${LANG === 'zh' ? '当前筛选下没有近期预测卡，请切换周期或置信度。' : 'No near-term cards for these filters.'}</p>`;
        return;
    }
    container.innerHTML = forecasts.map(item => {
        const metrics = item.metrics || {};
        const ids = encodeURIComponent(JSON.stringify(item.evidence_ids || []));
        return `<article class="forecast-topic-card confidence-${escapeHtml(item.confidence || 'low')}">
            <div class="forecast-card-heading"><div><small>${escapeHtml(modeLabel(item.mode))}</small><h3>${escapeHtml(item.topic)}</h3></div><span class="confidence-badge">${escapeHtml(confidenceLabel(item.confidence))}</span></div>
            <div class="trajectory-row"><span class="trajectory trajectory-${escapeHtml(item.trajectory || 'stable')}"><i class="fas fa-arrow-trend-up"></i>${escapeHtml(trajectoryLabel(item.trajectory))}</span><strong>${LANG === 'zh' ? '持续性' : 'Persistence'} ${Math.round(Number(metrics.persistence || 0) * 100)}%</strong></div>
            <div class="forecast-metric-grid"><div><span>${LANG === 'zh' ? '速度' : 'Velocity'}</span><strong>${signed(metrics.velocity)}</strong></div><div><span>${LANG === 'zh' ? '加速度' : 'Acceleration'}</span><strong>${signed(metrics.acceleration)}</strong></div><div><span>${LANG === 'zh' ? '来源类型' : 'Sources'}</span><strong>${Number(metrics.source_diversity || 0)}</strong></div></div>
            <p class="research-action"><i class="fas fa-flask"></i>${escapeHtml(item.research_action || '')}</p>
            <div class="driver-list">${(item.drivers || []).map(driver => `<span>${escapeHtml(driver)}</span>`).join('')}</div>
            <details><summary>${LANG === 'zh' ? '反证条件与数据缺口' : 'Counter-signals and gaps'}</summary><ul>${(item.counter_signals || []).map(signal => `<li>${escapeHtml(signal)}</li>`).join('')}</ul></details>
            <button type="button" class="forecast-evidence-btn" data-evidence-ids="${ids}"><i class="fas fa-folder-open"></i>${LANG === 'zh' ? '查看支撑材料' : 'View evidence'} · ${(item.evidence_ids || []).length}</button>
        </article>`;
    }).join('');
    container.querySelectorAll('.forecast-evidence-btn').forEach(button => {
        button.addEventListener('click', () => openEvidenceDrawer(
            JSON.parse(decodeURIComponent(button.dataset.evidenceIds || '%5B%5D'))
        ));
    });
}

function renderForecastTransmission() {
    const container = document.getElementById('forecast-transmission');
    if (!container) return;
    const sourceLabels = LANG === 'zh'
        ? {paper: '论文', policy: '政策', news: '国内新闻', industry_report: '行业报告'}
        : {paper: 'Paper', policy: 'Policy', news: 'News', industry_report: 'Report'};
    const items = state.forecast?.lead_lag || [];
    container.innerHTML = items.length ? items.map(item => {
        const steps = (item.sequence || []).map((step, index) => `<div class="transmission-step"><span>${escapeHtml(sourceLabels[step.source_type] || step.source_type)}</span><strong>${escapeHtml(step.onset || '')}</strong><small>${Number(step.count || 0)} ${LANG === 'zh' ? '条' : 'items'}</small></div>${index < item.sequence.length - 1 ? '<i class="fas fa-arrow-right"></i>' : ''}`).join('');
        return `<article class="transmission-item"><div><h3>${escapeHtml(item.topic)}</h3><span class="signal-status status-${escapeHtml(item.status)}">${item.status === 'supported' ? (LANG === 'zh' ? '有重复证据' : 'Supported') : (LANG === 'zh' ? '证据不足' : 'Insufficient')}</span></div><div class="transmission-track">${steps || `<p>${escapeHtml(item.limitation || '')}</p>`}</div><small>${escapeHtml(item.limitation || '')}</small></article>`;
    }).join('') : `<p class="trend-note">${LANG === 'zh' ? '当前筛选下没有传导证据。' : 'No transmission evidence.'}</p>`;
}

function renderForecastScenarios() {
    const container = document.getElementById('forecast-scenarios');
    if (!container) return;
    const scenarios = state.forecast?.scenarios || [];
    container.innerHTML = scenarios.length ? scenarios.map(item => `<article class="scenario-card">
        <div><h3>${escapeHtml(item.topic)}</h3><span class="confidence-badge">${escapeHtml(confidenceLabel(item.confidence))}</span></div>
        <p class="scenario-base"><strong>${LANG === 'zh' ? '基准' : 'Base'}：</strong>${escapeHtml(item.base_case || '')}</p>
        <p class="scenario-up"><strong>${LANG === 'zh' ? '上行' : 'Upside'}：</strong>${escapeHtml(item.upside || '')}</p>
        <p class="scenario-down"><strong>${LANG === 'zh' ? '下行' : 'Downside'}：</strong>${escapeHtml(item.downside || '')}</p>
    </article>`).join('') : `<p class="trend-note">${LANG === 'zh' ? '请选择“战略”或“双周期”查看情景。' : 'Choose strategic or both horizons.'}</p>`;
}

function renderForecastMonitoring() {
    const container = document.getElementById('forecast-monitoring');
    if (!container) return;
    const items = (state.forecast?.forecasts || []).length ? state.forecast.forecasts : (state.forecast?.scenarios || []);
    container.innerHTML = items.length ? items.map(item => `<article class="monitoring-card"><h3>${escapeHtml(item.topic)}</h3><div><strong>${LANG === 'zh' ? '持续监测' : 'Watch'}</strong>${(item.watch_indicators || item.triggers || []).map(value => `<span>${escapeHtml(value)}</span>`).join('')}</div><div class="counter-monitor"><strong>${LANG === 'zh' ? '下调判断条件' : 'Downgrade when'}</strong>${(item.counter_signals || []).map(value => `<span>${escapeHtml(value)}</span>`).join('')}</div></article>`).join('') : `<p class="trend-note">${LANG === 'zh' ? '当前筛选下暂无监测项。' : 'No monitoring items.'}</p>`;
}

function openEvidenceDrawer(evidenceIds) {
    const drawer = document.getElementById('forecast-evidence-drawer');
    const list = document.getElementById('forecast-evidence-list');
    const count = document.getElementById('forecast-evidence-count');
    if (!drawer || !list) return;
    const documents = [
        ...state.allPapers,
        ...Object.values(state.directories).flatMap(directory => directory.documents || [])
    ];
    const index = new Map(documents.map(document => [String(document.id || ''), document]));
    const uniqueIds = [...new Set(evidenceIds || [])];
    if (count) count.textContent = String(uniqueIds.length);
    list.innerHTML = uniqueIds.length ? uniqueIds.map(id => {
        const document = index.get(String(id));
        const title = document?.title || id;
        const source = document?.source_name || document?.source_type || (LANG === 'zh' ? '历史语料' : 'Historical corpus');
        const url = document?.url || document?.entry_url || '';
        return `<article><div><span>${escapeHtml(source)}</span><small>${escapeHtml(document?.published_at || '')}</small></div>${url ? `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(title)}</a>` : `<strong>${escapeHtml(title)}</strong>`}<code>${escapeHtml(id)}</code></article>`;
    }).join('') : `<p class="trend-note">${LANG === 'zh' ? '没有可展示的证据ID。' : 'No evidence IDs.'}</p>`;
    drawer.open = true;
    drawer.scrollIntoView({behavior: 'smooth', block: 'start'});
}

function addMonth(month, offset) {
    const [year, value] = String(month || '').split('-').map(Number);
    if (!year || !value) return '';
    const date = new Date(Date.UTC(year, value - 1 + offset, 1));
    return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, '0')}`;
}

function signed(value) {
    const number = Number(value || 0);
    return `${number >= 0 ? '+' : ''}${number.toFixed(3)}`;
}

function confidenceLabel(value) {
    const labels = LANG === 'zh' ? {high: '高置信', medium: '中置信', low: '低置信'} : {high: 'High', medium: 'Medium', low: 'Low'};
    return labels[value] || labels.low;
}

function trajectoryLabel(value) {
    const labels = LANG === 'zh' ? {rising: '上升', stable: '稳定', declining: '回落'} : {rising: 'Rising', stable: 'Stable', declining: 'Declining'};
    return labels[value] || labels.stable;
}

function modeLabel(value) {
    if (LANG === 'zh') return value === 'quantitative' ? '定量预测' : '低置信情景';
    return value === 'quantitative' ? 'Quantitative' : 'Low-confidence scenario';
}

const CHART_PALETTES = {light: ['#426a96', '#588087', '#967b55', '#65826e', '#8c7286'], dark: ['#8caed0', '#88b3b8', '#c4aa7f', '#98b5a0', '#b8a0b3']};
function chartPalette() { return CHART_PALETTES[state.theme] || CHART_PALETTES.light; }
const SOURCE_ORDER = ['paper', 'policy', 'news', 'industry_report', 'unknown'];
function chartColor(name) {
    let hash = 0;
    for (const char of String(name)) hash = ((hash * 31) + char.charCodeAt(0)) >>> 0;
    return chartPalette()[hash % chartPalette().length];
}
function numericEntries(counts) {
    return Object.entries(counts || {}).filter(([, value]) => value != null && value !== '' && Number.isFinite(Number(value)));
}
function dateRange(items) {
    const dates = items.map(item => String(item.date || '')).filter(Boolean).sort();
    return dates.length ? `${dates[0]} — ${dates[dates.length - 1]}` : (LANG === 'zh' ? '日期未提供' : 'Dates unavailable');
}
function renderCategoryChart() {
    const canvas = document.getElementById('category-chart');
    if (!canvas || typeof Chart === 'undefined') return;
    const entries = numericEntries(state.analysis?.statistics?.category_distribution).sort((a, b) => b[1] - a[1]);
    setChartAvailability(canvas, entries.length > 0);
    if (state.categoryChart) state.categoryChart.destroy();
    if (!entries.length) return;
    const dates = Object.keys(state.analysis?.statistics?.time_distribution || {}).map(date => ({date}));
    updateElement('category-chart-scope', LANG === 'zh'
        ? `本次分析 ${state.analysis.document_count ?? '—'} 条资料 · ${dateRange(dates)} · 单位：标签出现次数，可一文多标签，含类型和优先级标签。`
        : `${state.analysis.document_count ?? '—'} analyzed documents · ${dateRange(dates)} · Tag occurrences; multiple tags per document, including type and priority labels.`);
    state.categoryChart = new Chart(canvas, {
        type: 'bar',
        data: {labels: entries.map(([key]) => key), datasets: [{label: LANG === 'zh' ? '出现次数' : 'Occurrences', data: entries.map(([, value]) => value), backgroundColor: entries.map(([key]) => chartColor(key))}]},
        options: {indexAxis: 'y', responsive: true, scales: {x: {beginAtZero: true, ticks: {precision: 0}, title: {display: true, text: LANG === 'zh' ? '次数' : 'Count'}}}, plugins: {legend: {display: false}}}
    });
}

function renderTrendTimeline() {
    const canvas = document.getElementById('trend-chart');
    const keywordStrip = document.getElementById('trend-keyword-strip');
    if (!canvas || typeof Chart === 'undefined') return;

    const temporalTimeline = state.analysis?.temporal_trends?.timeline || [];
    const snapshots = temporalTimeline.length
        ? temporalTimeline
        : state.history.length
            ? state.history.map(item => ({
                ...item,
                document_count: item.paper_count || 0,
                topic_counts: item.categories || {}
            }))
            : [{
                date: state.analysis?.date || '',
                document_count: state.analysis?.document_count || state.analysis?.paper_count || state.allPapers.length,
                topic_counts: state.analysis?.statistics?.category_distribution || {}
            }];
    const usableSnapshots = snapshots.filter(snapshot => snapshot.date && snapshot.document_count != null).sort((a, b) => String(a.date).localeCompare(String(b.date)));
    updateElement('trend-chart-scope', LANG === 'zh' ? `${dateRange(usableSnapshots)} · 单位：条。仅展示有记录日期，日期间隔不等；缺失日期不补零，不表示连续增长。` : `${dateRange(usableSnapshots)} · Documents on recorded dates only; unequal intervals, missing dates are not zero.`);
    setChartAvailability(canvas, usableSnapshots.length > 0);
    if (!usableSnapshots.length) return;

    const topicTotals = {};
    usableSnapshots.forEach(snapshot => {
        Object.entries(snapshot.topic_counts || {}).forEach(([topic, count]) => {
            topicTotals[topic] = (topicTotals[topic] || 0) + Number(count || 0);
        });
    });
    const topTopics = Object.entries(topicTotals)
        .sort((left, right) => right[1] - left[1])
        .slice(0, 3)
        .map(([topic]) => topic);
    const topicDatasets = topTopics.map((topic, index) => ({
        label: topic,
        data: usableSnapshots.map(snapshot => Number(snapshot.topic_counts?.[topic] || 0)),
        borderColor: chartColor(topic),
        backgroundColor: chartColor(topic),
        fill: false,
        tension: 0
    }));

    if (state.trendChart) state.trendChart.destroy();
    state.trendChart = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: usableSnapshots.map(snapshot => snapshot.date),
            datasets: [
                {
                    label: LANG === 'zh' ? '文档数量' : 'Documents',
                    data: usableSnapshots.map(snapshot => snapshot.document_count || 0),
                    borderColor: '#426a96',
                    backgroundColor: chartPalette()[0],
                    fill: true,
                    tension: 0
                },
                ...topicDatasets
            ]
        },
        options: {
            responsive: true,
            scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
            plugins: {
                legend: { position: 'bottom' },
                tooltip: {
                    callbacks: {
                        afterBody: context => {
                            const snapshot = usableSnapshots[context[0].dataIndex];
                            const topics = Object.entries(snapshot.topic_counts || {}).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([topic]) => topic);
                            return topics.length ? `${LANG === 'zh' ? '主题' : 'Topics'}: ${topics.join(', ')}` : '';
                        }
                    }
                }
            }
        }
    });

    if (keywordStrip) {
        const latest = usableSnapshots[usableSnapshots.length - 1];
        const topics = Object.entries(latest.topic_counts || {}).sort((a, b) => b[1] - a[1]).slice(0, 12);
        keywordStrip.innerHTML = topics.length
            ? `<span class="scope-note">${LANG === 'zh' ? '最后有记录日的标签：' : 'Tags on last recorded date: '}</span>` + topics.map(([topic, count]) => `<span class="trend-keyword">${escapeHtml(topic)} · ${Number(count)}</span>`).join('')
            : `<span class="trend-note">${t('timelineHint')}</span>`;
    }
}

function renderSourceComparisonChart() {
    const canvas = document.getElementById('source-comparison-chart');
    const empty = document.getElementById('source-comparison-empty');
    if (!canvas || typeof Chart === 'undefined') return;
    const timeline = state.analysis?.temporal_trends?.timeline || [];
    const latestCounts = timeline.length ? timeline[timeline.length - 1].source_counts || {} : {};
    const windowCounts = state.analysis?.temporal_trends?.windows?.['7']?.cross_source_comparison?.source_counts || {};
    const counts = Object.keys(latestCounts).length ? latestCounts : windowCounts;
    const entries = numericEntries(counts).sort((a, b) => SOURCE_ORDER.indexOf(a[0]) - SOURCE_ORDER.indexOf(b[0]));
    updateElement('source-comparison-chart-scope', LANG === 'zh' ? `${Object.keys(latestCounts).length ? '最后有记录日期 ' + timeline[timeline.length - 1].date : '分析产物近 7 日窗口'} · 单位：条；不是全库来源占比。` : `${Object.keys(latestCounts).length ? timeline[timeline.length - 1].date : '7-day analysis window'} · Documents; not whole-corpus shares.`);
    setChartAvailability(canvas, entries.length > 0, t('signalInsufficient'));
    if (!entries.length) {
        return;
    }
    if (empty) empty.textContent = '';
    if (state.sourceComparisonChart) state.sourceComparisonChart.destroy();
    const labels = LANG === 'zh'
        ? {paper: '论文', policy: '政策', news: '新闻', industry_report: '行业报告', unknown: '其他'}
        : {paper: 'Paper', policy: 'Policy', news: 'News', industry_report: 'Industry report', unknown: 'Other'};
    state.sourceComparisonChart = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: entries.map(([name]) => labels[name] || name),
            datasets: [{label: LANG === 'zh' ? '文档数' : 'Documents', data: entries.map(([, count]) => count), backgroundColor: entries.map(([name]) => chartPalette()[SOURCE_ORDER.indexOf(name)] || chartPalette()[0])}]
        },
        options: {responsive: true, scales: {y: {beginAtZero: true, ticks: {precision: 0}}}, plugins: {legend: {display: false}}}
    });
}

function renderEntityTrendChart() {
    const canvas = document.getElementById('entity-trend-chart');
    const empty = document.getElementById('entity-trend-empty');
    if (!canvas || typeof Chart === 'undefined') return;
    const timeline = state.analysis?.temporal_trends?.timeline || [];
    updateElement('entity-trend-chart-scope', LANG === 'zh' ? `${dateRange(timeline)} · 前 5 个实体，单位：资料中的提及次数；同一资料可含多个实体。` : `${dateRange(timeline)} · Top 5 entities, counted as document mentions; multiple entities per document.`);
    const totals = {};
    timeline.forEach(snapshot => Object.entries(snapshot.entity_counts || {}).forEach(([entity, count]) => {
        totals[entity] = (totals[entity] || 0) + Number(count || 0);
    }));
    const entities = Object.entries(totals).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([entity]) => entity);
    setChartAvailability(canvas, timeline.length > 0 && entities.length > 0, t('signalInsufficient'));
    if (!timeline.length || !entities.length) {
        return;
    }
    if (empty) empty.textContent = '';
    if (state.entityTrendChart) state.entityTrendChart.destroy();
    state.entityTrendChart = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: entities,
            datasets: [{label: LANG === 'zh' ? '提及次数' : 'Mentions', data: entities.map(entity => totals[entity]), backgroundColor: entities.map(chartColor)}]
        },
        options: {indexAxis: 'y', responsive: true, scales: {x: {beginAtZero: true, ticks: {precision: 0}}}, plugins: {legend: {display: false}}}
    });
}

function renderResearchMatrix() {
    const container = document.getElementById('research-matrix');
    if (!container) return;

    const rows = state.allPapers.map(paper => {
        const knowledge = state.knowledgeByPaperId[paper.id];
        const method = getKnowledgeValue(knowledge, 'method') || getAdaptiveFacetValue(knowledge, 'solution_approach');
        const scenario = getKnowledgeValue(knowledge, 'scenario') || getAdaptiveFacetValue(knowledge, 'application_context');
        const mechanismValue = getAdaptiveFacetValue(knowledge, 'mechanism_or_process') || getAdaptiveFacetValue(knowledge, 'market_structure') || getAdaptiveFacetValue(knowledge, 'interaction_type');
        if (!method && !scenario && !mechanismValue) return null;
        return {
            title: paper.title,
            method: method || t('unknown'),
            scenario: scenario || t('unknown'),
            mechanism: mechanismValue || t('unknown')
        };
    }).filter(Boolean).slice(0, 12);

    updateElement('matrix-scope', LANG === 'zh' ? `当前加载的 ${state.allPapers.length} 篇论文 · 展示 ${rows.length} 条结构化记录；逐篇列出方法、场景和机制。` : `${state.allPapers.length} loaded papers · ${rows.length} structured records; method, scenario and mechanism per paper.`);
    if (!rows.length) {
        container.innerHTML = emptyState(t('noData'));
        return;
    }
    container.innerHTML = `<table class="comparison-table"><thead><tr><th>${t('comparisonPaper')}</th><th>${t('comparisonMethod')}</th><th>${t('comparisonScenario')}</th><th>${t('mechanism')}</th></tr></thead><tbody>${rows.map(row => `<tr><td>${escapeHtml(row.title)}</td><td>${escapeHtml(row.method)}</td><td>${escapeHtml(row.scenario)}</td><td>${escapeHtml(row.mechanism)}</td></tr>`).join('')}</tbody></table>`;
}

function renderComparisonTable() {
    const container = document.getElementById('comparison-table');
    if (!container) return;

    const rows = state.allPapers.map(paper => {
        const knowledge = state.knowledgeByPaperId[paper.id];
        return {
            paper,
            problem: getKnowledgeValue(knowledge, 'problem'),
            method: getKnowledgeValue(knowledge, 'method'),
            scenario: getKnowledgeValue(knowledge, 'scenario'),
            metric: getKnowledgeValue(knowledge, 'metric'),
            contribution: getKnowledgeValue(knowledge, 'contribution')
        };
    }).filter(row => row.problem || row.method || row.contribution).slice(0, 10);

    if (!rows.length) {
        updateElement('comparison-scope', LANG === 'zh' ? `当前加载的 ${state.allPapers.length} 篇论文 · 展示 ${rows.length} 篇；字段来自结构化抽取，未提供字段显示破折号。` : `${state.allPapers.length} loaded papers · ${rows.length} shown; extracted fields, dashes indicate missing data.`);
    container.innerHTML = `<p class="trend-note">${t('noData')}</p>`;
        return;
    }

    updateElement('comparison-scope', LANG === 'zh' ? `当前加载的 ${state.allPapers.length} 篇论文 · 展示 ${rows.length} 篇；字段来自结构化抽取，未提供字段显示破折号。` : `${state.allPapers.length} loaded papers · ${rows.length} shown; extracted fields, dashes indicate missing data.`);
    container.innerHTML = `
        <table class="comparison-table">
            <thead>
                <tr>
                    <th>${t('comparisonPaper')}</th>
                    <th>${t('comparisonProblem')}</th>
                    <th>${t('comparisonMethod')}</th>
                    <th>${t('comparisonScenario')}</th>
                    <th>${t('comparisonMetric')}</th>
                    <th>${t('comparisonContribution')}</th>
                </tr>
            </thead>
            <tbody>
                ${rows.map(row => `
                    <tr>
                        <td>${sourceLink(row.paper.entry_url || row.paper.url, row.paper.title, '') || escapeHtml(row.paper.title)}</td>
                        <td>${escapeHtml(row.problem || '—')}</td>
                        <td>${escapeHtml(row.method || '—')}</td>
                        <td>${escapeHtml(row.scenario || '—')}</td>
                        <td>${escapeHtml(row.metric || '—')}</td>
                        <td>${escapeHtml(row.contribution || '—')}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

function getKnowledgeValue(knowledge, field) {
    const item = knowledge?.generic?.[field];
    if (!item) return '';
    return typeof item === 'string' ? item : item.value || '';
}

function getAdaptiveFacetValue(knowledge, facetName) {
    const item = (knowledge?.adaptive_facets || []).find(facet => facet.facet === facetName && facet.value);
    return item?.value || '';
}

function shorten(value, maxLength = 100) {
    if (!value) return '';
    const text = String(value).trim();
    return text.length > maxLength ? `${text.slice(0, maxLength - 1)}…` : text;
}

// ==================== 过滤和搜索 ==================== //
function filterPapers(papers) {
    let filtered = papers;
    
    // 按类别过滤
    if (state.selectedCategory) {
        filtered = filtered.filter(paper => 
            paper.categories && paper.categories.includes(state.selectedCategory)
        );
    }

    if (state.selectedPriority) {
        filtered = filtered.filter(paper => {
            const card = paper.web_card || {};
            const suggestion = card.reading_suggestion || {};
            return (card.read_priority || suggestion.read_priority) === state.selectedPriority;
        });
    }
    
    // 按搜索关键词过滤
    if (state.searchQuery) {
        const query = state.searchQuery.toLowerCase();
        filtered = filtered.filter(paper => 
            (paper.title && paper.title.toLowerCase().includes(query)) ||
            (paper.abstract && paper.abstract.toLowerCase().includes(query)) ||
            (paper.authors && paper.authors.some(author => author.toLowerCase().includes(query)))
        );
    }
    
    return filtered;
}

function filterByCategory(category) {
    state.selectedCategory = category;
    
    // 更新侧边栏类别高亮
    document.querySelectorAll('.category-item').forEach(item => {
        item.classList.toggle('active', item.dataset.category === category);
    });
    
    // 更新下拉框
    const select = document.getElementById('paper-category-filter');
    if (select) {
        select.value = category;
    }
    
    // Category filtering is supported by the server across all pages.
    loadPapers(1);
}

function searchPapers(query) {
    state.searchQuery = query;
    renderPapers(filterPapers(state.allPapers));
}

// ==================== 事件监听 ==================== //
function initEventListeners() {
    // 主题切换
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }

    document.querySelectorAll('[data-narrative-view]').forEach(tab => {
        tab.addEventListener('click', () => {
            state.narrativeView = tab.dataset.narrativeView || 'paper';
            document.querySelectorAll('[data-narrative-view]').forEach(item => {
                const active = item === tab;
                item.classList.toggle('active', active);
                item.setAttribute('aria-selected', String(active));
                item.tabIndex = active ? 0 : -1;
            });
            loadNarrative();
        });
    });
    document.getElementById('narrative-refresh')?.addEventListener('click', () => loadNarrative({refresh: true}));
    document.getElementById('narrative-drawer-close')?.addEventListener('click', closeNarrativeEvidence);
    document.getElementById('narrative-drawer-backdrop')?.addEventListener('click', closeNarrativeEvidence);
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape') closeNarrativeEvidence();
    });
    
    // 搜索
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                searchPapers(e.target.value);
            }, 300);
        });
    }
    
    // 类别筛选
    const categoryFilter = document.getElementById('paper-category-filter');
    if (categoryFilter) {
        categoryFilter.addEventListener('change', (e) => {
            filterByCategory(e.target.value);
        });
    }

    const priorityFilter = document.getElementById('paper-priority-filter');
    if (priorityFilter) {
        priorityFilter.addEventListener('change', (event) => {
            state.selectedPriority = event.target.value;
            renderPapers(filterPapers(state.allPapers));
        });
    }
    
    // 每页显示数量
    const perPageSelect = document.getElementById('papers-per-page');
    if (perPageSelect) {
        perPageSelect.addEventListener('change', (e) => {
            state.papersPerPage = parseInt(e.target.value);
            loadPapers(1);
        });
    }
    
    // 排序
    const sortSelect = document.getElementById('paper-sort');
    if (sortSelect) {
        sortSelect.addEventListener('change', (e) => {
            sortPapers(e.target.value);
        });
    }

    document.querySelectorAll('[data-directory-search]').forEach(input => {
        let searchTimeout;
        input.addEventListener('input', event => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                const sourceType = event.target.dataset.directorySearch;
                state.directories[sourceType].search = event.target.value;
                loadDirectory(sourceType);
            }, 300);
        });
    });

    document.querySelectorAll('[data-directory-priority]').forEach(select => {
        select.addEventListener('change', event => {
            const sourceType = event.target.dataset.directoryPriority;
            state.directories[sourceType].priority = event.target.value;
            loadDirectory(sourceType);
        });
    });

    document.querySelectorAll('[data-directory-topic]').forEach(input => {
        let topicTimeout;
        input.addEventListener('input', event => {
            clearTimeout(topicTimeout);
            topicTimeout = setTimeout(() => {
                const sourceType = event.target.dataset.directoryTopic;
                state.directories[sourceType].topic = event.target.value;
                loadDirectory(sourceType);
            }, 300);
        });
    });

    document.querySelectorAll('[data-directory-date-from]').forEach(input => {
        input.addEventListener('change', event => {
            const sourceType = event.target.dataset.directoryDateFrom;
            state.directories[sourceType].dateFrom = event.target.value;
            loadDirectory(sourceType);
        });
    });

    document.querySelectorAll('[data-directory-date-to]').forEach(input => {
        input.addEventListener('change', event => {
            const sourceType = event.target.dataset.directoryDateTo;
            state.directories[sourceType].dateTo = event.target.value;
            loadDirectory(sourceType);
        });
    });

    document.querySelectorAll('[data-directory-sort]').forEach(select => {
        select.addEventListener('change', event => {
            const sourceType = event.target.dataset.directorySort;
            state.directories[sourceType].sort = event.target.value;
            loadDirectory(sourceType);
        });
    });

    document.getElementById('report-type')?.addEventListener('change', event => {
        loadReport(event.target.value);
    });
    document.getElementById('report-refresh')?.addEventListener('click', () => {
        loadReport();
    });
    document.getElementById('scheduler-status-refresh')?.addEventListener('click', () => {
        loadSchedulerStatus();
    });

    document.getElementById('home-filter-apply')?.addEventListener('click', () => {
        state.homeFilters = {
            sourceType: document.getElementById('home-source-filter')?.value || 'all',
            topic: document.getElementById('home-topic-filter')?.value || '',
            priority: document.getElementById('home-priority-filter')?.value || '',
            dateFrom: document.getElementById('home-date-from')?.value || '',
            dateTo: document.getElementById('home-date-to')?.value || ''
        };
        loadIntelligenceHome();
    });
}

function sortPapers(sortBy) {
    state.paperSort = sortBy;
    const papers = [...state.allPapers];
    
    switch (sortBy) {
        case 'relevance':
            papers.sort((a, b) =>
                Number(b.web_card?.importance_score || 0) -
                Number(a.web_card?.importance_score || 0)
            );
            break;
        case 'date':
            papers.sort((a, b) => new Date(b.published) - new Date(a.published));
            break;
        case 'title':
            papers.sort((a, b) => a.title.localeCompare(b.title));
            break;
        case 'citations':
            papers.sort((a, b) =>
                Number(b.web_card?.source_metadata?.citation_count || 0) -
                Number(a.web_card?.source_metadata?.citation_count || 0)
            );
            break;
    }
    
    state.allPapers = papers;
    renderPapers(filterPapers(papers));
}

// ==================== 滚动行为 ==================== //
function initScrollBehavior() {
    const backToTop = document.getElementById('back-to-top');
    
    window.addEventListener('scroll', () => {
        if (window.pageYOffset > 300) {
            backToTop.classList.add('visible');
        } else {
            backToTop.classList.remove('visible');
        }
    });
    
    backToTop.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
    });
}

// ==================== 工具函数 ==================== //
function updateElement(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = value;
    }
}

function showLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) element.innerHTML = `<div class="loading" role="status"><div class="spinner" aria-hidden="true"></div><p>${t('loading')}</p></div>`;
}

function emptyState(message) {
    return `<div class="empty-state" role="status"><i class="far fa-folder-open" aria-hidden="true"></i><p>${escapeHtml(message)}</p></div>`;
}

function showError(elementId, message) {
    const element = document.getElementById(elementId);
    if (!element) return;
    element.innerHTML = `<div class="error-state" role="alert"><i class="fas fa-circle-exclamation" aria-hidden="true"></i><p>${escapeHtml(message)}</p><button type="button" class="btn-paper btn-secondary">${LANG === 'zh' ? '重试' : 'Retry'}</button></div>`;
    const retry = {
        'papers-list': () => loadPapers(state.currentPage),
        'featured-papers': () => loadPapers(state.currentPage),
        'policy-list': () => loadDirectory('policy', state.directories.policy.page),
        'news-list': () => loadDirectory('news', state.directories.news.page),
        'industry-report-list': () => loadDirectory('industry_report', state.directories.industry_report.page),
        'today-recommendations': loadIntelligenceHome,
        'narrative-content': loadNarrative,
        'intelligence-report': () => loadReport(),
        'statistics-error': loadAnalysis,
        'wordcloud-container': loadWordcloud,
        'scheduler-job-status': loadSchedulerStatus,
        'home-report-entry': () => loadReport(),
        'paper-support-status': async () => {
            await Promise.all([loadKnowledge(), loadCategories()]);
            renderPaperSupportStatus();
            if (state.papersLoaded) renderPapers(filterPapers(state.allPapers));
        }
    }[elementId];
    const button = element.querySelector('button');
    if (retry) button.addEventListener('click', () => retry());
    else button.remove();
}

function escapeHtml(text) {
    if (text == null) return '';
    return String(text).replace(/[&<>"']/g, character => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[character]));
}

function hasFilters(filters) {
    return Boolean(filters.search || filters.topic || filters.priority || filters.dateFrom || filters.dateTo || (filters.sourceType && filters.sourceType !== 'all'));
}

function filterDescription(filters) {
    const names = LANG === 'zh'
        ? {paper: '论文', policy: '政策', news: '新闻', industry_report: '行业报告'}
        : {paper: 'Papers', policy: 'Policies', news: 'News', industry_report: 'Reports'};
    const values = [filters.sourceType !== 'all' ? names[filters.sourceType] : '', filters.search, filters.topic,
        filters.priority ? priorityLabel(filters.priority) : '',
        filters.dateFrom ? `${LANG === 'zh' ? '起始' : 'From'} ${filters.dateFrom}` : '',
        filters.dateTo ? `${LANG === 'zh' ? '截止' : 'To'} ${filters.dateTo}` : ''].filter(Boolean);
    return values.length ? `${LANG === 'zh' ? '已应用：' : 'Applied: '}${values.join(' · ')}` : '';
}

// Resolve forecast document IDs against the existing report evidence and loaded records.
function documentEvidenceIndex(ids) {
    const index = {};
    const cited = Object.values(state.report?.evidence_indexes || {}).flatMap(items => Object.values(items));
    const documents = [...state.allPapers, ...Object.values(state.directories).flatMap(item => item.documents)];
    for (const id of ids) {
        const evidence = cited.find(item => item.document_id === id);
        const record = documents.find(item => item.id === id);
        index[id] = evidence || (record ? {
            title: record.title, source_name: record.source_name, event_date: record.published_at || record.published,
            excerpt: record.summary || record.abstract, url: record.url || record.entry_url
        } : {title: LANG === 'zh' ? '历史证据记录' : 'Historical evidence', excerpt: LANG === 'zh' ? '当前页面未加载该记录的详情，暂不提供原文跳转。' : 'Details are not loaded for this historical record; no source link is available.'});
    }
    return index;
}

// ==================== 导出 ==================== //
window.dailyArxiv = {
    navigateToSection,
    filterByCategory,
    searchPapers,
    loadPapers,
    loadDirectory,
    loadReport,
    loadIntelligenceHome,
    loadNarrative,
    loadForecast,
    toggleTheme
};
