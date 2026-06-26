#!/usr/bin/env python3
"""
测试 Web 服务

检查所有 API 端点是否正常工作
"""
import sys
from pathlib import Path
import time
import requests

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_web_service(base_url='http://localhost:5000'):
    """测试 Web 服务的所有端点"""
    
    print("\n" + "=" * 60)
    print("🧪 Web 服务 API 测试")
    print("=" * 60)
    
    tests = []
    
    # 测试 1: 主页
    print("\n测试 1: 主页")
    try:
        response = requests.get(f'{base_url}/')
        if response.status_code == 200:
            print("✅ 主页加载成功")
            tests.append(True)
        else:
            print(f"❌ 主页加载失败: {response.status_code}")
            tests.append(False)
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        tests.append(False)
    
    # 测试 2: 统计信息
    print("\n测试 2: 统计信息 API")
    try:
        response = requests.get(f'{base_url}/api/stats')
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 统计信息加载成功")
            print(f"   论文数: {data.get('papers_count')}")
            print(f"   总结数: {data.get('summaries_count')}")
            tests.append(True)
        else:
            print(f"❌ 统计信息加载失败: {response.status_code}")
            tests.append(False)
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        tests.append(False)
    
    # 测试 3: 趋势分析
    print("\n测试 3: 趋势分析 API")
    try:
        response = requests.get(f'{base_url}/api/analysis')
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 趋势分析加载成功")
            print(f"   关键词数: {len(data.get('keywords', []))}")
            print(f"   主题数: {len(data.get('topics', []))}")
            tests.append(True)
        else:
            print(f"❌ 趋势分析加载失败: {response.status_code}")
            tests.append(False)
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        tests.append(False)
    
    # 测试 4: 论文列表
    print("\n测试 4: 论文列表 API")
    try:
        response = requests.get(f'{base_url}/api/papers?page=1&per_page=10')
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 论文列表加载成功")
            print(f"   总论文数: {data.get('total')}")
            print(f"   当前页论文数: {len(data.get('papers', []))}")
            first_paper = (data.get('papers') or [None])[0]
            if first_paper and first_paper.get('web_card'):
                print(f"   web_card: 已提供标准化前端展示结构")
                print(f"   来源: {first_paper['web_card'].get('source_name')}")
                tests.append(True)
            else:
                print("❌ 缺少 web_card 标准化展示结构")
                tests.append(False)
        else:
            print(f"❌ 论文列表加载失败: {response.status_code}")
            tests.append(False)
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        tests.append(False)

    # 测试 4.5: 单篇论文详情
    print("\n测试 4.5: 论文详情 API")
    try:
        papers_response = requests.get(f'{base_url}/api/papers?page=1&per_page=1')
        papers_payload = papers_response.json() if papers_response.status_code == 200 else {}
        first_paper = (papers_payload.get('papers') or [None])[0]
        if not first_paper:
            print("❌ 没有可测试的论文详情")
            tests.append(False)
        else:
            paper_id = first_paper.get('id')
            response = requests.get(f'{base_url}/api/papers/{paper_id}')
            if response.status_code == 200:
                detail = response.json()
                if detail.get('web_card') and detail['web_card'].get('title'):
                    print("✅ 论文详情包含标准化 web_card")
                    print(f"   标题: {detail['web_card'].get('title')}")
                    tests.append(True)
                else:
                    print("❌ 论文详情缺少 web_card")
                    tests.append(False)
            else:
                print(f"❌ 论文详情加载失败: {response.status_code}")
                tests.append(False)
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        tests.append(False)
    
    # 测试 5: 类别列表
    print("\n测试 5: 类别列表 API")
    try:
        response = requests.get(f'{base_url}/api/categories')
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 类别列表加载成功")
            print(f"   类别数: {len(data)}")
            if len(data) > 0:
                print(f"   示例: {data[0]['name']} ({data[0]['count']} 篇)")
            tests.append(True)
        else:
            print(f"❌ 类别列表加载失败: {response.status_code}")
            tests.append(False)
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        tests.append(False)
    
    # 测试 6: 词云图
    print("\n测试 6: 词云图 API")
    try:
        response = requests.get(f'{base_url}/api/wordcloud')
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 词云图 API 成功")
            print(f"   URL: {data.get('url')}")
            tests.append(True)
        else:
            print(f"❌ 词云图加载失败: {response.status_code}")
            tests.append(False)
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        tests.append(False)
    
    # 测试 7: 自适应知识抽取
    print("\n测试 7: 自适应知识抽取 API")
    try:
        response = requests.get(f'{base_url}/api/knowledge')
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 结构化知识加载成功")
            print(f"   抽取论文数: {len(data.get('papers', []))}")
            print(f"   Facet 数: {len(data.get('facet_schema', []))}")
            tests.append(True)
        else:
            print(f"❌ 结构化知识加载失败: {response.status_code}")
            tests.append(False)
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        tests.append(False)
    
    # 测试 8: 历史趋势 API
    print("\n测试 8: 历史趋势 API")
    try:
        response = requests.get(f'{base_url}/api/history')
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 历史趋势加载成功")
            print(f"   快照数: {data.get('count')}")
            tests.append(True)
        else:
            print(f"❌ 历史趋势加载失败: {response.status_code}")
            tests.append(False)
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        tests.append(False)
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    passed = sum(tests)
    total = len(tests)
    print(f"通过: {passed}/{total}")
    print(f"成功率: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\n✅ 所有测试通过！")
        return True
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
        return False


def check_server_running(base_url='http://localhost:5000'):
    """检查服务器是否运行"""
    print("\n检查 Web 服务是否运行...")
    try:
        response = requests.get(f'{base_url}/api/stats', timeout=2)
        print("✅ Web 服务正在运行")
        return True
    except:
        print("❌ Web 服务未运行")
        print("\n请先启动 Web 服务:")
        print("  python src/web/app.py")
        return False


def main():
    """主函数"""
    base_url = 'http://localhost:5000'
    
    if not check_server_running(base_url):
        sys.exit(1)
    
    time.sleep(1)
    
    success = test_web_service(base_url)
    
    if success:
        print("\n💡 提示:")
        print(f"  访问 Web 界面: {base_url}")
        print(f"  API 文档: {base_url}/api/stats")
        print()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
