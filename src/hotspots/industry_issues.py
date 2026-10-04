"""Fixed cross-event questions; matching still requires two independent judgments."""

ISSUES = {
    'electricity-market': ('全国统一电力市场建设与运行', '中国电力市场',
        '市场化交易如何配置电力资源、促进消纳并改善供需匹配',
        '包含中长期、现货、跨省跨区、绿电交易的规模和结构、规则实施、价格传导、参与主体与运行堵点。统计发布、制度变化和独立采访是同一问题的不同证据；不包含一般设备建设、企业业绩或单纯并网安全。'),
    'power-safety': ('新型电力系统安全治理', '中国电力系统',
        '如何落实并网主体安全责任和事故防控',
        '包含并网运行安全制度、事故预防、应急处置和执法实践；不包含交易价格机制、一般行政巡视或人事安排。'),
    'gas-access': ('油气管网公平开放', '中国油气管网',
        '如何实现管网公平接入和透明监管',
        '包含第三方接入、信息公开、容量利用与公平开放监管；不包含一般油气价格波动。'),
    'storage-market': ('储能市场参与与商业化', '中国储能系统',
        '储能如何获得市场收益并提供系统调节服务',
        '包含储能入市规则、收益机制、独立运营与实际调节效果；不包含单家企业融资、产品发布或纯材料研究。'),
}

# Recall requires direct subject evidence in the article, never energy background alone.
ANCHORS = {
    'electricity-market': ('电力市场', '电力交易', '现货交易', '绿电交易', '售电', '中长期交易', '输电权'),
    'power-safety': ('电力安全', '并网', '电网安全', '供电安全', '电力事故'),
    'gas-access': ('油气管网', '管网设施', '公平开放'),
    'storage-market': ('储能',),
}


def eligible_definitions(document: dict) -> list[dict]:
    text = str(document.get('title', '')) + str(document.get('raw_text') or document.get('abstract') or '')
    return [row for row in definitions()
            if any(term in text for term in ANCHORS[row['id'].removeprefix('industry-issue-')])]


def definitions() -> list[dict]:
    return [{'id': 'industry-issue-' + key,
             'definition': dict(zip(('title', 'system', 'problem', 'definition'), values))}
            for key, values in ISSUES.items()]
