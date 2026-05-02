"""
字符串工具函数模块

提供常用的字符串处理函数，包括回文判断和字符串反转。
"""

import re


def is_palindrome(s: str) -> bool:
    """
    判断给定字符串是否为回文串。

    回文定义：从左到右读与从右到左读完全一致的字符串。
    判断规则：
    1. 大小写不敏感
    2. 仅检测字母数字字符，忽略空格、标点、特殊字符
    3. 空字符串视为回文

    参数:
        s (str): 待检测的字符串

    返回:
        bool: 是回文返回 True，否则返回 False

    示例:
        >>> is_palindrome("")
        True
        >>> is_palindrome("aba")
        True
        >>> is_palindrome("Abba")
        True
        >>> is_palindrome("a man a plan a canal Panama")
        True
        >>> is_palindrome("abc")
        False
    """
    # 过滤出字母数字字符，并转为小写
    filtered = re.sub(r'[^a-zA-Z0-9]', '', s).lower()
    return filtered == filtered[::-1]


def reverse_string(s: str) -> str:
    """
    反转给定字符串。

    逐字符反转，包括空格和特殊字符。
    返回新字符串，不修改原字符串。

    参数:
        s (str): 待反转的字符串

    返回:
        str: 反转后的新字符串

    示例:
        >>> reverse_string("")
        ''
        >>> reverse_string("abc")
        'cba'
        >>> reverse_string("racecar")
        'racecar'
        >>> reverse_string("hello world")
        'dlrow olleh'
    """
    return s[::-1]
