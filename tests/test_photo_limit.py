import unittest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import strings
from main import owner_photo, OWNER_CONTACT, OWNER_PHOTO, MAX_LISTING_PHOTOS


class TestPhotoLimit(unittest.TestCase):
    @patch("watermark.apply_watermark")
    def test_owner_photo_under_limit(self, mock_watermark):
        mock_watermark.return_value = b"watermarked_data"

        update = MagicMock()
        photo_mock = MagicMock()
        photo_file = AsyncMock()
        photo_file.download_as_bytearray.return_value = bytearray(b"raw_data")
        photo_mock.get_file.return_value = photo_file
        update.message.photo = [photo_mock]
        update.message.reply_photo = AsyncMock()
        sent_photo = MagicMock()
        sent_photo.photo = [MagicMock(file_id="photo_123")]
        update.message.reply_photo.return_value = sent_photo
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.user_data = {"photos": ["photo_1"]}

        result = asyncio.run(owner_photo(update, context))
        self.assertEqual(result, OWNER_PHOTO)
        self.assertEqual(len(context.user_data["photos"]), 2)

    @patch("watermark.apply_watermark")
    def test_owner_photo_reaches_limit_auto_advance(self, mock_watermark):
        mock_watermark.return_value = b"watermarked_data"

        update = MagicMock()
        photo_mock = MagicMock()
        photo_file = AsyncMock()
        photo_file.download_as_bytearray.return_value = bytearray(b"raw_data")
        photo_mock.get_file.return_value = photo_file
        update.message.photo = [photo_mock]
        update.message.reply_photo = AsyncMock()
        sent_photo = MagicMock()
        sent_photo.photo = [MagicMock(file_id="photo_5")]
        update.message.reply_photo.return_value = sent_photo
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.user_data = {"photos": ["photo_1", "photo_2", "photo_3", "photo_4"]}

        result = asyncio.run(owner_photo(update, context))
        self.assertEqual(result, OWNER_CONTACT)
        self.assertEqual(len(context.user_data["photos"]), 5)
        update.message.reply_text.assert_any_call(
            strings.PHOTO_LIMIT_REACHED_AUTO_ADVANCE.format(max_photos=MAX_LISTING_PHOTOS),
            parse_mode='HTML'
        )

    def test_owner_photo_exceeds_limit(self):
        update = MagicMock()
        update.message.photo = [MagicMock()]
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.user_data = {"photos": ["p1", "p2", "p3", "p4", "p5"]}

        result = asyncio.run(owner_photo(update, context))
        self.assertEqual(result, OWNER_CONTACT)
        update.message.reply_text.assert_any_call(
            strings.PHOTO_LIMIT_REACHED_AUTO_ADVANCE.format(max_photos=MAX_LISTING_PHOTOS),
            parse_mode='HTML'
        )


if __name__ == "__main__":
    unittest.main()
