"""
启动FastAPI服务器
"""
import uvicorn
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if __name__ == "__main__":
    # Windows 控制台默认使用 GBK，输出 emoji 会抛 UnicodeEncodeError，统一切到 UTF-8
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    from config.settings import get_settings

    settings = get_settings()

    print("=" * 60)
    print("🚀 启动 AgentGraph Sentinel API服务器")
    print("=" * 60)
    print()
    print(f"📍 API地址: http://localhost:{settings.API_PORT}")
    print(f"📖 API文档: http://localhost:{settings.API_PORT}/docs")
    print()
    print("按 Ctrl+C 停止服务器")
    print("=" * 60)
    print()

    uvicorn.run(
        "api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        log_level="info"
    )
