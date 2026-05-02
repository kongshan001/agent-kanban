"""
字符串工具函数单元测试

使用 unittest 框架对 string_utils 模块进行完整测试。
"""

import unittest
from string_utils import is_palindrome, reverse_string


class TestStringUtils(unittest.TestCase):
    """字符串工具函数测试类"""

    # ========== is_palindrome 测试用例 ==========

    def test_is_palindrome_empty(self):
        """测试空字符串"""
        self.assertTrue(is_palindrome(""))

    def test_is_palindrome_single_char(self):
        """测试单字符"""
        self.assertTrue(is_palindrome("a"))

    def test_is_palindrome_same_chars(self):
        """测试相同字符 aa"""
        self.assertTrue(is_palindrome("aa"))

    def test_is_palindrome_simple(self):
        """测试普通回文 'aba'"""
        self.assertTrue(is_palindrome("aba"))

    def test_is_palindrome_case_insensitive(self):
        """测试大小写不敏感 'Abba'"""
        self.assertTrue(is_palindrome("Abba"))

    def test_is_palindrome_with_spaces(self):
        """测试带空格回文 'a man a plan a canal Panama'"""
        self.assertTrue(is_palindrome("a man a plan a canal Panama"))

    def test_is_palindrome_not_palindrome(self):
        """测试非回文 'abc'"""
        self.assertFalse(is_palindrome("abc"))

    def test_is_palindrome_not_palindrome_even(self):
        """测试非回文偶数 'abca'"""
        self.assertFalse(is_palindrome("abca"))

    # ========== reverse_string 测试用例 ==========

    def test_reverse_string_empty(self):
        """测试空字符串反转"""
        self.assertEqual(reverse_string(""), "")

    def test_reverse_string_single(self):
        """测试单字符反转"""
        self.assertEqual(reverse_string("a"), "a")

    def test_reverse_string_normal(self):
        """测试普通字符串反转 'abc' -> 'cba'"""
        self.assertEqual(reverse_string("abc"), "cba")

    def test_reverse_string_palindrome(self):
        """测试回文反转 'racecar' -> 'racecar'"""
        self.assertEqual(reverse_string("racecar"), "racecar")

    def test_reverse_string_with_spaces(self):
        """测试带空格反转 'hello world' -> 'dlrow olleh'"""
        self.assertEqual(reverse_string("hello world"), "dlrow olleh")


if __name__ == "__main__":
    unittest.main()
