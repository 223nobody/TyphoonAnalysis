"""
测试中文数字转阿拉伯数字功能
"""
from app.api.asr import chinese_to_number, convert_chinese_numbers_in_text


def test_chinese_to_number():
    """测试单个中文数字转换"""
    test_cases = [
        ("二", 2),
        ("十", 10),
        ("一百", 100),
        ("一百二十三", 123),
        ("二零零零", 2000),
        ("二〇二四", 2024),
        ("一万", 10000),
        ("十二", 12),
        ("二十", 20),
        ("三十五", 35),
        ("九十九", 99),
        ("一千零一", 1001),
        ("一万二千三百四十五", 12345),
        ("零五二零", 520),  # 注意：前导零会被去掉
    ]
    
    print("=" * 60)
    print("测试中文数字转阿拉伯数字")
    print("=" * 60)
    
    for cn, expected in test_cases:
        result = chinese_to_number(cn)
        status = "✅" if result == expected else "❌"
        print(f"{status} {cn:15s} -> {result:10} (期望: {expected})")


def test_convert_in_text():
    """测试文本中的数字转换"""
    test_cases = [
        ("二零零零年有哪些台风？", "2000年有哪些台风？"),
        ("二〇二四年台风情况如何？", "2024年台风情况如何？"),
        ("请查询一九九九年的数据", "请查询1999年的数据"),
        ("第三号台风在哪里？", "第3号台风在哪里？"),
        ("一百二十个台风", "120个台风"),
        ("风速达到二十五米每秒", "风速达到25米每秒"),
        ("二零二三年有十个台风", "2023年有10个台风"),
        ("零五二零是什么日子", "520是什么日子"),  # 前导零会被去掉
    ]
    
    print("\n" + "=" * 60)
    print("测试文本中的数字转换")
    print("=" * 60)
    
    for input_text, expected in test_cases:
        result = convert_chinese_numbers_in_text(input_text)
        status = "✅" if result == expected else "❌"
        print(f"\n{status} 输入: {input_text}")
        print(f"   输出: {result}")
        if result != expected:
            print(f"   期望: {expected}")


if __name__ == "__main__":
    test_chinese_to_number()
    test_convert_in_text()
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
