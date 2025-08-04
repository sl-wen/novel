#!/usr/bin/env python3
"""
修复bookName属性问题
确保SearchResult对象正确支持bookName属性
"""

import sys
import os
from pathlib import Path

def fix_search_result_model():
    """修复SearchResult模型"""
    print("🔧 修复SearchResult模型...")
    
    model_file = Path("app/models/search.py")
    if not model_file.exists():
        print("❌ 找不到SearchResult模型文件")
        return False
    
    # 创建修复后的模型内容
    fixed_content = '''import logging
from typing import List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SearchResult(BaseModel):
    """搜索结果模型"""

    title: str = Field(..., description="书名")
    author: str = Field(default="", description="作者")
    intro: str = Field(default="", description="简介")
    cover: str = Field(default="", description="封面")
    url: str = Field(..., description="链接")
    category: str = Field(default="", description="分类")
    status: str = Field(default="", description="状态")
    word_count: str = Field(default="", description="字数")
    update_time: str = Field(default="", description="更新时间")
    latest_chapter: str = Field(default="", description="最新章节")
    source_id: int = Field(default=0, description="书源ID")
    source_name: str = Field(default="", description="书源名称")
    score: float = Field(default=0.0, description="相关性得分")

    def model_post_init(self, __context) -> None:
        """模型初始化后的处理"""
        # 确保向后兼容性
        if hasattr(self, 'title') and self.title:
            # 动态添加bookName属性以保持兼容性
            object.__setattr__(self, 'bookName', self.title)

    def __getattr__(self, name):
        """动态属性访问，支持bookName等旧属性名"""
        if name == 'bookName':
            return self.title
        elif name == 'sourceId':
            return self.source_id
        elif name == 'sourceName':
            return self.source_name
        elif name == 'latestChapter':
            return self.latest_chapter
        elif name == 'lastUpdateTime':
            return self.update_time
        elif name == 'wordCount':
            return self.word_count
        elif name == 'coverUrl':
            return self.cover
        else:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def model_dump(self, **kwargs):
        """自定义序列化，包含兼容性字段"""
        data = super().model_dump(**kwargs)
        # 添加兼容性字段
        data['bookName'] = self.title
        data['sourceId'] = self.source_id
        data['sourceName'] = self.source_name
        data['latestChapter'] = self.latest_chapter
        data['lastUpdateTime'] = self.update_time
        data['wordCount'] = self.word_count
        data['coverUrl'] = self.cover
        return data


class SearchResponse(BaseModel):
    """搜索响应模型"""

    code: int = 200
    message: str = "success"
    data: List[SearchResult] = []
'''
    
    # 备份原文件
    backup_file = model_file.with_suffix(".py.backup")
    with open(model_file, "r", encoding="utf-8") as f:
        original_content = f.read()
    with open(backup_file, "w", encoding="utf-8") as f:
        f.write(original_content)
    
    # 写入修复后的内容
    with open(model_file, "w", encoding="utf-8") as f:
        f.write(fixed_content)
    
    print(f"✅ SearchResult模型已修复，原文件备份到: {backup_file}")
    return True

def create_test_script():
    """创建测试脚本"""
    print("🔧 创建测试脚本...")
    
    test_script = '''#!/usr/bin/env python3
"""
测试SearchResult的bookName属性
"""

import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

def test_search_result():
    """测试SearchResult模型"""
    print("🔍 测试SearchResult模型...")
    
    try:
        from app.models.search import SearchResult
        
        # 创建SearchResult对象
        result = SearchResult(
            title="斗破苍穹",
            author="天蚕土豆",
            url="http://example.com/book/1",
            source_id=1,
            source_name="测试书源"
        )
        
        print(f"✅ SearchResult创建成功")
        print(f"   - title: {result.title}")
        print(f"   - author: {result.author}")
        
        # 测试bookName属性访问
        try:
            book_name = result.bookName
            print(f"✅ bookName属性访问成功: {book_name}")
        except AttributeError as e:
            print(f"❌ bookName属性访问失败: {str(e)}")
            return False
        
        # 测试序列化
        try:
            data = result.model_dump()
            print(f"✅ 序列化成功")
            print(f"   - bookName在序列化数据中: {'bookName' in data}")
            if 'bookName' in data:
                print(f"   - bookName值: {data['bookName']}")
        except Exception as e:
            print(f"❌ 序列化失败: {str(e)}")
            return False
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        print(f"详细错误:\\n{traceback.format_exc()}")
        return False

async def test_search_service():
    """测试搜索服务"""
    print("\\n🔍 测试搜索服务...")
    
    try:
        from app.services.novel_service import NovelService
        
        service = NovelService()
        results = await service.search("斗破苍穹", max_results=3)
        print(f"✅ 搜索成功，找到 {len(results)} 条结果")
        
        if results:
            first_result = results[0]
            print(f"   - 第一个结果类型: {type(first_result)}")
            
            # 测试属性访问
            try:
                title = first_result.title
                print(f"   - ✅ title: {title}")
            except AttributeError as e:
                print(f"   - ❌ title访问失败: {str(e)}")
            
            try:
                book_name = first_result.bookName
                print(f"   - ✅ bookName: {book_name}")
            except AttributeError as e:
                print(f"   - ❌ bookName访问失败: {str(e)}")
                return False
            
            try:
                author = first_result.author
                print(f"   - ✅ author: {author}")
            except AttributeError as e:
                print(f"   - ❌ author访问失败: {str(e)}")
        
        return True
    except Exception as e:
        print(f"❌ 搜索服务测试失败: {str(e)}")
        import traceback
        print(f"详细错误:\\n{traceback.format_exc()}")
        return False

async def main():
    """主函数"""
    print("🚀 SearchResult bookName属性测试")
    print("=" * 50)
    
    # 测试模型
    model_ok = test_search_result()
    
    # 测试搜索服务
    service_ok = await test_search_service()
    
    # 总结
    print("\\n" + "=" * 50)
    print("📊 测试总结:")
    print(f"  模型测试: {'✅ 通过' if model_ok else '❌ 失败'}")
    print(f"  搜索服务: {'✅ 通过' if service_ok else '❌ 失败'}")
    
    if model_ok and service_ok:
        print("\\n🎉 所有测试通过！")
    else:
        print("\\n⚠️  存在问题，请检查错误信息")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
'''
    
    with open("test_bookname_fix.py", "w", encoding="utf-8") as f:
        f.write(test_script)
    
    print("✅ 测试脚本已创建: test_bookname_fix.py")

def main():
    """主函数"""
    print("🔧 修复SearchResult的bookName属性问题")
    print("=" * 50)
    
    # 修复SearchResult模型
    if fix_search_result_model():
        print("✅ SearchResult模型修复完成")
    else:
        print("❌ SearchResult模型修复失败")
        return
    
    # 创建测试脚本
    create_test_script()
    
    print("\n🎉 修复完成！")
    print("📋 接下来的步骤:")
    print("1. 测试修复: python test_bookname_fix.py")
    print("2. 重启API服务: python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    print("3. 测试API: python test_api_search.py")
    
    print("\n💡 修复说明:")
    print("- 添加了__getattr__方法支持bookName等旧属性名")
    print("- 在model_dump中包含兼容性字段")
    print("- 使用model_post_init确保属性正确设置")

if __name__ == "__main__":
    main()