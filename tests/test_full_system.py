import asyncio
import io
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

os.environ["BOT_TOKEN"] = "dummy-token"
os.environ["ADMIN_IDS"] = "100,999"

import database
import location_options
import main
import strings
import watermark

# Ensure main.ADMIN_IDS has test admin IDs
main.ADMIN_IDS = [100, 999]


class FullSystemFunctionalityTests(unittest.TestCase):
    def setUp(self):
        os.environ["DB_ENGINE"] = "sqlite"
        database.SQLITE_PATH = "test_full_system.db"
        if os.path.exists("test_full_system.db"):
            try:
                os.remove("test_full_system.db")
            except PermissionError:
                pass
        database.init_db()
        database.execute_query("DELETE FROM users", commit=True)
        database.execute_query("DELETE FROM listings", commit=True)
        database.execute_query("DELETE FROM alerts", commit=True)

    def tearDown(self):
        if os.path.exists("test_full_system.db"):
            try:
                os.remove("test_full_system.db")
            except PermissionError:
                pass

    # ── 1. Database Operations ──────────────────────────────────────────────────
    def test_database_user_and_listing_crud(self):
        database.add_user(100, "seller_user", role="user")
        users = database.get_all_users()
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0][0], 100)
        self.assertEqual(users[0][1], "seller_user")

        listing_id = database.add_listing(
            owner_id=100,
            title="Apartment for Rent",
            location="አዲስ አበባ - ቦሌ",
            price="15000",
            photo_file_id="file_id_1,file_id_2",
            contact_phone="0911223344",
            fee_amount=50,
            listing_type="property",
            property_purpose="rent"
        )
        self.assertTrue(listing_id > 0)

        listing = database.get_listing_by_id(listing_id)
        self.assertIsNotNone(listing)
        self.assertEqual(listing[2], "Apartment for Rent")

        # TXID update & approval
        database.update_listing_txid(listing_id, "TX123456")
        self.assertTrue(database.approve_listing(listing_id))
        self.assertFalse(database.approve_listing(listing_id))  # Idempotent return False on 2nd attempt

        # Retrieve active listings
        active = database.get_all_listings()
        self.assertEqual(len(active), 1)

        # Deletion
        database.delete_listing(listing_id)
        active_after = database.get_all_listings()
        self.assertEqual(len(active_after), 0)

    def test_database_alerts_and_expiration(self):
        database.add_alert(200, "🏠 ቤት/መሬት", "አዲስ አበባ/ዙሪያ", "ቦሌ", "buy", "Condo")
        alerts = database.get_alerts_by_user(200)
        self.assertEqual(len(alerts), 1)

        database.delete_alert(alerts[0][0], 200)
        self.assertEqual(len(database.get_alerts_by_user(200)), 0)

        # Expire old listings test for service listing older than 30 days
        lid = database.add_listing(100, "Old Service", "City", "100", None, "0900", fee_amount=50, listing_type="service")
        database.execute_query("UPDATE listings SET created_at = '2020-01-01 00:00:00', status = 'paid' WHERE id = ?", (lid,), commit=True)
        database.expire_old_listings()
        expired_listing = database.get_listing_by_id(lid)
        self.assertEqual(expired_listing[9], "expired")

    # ── 2. Location Options ─────────────────────────────────────────────────────
    def test_location_options(self):
        cities = location_options.CITY_OPTIONS
        self.assertIn("አዲስ አበባ/ዙሪያ", cities)

        kb = location_options.get_city_keyboard()
        self.assertTrue(len(kb) > 0)

        neigh_kb = location_options.get_neighborhood_keyboard("አዲስ አበባ/ዙሪያ")
        self.assertTrue(len(neigh_kb) > 0)

        loc_str = location_options.build_location_string("አዲስ አበባ/ዙሪያ", "ቦሌ")
        self.assertEqual(loc_str, "አዲስ አበባ/ዙሪያ - ቦሌ")

    # ── 3. Start & Subscription Flow ───────────────────────────────────────────
    def test_start_command_flow(self):
        async def run_test():
            captured = []
            async def fake_reply(text, *args, **kwargs):
                captured.append(text)

            update = SimpleNamespace(
                effective_user=SimpleNamespace(id=777, username="regularuser"),
                message=SimpleNamespace(text="/start", reply_text=fake_reply),
                effective_message=SimpleNamespace(text="/start", reply_text=fake_reply),
                callback_query=None,
            )
            context = SimpleNamespace(user_data={}, bot=SimpleNamespace(), args=[])

            with patch.object(main, "is_subscribed", AsyncMock(return_value=True)):
                res = await main.start(update, context)

            self.assertEqual(res, main.CHOOSING_ROLE)
            self.assertEqual(captured[0], strings.WELCOME_MSG)

        asyncio.run(run_test())

    def test_start_deep_linking(self):
        async def run_test():
            lid = database.add_listing(100, "Deep Link Listing", "City", "5000", None, "0900", property_purpose="sell")
            database.approve_listing(lid)

            captured = []
            async def fake_reply(text, *args, **kwargs):
                captured.append(text)

            update = SimpleNamespace(
                effective_user=SimpleNamespace(id=777, username="seeker"),
                effective_chat=SimpleNamespace(id=777),
                message=SimpleNamespace(text=f"/start view_{lid}", reply_text=fake_reply),
                effective_message=SimpleNamespace(text=f"/start view_{lid}", reply_text=fake_reply),
                callback_query=None,
            )
            context = SimpleNamespace(
                user_data={},
                bot=SimpleNamespace(send_message=AsyncMock(), send_photo=AsyncMock(), send_media_group=AsyncMock()),
                args=[f"view_{lid}"]
            )

            res = await main.start(update, context)
            self.assertEqual(res, main.CHOOSING_ROLE)
            context.bot.send_message.assert_called_once()

        asyncio.run(run_test())

    # ── 4. Owner Registration Flow ─────────────────────────────────────────────
    def test_owner_complete_submission_flow(self):
        async def run_test():
            # 1. owner_start
            update = SimpleNamespace(
                effective_user=SimpleNamespace(id=100, username="seller_user", first_name="Seller"),
                message=SimpleNamespace(text=strings.ROLE_SELLER, reply_text=AsyncMock())
            )
            context = SimpleNamespace(user_data={}, bot=SimpleNamespace())
            res1 = await main.owner_start(update, context)
            self.assertEqual(res1, main.OWNER_MENU)
            self.assertEqual(context.user_data["listing_type"], "property")

            # 2. owner_add_new
            res2 = await main.owner_add_new(update, context)
            self.assertEqual(res2, main.OWNER_CATEGORY)

            # 3. owner_category
            update.message.text = strings.CATEGORY_HOUSE
            res3 = await main.owner_category(update, context)
            self.assertEqual(res3, main.OWNER_TITLE)

            # 4. owner_title
            update.message.text = "Modern Villa"
            res4 = await main.owner_title(update, context)
            self.assertEqual(res4, main.OWNER_CITY)

            # 5. owner_city (pick city)
            update.message.text = "አዲስ አበባ/ዙሪያ"
            res5_a = await main.owner_city(update, context)
            self.assertEqual(res5_a, main.OWNER_CITY)

            # 6. owner_city (pick neighborhood)
            update.message.text = "ቦሌ"
            res5_b = await main.owner_city(update, context)
            self.assertEqual(res5_b, main.OWNER_PRICE)

            # 7. owner_price
            update.message.text = "2500000"
            res6 = await main.owner_price(update, context)
            self.assertEqual(res6, main.OWNER_PHOTO)

            # 8. owner_skip_photo
            res7 = await main.owner_skip_photo(update, context)
            self.assertEqual(res7, main.OWNER_CONTACT)

            # 9. owner_contact -> stores pending listing
            update.message.text = "0911001122"
            update.message.contact = None
            res8 = await main.owner_contact(update, context)
            self.assertEqual(res8, main.OWNER_PAYMENT)
            pending_id = context.user_data.get("listing_id")
            self.assertIsNotNone(pending_id)

            # 10. owner_submit_txid
            update.message.text = "TX998877"
            update.message.photo = None
            res9 = await main.owner_submit_txid(update, context)
            listing = database.get_listing_by_id(pending_id)
            self.assertEqual(listing[11], "TX998877")

        asyncio.run(run_test())

    # ── 5. Seeker Search & Looking For Flow ────────────────────────────────────
    def test_seeker_search_and_looking_for_flow(self):
        async def run_test():
            # Add an active listing to search for
            lid = database.add_listing(100, "Toyota Yaris 2020", "አዲስ አበባ/ዙሪያ - ቦሌ", "1200000", None, "0911000000", listing_type="property", property_purpose="sell")
            database.approve_listing(lid)

            # 1. Seeker execute search
            update = SimpleNamespace(
                effective_user=SimpleNamespace(id=200, username="seeker_user", first_name="Seeker"),
                effective_chat=SimpleNamespace(id=200),
                message=SimpleNamespace(text="Toyota", reply_text=AsyncMock())
            )
            bot = SimpleNamespace(send_message=AsyncMock(), send_photo=AsyncMock(), send_media_group=AsyncMock())
            context = SimpleNamespace(user_data={'current_listings': [database.get_listing_by_id(lid)], 'is_for_owner': False}, bot=bot)

            # Test send_listing_page
            await main.send_listing_page(update, context, 0)
            bot.send_message.assert_called_once()

            # 2. Seeker "Looking For" Submission Flow
            context.user_data.clear()
            update.message.text = strings.ROLE_BUYER

            # Start Looking For
            res_lf1 = await main.seeker_looking_for_start(update, context)
            self.assertEqual(res_lf1, main.SEEKER_CATEGORY)

            # Category
            update.message.text = strings.CATEGORY_VEHICLE
            res_lf2 = await main.seeker_category(update, context)
            self.assertEqual(res_lf2, main.SEEKER_CITY)

            # City
            update.message.text = "አዲስ አበባ/ዙሪያ"
            res_lf3 = await main.seeker_browse_city(update, context)
            self.assertEqual(res_lf3, main.SEEKER_CITY)

            # Neighborhood
            update.message.text = "ቦሌ"
            res_lf4 = await main.seeker_browse_city(update, context)
            self.assertEqual(res_lf4, main.SEEKER_LOOKING_FOR_DESC)

            # Description
            update.message.text = "Looking for clean Toyota Corolla 2018+"
            res_lf5 = await main.seeker_looking_for_description(update, context)
            self.assertEqual(res_lf5, main.SEEKER_LOOKING_FOR_PRICE)

            # Price limit
            update.message.text = "1500000 Birr"
            res_lf6 = await main.seeker_looking_for_price(update, context)
            self.assertEqual(res_lf6, main.SEEKER_LOOKING_FOR_CONTACT)

            # Contact
            update.message.text = "0922334455"
            update.message.contact = None
            res_lf7 = await main.seeker_looking_for_contact(update, context)
            self.assertEqual(res_lf7, main.LOOKING_FOR_PAYMENT)
            lf_id = context.user_data.get("looking_for_listing_id")
            self.assertIsNotNone(lf_id)

            # Payment submission for looking for
            update.message.text = "TX_LOOKING_FOR_001"
            update.message.photo = None
            res_lf8 = await main.seeker_looking_for_txid(update, context)
            self.assertEqual(res_lf8, main.CHOOSING_ROLE)

        asyncio.run(run_test())

    # ── 6. Admin Callbacks & Broadcast ──────────────────────────────────────────
    def test_admin_approval_rejection_and_broadcast(self):
        async def run_test():
            lid = database.add_listing(100, "Villa for Sale", "City", "5000000", None, "0911111111", listing_type="property", property_purpose="sell")

            # Callback update for admin approval
            query = SimpleNamespace(
                data=f"approve_{lid}",
                answer=AsyncMock(),
                edit_message_text=AsyncMock(),
                message=SimpleNamespace(text="Pending Listing", photo=None)
            )
            update = SimpleNamespace(
                callback_query=query,
                effective_user=SimpleNamespace(id=100, username="admin_user"),  # admin in test env
                effective_chat=SimpleNamespace(id=100)
            )
            bot = SimpleNamespace(send_message=AsyncMock(), send_photo=AsyncMock(), send_media_group=AsyncMock(), get_me=AsyncMock(return_value=SimpleNamespace(username="demo_bot")))
            context = SimpleNamespace(bot=bot, user_data={})

            with patch.object(main, "post_listing_to_channel", new=AsyncMock()):
                await main.handle_callback(update, context)

            listing = database.get_listing_by_id(lid)
            self.assertEqual(listing[9], "paid")  # status updated to paid/approved

            # Rejection callback
            lid2 = database.add_listing(100, "Spam Listing", "City", "0", None, "0900", listing_type="property", property_purpose="sell")
            query2 = SimpleNamespace(
                data=f"reject_{lid2}",
                answer=AsyncMock(),
                edit_message_text=AsyncMock(),
                message=SimpleNamespace(text="Pending Listing", photo=None)
            )
            update2 = SimpleNamespace(callback_query=query2, effective_user=SimpleNamespace(id=100, username="admin_user"), effective_chat=SimpleNamespace(id=100))
            await main.handle_callback(update2, context)

            listing2 = database.get_listing_by_id(lid2)
            self.assertIsNone(listing2)  # Deleted upon rejection

        asyncio.run(run_test())

    # ── 7. Timeout & Post-Timeout Interactions ──────────────────────────────────
    def test_timeout_and_post_timeout_routing(self):
        async def run_test():
            captured = []
            async def fake_reply(text, *args, **kwargs):
                captured.append(text)

            update = SimpleNamespace(
                effective_user=SimpleNamespace(id=777, username="user"),
                message=SimpleNamespace(text="some text", reply_text=fake_reply),
                effective_message=SimpleNamespace(text="some text", reply_text=fake_reply),
                callback_query=None
            )
            context = SimpleNamespace(user_data={}, bot=SimpleNamespace(), args=[])

            # 1. Timeout occurs on non-/start text update -> triggers TIMEOUT_MSG immediately
            await main.timeout_handler(update, context)
            self.assertEqual(captured, [strings.TIMEOUT_MSG])
            self.assertNotIn("pending_timeout_message", context.user_data)

            # 2. Explicit /start afterwards discards timeout notice and shows welcome
            captured.clear()
            update.message.text = "/start"
            update.effective_message.text = "/start"
            context.user_data["pending_timeout_message"] = strings.TIMEOUT_MSG

            with patch.object(main, "is_subscribed", AsyncMock(return_value=True)):
                await main.start(update, context)

            self.assertEqual(captured, [strings.WELCOME_MSG])

        asyncio.run(run_test())

    # ── 8. Watermarking ─────────────────────────────────────────────────────────
    def test_watermark_processing(self):
        from PIL import Image
        img = Image.new('RGB', (100, 100), color='red')
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        raw_bytes = buf.getvalue()

        watermarked_bio = watermark.apply_watermark(raw_bytes)
        watermarked_bytes = watermarked_bio.getvalue()
        self.assertTrue(len(watermarked_bytes) > 0)


if __name__ == "__main__":
    unittest.main()
