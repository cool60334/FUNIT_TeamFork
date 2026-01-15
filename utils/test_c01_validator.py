import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import unittest
from utils.output_validators import validate_hook, _check_ai_phrases, validate_draft

class TestC01Validators(unittest.TestCase):

    def test_validate_hook_generic(self):
        content = """在這個數位化的時代，人工智慧正在改變我們的生活。
        
        這是一篇關於 AI 的文章。
        """
        errors = validate_hook(content)
        self.assertTrue(any("AI 味" in e for e in errors), f"Failed to catch generic hook. Errors: {errors}")

    def test_validate_hook_good(self):
        content = """我的阿嬤第一次看到 ChatGPT 的時候，她的表情就像看到鬼一樣。
        
        這是一篇關於 AI 的文章。
        """
        errors = validate_hook(content)
        self.assertEqual(len(errors), 0, f"False positive on good hook. Errors: {errors}")

    def test_check_ai_phrases(self):
        content = """
        AI 技術日新月異。
        總而言之，我們應該擁抱它。
        值得注意的是，風險依然存在。
        """
        errors = _check_ai_phrases(content)
        self.assertTrue(any("總而言之" in e for e in errors))
        self.assertTrue(any("值得注意的是" in e for e in errors))

    def test_check_ai_phrases_clean(self):
        content = """
        AI 技術進步很快。
        所以說，我們最好快點學會用它。
        別忘了，風險還是有的。
        """
        errors = _check_ai_phrases(content)
        self.assertEqual(len(errors), 0, f"False positive on clean content. Errors: {errors}")

if __name__ == '__main__':
    unittest.main()
