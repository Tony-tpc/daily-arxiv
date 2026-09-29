"""Read-only local UI review with isolated Edge/Chromium and screenshot artifacts.

Install the optional QA dependency ``playwright`` and run
``python -m test.manual_visual_review``. Uses system Edge on Windows; elsewhere
install Playwright Chromium. Reports/charts read the existing local dataset.
No records or application configuration are written. Output: data/ui-review/.
"""

import json
import logging
import sys
from pathlib import Path
from threading import Thread

from playwright.sync_api import expect, sync_playwright
from werkzeug.serving import make_server

from test.manual_web_fixtures import create_fixture_app


OUTPUT = Path(__file__).resolve().parents[1] / 'data' / 'ui-review'
ROUTES = ('overview', 'papers', 'policies', 'news', 'industry-reports',
          'paper-report', 'policy-analysis', 'analysis', 'reports', 'statistics')


def assert_layout(page):
    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth'), 'Horizontal overflow'
    assert page.locator('.content-section.active').count() == 1
    page.wait_for_function("""() => [...document.querySelectorAll('img[data-energy-image]')]
        .filter(img => {
            const r = img.getBoundingClientRect();
            return r.width && r.height && r.bottom > 0 && r.top < innerHeight;
        }).every(img => img.complete && img.naturalWidth > 0)""")


def navigate(page, route):
    if page.locator('#mobile-menu-btn').is_visible():
        page.locator('#mobile-menu-btn').click()
    page.locator(f'.sidebar [data-section="{route}"]').click()
    page.wait_for_load_state('networkidle')
    expect(page.locator(f'.sidebar [data-section="{route}"]')).to_have_attribute('aria-current', 'page')
    assert_layout(page)


def run_review():
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    server = make_server('127.0.0.1', 0, create_fixture_app(), threaded=True)
    Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    results = []
    errors = []
    try:
        with sync_playwright() as playwright:
            options = {'channel': 'msedge'} if sys.platform == 'win32' else {}
            browser = playwright.chromium.launch(headless=True, **options)
            for width in (1440, 1024, 390):
                for theme in ('light', 'dark'):
                    context = browser.new_context(viewport={'width': width, 'height': 1000 if width > 390 else 844},
                                                  reduced_motion='reduce')
                    context.add_init_script(f"localStorage.setItem('theme', '{theme}')")
                    page = context.new_page()
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.goto(base, wait_until='networkidle')
                    page.locator('.overview-hero').wait_for()
                    assert page.evaluate('document.fonts.check("14px Inter")')
                    for route in ROUTES:
                        navigate(page, route)
                        if route in ('overview', 'papers', 'analysis', 'statistics'):
                            page.screenshot(path=str(OUTPUT / f'{route}-{width}-{theme}.png'))
                    # Reading and evidence controls use the real locally stored report.
                    navigate(page, 'paper-report')
                    if page.locator('#narrative-toc a').count():
                        toc = page.locator('#analysis-section .reader-toc')
                        if not toc.evaluate('el => el.open'):
                            toc.locator('summary').click()
                        page.locator('#narrative-toc a').first.click()
                        if page.locator('#narrative-content .narrative-citation').count():
                            page.locator('#narrative-content .narrative-citation').first.click()
                            expect(page.locator('#narrative-evidence-drawer')).to_have_class('narrative-evidence-drawer open')
                            page.keyboard.press('Escape')
                            expect(page.locator('#narrative-evidence-drawer')).not_to_have_class('narrative-evidence-drawer open')
                    page.locator('#theme-toggle').click()
                    expect(page.locator('html')).to_have_attribute('data-theme', 'dark' if theme == 'light' else 'light')
                    if width == 390:
                        page.locator('#mobile-menu-btn').click()
                        page.keyboard.press('Escape')
                        expect(page.locator('#mobile-menu-btn')).to_be_focused()
                    results.append({'width': width, 'theme': theme, 'routes': len(ROUTES), 'passed': True})
                    print(f'PASS {width}px {theme}: all 10 routes, theme and reader controls', flush=True)
                    context.close()

            page = browser.new_page(viewport={'width': 390, 'height': 844})
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(base + '/?case=many#papers', wait_until='networkidle')
            expect(page.locator('#papers-list .document-row')).to_have_count(20)
            page.locator('#papers-list .document-details > summary').first.click()
            expect(page.locator('#papers-list .paper-abstract').first).to_be_visible()
            assert_layout(page)
            page.locator('#papers-list .document-row').first.scroll_into_view_if_needed()
            page.screenshot(path=str(OUTPUT / 'paper-expanded-mobile.png'))
            page.locator('#search-input').fill('no-such-paper-qa')
            expect(page.locator('#papers-list .empty-state')).to_be_visible()
            page.locator('#paper-filter-clear').click()
            expect(page.locator('#papers-list .document-row')).to_have_count(20)
            page.locator('#papers-per-page').select_option('10')
            expect(page.locator('#papers-list .document-row')).to_have_count(10)
            page.locator('#pagination button').filter(has_text='2').click()
            expect(page.locator('#papers-list h3').first).to_contain_text('11')
            page.locator('#paper-sort').select_option('title')
            assert_layout(page)

            page.goto(base + '/?case=empty#papers', wait_until='networkidle')
            expect(page.locator('#papers-list .empty-state')).to_be_visible()
            page.screenshot(path=str(OUTPUT / 'empty-mobile.png'))
            # An actual failed image request must produce a usable, local placeholder.
            page.route('**/images/energy/wind.webp', lambda route: route.abort())
            page.goto(base, wait_until='networkidle')
            hero = page.locator('.hero-visual img')
            expect(hero).to_have_attribute('data-image-fallback', 'true')
            expect(hero).to_have_attribute('src', '/static/images/energy/placeholder.svg')
            assert hero.evaluate('img => img.complete && img.naturalWidth > 0')
            page.screenshot(path=str(OUTPUT / 'image-fallback-mobile.png'))
            page.unroute('**/images/energy/wind.webp')
            page.goto(base + '/?case=fail-once#papers', wait_until='networkidle')
            page.locator('#papers-list .error-state button').click()
            expect(page.locator('#papers-list .error-state')).to_have_count(0)
            assert_layout(page)
            page.goto(base + '/?language=en#papers', wait_until='networkidle')
            expect(page.locator('#papers-section h1')).to_have_text('Papers')
            assert_layout(page)
            page.screenshot(path=str(OUTPUT / 'english-mobile.png'))
            browser.close()
        assert not errors, errors
        results.append({'scenarios': ['long titles', 'expanded abstracts', 'search', 'clear filters',
                                      'page size', 'pagination', 'sort', 'empty', 'image failure',
                                      'API retry', 'English'], 'passed': True})
        (OUTPUT / 'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
        print('PASS scenario checks; no JavaScript exceptions', flush=True)
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    run_review()
