from __future__ import annotations

import argparse

import uvicorn

from app.config import load_settings
from app.pipeline import import_all, init_database


def build_parser() -> argparse.ArgumentParser:
    settings = load_settings()
    parser = argparse.ArgumentParser(description="同城配送经营分析系统")
    subparsers = parser.add_subparsers(dest="command", required=True)

    import_parser = subparsers.add_parser("import", help="导入数据并重建受影响月份的汇总")
    import_parser.add_argument(
        "--mode",
        default="auto",
        choices=["auto", "force"],
        help="导入模式：auto=按文件去重跳过未变化文件；force=忽略去重并强制重建当前文件对应月份",
    )

    server_parser = subparsers.add_parser("server", help="启动本地网页看板服务")
    server_parser.add_argument("--host", default=None, help=f"服务器主机地址（默认：{settings.server.host}）")
    server_parser.add_argument("--port", type=int, default=None, help=f"服务器端口（默认：{settings.server.port}）")
    server_parser.add_argument("--reload", action="store_true", default=None, help=f"启用热重载（默认：{settings.server.reload}）")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    settings = load_settings()

    if args.command == "import":
      init_database(settings)
      result = import_all(settings, mode=args.mode)
      print(result)
      return

    from app.api import create_app

    uvicorn.run(
        create_app,
        host=args.host or settings.server.host,
        port=args.port or settings.server.port,
        reload=args.reload or settings.server.reload,
        factory=True,
        use_colors=False,
    )


if __name__ == "__main__":
    main()
