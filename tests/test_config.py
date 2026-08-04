import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest


class TestConfig(unittest.TestCase):
    def test_server_port_default(self):
        import config
        self.assertEqual(config.SERVER_PORT, 8800)

    def test_deepseek_config_exists(self):
        import config
        self.assertTrue(config.DEEPSEEK_BASE_URL.endswith("/anthropic"))
        self.assertEqual(config.DEEPSEEK_MODEL, "deepseek-v4-flash")
        # key 从 .env 读取，能取到即可（不校验内容）
        self.assertIsInstance(config.DEEPSEEK_API_KEY, str)


if __name__ == "__main__":
    unittest.main()
