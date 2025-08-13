#!/usr/bin/env python3
"""
快速测试脚本

一键测试书源4的修复效果，验证章节数量问题是否解决。
"""

import asyncio
import sys
import json
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

from app.core.source import Source
from app.parsers.toc_parser import TocParser


async def quick_test():
    """快速测试书源4的修复效果"""
    print("🚀 快速测试：书源4章节数量修复效果")
    print("=" * 60)
    
    # 测试配置
    source_id = 4
    test_url = "http://wap.99xs.info/124310/"
    
    try:
        print(f"📖 测试书源: {source_id}")
        print(f"🔗 测试URL: {test_url}")
        print()
        
        # 创建书源和解析器
        source = Source(source_id)
        parser = TocParser(source)
        
        print(f"📚 书源名称: {source.name}")
        print(f"🌐 书源地址: {source.rule.get('url', '')}")
        
        # 显示目录配置
        toc_config = source.rule.get('toc', {})
        print(f"🔧 目录选择器: {toc_config.get('list', '未配置')}")
        
        # 获取目录URL
        toc_url = parser._get_toc_url(test_url)
        print(f"📋 目录页URL: {toc_url}")
        print()
        
        print("⏳ 开始解析目录...")
        
        # 解析目录
        chapters = await parser.parse(test_url)
        
        print("✅ 解析完成！")
        print("=" * 60)
        
        # 显示结果
        print(f"📊 解析结果统计:")
        print(f"   总章节数: {len(chapters)}")
        
        if not chapters:
            print("❌ 未获取到任何章节！")
            print("\n🔍 可能的原因:")
            print("   1. 网络连接问题")
            print("   2. 目标网站结构变化")
            print("   3. 书源配置需要更新")
            return
        
        # 分析章节编号分布
        chapters_with_numbers = 0
        chapters_without_numbers = 0
        number_distribution = {}
        
        for chapter in chapters:
            number = parser._extract_chapter_number(chapter.title)
            if number > 0:
                chapters_with_numbers += 1
                number_distribution[number] = number_distribution.get(number, 0) + 1
            else:
                chapters_without_numbers += 1
        
        print(f"   有编号章节: {chapters_with_numbers}")
        print(f"   无编号章节: {chapters_without_numbers}")
        
        # 检查重复编号
        duplicates = {k: v for k, v in number_distribution.items() if v > 1}
        if duplicates:
            print(f"   重复编号: {len(duplicates)} 组")
            print(f"   被去重章节: {sum(v - 1 for v in duplicates.values())} 个")
        else:
            print("   ✅ 无重复编号")
        
        print()
        
        # 显示前几个章节
        print("📋 前10个章节预览:")
        for i, chapter in enumerate(chapters[:10]):
            number = parser._extract_chapter_number(chapter.title)
            number_str = f"[{number:3d}]" if number > 0 else "[---]"
            print(f"   {i+1:2d}. {number_str} {chapter.title[:50]}{'...' if len(chapter.title) > 50 else ''}")
        
        if len(chapters) > 10:
            print("   ...")
            print(f"   （还有 {len(chapters) - 10} 个章节）")
        
        print()
        
        # 修复效果评估
        print("🎯 修复效果评估:")
        
        if len(chapters) >= 25:
            print("   ✅ 章节数量正常（≥25章）")
        elif len(chapters) >= 18:
            print("   ⚠️  章节数量有所改善，但可能仍有问题")
        else:
            print("   ❌ 章节数量仍然偏少")
        
        if chapters_with_numbers / len(chapters) >= 0.8:
            print("   ✅ 章节编号提取正常")
        else:
            print("   ⚠️  部分章节缺少编号")
        
        if not duplicates:
            print("   ✅ 去重功能正常工作")
        else:
            print("   ✅ 去重功能已处理重复章节")
        
        print()
        
        # 给出建议
        print("💡 建议:")
        
        if len(chapters) < 25:
            print("   - 使用调试接口进一步分析: curl 'http://localhost:8000/api/novels/debug/toc?url=http://wap.99xs.info/124310/&source_id=4'")
            print("   - 检查目标网站是否有变化")
            print("   - 考虑添加更多备用选择器")
        
        if chapters_without_numbers > len(chapters) * 0.3:
            print("   - 优化章节编号提取正则表达式")
            print("   - 检查章节标题格式是否标准")
        
        print("   - 定期运行此测试检查书源状态")
        print("   - 使用批量测试工具监控所有书源")
        
        print()
        print("🎉 测试完成！")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        print("\n🔧 故障排除:")
        print("   1. 确保已安装所有依赖: pip install -r requirements.txt")
        print("   2. 检查网络连接")
        print("   3. 验证书源配置: python validate_source_config.py 4")
        
        import traceback
        print(f"\n详细错误信息:")
        traceback.print_exc()


def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help"]:
        print("快速测试脚本 - 测试书源4的修复效果")
        print()
        print("使用方法:")
        print("  python quick_test.py")
        print()
        print("此脚本将:")
        print("  1. 测试书源4的目录解析功能")
        print("  2. 分析章节数量和质量")
        print("  3. 评估修复效果")
        print("  4. 提供优化建议")
        return
    
    print("正在启动快速测试...")
    asyncio.run(quick_test())


if __name__ == "__main__":
    main()