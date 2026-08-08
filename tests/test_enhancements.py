import asyncio
import asyncio
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

try:
    from unittest.mock import AsyncMock
except ImportError:
    class AsyncMock(unittest.mock.Mock):
        async def __call__(self, *args, **kwargs):
            result = super().__call__(*args, **kwargs)
            if asyncio.iscoroutine(result):
                return await result
            return result

        def assert_awaited_once(self):
            return self.assert_called_once()

        def assert_not_awaited(self):
            return self.assert_not_called()

        def assert_awaited_with(self, *args, **kwargs):
            return self.assert_called_with(*args, **kwargs)

        def assert_awaited_once_with(self, *args, **kwargs):
            return self.assert_called_once_with(*args, **kwargs)

os.environ.setdefault("BOT_TOKEN", "dummy-token")

import database
import main
import strings

class EnhancementTests(unittest.TestCase):
    def setUp(self):
        os.environ["DB_ENGINE"] = "sqlite"
        database.SQLITE_PATH = "test_rental_bot.db"
        if os.path.exists("test_rental_bot.db"):
            try:
                os.remove("test_rental_bot.db")
            except PermissionError:
                pass
        database.init_db()
        database.execute_query("DELETE FROM users", commit=True)
        database.execute_query("DELETE FROM listings", commit=True)
        database.execute_query("DELETE FROM alerts", commit=True)

    def tearDown(self):
        if os.path.exists("test_rental_bot.db"):
            try:
                os.remove("test_rental_bot.db")
            except PermissionError:
                pass

    def test_strings_categories(self):
        self.assertEqual(strings.CATEGORY_OTHER, "📦 ሌላ")
        self.assertEqual(strings.SERVICE_CATEGORY_OTHER, "📦 ሌላ")

    def test_property_purpose_extraction_supports_fresh_and_migrated_schemas(self):
        # Fresh schema row format (purpose at index 7):
        row_sell_fresh = (1, 100, "House", "City", "5000", None, "0911000000", "sell", "2026-01-01", "paid", 0, None, None, "property")
        # Migrated SQLite schema row format (purpose at index 13, created_at at index 7):
        row_rent_migrated = (2, 100, "Apt", "City", "3000", None, "0911000000", "2026-01-01", "paid", 0, None, None, "property", "rent")
        row_service_migrated = (3, 100, "Plumber", "City", "1000", None, "0911000000", "2026-01-01", "paid", 0, None, None, "service", "service")
        row_none = (4, 100, "Unknown", "City", "1000", None, "0911000000", "2026-01-01", "paid", 0, None, None, "property", None)

        self.assertEqual(main.get_property_purpose_from_row(row_sell_fresh), "sell")
        self.assertEqual(main.get_property_purpose_from_row(row_rent_migrated), "rent")
        self.assertEqual(main.get_property_purpose_from_row(row_service_migrated), "service")
        # Ensure that when purpose is None, contact_phone or date is NOT returned as purpose
        self.assertIsNone(main.get_property_purpose_from_row(row_none))

    def test_alerts_with_description(self):
        database.add_alert(
            telegram_id=12345,
            category="🏠 ቤት/መሬት",
            city="አዲስ አበባ/ዙሪያ",
            neighborhood="ቦሌ",
            property_purpose="buy",
            description="ባለ 2 ክፍል ኮንዶሚኒየም"
        )
        alerts = database.get_alerts_by_user(12345)
        self.assertEqual(len(alerts), 1)
        alert = alerts[0]
        # alert structure: id, telegram_id, category, city, neighborhood, property_purpose, created_at, description
        self.assertEqual(alert[1], 12345)
        self.assertEqual(alert[2], "🏠 ቤት/መሬት")
        self.assertEqual(alert[3], "አዲስ አበባ/ዙሪያ")
        self.assertEqual(alert[4], "ቦሌ")
        self.assertEqual(alert[5], "buy")
        self.assertEqual(alert[7], "ባለ 2 ክፍል ኮንዶሚኒየም")

    def test_get_listings_by_owner_filtering(self):
        database.add_listing(100, "Listing 1", "አዲስ አበባ - ቦሌ", "1000", None, "0911000000", listing_type="property", property_purpose="sell")
        database.add_listing(100, "Listing 2", "አዲስ አበባ - ቦሌ", "2000", None, "0911000000", listing_type="property", property_purpose="rent")
        database.add_listing(100, "Listing 3", "አዲስ አበባ - ቦሌ", "3000", None, "0911000000", listing_type="service", property_purpose=None)

        all_listings = database.get_listings_by_owner(100)
        self.assertEqual(len(all_listings), 3)

        sell_listings = database.get_listings_by_owner(100, listing_type="property", property_purpose="sell")
        self.assertEqual(len(sell_listings), 1)
        self.assertEqual(sell_listings[0][2], "Listing 1")

        rent_listings = database.get_listings_by_owner(100, listing_type="property", property_purpose="rent")
        self.assertEqual(len(rent_listings), 1)
        self.assertEqual(rent_listings[0][2], "Listing 2")

        service_listings = database.get_listings_by_owner(100, listing_type="service")
        self.assertEqual(len(service_listings), 1)
        self.assertEqual(service_listings[0][2], "Listing 3")

    def test_seeker_menu_keyboard_has_no_alert_buttons(self):
        keyboard = main.get_seeker_menu_keyboard()
        labels = [label for row in keyboard.keyboard for label in row]

        self.assertNotIn("ማሳወቂያ ፍጠር", labels)
        self.assertNotIn("ማሳወቂያዎችን ሰርዝ", labels)
        self.assertNotIn("የኔን ፍላጎቶች አስተዳድር", labels)

    def test_send_listing_page_renders_listing_without_error(self):
        async def run_test():
            listing = (
                1,
                100,
                "Luxury Home",
                "አዲስ አበባ - ቦሌ",
                "5000",
                None,
                "0911000000",
                "sell",
                "2026-01-01 12:00:00",
                "paid",
                0,
                None,
                None,
                "property",
            )
            update = SimpleNamespace(
                effective_user=SimpleNamespace(id=100),
                effective_chat=SimpleNamespace(id=200),
            )
            bot = SimpleNamespace(
                send_photo=AsyncMock(),
                send_message=AsyncMock(),
                send_media_group=AsyncMock(),
            )
            context = SimpleNamespace(
                user_data={"current_listings": [listing], "is_for_owner": False},
                bot=bot,
            )

            await main.send_listing_page(update, context, 0)

            bot.send_message.assert_called_once()

        asyncio.run(run_test())

    def test_send_listing_page_renders_rent_purpose_from_correct_column(self):
        async def run_test():
            listing = (
                1,
                100,
                "Luxury Home",
                "አዲስ አበባ - ቦሌ",
                "5000",
                None,
                "0911000000",
                "rent",
                "2026-01-01 12:00:00",
                "paid",
                0,
                None,
                None,
                "property",
            )
            update = SimpleNamespace(
                effective_user=SimpleNamespace(id=100),
                effective_chat=SimpleNamespace(id=200),
            )
            bot = SimpleNamespace(
                send_photo=AsyncMock(),
                send_message=AsyncMock(),
                send_media_group=AsyncMock(),
            )
            context = SimpleNamespace(
                user_data={"current_listings": [listing], "is_for_owner": False},
                bot=bot,
            )

            await main.send_listing_page(update, context, 0)

            sent_text = bot.send_message.call_args[1]["text"]
            self.assertIn("ኪራይ", sent_text)

        asyncio.run(run_test())

    def test_send_listing_page_uses_created_at_for_registration_date(self):
        async def run_test():
            listing = (
                1,
                100,
                "Luxury Home",
                "አዲስ አበባ - ቦሌ",
                "5000",
                None,
                "0911000000",
                "sell",
                "2026-01-01 12:00:00",
                "paid",
                0,
                None,
                None,
                "property",
            )
            update = SimpleNamespace(
                effective_user=SimpleNamespace(id=100),
                effective_chat=SimpleNamespace(id=200),
            )
            bot = SimpleNamespace(
                send_photo=AsyncMock(),
                send_message=AsyncMock(),
                send_media_group=AsyncMock(),
            )
            context = SimpleNamespace(
                user_data={"current_listings": [listing], "is_for_owner": False},
                bot=bot,
            )

            await main.send_listing_page(update, context, 0)

            sent_text = bot.send_message.call_args[1]["text"]
            self.assertIn("📅 የተመዘገበበት፦ 2026-01-01 12:00:00", sent_text)

        asyncio.run(run_test())

    def test_send_listing_page_handles_numeric_transaction_id_without_crash(self):
        async def run_test():
            listing = (
                1,
                100,
                "Luxury Home",
                "አዲስ አበባ - ቦሌ",
                "5000",
                None,
                "0911000000",
                "sell",
                "2026-01-01 12:00:00",
                "paid",
                0.0,
                12345,
                None,
                "property",
            )
            update = SimpleNamespace(
                effective_user=SimpleNamespace(id=100),
                effective_chat=SimpleNamespace(id=200),
            )
            bot = SimpleNamespace(
                send_photo=AsyncMock(),
                send_message=AsyncMock(),
                send_media_group=AsyncMock(),
            )
            context = SimpleNamespace(
                user_data={"current_listings": [listing], "is_for_owner": False},
                bot=bot,
            )

            await main.send_listing_page(update, context, 0)

            bot.send_message.assert_called_once()

        asyncio.run(run_test())

    def test_start_after_timeout_discards_timeout_msg_and_shows_only_welcome(self):
        async def run_test():
            captured_messages = []

            async def fake_reply_text(text, *args, **kwargs):
                captured_messages.append(text)

            update = SimpleNamespace(
                effective_user=SimpleNamespace(id=777, username="user"),
                message=SimpleNamespace(text="/start", reply_text=fake_reply_text),
                effective_message=SimpleNamespace(text="/start", reply_text=fake_reply_text),
                callback_query=None,
            )
            context = SimpleNamespace(user_data={"pending_timeout_message": strings.TIMEOUT_MSG}, bot=SimpleNamespace(), args=[])

            with patch.object(main, "is_subscribed", AsyncMock(return_value=True)):
                await main.start(update, context)

            self.assertNotIn("pending_timeout_message", context.user_data)
            self.assertEqual(captured_messages, [strings.WELCOME_MSG])

        asyncio.run(run_test())

    def test_non_start_text_after_timeout_triggers_timeout_msg(self):
        async def run_test():
            captured_messages = []

            async def fake_reply_text(text, *args, **kwargs):
                captured_messages.append(text)

            update = SimpleNamespace(
                effective_user=SimpleNamespace(id=100, username="user"),
                message=SimpleNamespace(text="hello", reply_text=fake_reply_text),
                effective_message=SimpleNamespace(text="hello", reply_text=fake_reply_text),
                callback_query=None,
            )
            context = SimpleNamespace(user_data={"pending_timeout_message": strings.TIMEOUT_MSG}, bot=SimpleNamespace(), args=[])

            handled = await main.check_and_send_timeout_notice(update, context)

            self.assertTrue(handled)
            self.assertNotIn("pending_timeout_message", context.user_data)
            self.assertEqual(captured_messages, [strings.TIMEOUT_MSG])

        asyncio.run(run_test())

    def test_start_shows_welcome_and_main_menu(self):
        async def run_test():
            captured = []

            async def fake_reply_text(text, *args, **kwargs):
                captured.append((text, kwargs))

            update = SimpleNamespace(
                effective_user=SimpleNamespace(id=777, username="user"),
                message=SimpleNamespace(text="/start", reply_text=fake_reply_text),
                effective_message=SimpleNamespace(text="/start", reply_text=fake_reply_text),
                callback_query=None,
            )
            context = SimpleNamespace(user_data={}, bot=SimpleNamespace(), args=[])

            with patch.object(main, "is_subscribed", AsyncMock(return_value=True)):
                await main.start(update, context)

            self.assertEqual(len(captured), 1)
            self.assertEqual(captured[0][0], strings.WELCOME_MSG)
            reply_markup = captured[0][1]["reply_markup"]
            keyboard_labels = [[button.text for button in row] for row in reply_markup.keyboard]
            expected = [
                [strings.ROLE_SELLER, strings.ROLE_LANDLORD],
                [strings.ROLE_BUYER, strings.ROLE_RENTER],
                [strings.ROLE_SERVICE_PROVIDER, strings.ROLE_SERVICE_SEEKER],
                [strings.HELP_BTN],
            ]
            self.assertEqual(keyboard_labels, expected)

        asyncio.run(run_test())

    def test_timeout_notice_is_not_queued_for_start_text(self):
        async def run_test():
            captured_messages = []

            async def fake_reply_text(text, *args, **kwargs):
                captured_messages.append(text)

            update = SimpleNamespace(
                effective_user=SimpleNamespace(id=777, username="user"),
                message=SimpleNamespace(text="/start", reply_text=fake_reply_text),
                effective_message=SimpleNamespace(text="/start", reply_text=fake_reply_text),
                callback_query=None,
            )
            context = SimpleNamespace(user_data={}, bot=SimpleNamespace(), args=[])

            await main.timeout_handler(update, context)
            await main.start(update, context)

            self.assertNotIn("pending_timeout_message", context.user_data)
            self.assertEqual(captured_messages, [strings.WELCOME_MSG])

        asyncio.run(run_test())

    def test_post_listing_to_channel_posts_once_per_listing(self):
        async def run_test():
            listing_id = database.add_listing(
                100,
                "Luxury Home",
                "አዲስ አበባ - ቦሌ",
                "5000",
                None,
                "0911000000",
                listing_type="property",
                property_purpose="sell",
            )
            listing = database.get_listing_by_id(listing_id)
            bot = SimpleNamespace(
                send_media_group=AsyncMock(return_value=[SimpleNamespace(message_id=1)]),
                send_photo=AsyncMock(return_value=SimpleNamespace(message_id=1)),
                send_message=AsyncMock(return_value=SimpleNamespace(message_id=1)),
                get_me=AsyncMock(return_value=SimpleNamespace(username="demo_bot")),
                get_file=AsyncMock(),
            )
            context = SimpleNamespace(bot=bot)

            with patch.dict(os.environ, {"MINI_APP_URL": ""}, clear=False):
                await main.post_listing_to_channel(context, listing, "property", "sell", channel_id="channel")
                await main.post_listing_to_channel(context, listing, "property", "sell", channel_id="channel")

            bot.send_message.assert_awaited_once()
            self.assertTrue(database.is_listing_channel_notified(listing_id))

        asyncio.run(run_test())

    def test_post_listing_to_channel_posts_once_for_multi_photo_listing(self):
        async def run_test():
            bot = SimpleNamespace(
                send_media_group=AsyncMock(return_value=[SimpleNamespace(message_id=1)]),
                send_photo=AsyncMock(return_value=SimpleNamespace(message_id=1)),
                send_message=AsyncMock(return_value=SimpleNamespace(message_id=1)),
                get_me=AsyncMock(return_value=SimpleNamespace(username="demo_bot")),
                get_file=AsyncMock(side_effect=[
                    SimpleNamespace(file_path="photos/1.jpg"),
                    SimpleNamespace(file_path="photos/2.jpg"),
                ]),
            )
            context = SimpleNamespace(bot=bot)
            listing = (
                1,
                100,
                "Luxury Home",
                "አዲስ አበባ - ቦሌ",
                "5000",
                "photo1,photo2",
                "0911000000",
                "rent",
                "2026-01-01 12:00:00",
                "paid",
                0,
                None,
                None,
                "property",
            )

            with patch.dict(os.environ, {"MINI_APP_URL": ""}, clear=False):
                await main.post_listing_to_channel(context, listing, "property", "rent", channel_id="channel")

            bot.send_photo.assert_awaited_once()
            bot.send_media_group.assert_not_awaited()
            bot.send_message.assert_not_awaited()
            sent_caption = bot.send_photo.call_args[1]["caption"]
            self.assertIn("📸 +1 ተጨማሪ ፎቶዎች", sent_caption)
            reply_markup = bot.send_photo.call_args[1]["reply_markup"]
            buttons = reply_markup.inline_keyboard
            self.assertEqual(buttons[0][0].url, "https://t.me/demo_bot?start=view_1")

        asyncio.run(run_test())

    def test_post_listing_to_channel_is_race_safe_for_concurrent_calls(self):
        async def run_test():
            listing_id = database.add_listing(
                100,
                "Luxury Home",
                "አዲስ አበባ - ቦሌ",
                "5000",
                None,
                "0911000000",
                listing_type="property",
                property_purpose="sell",
            )
            listing = database.get_listing_by_id(listing_id)

            started = asyncio.Event()
            release = asyncio.Event()
            send_calls = 0

            async def delayed_send_message(*args, **kwargs):
                nonlocal send_calls
                send_calls += 1
                started.set()
                await release.wait()
                return SimpleNamespace(message_id=1)

            bot = SimpleNamespace(
                send_media_group=AsyncMock(),
                send_photo=AsyncMock(),
                send_message=AsyncMock(side_effect=delayed_send_message),
                get_me=AsyncMock(return_value=SimpleNamespace(username="demo_bot")),
                get_file=AsyncMock(),
            )
            context = SimpleNamespace(bot=bot)

            with patch.dict(os.environ, {"MINI_APP_URL": ""}, clear=False):
                task1 = asyncio.create_task(main.post_listing_to_channel(context, listing, "property", "sell", channel_id="channel"))
                await started.wait()
                task2 = asyncio.create_task(main.post_listing_to_channel(context, listing, "property", "sell", channel_id="channel"))
                release.set()
                await asyncio.gather(task1, task2)

            self.assertEqual(send_calls, 1)
            self.assertTrue(database.is_listing_channel_notified(listing_id))

        asyncio.run(run_test())

    def test_approve_listing_is_idempotent_on_repeated_calls(self):
        listing_id = database.add_listing(
            100,
            "Luxury Home",
            "አዲስ አበባ - ቦሌ",
            "5000",
            None,
            "0911000000",
            listing_type="property",
            property_purpose="sell",
        )

        self.assertTrue(database.approve_listing(listing_id))
        self.assertFalse(database.approve_listing(listing_id))

    def test_approve_callback_skips_duplicate_owner_notification_for_paid_listing(self):
        async def run_test():
            query = SimpleNamespace(
                data="approve_1",
                answer=AsyncMock(),
                edit_message_text=AsyncMock(),
                message=SimpleNamespace(text="pending", photo=None),
            )
            update = SimpleNamespace(
                callback_query=query,
                effective_user=SimpleNamespace(id=1),
                effective_chat=SimpleNamespace(id=2),
            )
            bot = SimpleNamespace(send_message=AsyncMock(), send_photo=AsyncMock(), send_media_group=AsyncMock())
            context = SimpleNamespace(bot=bot, user_data={})

            listing = (
                1,
                100,
                "Luxury Home",
                "አዲስ አበባ - ቦሌ",
                "5000",
                None,
                "0911000000",
                "rent",
                "2026-01-01 12:00:00",
                "paid",
                0,
                None,
                None,
                "property",
            )

            with patch.object(main.database, "approve_listing") as approve_mock, \
                 patch.object(main.database, "get_listing_by_id", return_value=listing), \
                 patch.object(main.database, "get_matching_alerts", return_value=[]), \
                 patch.object(main, "post_listing_to_channel", new=AsyncMock()):
                await main.handle_callback(update, context)

            bot.send_message.assert_not_called()
            approve_mock.assert_not_called()

        asyncio.run(run_test())

    def test_owner_contact_stores_pending_submission_before_admin_approval(self):
        async def run_test():
            update = SimpleNamespace(
                effective_user=SimpleNamespace(id=100),
                message=SimpleNamespace(
                    text="0911000000",
                    contact=None,
                    reply_text=AsyncMock(),
                ),
            )
            context = SimpleNamespace(
                user_data={
                    "title": "Luxury Home",
                    "location": "አዲስ አበባ - ቦሌ",
                    "price": "5000",
                    "contact": "0911000000",
                    "listing_type": "property",
                    "sub_role": strings.ROLE_LANDLORD,
                    "photos": [],
                },
                bot=SimpleNamespace(),
            )

            with patch.object(main.database, "add_listing") as add_listing_mock, \
                 patch.object(main, "_create_pending_submission", return_value="pending_123") as create_pending_mock:
                await main.owner_contact(update, context)

            add_listing_mock.assert_not_called()
            create_pending_mock.assert_called_once()
            self.assertEqual(context.user_data["listing_id"], "pending_123")

        asyncio.run(run_test())

    def test_reset_conversation_state_clears_stale_flow_data(self):
        context = SimpleNamespace(user_data={
            "title": "old",
            "category": "cat",
            "city": "city",
            "location": "loc",
            "price": "100",
            "photos": ["img"],
            "contact": "123",
            "listing_id": 1,
            "current_listings": [1],
            "is_for_owner": True,
            "seeker_listing_type": "property",
            "seeker_property_purpose": "rent",
            "looking_for_desc": "desc",
        })

        main.reset_conversation_state(context)

        self.assertNotIn("title", context.user_data)
        self.assertNotIn("category", context.user_data)
        self.assertNotIn("current_listings", context.user_data)
        self.assertNotIn("seeker_listing_type", context.user_data)
        self.assertNotIn("looking_for_desc", context.user_data)

    def test_owner_submit_txid_handles_missing_listing_id(self):
        async def run_test():
            update = SimpleNamespace(
                effective_user=SimpleNamespace(id=100, username="owner"),
                message=SimpleNamespace(
                    text="123456",
                    photo=None,
                    reply_text=AsyncMock(),
                ),
            )
            context = SimpleNamespace(user_data={}, bot=SimpleNamespace())

            result = await main.owner_submit_txid(update, context)

            self.assertEqual(result, main.CHOOSING_ROLE)
            update.message.reply_text.assert_awaited_once()

        asyncio.run(run_test())

    def test_seeker_looking_for_start_clears_previous_draft_data(self):
        async def run_test():
            update = SimpleNamespace(
                message=SimpleNamespace(text=strings.ROLE_RENTER),
            )
            context = SimpleNamespace(user_data={
                "looking_for_desc": "old desc",
                "looking_for_price": "1000",
                "looking_for_contact": "123456",
                "looking_for_city": "city",
                "looking_for_neighborhood": "neigh",
                "looking_for_purpose": "buy",
                "in_looking_for_post": False,
                "in_looking_for_search": True,
                "seeker_listing_type": "property",
                "seeker_property_purpose": "sell",
            })

            with patch.object(main, "seeker_ask_category", new=AsyncMock(return_value=main.SEEKER_CATEGORY)) as ask_category_mock:
                result = await main.seeker_looking_for_start(update, context)

            self.assertEqual(result, main.SEEKER_CATEGORY)
            self.assertNotIn("looking_for_desc", context.user_data)
            self.assertNotIn("looking_for_price", context.user_data)
            self.assertNotIn("looking_for_contact", context.user_data)
            self.assertNotIn("looking_for_city", context.user_data)
            self.assertNotIn("looking_for_neighborhood", context.user_data)
            self.assertNotIn("seeker_category", context.user_data)
            self.assertNotIn("seeker_city", context.user_data)
            self.assertNotIn("seeker_neighborhood", context.user_data)
            self.assertEqual(context.user_data["looking_for_purpose"], "buy")
            self.assertTrue(context.user_data["in_looking_for_post"])
            self.assertFalse(context.user_data["in_looking_for_search"])
            ask_category_mock.assert_awaited_once()

        asyncio.run(run_test())

    def test_property_purpose_extraction_strictly_checks_index_7(self):
        # Full DB row format:
        # (id, owner_id, title, location, price, photo_file_id, contact_phone, property_purpose, created_at, status, fee_amount, transaction_id, last_checked_at, listing_type)
        row_sell = (1, 100, "House", "City", "5000", None, "0911000000", "sell", "2026-01-01", "paid", 0, None, None, "property")
        row_rent = (2, 100, "Apt", "City", "3000", None, "0911000000", "rent", "2026-01-01", "paid", 0, None, None, "property")
        row_service = (3, 100, "Plumber", "City", "1000", None, "0911000000", "service", "2026-01-01", "paid", 0, None, None, "service")
        row_none = (4, 100, "Unknown", "City", "1000", None, "0911000000", None, "2026-01-01", "paid", 0, None, None, "property")

        self.assertEqual(main.get_property_purpose_from_row(row_sell), "sell")
        self.assertEqual(main.get_property_purpose_from_row(row_rent), "rent")
        self.assertEqual(main.get_property_purpose_from_row(row_service), "service")
        # Ensure that when index 7 is None, contact_phone (0911000000) or date is NOT returned as purpose
        self.assertIsNone(main.get_property_purpose_from_row(row_none))

    def test_listing_titles_generation(self):
        self.assertEqual(main.get_listing_title("property", "sell"), "ለሽያጭ የቀረበ")
        self.assertEqual(main.get_listing_title("property", "rent"), "ለኪራይ የቀረበ")
        self.assertEqual(main.get_listing_title("service", None), "አገልግሎት")

        self.assertEqual(main.get_looking_for_title("buy"), "ፈላጊ — ለግዢ")
        self.assertEqual(main.get_looking_for_title("rent"), "ፈላጊ — ለኪራይ")
        self.assertEqual(main.get_looking_for_title("service"), "ፈላጊ — አገልግሎት")
        self.assertEqual(main.get_looking_for_title(None), "ፍላጎት — ተፈላጊ")

if __name__ == "__main__":
    unittest.main()

