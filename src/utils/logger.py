"""
日志工具
"""
import logging
import sys

try:
    from loguru import logger
except ImportError:
    logger = logging.getLogger("agentgraph_sentinel")

def setup_logger():
    """配置日志"""
    if isinstance(logger, logging.Logger):
        if not logger.handlers:
            logger.setLevel(logging.DEBUG)
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s:%(funcName)s - %(message)s"))
            logger.addHandler(handler)
        return logger

    logger.remove()
    
    # 控制台输出
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level="DEBUG"
    )
    
    # 文件输出
    logger.add(
        "logs/ags_{time}.log",
        rotation="500 MB",
        retention="10 days",
        level="DEBUG"
    )
    
    return logger

# 全局logger实例
log = setup_logger()
