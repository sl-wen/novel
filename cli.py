#!/usr/bin/env python3
"""Novel CLI - 小说搜索与下载命令行工具"""

import asyncio
import os
import sys
import time

import click


def get_service():
    """延迟初始化 NovelService，避免 import 时触发不需要的依赖"""
    from app.services.novel_service import NovelService
    return NovelService()


@click.group()
@click.version_option(version="1.0.0", prog_name="novel-cli")
def cli():
    """📖 小说搜索与下载 CLI"""
    pass


@cli.command()
@click.argument("keyword")
@click.option("-n", "--max-results", default=20, help="最大返回结果数", show_default=True)
def search(keyword: str, max_results: int):
    """搜索小说

    示例: novel search "斗破苍穹"
    """
    click.echo(f"🔍 搜索: {keyword} ...\n")
    service = get_service()
    start = time.time()

    results = asyncio.run(service.search(keyword, max_results=max_results))
    elapsed = time.time() - start

    if not results:
        click.echo("❌ 未找到结果")
        return

    click.echo(f"找到 {len(results)} 条结果 (耗时 {elapsed:.1f}s)\n")

    for i, r in enumerate(results, 1):
        title = r.title or "未知"
        author = r.author or "未知"
        source_name = getattr(r, "sourceName", "") or getattr(r, "source_name", "") or ""
        source_id = getattr(r, "sourceId", None) or getattr(r, "source_id", None) or ""
        url = r.url or ""
        chapters = getattr(r, "chapterCount", None)

        chapter_info = f", {chapters}章" if chapters else ""
        click.echo(f"  {i:>3}. 📖 {title} - {author}{chapter_info}")
        click.echo(f"       书源: {source_name} (ID:{source_id})")
        click.echo(f"       URL:  {url}")
        click.echo()

    click.echo(f"💡 下载: novel download <URL> -s <书源ID>")


@cli.command()
@click.argument("url")
@click.option("-s", "--source-id", required=True, type=int, help="书源ID")
@click.option("-o", "--output", default=".", help="输出目录", show_default=True)
@click.option("-f", "--format", "fmt", default="txt", help="输出格式 (txt/epub)", show_default=True)
def download(url: str, source_id: int, output: str, fmt: str):
    """下载小说

    示例: novel download "https://xxx.com/book/123" -s 1 -o ~/Downloads
    """
    if fmt not in ("txt", "epub"):
        click.echo(f"❌ 不支持格式: {fmt}，仅支持 txt/epub")
        return

    click.echo(f"📥 开始下载...")
    click.echo(f"   URL: {url}")
    click.echo(f"   书源ID: {source_id}")
    click.echo(f"   格式: {fmt}")
    click.echo()

    service = get_service()
    start = time.time()

    try:
        file_path = asyncio.run(service.download(url, source_id, format=fmt))

        if not file_path or not os.path.exists(file_path):
            click.echo("❌ 下载失败: 文件未生成")
            sys.exit(1)

        # 移动到输出目录
        if output != ".":
            os.makedirs(output, exist_ok=True)
            import shutil
            dest = os.path.join(output, os.path.basename(file_path))
            shutil.move(file_path, dest)
            file_path = dest

        elapsed = time.time() - start
        file_size = os.path.getsize(file_path)
        size_mb = file_size / (1024 * 1024)

        click.echo(f"\n✅ 下载完成!")
        click.echo(f"   文件: {file_path}")
        click.echo(f"   大小: {size_mb:.2f} MB")
        click.echo(f"   耗时: {elapsed:.1f}s")

    except KeyboardInterrupt:
        click.echo("\n⚠️ 下载已取消")
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ 下载失败: {str(e)}")
        sys.exit(1)


@cli.command()
def sources():
    """列出所有书源"""
    service = get_service()
    result = asyncio.run(service.get_sources())

    if not result:
        click.echo("❌ 没有可用的书源")
        return

    click.echo(f"📚 共 {len(result)} 个书源\n")

    search_count = 0
    download_count = 0

    for s in result:
        sid = s.get("id", "?")
        name = s.get("name", "未知")
        url = s.get("url", "")
        search_ok = "✅" if s.get("search_enabled") else "❌"
        download_ok = "✅" if s.get("download_enabled") else "❌"
        enabled = "🟢" if s.get("enabled", True) else "🔴"

        if s.get("search_enabled"):
            search_count += 1
        if s.get("download_enabled"):
            download_count += 1

        click.echo(f"  {enabled} ID:{sid:>3}  {name}")
        click.echo(f"         搜索:{search_ok}  下载:{download_ok}  {url}")

    click.echo(f"\n  可搜索: {search_count}  可下载: {download_count}")


if __name__ == "__main__":
    cli()
