"""
Daily arXiv Agent - 主程序入口 / Main entry

每日追踪 arXiv 最新论文，使用 LLM 进行总结和分析 /
Track latest arXiv papers daily and summarize/analyze them with LLMs
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径 / Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.pipeline.context import create_pipeline_context
from src.pipeline.runner import run_pipeline
from src.utils import load_config, load_env, setup_logging, get_date_string, pick_text


def main():
    """主函数 / Main function"""
    # 加载配置 / Load configuration
    load_env()
    config = load_config()
    logger = setup_logging(config)
    text = lambda zh, en: pick_text(config, zh, en)
    
    logger.info("=" * 60)
    logger.info(text("Daily arXiv Agent 启动", "Daily arXiv Agent started"))
    logger.info(f"{text('日期', 'Date')}: {get_date_string()}")
    logger.info("=" * 60)
    
    try:
        context = create_pipeline_context(config, logger, text)
        run_pipeline(context)
        
        if not context.stop_requested:
            logger.info("=" * 60)
            logger.info(text("✅ 所有任务完成！", "✅ All tasks completed!"))
            logger.info("=" * 60)
            logger.info(text("提示: 运行 'python src/web/app.py' 启动 Web 服务查看结果", "Tip: run 'python src/web/app.py' to start the web service"))
        
    except Exception as e:
        logger.error(text(f"❌ 执行出错: {str(e)}", f"❌ Execution failed: {str(e)}"), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
