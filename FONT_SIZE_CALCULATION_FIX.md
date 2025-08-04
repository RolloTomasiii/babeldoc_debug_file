# BabelDoc字体大小计算错误问题修复方案

## 问题确认：字体映射失败后的字体大小计算错误

用户观察非常精准：**不兼容字体使用默认字体后，font-size计算逻辑出现严重错误**。

### 🎯 问题分析

#### 根本原因链条
```
原始字体（如Arial，0.8点）
    ↓ 字体提取失败
字体属性设为None 
    ↓ 字体映射失败
返回None或使用base font
    ↓ 保留原始font_size值
使用新字体但保留旧字体大小
    ↓ char_lengths计算错误
实际显示字体异常小（视觉效果2/3大小，font_size值却小几倍）
```

#### 关键问题代码位置

1. **字体映射失败** (`fontmap.py:224`)
```python
logger.warning(f"Can't find font for {char_unicode}...")
return None  # ← 问题：返回None导致后续处理异常
```

2. **TypesettingUnit过滤** (`typesetting.py:1427`)
```python
result = list(filter(
    lambda x: x.unicode is None or x.font is not None,  # ← 过滤掉font=None的单元
    result,
))
```

3. **字体大小计算** (`typesetting.py:453`)
```python
char_width = self.font.char_lengths(self.unicode, self.font_size)[0]
# ← 问题：使用新字体但保留原字体大小
```

### 🔧 修复方案

#### 1. 改进字体映射回退机制

修改`fontmap.py`，确保总是返回有效字体：

```python
def map(self, original_font: PdfFont, char_unicode: str):
    # ... 现有映射逻辑 ...
    
    # 最终回退：使用base font
    if self.base_font.has_glyph(current_char):
        logger.debug(f"使用base font作为回退: {char_unicode}")
        return self.base_font
    
    # 如果连base font都不支持，使用第一个可用字体
    for font in self.fonts.values():
        if font.has_glyph(current_char):
            logger.warning(f"使用任意可用字体作为最终回退: {char_unicode} -> {font.font_id}")
            return font
    
    # 极端情况：返回base font即使不支持该字符
    logger.error(f"无任何字体支持字符 {char_unicode}，强制使用base font")
    return self.base_font
```

#### 2. 实现字体大小缩放补偿

当字体映射发生时，需要根据字体特征调整字体大小：

```python
def calculate_font_size_compensation(self, original_font, mapped_font, original_size):
    """计算字体映射后的大小补偿"""
    if not original_font or not mapped_font:
        return original_size
    
    # 基于字体特征计算补偿系数
    try:
        # 使用标准字符测试两种字体的实际尺寸比例
        test_char = "A"
        original_width = original_font.char_lengths(test_char, 100)[0] if hasattr(original_font, 'char_lengths') else 100
        mapped_width = mapped_font.char_lengths(test_char, 100)[0]
        
        # 计算宽度比例作为补偿基础
        width_ratio = original_width / mapped_width if mapped_width > 0 else 1.0
        
        # 限制补偿范围，避免过度调整
        compensation = max(0.5, min(2.0, width_ratio))
        
        adjusted_size = original_size * compensation
        
        logger.debug(
            f"字体大小补偿: {original_font.name} -> {mapped_font.font_id}, "
            f"原始大小: {original_size:.3f}, 补偿系数: {compensation:.3f}, "
            f"调整后: {adjusted_size:.3f}"
        )
        
        return adjusted_size
        
    except Exception as e:
        logger.warning(f"字体大小补偿计算失败: {e}, 使用原始大小")
        return original_size
```

#### 3. 修改TypesettingUnit创建逻辑

```python
def create_typesetting_units(self, paragraph, fonts):
    # ... 现有代码 ...
    
    for char_unicode in composition.pdf_same_style_unicode_characters.unicode:
        original_font = get_font(font_id, paragraph.xobj_id)
        mapped_font = self.font_mapper.map(original_font, char_unicode)
        
        # 确保mapped_font不为None
        if mapped_font is None:
            logger.warning(f"字体映射失败，使用base font: {char_unicode}")
            mapped_font = self.font_mapper.base_font
        
        # 计算补偿后的字体大小
        compensated_size = self.font_mapper.calculate_font_size_compensation(
            original_font, mapped_font, style.font_size
        )
        
        result.append(TypesettingUnit(
            unicode=char_unicode,
            font=mapped_font,
            original_font=original_font,
            font_size=compensated_size,  # ← 使用补偿后的大小
            style=style,
            xobj_id=paragraph.xobj_id,
            debug_info=debug_info,
        ))
```

#### 4. 增强调试信息

```python
def validate_font_size_calculation(self, typesetting_units):
    """验证字体大小计算的合理性"""
    for unit in typesetting_units:
        if unit.unicode and unit.font:
            expected_width = unit.font.char_lengths(unit.unicode, unit.font_size)[0]
            actual_width = unit.width
            
            if abs(expected_width - actual_width) > 0.1:
                logger.warning(
                    f"字体大小计算异常: {unit.unicode}, "
                    f"期望宽度: {expected_width:.3f}, 实际宽度: {actual_width:.3f}, "
                    f"字体: {unit.font.font_id}, 大小: {unit.font_size:.3f}"
                )
```

### 🎯 关键修复点

1. **确保字体映射永不返回None**
2. **实现字体大小补偿机制**
3. **基于字体特征调整font_size值**
4. **保持视觉效果与数值的一致性**

### 📊 预期效果

1. **视觉一致性**：映射后字体的视觉大小与原始字体接近
2. **数值准确性**：font_size值反映实际的视觉效果
3. **兼容性**：不影响正常字体的处理
4. **可调试性**：提供详细的字体映射和大小调整日志

这个修复方案直接解决了用户发现的核心问题：**字体映射后的font_size计算错误**。