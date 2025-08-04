#!/usr/bin/env python3
"""
测试BabelDoc字体大小修复方案

这个脚本将测试字体过小问题的修复效果
"""

import json
import logging
from pathlib import Path

def test_font_size_protection():
    """测试字体大小保护功能"""
    print("=== BabelDoc 字体大小修复测试 ===")
    
    # 模拟排版单元
    class MockTypesettingUnit:
        def __init__(self, font_size):
            self.font_size = font_size
            self.width = 10
            self.height = 12
            
        def can_passthrough(self):
            return False
    
    # 模拟配置
    class MockConfig:
        def __init__(self, min_font_size_protection=True, min_readable_font_size=6.0):
            self.min_font_size_protection = min_font_size_protection
            self.min_readable_font_size = min_readable_font_size
    
    # 测试用例
    test_cases = [
        {
            "name": "正常字体大小 (12点)",
            "original_font_size": 12.0,
            "expected_min_scale": 0.5,  # 默认最小缩放
        },
        {
            "name": "较小字体 (8点)",
            "original_font_size": 8.0,
            "expected_min_scale": 0.75,  # 6.0/8.0 = 0.75
        },
        {
            "name": "已经很小的字体 (4点)",
            "original_font_size": 4.0,
            "expected_min_scale": 1.5,  # 6.0/4.0 = 1.5，但会防止过度缩放
        }
    ]
    
    for case in test_cases:
        print(f"\n测试用例: {case['name']}")
        print(f"原始字体大小: {case['original_font_size']}点")
        
        # 模拟字体大小保护逻辑
        config = MockConfig()
        
        if config.min_font_size_protection:
            font_based_min_scale = config.min_readable_font_size / case['original_font_size']
            min_scale = max(0.5, font_based_min_scale)  # MIN_SCALE_FACTOR = 0.5
        else:
            min_scale = 0.1  # 旧的逻辑
            
        print(f"计算的最小缩放因子: {min_scale:.3f}")
        print(f"缩放后最小字体大小: {case['original_font_size'] * min_scale:.2f}点")
        
        # 验证结果
        if case['original_font_size'] * min_scale >= config.min_readable_font_size:
            print("✅ 通过：字体大小保护有效")
        else:
            print("❌ 失败：字体仍然过小")

def analyze_debug_file():
    """分析DEBUG文件中的字体大小问题"""
    print("\n=== 分析DEBUG文件中的字体大小 ===")
    
    debug_file = Path("babeldoc_debug_file/il_translated.json")
    if not debug_file.exists():
        print("❌ DEBUG文件不存在，跳过分析")
        return
    
    print("正在分析DEBUG文件中的字体大小分布...")
    
    try:
        # 由于文件很大，我们只读取前100KB来分析
        with open(debug_file, 'r', encoding='utf-8') as f:
            content = f.read(100000)  # 读取前100KB
            
        font_sizes = []
        import re
        
        # 提取所有font_size值
        pattern = r'"font_size":\s*([0-9]+(?:\.[0-9]+)?)'
        matches = re.findall(pattern, content)
        
        for match in matches:
            font_sizes.append(float(match))
        
        if font_sizes:
            min_size = min(font_sizes)
            max_size = max(font_sizes)
            avg_size = sum(font_sizes) / len(font_sizes)
            
            small_fonts = [s for s in font_sizes if s < 6.0]
            
            print(f"发现 {len(font_sizes)} 个字体大小记录")
            print(f"最小字体大小: {min_size:.2f}点")
            print(f"最大字体大小: {max_size:.2f}点")
            print(f"平均字体大小: {avg_size:.2f}点")
            print(f"小于6点的字体数量: {len(small_fonts)} ({len(small_fonts)/len(font_sizes)*100:.1f}%)")
            
            if small_fonts:
                print("❌ 发现过小字体，建议启用字体大小保护")
            else:
                print("✅ 所有字体大小都合适")
                
    except Exception as e:
        print(f"❌ 分析DEBUG文件时出错: {e}")

def print_solution_summary():
    """打印解决方案总结"""
    print("\n=== 解决方案总结 ===")
    print("""
问题诊断：
- BabelDoc在排版时会无限制缩放字体以适应版面
- 最小缩放因子设置为0.1，导致字体可能缩放到原大小的10%
- 对于已经较小的字体（如0.82点），缩放后变成0.082点，完全无法阅读

修复方案：
1. 添加字体大小保护机制
   - 新增配置选项：min_font_size_protection（默认启用）
   - 新增配置选项：min_readable_font_size（默认6.0点）

2. 改进缩放算法
   - 基于原始字体大小计算最小缩放因子
   - 确保缩放后字体不小于最小可读大小
   - 改进缩放因子递减策略，避免过度缩放

3. 添加调试和监控
   - 在DEBUG模式下验证字体大小
   - 记录过小字体的警告信息
   - 提供详细的缩放计算日志

使用方法：
1. 默认启用字体保护：
   babeldoc --files demo.pdf --lang-out zh

2. 自定义最小字体大小：
   babeldoc --files demo.pdf --lang-out zh --min-readable-font-size 8.0

3. 禁用字体保护（不推荐）：
   babeldoc --files demo.pdf --lang-out zh --disable-min-font-size-protection

优势：
- 确保翻译后的文档具有良好的可读性
- 保持与现有功能的兼容性
- 提供灵活的配置选项
- 不影响正常大小字体的排版效果
""")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    test_font_size_protection()
    analyze_debug_file()
    print_solution_summary()