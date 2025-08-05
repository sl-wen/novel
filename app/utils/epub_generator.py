import os
import zipfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import logging
from xml.sax.saxutils import escape

from app.models.book import Book
from app.models.chapter import Chapter

logger = logging.getLogger(__name__)


class EPUBGenerator:
    """EPUB电子书生成器"""
    
    def __init__(self):
        self.uuid = str(uuid.uuid4())
        self.creation_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    def generate(self, book: Book, chapters: List[Chapter], output_path: str) -> str:
        """
        生成EPUB文件
        
        Args:
            book: 书籍信息
            chapters: 章节列表
            output_path: 输出文件路径
            
        Returns:
            生成的EPUB文件路径
        """
        try:
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as epub_zip:
                # 1. 添加mimetype文件
                self._add_mimetype(epub_zip)
                
                # 2. 添加META-INF/container.xml
                self._add_container_xml(epub_zip)
                
                # 3. 添加内容文件
                self._add_content_opf(epub_zip, book, chapters)
                
                # 4. 添加目录文件
                self._add_toc_ncx(epub_zip, book, chapters)
                
                # 5. 添加章节HTML文件
                self._add_chapter_files(epub_zip, chapters)
                
                # 6. 添加样式文件
                self._add_stylesheet(epub_zip)
            
            logger.info(f"EPUB文件生成成功: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"生成EPUB文件失败: {str(e)}")
            raise
    
    def _add_mimetype(self, epub_zip: zipfile.ZipFile):
        """添加mimetype文件"""
        epub_zip.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
    
    def _add_container_xml(self, epub_zip: zipfile.ZipFile):
        """添加META-INF/container.xml"""
        container_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>'''
        epub_zip.writestr("META-INF/container.xml", container_xml)
    
    def _add_content_opf(self, epub_zip: zipfile.ZipFile, book: Book, chapters: List[Chapter]):
        """添加内容描述文件"""
        # 生成manifest项目
        manifest_items = ['<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>']
        manifest_items.append('<item id="css" href="stylesheet.css" media-type="text/css"/>')
        
        for i, chapter in enumerate(chapters, 1):
            chapter_id = f"chapter{i:04d}"
            manifest_items.append(f'<item id="{chapter_id}" href="{chapter_id}.html" media-type="application/xhtml+xml"/>')
        
        # 生成spine项目
        spine_items = []
        for i in range(1, len(chapters) + 1):
            chapter_id = f"chapter{i:04d}"
            spine_items.append(f'<itemref idref="{chapter_id}"/>')
        
        content_opf = f'''<?xml version="1.0" encoding="UTF-8"?>
<package version="2.0" xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
        <dc:title>{escape(book.title)}</dc:title>
        <dc:creator opf:role="aut">{escape(book.author or "未知作者")}</dc:creator>
        <dc:description>{escape(book.description or "")}</dc:description>
        <dc:language>zh</dc:language>
        <dc:identifier id="BookId" opf:scheme="UUID">{self.uuid}</dc:identifier>
        <dc:date>{self.creation_date}</dc:date>
        <meta name="cover" content="cover"/>
    </metadata>
    <manifest>
        {chr(10).join(manifest_items)}
    </manifest>
    <spine toc="ncx">
        {chr(10).join(spine_items)}
    </spine>
</package>'''
        
        epub_zip.writestr("OEBPS/content.opf", content_opf)
    
    def _add_toc_ncx(self, epub_zip: zipfile.ZipFile, book: Book, chapters: List[Chapter]):
        """添加目录导航文件"""
        # 生成导航点
        nav_points = []
        for i, chapter in enumerate(chapters, 1):
            chapter_id = f"chapter{i:04d}"
            nav_points.append(f'''        <navPoint id="navPoint-{i}" playOrder="{i}">
            <navLabel>
                <text>{escape(chapter.title)}</text>
            </navLabel>
            <content src="{chapter_id}.html"/>
        </navPoint>''')
        
        toc_ncx = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
<ncx version="2005-1" xmlns="http://www.daisy.org/z3986/2005/ncx/">
    <head>
        <meta name="dtb:uid" content="{self.uuid}"/>
        <meta name="dtb:depth" content="1"/>
        <meta name="dtb:totalPageCount" content="0"/>
        <meta name="dtb:maxPageNumber" content="0"/>
    </head>
    <docTitle>
        <text>{escape(book.title)}</text>
    </docTitle>
    <navMap>
{chr(10).join(nav_points)}
    </navMap>
</ncx>'''
        
        epub_zip.writestr("OEBPS/toc.ncx", toc_ncx)
    
    def _add_chapter_files(self, epub_zip: zipfile.ZipFile, chapters: List[Chapter]):
        """添加章节HTML文件"""
        for i, chapter in enumerate(chapters, 1):
            chapter_id = f"chapter{i:04d}"
            
            # 清理和格式化章节内容
            content = self._format_chapter_content(chapter.content)
            
            chapter_html = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{escape(chapter.title)}</title>
    <link rel="stylesheet" type="text/css" href="stylesheet.css"/>
</head>
<body>
    <div class="chapter">
        <h1 class="chapter-title">{escape(chapter.title)}</h1>
        <div class="chapter-content">
            {content}
        </div>
    </div>
</body>
</html>'''
            
            epub_zip.writestr(f"OEBPS/{chapter_id}.html", chapter_html)
    
    def _format_chapter_content(self, content: str) -> str:
        """格式化章节内容"""
        if not content:
            return "<p>内容为空</p>"
        
        # 清理内容
        from app.utils.text_validator import TextValidator
        content = TextValidator.clean_text(content)
        
        # 转义HTML特殊字符
        content = escape(content)
        
        # 将换行转换为段落
        paragraphs = content.split('\n')
        formatted_paragraphs = []
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if paragraph:
                formatted_paragraphs.append(f"<p>{paragraph}</p>")
        
        return '\n'.join(formatted_paragraphs) if formatted_paragraphs else "<p>内容为空</p>"
    
    def _add_stylesheet(self, epub_zip: zipfile.ZipFile):
        """添加样式表文件"""
        css_content = '''/* EPUB样式表 */
body {
    font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "WenQuanYi Micro Hei", sans-serif;
    font-size: 16px;
    line-height: 1.8;
    margin: 0;
    padding: 20px;
    color: #333;
    background-color: #fff;
}

.chapter {
    max-width: 800px;
    margin: 0 auto;
}

.chapter-title {
    font-size: 24px;
    font-weight: bold;
    text-align: center;
    margin: 30px 0;
    padding: 20px 0;
    border-bottom: 2px solid #eee;
    color: #2c3e50;
}

.chapter-content {
    text-align: justify;
}

.chapter-content p {
    margin: 1em 0;
    text-indent: 2em;
    word-wrap: break-word;
}

.chapter-content p:first-child {
    margin-top: 0;
}

.chapter-content p:last-child {
    margin-bottom: 0;
}

/* 移动设备适配 */
@media screen and (max-width: 600px) {
    body {
        padding: 10px;
        font-size: 14px;
    }
    
    .chapter-title {
        font-size: 20px;
        margin: 20px 0;
    }
    
    .chapter-content p {
        text-indent: 1.5em;
    }
}'''
        
        epub_zip.writestr("OEBPS/stylesheet.css", css_content)