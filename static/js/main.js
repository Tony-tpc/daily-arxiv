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
        unknown: 'Unknown',
        authorLabel: '作者',
        sourceLabel: '来源',
        priorityLabel: '优先级',
        recommendationLabel: '建议动作',
        scoreLabel: '综合分',
        scoreBreakdown: '查看五维评分',
        relevanceReason: '推荐依据',
        relatedTopicsLabel: '相关主题',
        citationsLabel: '引用次数',
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
        relatedIntelligence: '关联情报',
        duplicateSources: '已合并来源',
        reportLoadFailed: '报告加载失败',
        reportEmpty: '本周期暂无可展示条目',
        reportOriginal: '查看原始来源',
        reportPeriod: '报告周期',
        reportGenerated: '生成于',
        noIntelligence: '暂无符合条件的科研情报',
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
        relatedIntelligence: 'Related intelligence',
        duplicateSources: 'Merged sources',
        reportLoadFailed: 'Failed to load report',
        reportEmpty: 'No items in this period',
        reportOriginal: 'Open source',
        reportPeriod: 'Period',
        reportGenerated: 'Generated',
        noIntelligence: 'No matching intelligence',
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
        policy: {documents: [], total: 0, search: '', topic: '', priority: '', dateFrom: '', dateTo: '', sort: 'relevance'},
        news: {documents: [], total: 0, search: '', topic: '', priority: '', dateFrom: '', dateTo: '', sort: 'relevance'},
        industry_report: {documents: [], total: 0, search: '', topic: '', priority: '', dateFrom: '', dateTo: '', sort: 'relevance'}
    },
    homeFilters: {sourceType: 'all', topic: '', priority: '', dateFrom: '', dateTo: ''},
    allCategories: [],
    analysis: null,
    report: null,
    history: [],
    knowledgeByPaperId: {},
    facetSchema: [],
    categoryChart: null,
    trendChart: null,
    sourceComparisonChart: null,
    entityTrendChart: null,
    currentDate: new Date(),
    theme: localStorage.getItem('theme') || 'light'
};

// ==================== 初始化 ==================== //
document.addEventListener('DOMContentLoaded', async function() {
    initTheme();
    initNavigation();
    initCalendar();
    initEventListeners();
    
    // 加载数据
    await loadAllData();
    
    // 初始化UI组件
    initScrollBehavior();
    initMobileMenu();
});

// ==================== 主题切换 ==================== //
function initTheme() {
    const html = document.documentElement;
    html.setAttribute('data-theme', state.theme);
    
    const themeToggle = document.getElementById('theme-toggle');
    const icon = themeToggle.querySelector('i');
    icon.className = state.theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
}

function toggleTheme() {
    state.theme = state.theme === 'light' ? 'dark' : 'light';
    localStorage.setItem('theme', state.theme);
    initTheme();
}

// ==================== 导航 ==================== //
function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const section = item.dataset.section;
            navigateToSection(section);
        });
    });
    
    // 处理链接点击
    document.querySelectorAll('[data-section]').forEach(link => {
        link.addEventListener('click', (e) => {
            const section = link.dataset.section;
            if (section) {
                e.preventDefault();
                navigateToSection(section);
            }
        });
    });
}

function navigateToSection(sectionName) {
    // 更新状态
    state.currentSection = sectionName;
    
    // 更新导航栏
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.section === sectionName);
    });
    
    // 切换内容区域
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.toggle('active', section.id === `${sectionName}-section`);
    });
    
    // 关闭移动端菜单
    closeMobileMenu();
    
    // 滚动到顶部
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ==================== 移动端菜单 ==================== //
function initMobileMenu() {
    const mobileBtn = document.getElementById('mobile-menu-btn');
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebar-toggle-btn');
    
    if (mobileBtn) {
        mobileBtn.addEventListener('click', toggleMobileMenu);
    }
    
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', closeMobileMenu);
    }
    
    // 点击遮罩关闭
    document.addEventListener('click', (e) => {
        if (sidebar && sidebar.classList.contains('open')) {
            if (!sidebar.contains(e.target) && !mobileBtn.contains(e.target)) {
                closeMobileMenu();
            }
        }
    });
}

function toggleMobileMenu() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('open');
}

function closeMobileMenu() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.remove('open');
}

// ==================== 日历 ==================== //
function initCalendar() {
    renderCalendar(state.currentDate);
    
    document.getElementById('prev-month')?.addEventListener('click', () => {
        state.currentDate.setMonth(state.currentDate.getMonth() - 1);
        renderCalendar(state.currentDate);
    });
    
    document.getElementById('next-month')?.addEventListener('click', () => {
        state.currentDate.setMonth(state.currentDate.getMonth() + 1);
        renderCalendar(state.currentDate);
    });
}

function renderCalendar(date) {
    const year = date.getFullYear();
    const month = date.getMonth();
    
    // 更新标题
    const monthNames = I18N[LANG].monthNames;
    document.getElementById('current-month').textContent = LANG === 'en'
        ? `${monthNames[month]} ${year}`
        : `${year}年${monthNames[month]}`;
    
    // 获取月份第一天和最后一天
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const startDay = firstDay.getDay(); // 0 (周日) - 6 (周六)
    const totalDays = lastDay.getDate();
    
    // 生成日历网格
    const calendarBody = document.getElementById('calendar-body');
    calendarBody.innerHTML = '';
    
    // 星期标题
    const weekDays = I18N[LANG].weekDays;
    weekDays.forEach(day => {
        const dayHeader = document.createElement('div');
        dayHeader.className = 'calendar-day-header';
        dayHeader.textContent = day;
        dayHeader.style.cssText = 'font-weight: 600; color: var(--text-secondary); text-align: center; padding: 0.5rem 0;';
        calendarBody.appendChild(dayHeader);
    });
    
    // 填充空白日期
    for (let i = 0; i < startDay; i++) {
        const emptyDay = document.createElement('div');
        emptyDay.className = 'calendar-day empty';
        calendarBody.appendChild(emptyDay);
    }
    
    // 填充日期
    const today = new Date();
    for (let day = 1; day <= totalDays; day++) {
        const dayElement = document.createElement('div');
        dayElement.className = 'calendar-day';
        dayElement.textContent = day;
        
        // 标记今天
        if (year === today.getFullYear() && month === today.getMonth() && day === today.getDate()) {
            dayElement.classList.add('active');
        }
        
        // TODO: 检查是否有数据，添加 has-data 类
        // dayElement.classList.add('has-data');
        
        dayElement.addEventListener('click', () => {
            // TODO: 加载特定日期的数据
            console.log(`Selected date: ${year}-${month + 1}-${day}`);
        });
        
        calendarBody.appendChild(dayElement);
    }
}

// ==================== 数据加载 ==================== //
async function loadAllData() {
    try {
        await Promise.all([
            loadStats(),
            loadAnalysis(),
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
        renderPapers(filterPapers(state.allPapers));
        renderFeaturedPapers(state.allPapers.slice(0, 5));
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
        if (!response.ok) {
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
        console.warn('加载结构化知识失败:', error);
        state.knowledgeByPaperId = {};
        state.facetSchema = [];
    }
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

async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        if (!response.ok) throw new Error('Failed to load stats');
        
        const stats = await response.json();
        
        // 更新统计卡片
        updateElement('total-papers', stats.papers_count || 0);
        updateElement('total-summaries', stats.summaries_count || 0);
        
        // 更新最后更新时间
        if (stats.last_update) {
            updateElement('last-update-time', stats.last_update);
        }
        
        // 从分析数据获取更多统计
        const analysisRes = await fetch('/api/analysis');
        if (analysisRes.ok) {
            const analysis = await analysisRes.json();
            const keywords = analysis.keywords || [];
            const categories = Object.keys(analysis.statistics?.category_distribution || {});
            
            updateElement('total-categories', categories.length);
            updateElement('hot-topics', Math.min(keywords.length, 10));
        }
    } catch (error) {
        console.error('加载统计数据失败:', error);
    }
}

async function loadAnalysis() {
    try {
        const response = await fetch('/api/analysis');
        if (!response.ok) throw new Error('Failed to load analysis');
        
        const analysis = await response.json();
        state.analysis = analysis;
        
        // 加载词云
        await loadWordcloud();
        
        // 加载LLM分析
        const llmAnalysis = analysis.llm_analysis || {};
        
        renderAnalysisContent('summary-content', llmAnalysis.analysis_summary_html || llmAnalysis.analysis_summary);
        renderAnalysisContent('hotspots-content', llmAnalysis.hotspots_html || llmAnalysis.hotspots);
        renderAnalysisContent('trends-content', llmAnalysis.trends_html || llmAnalysis.trends);
        renderAnalysisContent('future-content', llmAnalysis.future_directions_html || llmAnalysis.future_directions);
        renderAnalysisContent('ideas-content', llmAnalysis.research_ideas_html || llmAnalysis.research_ideas);
        renderResearchTrendModules();
        renderHomeTrendSignals();
        
    } catch (error) {
        console.error('加载分析数据失败:', error);
        showError('hotspots-content', t('loadAnalysisFailed'));
    }
}

async function loadWordcloud() {
    try {
        const response = await fetch('/api/wordcloud');
        if (!response.ok) throw new Error('Failed to load wordcloud');
        
        const data = await response.json();
        const container = document.getElementById('wordcloud-container');
        
        if (data.url) {
            container.innerHTML = `<img src="${data.url}" alt="Wordcloud" class="fade-in">`;
        } else {
            container.innerHTML = `<p style="color: var(--text-secondary);">${t('noWordcloud')}</p>`;
        }
    } catch (error) {
        console.error('加载词云失败:', error);
        const container = document.getElementById('wordcloud-container');
        container.innerHTML = `<p style="color: var(--text-secondary);">${t('wordcloudLoadFailed')}</p>`;
    }
}

async function loadPapers(page = 1) {
    try {
        showLoading('papers-list');
        
        const params = new URLSearchParams({
            page: page,
            per_page: state.papersPerPage,
            category: state.selectedCategory
        });
        
        const response = await fetch(`/api/papers?${params}`);
        if (!response.ok) throw new Error('Failed to load papers');
        
        const data = await response.json();
        state.allPapers = data.papers || [];
        state.currentPage = page;
        
        // 渲染论文列表
        renderPapers(filterPapers(state.allPapers));
        
        // 渲染分页
        renderPagination(data.total_pages, page);
        
        // 渲染热门论文（概览页）
        renderFeaturedPapers(state.allPapers.slice(0, 5));
        renderResearchMatrix();
        renderComparisonTable();
        
    } catch (error) {
        console.error('加载论文失败:', error);
        showError('papers-list', LANG === 'en' ? 'Failed to load papers' : '加载论文失败');
    }
}

async function loadCategories() {
    try {
        const response = await fetch('/api/categories');
        if (!response.ok) throw new Error('Failed to load categories');
        
        const categories = await response.json();
        state.allCategories = categories;
        
        // 渲染类别列表（侧边栏）
        renderCategoryList(categories);
        
        // 渲染类别筛选（论文列表页）
        renderCategoryFilter(categories);
        
    } catch (error) {
        console.error('加载类别失败:', error);
    }
}

// ==================== 渲染函数 ==================== //
function renderPapers(papers) {
    const container = document.getElementById('papers-list');
    
    if (!papers || papers.length === 0) {
        container.innerHTML = `<p style="text-align: center; color: var(--text-secondary); padding: 3rem;">${t('noPaperData')}</p>`;
        return;
    }
    
    container.innerHTML = papers.map(paper => {
        const knowledge = state.knowledgeByPaperId[paper.id];
        const card = paper.web_card || {};
        const links = card.links || {};
        const suggestion = card.reading_suggestion || {};
        const title = card.title || paper.title;
        const primaryUrl = links.primary_url || paper.entry_url || '#';
        const sourceUrl = links.source_url || paper.entry_url || primaryUrl;
        const pdfUrl = links.pdf_url || paper.pdf_url || sourceUrl;
        const authorLine = card.author_line || (paper.authors ? paper.authors.slice(0, 3).join(', ') : t('unknown'));
        const publishedAt = card.published_at || paper.published || 'N/A';
        const summaryText = card.summary || card.description || paper.summary || paper.abstract || t('noAbstract');
        const badges = card.badges || paper.categories || [];
        const relatedTopics = suggestion.related_topics || [];
        const priority = normalizePriority(card.read_priority || suggestion.read_priority);
        return `
        <div class="paper-card fade-in priority-card-${priority}">
            <div class="paper-header">
                <div>
                    <h3 class="paper-title">
                        <a href="${primaryUrl}" target="_blank">${escapeHtml(title)}</a>
                    </h3>
                    <div class="paper-meta">
                        <span class="paper-meta-item">
                            <i class="fas fa-calendar"></i>
                            ${publishedAt}
                        </span>
                        <span class="paper-meta-item">
                            <i class="fas fa-user"></i>
                            ${escapeHtml(authorLine || t('unknown'))}
                        </span>
                    </div>
                </div>
            </div>
            ${renderRankingPanel(card)}
            <p class="paper-abstract">${escapeHtml(summaryText)}</p>
            <div class="paper-meta" style="margin-bottom:0.375rem">
                ${renderCompactInfoBar(card, paper)}
            </div>
            ${renderKnowledgePanel(knowledge)}
            ${renderRelatedDocuments(card)}
            <div class="paper-categories">
                ${badges.map(cat => 
                    `<span class="category-badge">${escapeHtml(cat)}</span>`
                ).join('')}
                ${relatedTopics.map(topic =>
                    `<span class="category-badge">${escapeHtml(topic)}</span>`
                ).join('')}
            </div>
            <div class="paper-actions">
                <a href="${pdfUrl}" target="_blank" class="btn-paper btn-primary">
                    <i class="fas fa-file-pdf"></i>
                    PDF
                </a>
                <a href="${sourceUrl}" target="_blank" class="btn-paper btn-secondary">
                    <i class="fas fa-external-link-alt"></i>
                    arXiv
                </a>
            </div>
        </div>
    `;
    }).join('');
}

async function loadIntelligenceHome() {
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
        const response = await fetch(`/api/intelligence?${params}`);
        if (!response.ok) throw new Error('Failed to load intelligence');
        const payload = await response.json();
        updateElement('intelligence-result-count', `${payload.total || 0} ${LANG === 'zh' ? '条' : 'items'}`);
        renderTodayRecommendations(payload.documents || []);
        renderSourceSnapshot(payload.source_counts || {});
    } catch (error) {
        console.error('加载科研情报首页失败:', error);
        showError('today-recommendations', t('noIntelligence'));
    }
}

function renderTodayRecommendations(documents) {
    const container = document.getElementById('today-recommendations');
    if (!container) return;
    if (!documents.length) {
        container.innerHTML = `<p class="trend-note">${t('noIntelligence')}</p>`;
        return;
    }
    const labels = LANG === 'zh'
        ? {paper: '论文', policy: '政策', news: '新闻', industry_report: '行业报告'}
        : {paper: 'Paper', policy: 'Policy', news: 'News', industry_report: 'Industry report'};
    container.innerHTML = documents.map(document => {
        const card = document.web_card || document;
        const suggestion = card.reading_suggestion || document.reading_suggestion || {};
        const url = card.links?.source_url || card.links?.primary_url || document.url || document.entry_url || '';
        const safeUrl = /^https?:\/\//i.test(url) ? url : '';
        const sourceType = card.source_type || document.source_type || 'paper';
        return `<article class="recommendation-card">
            <header><span class="report-source-chip">${labels[sourceType] || escapeHtml(sourceType)}</span><h3>${escapeHtml(card.title || document.title || '')}</h3><span class="report-score">${Number(card.importance_score || document.importance_score || 0).toFixed(1)}</span></header>
            <p>${escapeHtml(suggestion.why_relevant || card.summary || document.summary || document.abstract || '')}</p>
            <footer><span>${escapeHtml(suggestion.recommended_action || '')}</span>${safeUrl ? `<a href="${escapeHtml(safeUrl)}" target="_blank" rel="noopener noreferrer">${t('originalSource')} <i class="fas fa-arrow-up-right-from-square"></i></a>` : ''}</footer>
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
    container.innerHTML = items.map(([type, section, icon, label]) => `<button type="button" class="source-snapshot-item" data-home-section="${section}"><i class="fas ${icon}"></i><span>${label}</span><strong>${Number(counts[type] || 0)}</strong></button>`).join('');
    container.querySelectorAll('[data-home-section]').forEach(button => {
        button.addEventListener('click', () => navigateToSection(button.dataset.homeSection));
    });
}

function renderHomeTrendSignals() {
    const container = document.getElementById('home-trend-signals');
    if (!container) return;
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
    try {
        const response = await fetch('/api/scheduler/status');
        if (!response.ok) throw new Error('Failed to load scheduler status');
        const payload = await response.json();
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
        console.warn('加载调度状态失败:', error);
        container.innerHTML = `<p class="trend-note">${t('schedulerLoadFailed')}</p>`;
    }
}

async function loadReport(reportType) {
    const selectedType = reportType || document.getElementById('report-type')?.value || 'weekly';
    showLoading('intelligence-report');
    try {
        const response = await fetch(`/api/reports/latest?report_type=${encodeURIComponent(selectedType)}`);
        if (!response.ok) throw new Error('Failed to load report');
        state.report = await response.json();
        renderIntelligenceReport(state.report);
    } catch (error) {
        console.error('加载情报报告失败:', error);
        showError('intelligence-report', t('reportLoadFailed'));
    }
}

function renderIntelligenceReport(report) {
    updateElement('report-title', report.title || '');
    updateElement(
        'report-period',
        `${t('reportPeriod')}：${report.period_start || '—'} — ${report.period_end || '—'} · ${t('reportGenerated')} ${formatReportTime(report.generated_at)}`
    );
    const sourceCounts = report.source_counts || {};
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
    if (!sections.length) {
        container.innerHTML = `<div class="report-empty">${t('reportEmpty')}</div>`;
        return;
    }
    const icons = {
        hot_papers: 'fa-file-circle-check',
        policy_guidance: 'fa-landmark-flag',
        news_and_industry: 'fa-industry',
        key_trends: 'fa-arrow-trend-up',
        research_inspirations: 'fa-lightbulb',
        next_actions: 'fa-list-check'
    };
    container.innerHTML = sections.map((section, index) => {
        const items = section.items || [];
        return `<article class="report-section-card report-section-${escapeHtml(section.key || '')}">
            <header>
                <span class="report-section-index">${String(index + 1).padStart(2, '0')}</span>
                <i class="fas ${icons[section.key] || 'fa-file-lines'}"></i>
                <h2>${escapeHtml(section.title || '')}</h2>
                <span class="report-section-count">${items.length}</span>
            </header>
            <div class="report-section-items">
                ${items.length ? items.map(renderReportItem).join('') : `<p class="report-empty">${t('reportEmpty')}</p>`}
            </div>
        </article>`;
    }).join('');
}

function renderReportItem(item) {
    const score = Number(item.importance_score || 0);
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
            ${score > 0 ? `<span class="report-score">${score.toFixed(1)}</span>` : ''}
        </div>
        ${item.body ? `<p>${escapeHtml(item.body)}</p>` : ''}
        <div class="report-item-footer">
            ${item.meta ? `<span>${escapeHtml(item.meta)}</span>` : '<span></span>'}
            ${sourceUrl ? `<a href="${escapeHtml(sourceUrl)}" target="_blank" rel="noopener noreferrer">${t('reportOriginal')}<i class="fas fa-arrow-up-right-from-square"></i></a>` : ''}
        </div>
    </div>`;
}

function formatReportTime(value) {
    const parsed = new Date(value || '');
    if (Number.isNaN(parsed.getTime())) return value || '—';
    return new Intl.DateTimeFormat(LANG === 'zh' ? 'zh-CN' : 'en', {
        month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
    }).format(parsed);
}

async function loadDirectory(sourceType) {
    const directory = state.directories[sourceType];
    if (!directory) return;
    const ids = directoryIds(sourceType);
    showLoading(ids.list);
    const params = new URLSearchParams({
        source_type: sourceType,
        page: 1,
        per_page: 100,
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
        directory.documents = payload.documents || [];
        directory.total = Number(payload.total || 0);
        updateElement(ids.total, `${directory.total} ${sourceType === 'industry_report' && LANG === 'zh' ? '份' : LANG === 'zh' ? '条' : 'items'}`);
        updateElement(ids.navCount, directory.total);
        renderDirectoryDocuments(sourceType, directory.documents);
    } catch (error) {
        console.error(`加载 ${sourceType} 目录失败:`, error);
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
    if (!documents.length) {
        const empty = {
            policy: ['fa-landmark', t('emptyPolicyTitle'), t('emptyPolicyHint')],
            news: ['fa-newspaper', t('emptyNewsTitle'), t('emptyNewsHint')],
            industry_report: ['fa-industry', t('emptyReportTitle'), t('emptyReportHint')]
        }[sourceType];
        container.innerHTML = `<div class="directory-empty"><i class="fas ${empty[0]}"></i><strong>${empty[1]}</strong><span>${empty[2]}</span></div>`;
        return;
    }

    const icon = {policy: 'fa-landmark', news: 'fa-newspaper', industry_report: 'fa-industry'}[sourceType];
    container.innerHTML = documents.map(document => {
        const card = document.web_card || document;
        const links = card.links || {};
        const suggestion = card.reading_suggestion || {};
        const sourceUrl = links.source_url || links.primary_url || document.url || '#';
        const title = card.title || document.title || '';
        const publishedAt = card.published_at || document.published_at || 'N/A';
        const organization = card.author_line || card.source_name || document.source_name || t('unknown');
        const summary = card.summary || card.description || document.summary || document.raw_text || t('noAbstract');
        const badges = card.badges || document.tags || [];
        const priority = normalizePriority(card.read_priority || suggestion.read_priority);
        return `<article class="paper-card intelligence-card fade-in priority-card-${priority}">
            <div class="paper-header"><div>
                <h3 class="paper-title"><i class="fas ${icon} source-type-icon"></i><a href="${escapeHtml(sourceUrl)}" target="_blank" rel="noopener noreferrer">${escapeHtml(title)}</a></h3>
                <div class="paper-meta">
                    <span class="paper-meta-item"><i class="fas fa-calendar"></i>${escapeHtml(publishedAt)}</span>
                    <span class="paper-meta-item"><i class="fas fa-building"></i>${escapeHtml(organization)}</span>
                </div>
            </div></div>
            ${renderRankingPanel(card)}
            <p class="paper-abstract">${escapeHtml(summary)}</p>
            ${renderRelatedDocuments(card)}
            <div class="paper-categories">${badges.slice(0, 12).map(tag => `<span class="category-badge">${escapeHtml(tag)}</span>`).join('')}</div>
            <div class="paper-actions"><a href="${escapeHtml(sourceUrl)}" target="_blank" rel="noopener noreferrer" class="btn-paper btn-primary"><i class="fas fa-arrow-up-right-from-square"></i>${t('originalSource')}</a></div>
        </article>`;
    }).join('');
}

function renderRelatedDocuments(card) {
    const related = card.related_documents || [];
    const duplicateSources = card.duplicate_sources || [];
    if (!related.length && duplicateSources.length < 2) return '';
    const typeLabels = LANG === 'zh'
        ? {paper: '论文', policy: '政策', news: '新闻', industry_report: '行业报告'}
        : {paper: 'Paper', policy: 'Policy', news: 'News', industry_report: 'Industry report'};
    const links = related.map(item => `<a class="related-document" href="${escapeHtml(item.url || '#')}" target="_blank" rel="noopener noreferrer">
        <span class="related-type">${typeLabels[item.source_type] || escapeHtml(item.source_type)}</span>
        <span class="related-title">${escapeHtml(item.title)}</span>
        <strong>${Math.round(Number(item.score || 0) * 100)}</strong>
        <small>${escapeHtml(item.reason || '')}</small>
    </a>`).join('');
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
    const priority = normalizePriority(card.read_priority || suggestion.read_priority);
    const action = card.recommended_action || suggestion.recommended_action || '';
    const score = Number(card.importance_score);
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
        .filter(([key]) => Object.prototype.hasOwnProperty.call(breakdown, key))
        .map(([key, label]) => {
            const value = Math.max(0, Math.min(100, Number(breakdown[key]) || 0));
            return `<div class="score-row">
                <span>${label}</span>
                <div class="score-track"><i style="width:${value}%"></i></div>
                <strong>${Math.round(value)}</strong>
            </div>`;
        }).join('');

    return `<div class="ranking-panel ranking-${priority}">
        <div class="ranking-summary">
            <span class="priority-pill priority-${priority}">${priorityLabel(priority)}</span>
            ${action ? `<span class="action-pill"><i class="fas fa-book-open"></i>${escapeHtml(action)}</span>` : ''}
            ${Number.isFinite(score) ? `<span class="score-pill">${t('scoreLabel')} <strong>${score.toFixed(1)}</strong></span>` : ''}
        </div>
        ${!compact && rows ? `<details class="ranking-details">
            <summary>${t('scoreBreakdown')}</summary>
            <div class="score-grid">${rows}</div>
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

    if (card.source_name) {
        parts.push(`<span><i class="fas fa-database"></i> ${escapeHtml(card.source_name)}</span>`);
    }
    if (meta.citation_count !== undefined && meta.citation_count !== null) {
        const cites = meta.citation_count;
        const bracket = meta.impact_bracket || '';
        let badge = '';
        if (bracket === 'hot') badge = ' <span class=\"impact-badge impact-hot\">\u{1f525} \u9ad8\u5f15</span>';
        else if (bracket === 'high') badge = ' <span class=\"impact-badge impact-high\">\u{2b50} \u9ad8\u5f71\u54cd</span>';
        else if (bracket === 'notable') badge = ` <span class=\"impact-badge impact-notable\">\u{1f4c8} \u5f15\u7528 ${cites}</span>`;
        parts.push(`<span><i class="fas fa-quote-right"></i> ${escapeHtml(String(cites))}${badge}</span>`);
    }
    if (meta.openalex_primary_topic) {
        parts.push(`<span><i class="fas fa-tag"></i> ${escapeHtml(meta.openalex_primary_topic)}</span>`);
    }
    if (meta.openalex_institutions && meta.openalex_institutions.length) {
        parts.push(`<span><i class="fas fa-building"></i> ${escapeHtml(meta.openalex_institutions.slice(0, 2).join(', '))}</span>`);
    }

    if (!parts.length) return '';
    return parts.join(' <span style=\"color:var(--text-tertiary)\">|</span> ');
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

    const collapsedId = 'kp-body-' + Math.random().toString(36).slice(2, 8);

    return `
        <div class="knowledge-panel">
            <div class="knowledge-panel-title" onclick="var e=document.getElementById('${collapsedId}');e.style.display=e.style.display==='none'?'block':'none'">
                <i class="fas fa-sitemap"></i>
                <span>${t('structuredInsight')}</span>
                <span style="font-size:0.65rem;opacity:0.5;margin-left:auto;">▼</span>
            </div>
            ${facetBadges ? `
                <div class="facet-strip">
                    ${facetBadges}
                </div>
            ` : ''}
            <div id="${collapsedId}" style="display:none">
                <div class="knowledge-grid">${highlights}</div>
                ${evidenceRows ? `
                    <details class="knowledge-evidence">
                        <summary>${t('evidence')}</summary>
                        <div class="evidence-list">${evidenceRows}</div>
                    </details>
                ` : ''}
            </div>
        </div>
    `;
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
    
    if (!papers || papers.length === 0) {
        container.innerHTML = `<p style="text-align: center; color: var(--text-secondary);">${t('noPapers')}</p>`;
        return;
    }
    
    container.innerHTML = papers.map(paper => {
        const card = paper.web_card || {};
        const links = card.links || {};
        const title = card.title || paper.title;
        const summaryText = card.summary || card.description || paper.summary || paper.abstract || '';
        const primaryUrl = links.primary_url || paper.entry_url || '#';
        const sourceName = card.source_name || 'arXiv';
        return `
        <div class="paper-card fade-in">
            <h4 class="paper-title">
                <a href="${primaryUrl}" target="_blank">${escapeHtml(title)}</a>
            </h4>
            <p class="paper-abstract" style="display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
                ${escapeHtml(summaryText)}
            </p>
            ${renderRankingPanel(card, true)}
            ${renderCompactInfoBar(card, paper)}
            <div class="paper-actions" style="margin-top: 0.5rem;">
                <a href="${primaryUrl}" target="_blank" class="btn-paper btn-primary" style="font-size: 0.875rem; padding: 0.5rem 1rem;">
                    <i class="fas fa-arrow-right"></i>
                    ${t('viewDetail')}
                </a>
            </div>
        </div>
    `;
    }).join('');
}

function renderCategoryList(categories) {
    const container = document.getElementById('category-list');
    
    if (!categories || categories.length === 0) {
        container.innerHTML = `<p style="text-align: center; color: var(--text-secondary); font-size: 0.875rem;">${t('noCategories')}</p>`;
        return;
    }
    
    container.innerHTML = categories.slice(0, 10).map(cat => `
        <div class="category-item ${state.selectedCategory === cat.name ? 'active' : ''}" 
             data-category="${escapeHtml(cat.name)}">
            <span class="category-name">${escapeHtml(cat.name)}</span>
            <span class="category-count">${cat.count}</span>
        </div>
    `).join('');
    
    // 绑定点击事件
    container.querySelectorAll('.category-item').forEach(item => {
        item.addEventListener('click', () => {
            const category = item.dataset.category;
            filterByCategory(category === state.selectedCategory ? '' : category);
        });
    });
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
    const container = document.getElementById('pagination');
    if (!container) return;
    
    const pages = [];
    const maxVisible = 5;
    
    // 上一页
    pages.push(`
        <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" data-page="${currentPage - 1}">
                <i class="fas fa-chevron-left"></i>
            </a>
        </li>
    `);
    
    // 页码
    let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let endPage = Math.min(totalPages, startPage + maxVisible - 1);
    
    if (endPage - startPage < maxVisible - 1) {
        startPage = Math.max(1, endPage - maxVisible + 1);
    }
    
    for (let i = startPage; i <= endPage; i++) {
        pages.push(`
            <li class="page-item ${i === currentPage ? 'active' : ''}">
                <a class="page-link" href="#" data-page="${i}">${i}</a>
            </li>
        `);
    }
    
    // 下一页
    pages.push(`
        <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
            <a class="page-link" href="#" data-page="${currentPage + 1}">
                <i class="fas fa-chevron-right"></i>
            </a>
        </li>
    `);
    
    container.innerHTML = pages.join('');
    
    // 绑定点击事件
    container.querySelectorAll('.page-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const page = parseInt(link.dataset.page);
            if (page > 0 && page <= totalPages) {
                loadPapers(page);
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        });
    });
}

function renderAnalysisContent(elementId, content) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    if (content) {
        element.innerHTML = content;
    } else {
        element.innerHTML = `<p style="color: var(--text-secondary);">${t('noData')}</p>`;
    }
}

function renderResearchTrendModules() {
    renderCategoryChart();
    renderTrendTimeline();
    renderSourceComparisonChart();
    renderEntityTrendChart();
}

function renderCategoryChart() {
    const canvas = document.getElementById('category-chart');
    if (!canvas || typeof Chart === 'undefined') return;

    const distribution = state.analysis?.statistics?.category_distribution || {};
    const entries = Object.entries(distribution).slice(0, 8);
    if (!entries.length) return;

    if (state.categoryChart) state.categoryChart.destroy();
    state.categoryChart = new Chart(canvas, {
        type: 'doughnut',
        data: {
            labels: entries.map(([category]) => category),
            datasets: [{
                data: entries.map(([, count]) => count),
                backgroundColor: ['#4f46e5', '#06b6d4', '#f43f5e', '#f59e0b', '#10b981', '#8b5cf6', '#14b8a6', '#ef4444'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'bottom' }
            }
        }
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
    const usableSnapshots = snapshots.filter(snapshot => snapshot.date);
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
    const colors = ['#06b6d4', '#f59e0b', '#10b981'];
    const topicDatasets = topTopics.map((topic, index) => ({
        label: topic,
        data: usableSnapshots.map(snapshot => Number(snapshot.topic_counts?.[topic] || 0)),
        borderColor: colors[index],
        backgroundColor: `${colors[index]}20`,
        fill: false,
        tension: 0.35
    }));

    if (state.trendChart) state.trendChart.destroy();
    state.trendChart = new Chart(canvas, {
        type: 'line',
        data: {
            labels: usableSnapshots.map(snapshot => snapshot.date),
            datasets: [
                {
                    label: LANG === 'zh' ? '文档数量' : 'Documents',
                    data: usableSnapshots.map(snapshot => snapshot.document_count || 0),
                    borderColor: '#4f46e5',
                    backgroundColor: 'rgba(79, 70, 229, 0.12)',
                    fill: true,
                    tension: 0.35
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
            ? topics.map(([topic]) => `<span class="trend-keyword">${escapeHtml(topic)}</span>`).join('')
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
    const entries = Object.entries(counts);
    if (!entries.length) {
        if (empty) empty.textContent = t('signalInsufficient');
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
            datasets: [{label: LANG === 'zh' ? '文档数' : 'Documents', data: entries.map(([, count]) => count), backgroundColor: ['#4f46e5', '#f59e0b', '#06b6d4', '#10b981']}]
        },
        options: {responsive: true, scales: {y: {beginAtZero: true, ticks: {precision: 0}}}, plugins: {legend: {display: false}}}
    });
}

function renderEntityTrendChart() {
    const canvas = document.getElementById('entity-trend-chart');
    const empty = document.getElementById('entity-trend-empty');
    if (!canvas || typeof Chart === 'undefined') return;
    const timeline = state.analysis?.temporal_trends?.timeline || [];
    const totals = {};
    timeline.forEach(snapshot => Object.entries(snapshot.entity_counts || {}).forEach(([entity, count]) => {
        totals[entity] = (totals[entity] || 0) + Number(count || 0);
    }));
    const entities = Object.entries(totals).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([entity]) => entity);
    if (!timeline.length || !entities.length) {
        if (empty) empty.textContent = t('signalInsufficient');
        return;
    }
    if (empty) empty.textContent = '';
    if (state.entityTrendChart) state.entityTrendChart.destroy();
    const colors = ['#4f46e5', '#06b6d4', '#f59e0b', '#10b981', '#f43f5e'];
    state.entityTrendChart = new Chart(canvas, {
        type: 'line',
        data: {
            labels: timeline.map(item => item.date),
            datasets: entities.map((entity, index) => ({label: entity, data: timeline.map(item => Number(item.entity_counts?.[entity] || 0)), borderColor: colors[index], tension: 0.3}))
        },
        options: {responsive: true, scales: {y: {beginAtZero: true, ticks: {precision: 0}}}, plugins: {legend: {position: 'bottom'}}}
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
            method: shorten(method || t('unknown'), 76),
            scenario: shorten(scenario || t('unknown'), 76),
            mechanism: shorten(mechanismValue || t('unknown'), 76)
        };
    }).filter(Boolean).slice(0, 12);

    if (!rows.length) {
        container.innerHTML = `<p class="trend-note">${t('noData')}</p>`;
        return;
    }

    container.innerHTML = `
        <div class="matrix-grid matrix-grid-header">
            <div>${t('methodScenario')}</div>
            <div>${t('mechanism')}</div>
            <div>${t('relatedPapers')}</div>
        </div>
        ${rows.map(row => `
            <div class="matrix-grid matrix-row">
                <div class="matrix-cell">
                    <strong>${escapeHtml(row.method)}</strong>
                    <span>${escapeHtml(row.scenario)}</span>
                </div>
                <div class="matrix-cell">${escapeHtml(row.mechanism)}</div>
                <div class="matrix-cell matrix-paper-title">${escapeHtml(shorten(row.title, 96))}</div>
            </div>
        `).join('')}
    `;
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
        container.innerHTML = `<p class="trend-note">${t('noData')}</p>`;
        return;
    }

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
                        <td><a href="${row.paper.entry_url}" target="_blank">${escapeHtml(shorten(row.paper.title, 72))}</a></td>
                        <td>${escapeHtml(shorten(row.problem, 120))}</td>
                        <td>${escapeHtml(shorten(row.method, 120))}</td>
                        <td>${escapeHtml(shorten(row.scenario, 100))}</td>
                        <td>${escapeHtml(shorten(row.metric, 100))}</td>
                        <td>${escapeHtml(shorten(row.contribution, 140))}</td>
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
    state.currentPage = 1;
    
    // 更新侧边栏类别高亮
    document.querySelectorAll('.category-item').forEach(item => {
        item.classList.toggle('active', item.dataset.category === category);
    });
    
    // 更新下拉框
    const select = document.getElementById('paper-category-filter');
    if (select) {
        select.value = category;
    }
    
    // 重新渲染论文
    renderPapers(filterPapers(state.allPapers));
}

function searchPapers(query) {
    state.searchQuery = query;
    state.currentPage = 1;
    renderPapers(filterPapers(state.allPapers));
}

// ==================== 事件监听 ==================== //
function initEventListeners() {
    // 主题切换
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }
    
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
        window.scrollTo({ top: 0, behavior: 'smooth' });
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
    if (element) {
        element.innerHTML = `
            <div class="loading">
                <div class="spinner"></div>
                <p>${t('loading')}</p>
            </div>
        `;
    }
}

function showError(elementId, message) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = `
            <p style="text-align: center; color: var(--accent-color); padding: 2rem;">
                <i class="fas fa-exclamation-circle"></i> ${message}
            </p>
        `;
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
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
    toggleTheme
};
