import unittest
import asyncio
from unittest.mock import AsyncMock, MagicMock
import strings
from main import count_words, validate_input_limits


class TestWordLimit(unittest.TestCase):
    def test_count_words(self):
        self.assertEqual(count_words(""), 0)
        self.assertEqual(count_words("   "), 0)
        self.assertEqual(count_words("hello world"), 2)
        self.assertEqual(count_words("ባለ 2 ክፍል ቤት ቦሌ አካባቢ"), 6)
        self.assertEqual(count_words("  one   two  three "), 3)

    def test_validate_input_limits_valid(self):
        update = MagicMock()
        update.message = AsyncMock()

        # 5 words, 28 chars
        result = asyncio.run(validate_input_limits(update, "hello world test input valid", max_words=10, max_chars=50))
        self.assertTrue(result)
        update.message.reply_text.assert_not_called()

    def test_validate_input_limits_exceed_words(self):
        update = MagicMock()
        update.message = AsyncMock()

        # 5 words
        text = "word1 word2 word3 word4 word5"
        result = asyncio.run(validate_input_limits(update, text, max_words=3, max_chars=100))
        self.assertFalse(result)
        update.message.reply_text.assert_called_once()
        args, _ = update.message.reply_text.call_args
        self.assertIn(strings.WORD_LIMIT_EXCEEDED.format(max_words=3, count=5), args[0])

    def test_validate_input_limits_exceed_chars(self):
        update = MagicMock()
        update.message = AsyncMock()

        # 1 word, 20 characters
        text = "a" * 20
        result = asyncio.run(validate_input_limits(update, text, max_words=10, max_chars=15))
        self.assertFalse(result)
        update.message.reply_text.assert_called_once()
        args, _ = update.message.reply_text.call_args
        self.assertIn(strings.CHAR_LIMIT_EXCEEDED.format(max_chars=15, count=20), args[0])


if __name__ == "__main__":
    unittest.main()
