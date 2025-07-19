#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的测试运行脚本
"""

import sys
import os
import subprocess

def run_tests():
    """运行测试"""
    print("🧪 开始运行测试...")
    
    # 检查pytest是否安装
    try:
        import pytest
        print("✅ pytest已安装")
    except ImportError:
        print("❌ pytest未安装，正在安装...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pytest", "pytest-asyncio"])
    
    # 运行测试
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"
        ], capture_output=True, text=True)
        
        print("📋 测试输出:")
        print(result.stdout)
        
        if result.stderr:
            print("⚠️  警告信息:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("🎉 所有测试通过！")
        else:
            print("❌ 部分测试失败")
            
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ 测试运行失败: {e}")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1) 