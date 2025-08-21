#!/usr/bin/env python3
"""
通用书源测试脚本
- 按书源ID或名称测试搜索
- 展示搜索结果、详情页、目录概览
- 可选触发下载(txt/epub)，输出下载文件路径

用法示例：
  python source_tester.py --keyword 斗破 --source-id 8 --max-results 5 --show-toc 10
  python source_tester.py --keyword 遮天 --source-name 大熊猫文学 --download txt
  python source_tester.py --keyword 完美世界 --max-results 10  # 跨书源搜索
"""

import argparse
import asyncio
import contextlib
import logging
import sys
import time
from pathlib import Path

# 确保可以导入项目模块
sys.path.insert(0, str(Path(__file__).parent))

from app.parsers.search_parser import SearchParser
from app.services.novel_service import NovelService

# Windows 平台：使用 Selector 事件循环策略，避免退出时 Proactor 噪声
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass


def build_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="书源搜索/下载测试工具")
    parser.add_argument("--keyword", required=True, help="搜索关键词")
    parser.add_argument("--source-id", type=int, help="书源ID（优先于名称）")
    parser.add_argument("--source-name", type=str, help="书源名称（模糊匹配）")
    parser.add_argument(
        "--max-results", type=int, default=5, help="展示的最大搜索结果数"
    )
    parser.add_argument("--show-toc", type=int, default=8, help="展示目录前N章")
    parser.add_argument(
        "--download",
        choices=["none", "txt", "epub"],
        default="none",
        help="是否下载及下载格式",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="输出详细日志（默认仅显示错误）",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="仅输出汇总表格（不进行后续详细测试）",
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="跳过开头的汇总表格",
    )
    return parser.parse_args()


def _configure_logging(verbose: bool) -> None:
    # 基础配置：默认仅显示ERROR，避免干扰测试输出
    logging.basicConfig(
        level=logging.ERROR, format="%(levelname)s - %(name)s - %(message)s"
    )

    # 抑制项目内与第三方的冗余日志
    targets = [
        "app",
        "app.services.novel_service",
        "app.parsers.search_parser",
        "aiohttp",
        "asyncio",
    ]
    for name in targets:
        logging.getLogger(name).setLevel(logging.ERROR)

    if verbose:
        # 打开详细日志
        logging.getLogger().setLevel(logging.INFO)
        for name in targets:
            logging.getLogger(name).setLevel(logging.INFO)


async def search_in_specific_source(
    service: NovelService, source_id: int, keyword: str
):
    source = service.sources.get(source_id)
    if not source:
        raise ValueError(f"书源ID不存在: {source_id}")
    parser = SearchParser(source)
    start = time.time()
    results = await parser.parse(keyword)
    elapsed = (time.time() - start) * 1000
    return results, elapsed, source.rule.get("name", f"书源{source_id}")


async def search_across_sources(service: NovelService, keyword: str, max_results: int):
    start = time.time()
    results = await service.search(keyword, max_results=max_results)
    elapsed = (time.time() - start) * 1000
    return results, elapsed


@contextlib.contextmanager
def suppress_logs(enable: bool):
    if not enable:
        # 不抑制
        yield
        return
    prev = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        yield
    finally:
        logging.disable(prev)


async def summarize_all_sources(
    service: NovelService,
    keyword: str,
    max_results: int = 3,
    test_toc: bool = True,
    timeout_sec: int = 12,
    concurrency: int = 6,
    quiet: bool = True,
):
    """输出所有书源的能力表格：可搜索/可获取目录/可下载(基于规则)"""
    sources = service.sources
    sem = asyncio.Semaphore(concurrency)

    async def check_source(source_id: int, source) -> dict:
        async with sem:
            rule = source.rule
            name = rule.get("name", f"书源{source_id}")
            search_ok = False
            toc_ok = False
            result_count = 0
            elapsed_ms = 0
            with suppress_logs(quiet):
                try:
                    sp = SearchParser(source)
                    start = time.time()
                    results = await asyncio.wait_for(
                        sp.parse(keyword), timeout=timeout_sec
                    )
                    elapsed_ms = int((time.time() - start) * 1000)
                    result_count = len(results) if results else 0
                    search_ok = result_count > 0
                    if search_ok and test_toc:
                        first = results[0]
                        url = getattr(first, "url", "")
                        if url:
                            try:
                                toc = await asyncio.wait_for(
                                    service.get_toc(url, source_id), timeout=timeout_sec
                                )
                                toc_ok = bool(toc)
                            except Exception:
                                toc_ok = False
                except Exception:
                    search_ok = False
                    toc_ok = False

            return {
                "id": source_id,
                "name": name,
                "search": search_ok,
                "toc": toc_ok,
                "results": result_count,
                "time": elapsed_ms,
            }

    tasks = [check_source(sid, src) for sid, src in sources.items()]
    rows = await asyncio.gather(*tasks)

    # 打印表格
    print("\n所有书源能力概览：")
    header = ["ID", "书源", "可搜索", "可获取目录", "结果数", "耗时(ms)"]
    print("-" * 80)
    print(
        f"{header[0]:<4} {header[1]:<16} {header[2]:<6} {header[3]:<10} {header[4]:<6} {header[5]:<6} "
    )
    print("-" * 80)
    for r in sorted(rows, key=lambda x: x["id"]):
        s = "OK" if r["search"] else "X"
        t = "OK" if r["toc"] else "X"

        print(
            f"{r['id']:<4} {r['name']:<16} {s:<6} {t:<10} {r['results']:<6} {r['time']:<9}"
        )
    print("-" * 80)

    return rows


async def main():
    args = build_args()

    # 配置日志级别
    _configure_logging(args.verbose)

    service = NovelService()

    # 首先输出所有书源能力表格（除非显式跳过）
    if not args.no_summary:
        await summarize_all_sources(
            service,
            args.keyword,
            max_results=args.max_results,
            test_toc=True,
            quiet=not args.verbose,
        )
        if args.summary_only:
            print("\n(仅输出汇总表格，已结束)\n")
            return

    # 解析目标书源
    target_source_id = None
    if args.source_id is not None:
        target_source_id = args.source_id
    elif args.source_name:
        # 简单模糊匹配名称 -> 取第一个
        for sid, src in service.sources.items():
            name = src.rule.get("name", str(sid))
            if args.source_name in name:
                target_source_id = sid
                break
        if target_source_id is None:
            raise ValueError(f"未找到匹配的书源名称: {args.source_name}")

    print("=" * 80)
    print(f"关键词: {args.keyword}")
    if target_source_id is not None:
        print(
            f"指定书源: {service.sources[target_source_id].rule.get('name', target_source_id)} (ID: {target_source_id})"
        )
    else:
        print("跨书源搜索模式")
    print("=" * 80)

    # 执行搜索
    if target_source_id is not None:
        results, elapsed_ms, source_name = await search_in_specific_source(
            service, target_source_id, args.keyword
        )
        print(f"搜索完成（{source_name}）：{len(results)} 条，用时 {elapsed_ms:.0f} ms")
    else:
        results, elapsed_ms = await search_across_sources(
            service, args.keyword, args.max_results
        )
        print(f"搜索完成（跨书源）：{len(results)} 条，用时 {elapsed_ms:.0f} ms")

    if not results:
        print("未找到任何结果")
        return

    print("\n前N条结果：")
    for i, r in enumerate(results[: args.max_results]):
        # SearchResult 是 pydantic BaseModel
        try:
            title = getattr(r, "title", "N/A")
            author = getattr(r, "author", "N/A")
            url = getattr(r, "url", "")
            src_id = getattr(r, "source_id", 0)
            src_name = getattr(r, "source_name", "")
            print(
                f"  {i+1}. {title} - {author} [{src_name or 'N/A'}#{src_id}]\n     {url}"
            )
        except Exception as e:
            print(f"  {i+1}. 解析结果失败: {e}")

    # 选定用于详情/目录/下载的目标结果
    chosen = results[0]
    book_url = getattr(chosen, "url", "")
    book_source_id = getattr(chosen, "source_id", target_source_id or 0)
    book_source_name = getattr(chosen, "source_name", "")

    if not book_url or not book_source_id:
        print("无法解析到有效的详情URL或书源ID，跳过详情/目录/下载")
        return

    print("\n" + "-" * 80)
    print(f"详情与目录（来源：{book_source_name or book_source_id}）")
    # 获取详情
    detail_start = time.time()
    book = await service.get_book_detail(book_url, book_source_id)
    detail_ms = (time.time() - detail_start) * 1000
    if book:
        print(f"获取详情成功，用时 {detail_ms:.0f} ms")
        # 书名兜底：详情页缺失时回退为搜索结果标题
        fallback_title = getattr(chosen, "title", "N/A")
        book_title = getattr(book, "name", "") or fallback_title
        print(f"   书名: {book_title}  作者: {getattr(book, 'author', 'N/A')}")
        intro = getattr(book, "intro", "") or ""
        if intro:
            intro_short = intro.strip().replace("\n", " ")[:100]
            print(f"   简介: {intro_short}{'...' if len(intro) > 100 else ''}")
    else:
        print(f"获取详情失败，用时 {detail_ms:.0f} ms")

    # 获取目录
    toc_start = time.time()
    toc = await service.get_toc(book_url, book_source_id)
    toc_ms = (time.time() - toc_start) * 1000
    print(f"目录章节: {len(toc)} 条，用时 {toc_ms:.0f} ms")
    for i, ch in enumerate(toc[: args.show_toc]):
        try:
            print(
                f"   - {i+1}. {getattr(ch, 'title', 'N/A')}  ({getattr(ch, 'url', '')})"
            )
        except Exception:
            pass

    print("\n" + "=" * 80)
    print("测试完成")

    # 优雅关闭全局HTTP客户端，避免未关闭的session/connector告警
    try:
        await service.http_client.shutdown()
    except Exception:
        pass


if __name__ == "__main__":
    asyncio.run(main())
