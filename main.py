import os
import html
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import quote, urlparse
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    PicklePersistence,
)

import strings
import database
import watermark
import location_options

# Enable logging
is_production = os.getenv("ENV", "").lower() == "production"

log_handlers = [logging.StreamHandler()]
if not is_production:
    log_handlers.append(logging.FileHandler("bot_debug.log", encoding='utf-8'))

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=log_handlers
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
CHANNEL_ID = os.getenv("CHANNEL_ID")
# Channel username for subscription check (without @)
SUBSCRIPTION_CHANNEL = os.getenv("SUBSCRIPTION_CHANNEL", "gebeya_mereja_266")
MAX_LISTING_PHOTOS = 5

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set!")

# ─── Conversation States ───────────────────────────────────────────────────────
(
    CHOOSING_ROLE,
    OWNER_TITLE,
    OWNER_CATEGORY,
    OWNER_CITY,
    OWNER_PRICE,
    OWNER_PHOTO,
    OWNER_CONTACT,
    OWNER_PAYMENT,
    SEEKER_MENU,
    SEEKER_CITY,
    SEARCH_QUERY,
    ADMIN_BROADCAST,
    OWNER_MENU,
    SEEKER_CATEGORY,
    SEEKER_LOOKING_FOR_DESC,
    SEEKER_LOOKING_FOR_CONTACT,
    LOOKING_FOR_PAYMENT,
    SEEKER_LOOKING_FOR_PURPOSE,
    OWNER_LOOKING_FOR_DATE,
    SEEKER_LOOKING_FOR_PRICE,
) = range(20)


# ─── Subscription Check ────────────────────────────────────────────────────────

async def is_subscribed(bot, user_id: int) -> bool:
    """Return True if the user is a member of the subscription channel."""
    try:
        member = await bot.get_chat_member(chat_id=f"@{SUBSCRIPTION_CHANNEL}", user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        logger.warning(f"Could not check subscription for {user_id}: {e}")
        # If we can't check (e.g. bot not in channel), allow through
        return True


async def send_subscribe_prompt(update: Update):
    """Send the subscription prompt with a join + verify button."""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 ቻናሉን ይቀላቀሉ (Join Channel)", url=strings.SUBSCRIBE_CHANNEL_URL)],
        [InlineKeyboardButton(strings.SUBSCRIBE_BTN, callback_data="check_subscription")],
    ])
    await update.message.reply_text(
        strings.SUBSCRIBE_PROMPT,
        reply_markup=keyboard,
        parse_mode='HTML'
    )


# ─── Keyboards ────────────────────────────────────────────────────────────────

def get_main_keyboard():
    keyboard = [
        [strings.ROLE_SELLER, strings.ROLE_LANDLORD],
        [strings.ROLE_BUYER, strings.ROLE_RENTER],
        [strings.ROLE_SERVICE_PROVIDER, strings.ROLE_SERVICE_SEEKER],
        [strings.HELP_BTN]
    ]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)


def get_seeker_menu_keyboard():
    keyboard = [
        [strings.SEEKER_SEARCH],
        [strings.SEEKER_LOOKING_FOR],
        [strings.BACK],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_photo_keyboard():
    """Keyboard shown while user is uploading photos."""
    return ReplyKeyboardMarkup(
        [[strings.DONE_PHOTOS_BTN], [strings.SKIP], [strings.CANCEL]],
        resize_keyboard=True
    )


def get_listing_type_from_row(item):
    """Return the listing_type for a DB row, supporting both migrated and fresh schema variations.

    - Migrated SQLite: index 12 = listing_type ('property', 'service', 'looking_for')
    - Fresh schema:   index 13 = listing_type ('property', 'service', 'looking_for')
    """
    if not isinstance(item, (list, tuple)):
        return "property"
    for index in (12, 13, 14, 7, 8):
        if len(item) > index and item[index] in {"property", "service", "looking_for"}:
            return item[index]
    for val in item:
        if isinstance(val, str) and val in {"property", "service", "looking_for"}:
            return val
    return "property"


def get_property_purpose_from_row(item):
    """Return the property purpose for a DB row, supporting both migrated and fresh schema variations.

    - Migrated SQLite: index 13 = property_purpose ('buy', 'sell', 'rent', 'service')
    - Fresh schema:   index 7  = property_purpose ('buy', 'sell', 'rent', 'service')
    """
    if item is None:
        return None

    if isinstance(item, dict):
        for key in ("property_purpose", "purpose", "listing_purpose", "propertyPurpose"):
            value = item.get(key)
            if value in {"buy", "sell", "rent", "service"}:
                return value
        return None

    if hasattr(item, "keys"):
        for key in ("property_purpose", "purpose", "listing_purpose", "propertyPurpose"):
            try:
                value = item[key]
                if value in {"buy", "sell", "rent", "service"}:
                    return value
            except Exception:
                pass

    if isinstance(item, (list, tuple)):
        # Check index 13 (migrated SQLite) then index 7 (fresh schema)
        for index in (13, 7, 6, 8, 12, 14):
            if len(item) > index and item[index] in {"buy", "sell", "rent", "service"}:
                return item[index]
        for val in item:
            if isinstance(val, str) and val in {"buy", "sell", "rent", "service"}:
                return val
    return None


def get_listing_type_display_name(listing_type_val, property_purpose_val, title=None):
    """Return the human-readable Amharic label for a listing type/purpose.

    For regular listings (property/service) we show what is offered.
    For looking_for listings we show what the seeker is looking for.
    """
    if listing_type_val == 'looking_for':
        if property_purpose_val == 'buy':
            return 'ግዢ'
        if property_purpose_val == 'rent':
            return 'ኪራይ'
        if property_purpose_val == 'service':
            return 'አገልግሎት'
        return 'ፍላጎት'

    if listing_type_val == 'service' or property_purpose_val == 'service':
        return 'አገልግሎት'
    if property_purpose_val == 'sell':
        return 'ሽያጭ'
    if property_purpose_val == 'rent':
        return 'ኪራይ'

    # Intelligent fallback for old rows missing property_purpose:
    if title:
        title_str = str(title).lower()
        if "ኪራይ" in title_str or "ተከራይ" in title_str:
            return 'ኪራይ'
        if "ሽያጭ" in title_str or "ተሸጫ" in title_str or "ኮንዶሚኒየም" in title_str or "ቤት" in title_str:
            return 'ሽያጭ'
        if "አገልግሎት" in title_str:
            return 'አገልግሎት'

    return 'ሽያጭ/ኪራይ' if listing_type_val == 'property' else 'አገልግሎት'


def get_listing_title(listing_type_val, property_purpose_val, title=None):
    """Return a purpose-specific title for regular listing postings."""
    if listing_type_val == 'service' or property_purpose_val == 'service':
        return 'አገልግሎት'
    if property_purpose_val == 'sell':
        return 'ለሽያጭ የቀረበ'
    if property_purpose_val == 'rent':
        return 'ለኪራይ የቀረበ'

    if title:
        title_str = str(title).lower()
        if "ኪራይ" in title_str or "ተከራይ" in title_str:
            return 'ለኪራይ የቀረበ'
        if "ሽያጭ" in title_str or "ተሸጫ" in title_str:
            return 'ለሽያጭ የቀረበ'

    return 'ለሽያጭ/ለኪራይ የቀረበ'


def get_looking_for_title(property_purpose_val):
    """Return a purpose-specific title for looking-for postings."""
    if property_purpose_val == 'buy':
        return 'ፈላጊ — ለግዢ'
    if property_purpose_val == 'rent':
        return 'ፈላጊ — ለኪራይ'
    if property_purpose_val == 'service':
        return 'ፈላጊ — አገልግሎት'
    return 'ፍላጎት — ተፈላጊ'


def get_listing_status_from_row(item):
    """Return the listing status from a DB row, supporting all schema variations."""
    if not isinstance(item, (list, tuple)):
        return None
    for index in (8, 9, 7, 10):
        if len(item) > index and item[index] in {"pending", "paid", "rented", "expired"}:
            return item[index]
    for val in item:
        if isinstance(val, str) and val in {"pending", "paid", "rented", "expired"}:
            return val
    return None


def get_listing_transaction_id_from_row(item):
    """Return the transaction_id for a DB row, supporting all schema variations."""
    if item is None:
        return None

    if isinstance(item, dict):
        return item.get("transaction_id")

    if not isinstance(item, (list, tuple)):
        return None

    # Current schema: index 11 = transaction_id
    # Older/migrated rows may still use variant offsets.
    for index in (11, 10, 12, 13):
        if len(item) > index and item[index] is not None:
            return item[index]

    return None


def get_listing_created_at(item):
    """Return the created_at date for a DB row, supporting fresh and migrated schema variations."""
    if item is None:
        return None

    if isinstance(item, dict):
        for key in ("created_at", "createdAt", "date", "registered_at"):
            value = item.get(key)
            if value not in (None, ""):
                return value
        return None

    if hasattr(item, "keys"):
        for key in ("created_at", "createdAt", "date", "registered_at"):
            try:
                value = item[key]
            except Exception:
                continue
            if value not in (None, ""):
                return value
        return None

    if isinstance(item, (list, tuple)):
        for index in (8, 7, 9):
            if len(item) <= index:
                continue
            value = item[index]
            if isinstance(value, str) and value.strip():
                text = value.strip()
                if text in {"pending", "paid", "rented", "expired", "buy", "sell", "rent", "service", "property", "looking_for"}:
                    continue
                if text.startswith(("20", "19")) and ("-" in text or "/" in text or ":" in text):
                    return text
            elif isinstance(value, (int, float)):
                continue
        return None

    return None


def _create_pending_submission(context, owner_id, title, location, price, photos_str, contact, fee_amount, listing_type, property_purpose):
    """Create a pending submission record that is only promoted after admin approval."""
    return database.add_listing(
        owner_id,
        title,
        location,
        price,
        photos_str,
        contact,
        fee_amount=fee_amount,
        listing_type=listing_type,
        property_purpose=property_purpose,
    )


# ─── Start & Cancel ───────────────────────────────────────────────────────────

def reset_conversation_state(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear draft and pagination state so a new flow starts cleanly."""
    keys_to_clear = [
        "title", "category", "city", "location", "neighborhood", "price", "photos",
        "contact", "fee", "listing_id", "current_listings", "is_for_owner",
        "listing_type", "sub_role", "seeker_listing_type", "seeker_property_purpose",
        "seeker_category", "seeker_city", "seeker_neighborhood", "looking_for_city",
        "looking_for_neighborhood", "looking_for_desc", "looking_for_price",
        "looking_for_contact", "looking_for_listing_id", "looking_for_purpose",
        "in_looking_for_post", "in_looking_for_search", "lf_search_city",
        "lf_search_neighborhood", "last_media_group_ids",
    ]
    for key in keys_to_clear:
        context.user_data.pop(key, None)


def mark_admin_action_processed(context, listing_id, action):
    """Prevent the same approve/reject callback from being processed twice."""
    bot_data = getattr(context, "bot_data", None)
    if bot_data is None:
        bot_data = {}
        context.bot_data = bot_data

    processed_actions = bot_data.setdefault("processed_admin_actions", {})
    key = f"{action}:{listing_id}"
    if key in processed_actions:
        return True
    processed_actions[key] = True
    return False


async def check_and_send_timeout_notice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Send timeout notice only if pending_timeout_message is queued and interaction is NOT /start."""
    if not update:
        return False

    eff_msg = getattr(update, "effective_message", None) or getattr(update, "message", None)
    user_text = (getattr(eff_msg, "text", "") or "").strip()

    if user_text.startswith("/start"):
        context.user_data.pop("pending_timeout_message", None)
        return False

    pending_msg = context.user_data.pop("pending_timeout_message", None)
    if pending_msg:
        reset_conversation_state(context)
        if eff_msg:
            await eff_msg.reply_text(
                pending_msg,
                reply_markup=get_main_keyboard()
            )
        elif getattr(update, "callback_query", None) and update.callback_query.message:
            await update.callback_query.message.reply_text(
                pending_msg,
                reply_markup=get_main_keyboard()
            )
        return True
    return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Received start command from {update.effective_user.id}")
    user = update.effective_user
    database.add_user(user.id, user.username)

    # Discard any pending timeout message silently when /start is explicitly invoked
    context.user_data.pop("pending_timeout_message", None)
    reset_conversation_state(context)

    if user.id in ADMIN_IDS:
        database.add_user(user.id, user.username, role='admin')
        await update.message.reply_text(strings.ADMIN_TITLE)

    # Check for deep-linking arguments (e.g., /start view_123)
    if context.args and context.args[0].startswith("view_"):
        try:
            view_id = int(context.args[0].split("_")[1])
            target_listing = database.get_listing_by_id(view_id)
            if target_listing:
                context.user_data['current_listings'] = [target_listing]
                context.user_data['is_for_owner'] = False
                await send_listing_page(update, context, 0)
                await update.message.reply_text(
                    "👇 ከታች ካሉት አማራጮች ይምረጡ፦",
                    reply_markup=get_main_keyboard()
                )
                return CHOOSING_ROLE
            else:
                await update.message.reply_text(
                    "❌ የተጠየቀው መረጃ አልተገኘም ወይም ተሰርዟል።",
                    reply_markup=get_main_keyboard()
                )
                return CHOOSING_ROLE
        except Exception as e:
            logger.error(f"Error handling deep link parameter: {e}")
            await update.message.reply_text(
                "❌ መረጃውን በማቅረብ ላይ ስህተት ተፈጥሯል።",
                reply_markup=get_main_keyboard()
            )
            return CHOOSING_ROLE

    # Subscription check (skip for admins)
    if user.id not in ADMIN_IDS:
        subscribed = await is_subscribed(context.bot, user.id)
        if not subscribed:
            await send_subscribe_prompt(update)
            return CHOOSING_ROLE

    await update.message.reply_text(
        strings.WELCOME_MSG,
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )
    return CHOOSING_ROLE


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_conversation_state(context)
    await update.message.reply_text(
        strings.CANCEL_MSG, reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def timeout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Queue pending timeout notice when conversation times out, but do NOT send it yet."""
    context.user_data["pending_timeout_message"] = strings.TIMEOUT_MSG
    reset_conversation_state(context)
    return ConversationHandler.END


async def handle_post_timeout_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Catch-all message handler for post-timeout or unmatched non-command interactions."""
    await check_and_send_timeout_notice(update, context)


# ─── Subscription Callback ────────────────────────────────────────────────────

async def handle_check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the 'I joined the channel' button."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    subscribed = await is_subscribed(context.bot, user.id)
    if subscribed:
        await query.edit_message_text(strings.SUBSCRIBED_OK, parse_mode='HTML')
        await context.bot.send_message(
            chat_id=user.id,
            text=strings.WELCOME_MSG,
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
    else:
        await query.edit_message_text(strings.NOT_SUBSCRIBED_MSG, parse_mode='HTML',
                                      reply_markup=InlineKeyboardMarkup([
                                          [InlineKeyboardButton("📢 ቻናሉን ይቀላቀሉ", url=strings.SUBSCRIBE_CHANNEL_URL)],
                                          [InlineKeyboardButton(strings.SUBSCRIBE_BTN, callback_data="check_subscription")],
                                      ]))


# ─── Input Validation Helpers ─────────────────────────────────────────────────

def count_words(text: str) -> int:
    """Return the word count of a given string after stripping whitespace."""
    if not text:
        return 0
    return len(text.strip().split())


async def validate_input_limits(update: Update, text: str, max_words: int, max_chars: int) -> bool:
    """Validate word and character limits. Send reply and return False if invalid."""
    if not text or not update or not update.message:
        return True

    word_count = count_words(text)
    if word_count > max_words:
        await update.message.reply_text(
            strings.WORD_LIMIT_EXCEEDED.format(max_words=max_words, count=word_count)
        )
        return False

    char_count = len(text.strip())
    if char_count > max_chars:
        await update.message.reply_text(
            strings.CHAR_LIMIT_EXCEEDED.format(max_chars=max_chars, count=char_count)
        )
        return False

    return True


# ─── Location helpers ─────────────────────────────────────────────────────────

def parse_city_and_location(value: str):
    raw = (value or "").strip()
    if not raw:
        return "", ""

    for sep in [" - ", " -", "- ", " / ", "/", ",", ";"]:
        if sep in raw:
            parts = [part.strip() for part in raw.split(sep, 1)]
            if len(parts) == 2:
                return parts[0], parts[1]

    return raw, ""


# ─── Owner Flow ───────────────────────────────────────────────────────────────

async def owner_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_conversation_state(context)
    role_text = update.message.text
    if role_text == strings.ROLE_SERVICE_PROVIDER:
        context.user_data["listing_type"] = 'service'
        context.user_data["sub_role"] = strings.ROLE_SERVICE_PROVIDER
    elif role_text == strings.ROLE_SELLER:
        context.user_data["listing_type"] = 'property'
        context.user_data["sub_role"] = strings.ROLE_SELLER
    else:  # ROLE_LANDLORD
        context.user_data["listing_type"] = 'property'
        context.user_data["sub_role"] = strings.ROLE_LANDLORD

    keyboard = [[strings.OWNER_ADD_NEW], [strings.OWNER_MANAGE], [strings.OWNER_VIEW_LOOKING_FOR], [strings.BACK]]
    await update.message.reply_text(
        strings.OWNER_MENU_MSG, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return OWNER_MENU

async def owner_view_looking_for(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["in_looking_for_search"] = True
    context.user_data["in_looking_for_post"] = False
    # Map owner role to the corresponding looking-for purpose
    context.user_data["seeker_listing_type"] = 'looking_for'
    sub_role = context.user_data.get("sub_role", "")
    if sub_role == strings.ROLE_SELLER:
        context.user_data["seeker_property_purpose"] = 'buy'
    elif sub_role == strings.ROLE_LANDLORD:
        context.user_data["seeker_property_purpose"] = 'rent'
    elif sub_role == strings.ROLE_SERVICE_PROVIDER:
        context.user_data["seeker_property_purpose"] = 'service'
    else:
        context.user_data["seeker_property_purpose"] = None
    return await seeker_ask_category(update, context)


async def owner_add_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show category selection keyboard based on the role chosen on the home screen."""
    listing_type = context.user_data.get("listing_type", "property")

    if listing_type == "service":
        categories = [
            [strings.SERVICE_CATEGORY_HOUSE],
            [strings.SERVICE_CATEGORY_VEHICLE],
            [strings.SERVICE_CATEGORY_ELECTRONICS],
            [strings.SERVICE_CATEGORY_COSMETICS],
            [strings.SERVICE_CATEGORY_OTHER],
        ]
    else:
        categories = [
            [strings.CATEGORY_HOUSE],
            [strings.CATEGORY_VEHICLE],
            [strings.CATEGORY_FURNITURE],
            [strings.CATEGORY_ELECTRONICS],
            [strings.CATEGORY_COSMETICS],
            [strings.CATEGORY_OTHER],
        ]
    categories.append([strings.CANCEL])

    await update.message.reply_text(
        strings.OWNER_ASK_CATEGORY,
        reply_markup=ReplyKeyboardMarkup(categories, resize_keyboard=True, one_time_keyboard=True)
    )
    return OWNER_CATEGORY


async def owner_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save chosen category then ask for the listing description."""
    context.user_data["category"] = update.message.text
    await update.message.reply_text(
        strings.OWNER_START,
        reply_markup=ReplyKeyboardMarkup([[strings.CANCEL]], resize_keyboard=True)
    )
    return OWNER_TITLE


async def owner_manage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    listing_type = context.user_data.get("listing_type", "property")
    sub_role = context.user_data.get("sub_role", "")
    property_purpose = None
    if listing_type == 'property':
        if sub_role == strings.ROLE_SELLER:
            property_purpose = 'sell'
        elif sub_role == strings.ROLE_LANDLORD:
            property_purpose = 'rent'
    listings = database.get_listings_by_owner(user_id, listing_type=listing_type, property_purpose=property_purpose)

    if not listings:
        await update.message.reply_text(strings.OWNER_NO_LISTINGS)
        return OWNER_MENU

    context.user_data['current_listings'] = listings
    context.user_data['is_for_owner'] = True
    await send_listing_page(update, context, 0)
    return OWNER_MENU




async def owner_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if not await validate_input_limits(update, text, max_words=100, max_chars=500):
        return OWNER_TITLE

    category_prefix = context.user_data.get("category", "")
    if category_prefix:
        context.user_data["title"] = f"{category_prefix} - {text}"
    else:
        context.user_data["title"] = text
    # Ask city — pass no pre-selected city yet
    context.user_data.pop("city", None)
    keyboard = ReplyKeyboardMarkup(location_options.get_city_keyboard(), resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(strings.OWNER_ASK_CITY, reply_markup=keyboard)
    return OWNER_CITY


async def owner_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    selected_value = update.message.text.strip()
    city = context.user_data.get("city")

    if not city:
        if selected_value not in location_options.CITY_OPTIONS:
            await update.message.reply_text(
                strings.OWNER_ASK_CITY,
                reply_markup=ReplyKeyboardMarkup(location_options.get_city_keyboard(), resize_keyboard=True, one_time_keyboard=True),
            )
            return OWNER_CITY

        context.user_data["city"] = selected_value
        neighborhood_keyboard = location_options.get_neighborhood_keyboard(selected_value)
        keyboard = ReplyKeyboardMarkup(neighborhood_keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(strings.OWNER_ASK_LOCATION, reply_markup=keyboard)
        return OWNER_CITY

    # Now picking neighborhood
    city_value = context.user_data["city"]
    valid_neighborhoods = location_options.get_neighborhoods_for_city(city_value)
    if selected_value not in valid_neighborhoods:
        neighborhood_keyboard = location_options.get_neighborhood_keyboard(city_value)
        keyboard = ReplyKeyboardMarkup(neighborhood_keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(strings.OWNER_ASK_LOCATION, reply_markup=keyboard)
        return OWNER_CITY

    context.user_data["neighborhood"] = selected_value
    context.user_data["location"] = location_options.build_location_string(city_value, selected_value)
    await update.message.reply_text(
        strings.OWNER_ASK_PRICE,
        reply_markup=ReplyKeyboardMarkup([[strings.CANCEL]], resize_keyboard=True)
    )
    return OWNER_PRICE


async def owner_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import re
    price_text = update.message.text.strip()
    if not price_text:
        await update.message.reply_text(strings.PRICE_INVALID)
        return OWNER_PRICE

    if not await validate_input_limits(update, price_text, max_words=15, max_chars=100):
        return OWNER_PRICE

    # Try to extract a numeric value; if none, accept the text as-is (descriptive price)
    cleaned = re.sub(r'[^\d.]', '', price_text.replace(',', ''))
    if cleaned:
        try:
            price_val = float(cleaned)
            if price_val <= 0:
                raise ValueError
            context.user_data["price"] = price_text  # store original text
        except (ValueError, TypeError):
            await update.message.reply_text(strings.PRICE_INVALID)
            return OWNER_PRICE
    else:
        # Descriptive price like "ሶስት ሺ ብር" — accept it
        if len(price_text) < 2:
            await update.message.reply_text(strings.PRICE_INVALID)
            return OWNER_PRICE
        context.user_data["price"] = price_text

    # Reset photo list and show multi-photo prompt
    context.user_data["photos"] = []
    await update.message.reply_text(
        strings.OWNER_ASK_PHOTO.format(max_photos=MAX_LISTING_PHOTOS),
        reply_markup=get_photo_keyboard(),
        parse_mode='HTML'
    )
    return OWNER_PHOTO


def _looks_like_phone_number(text: str) -> bool:
    import re
    if not text:
        return False
    cleaned = re.sub(r'[^0-9+]', '', text)
    return bool(re.search(r'\d{7,}', cleaned))


async def owner_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming photos — keep collecting until user presses 'Finished' or reaches MAX_LISTING_PHOTOS."""
    if "photos" not in context.user_data:
        context.user_data["photos"] = []

    if update.message.photo:
        if len(context.user_data["photos"]) >= MAX_LISTING_PHOTOS:
            await update.message.reply_text(
                strings.PHOTO_LIMIT_REACHED_AUTO_ADVANCE.format(max_photos=MAX_LISTING_PHOTOS),
                parse_mode='HTML'
            )
            return await owner_done_photo(update, context)

        try:
            photo_file = await update.message.photo[-1].get_file()
            photo_bytes = await photo_file.download_as_bytearray()
            watermarked = watermark.apply_watermark(bytes(photo_bytes))
            sent = await update.message.reply_photo(photo=watermarked, caption="✅ ፎቶ ተቀብሏል (watermarked)")
            photo_id = sent.photo[-1].file_id
        except Exception as e:
            logger.warning(f"Watermark failed, using original: {e}")
            photo_id = update.message.photo[-1].file_id

        context.user_data["photos"].append(photo_id)
        count = len(context.user_data["photos"])

        if count >= MAX_LISTING_PHOTOS:
            await update.message.reply_text(
                strings.PHOTO_LIMIT_REACHED_AUTO_ADVANCE.format(max_photos=MAX_LISTING_PHOTOS),
                parse_mode='HTML'
            )
            return await owner_done_photo(update, context)

        await update.message.reply_text(
            strings.PHOTO_ADDED_MSG.format(count=count),
            reply_markup=get_photo_keyboard(),
            parse_mode='HTML'
        )
        return OWNER_PHOTO

    # Text received while in photo state
    return await owner_photo_text(update, context)


async def owner_photo_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages in the photo upload state."""
    if update.message.contact:
        context.user_data["contact"] = update.message.contact.phone_number
        return await owner_contact(update, context)

    text = update.message.text.strip() if update.message.text else ""

    if text in (strings.SKIP, "/skip", "ዝለል"):
        return await owner_skip_photo(update, context)

    if text in (strings.DONE, strings.DONE_PHOTOS_BTN, "📸 ፎቶ መጫን ጨርሻለሁ"):
        return await owner_done_photo(update, context)

    if _looks_like_phone_number(text):
        return await owner_contact(update, context)

    await update.message.reply_text(
        strings.OWNER_ASK_PHOTO.format(max_photos=MAX_LISTING_PHOTOS),
        reply_markup=get_photo_keyboard(),
        parse_mode='HTML'
    )
    return OWNER_PHOTO


async def owner_skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["photos"] = []
    await update.message.reply_text(
        strings.OWNER_ASK_CONTACT,
        reply_markup=ReplyKeyboardMarkup([[strings.CANCEL]], resize_keyboard=True)
    )
    return OWNER_CONTACT


async def owner_done_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "photos" not in context.user_data or not context.user_data["photos"]:
        context.user_data["photos"] = []

    await update.message.reply_text(
        strings.OWNER_ASK_CONTACT,
        reply_markup=ReplyKeyboardMarkup([[strings.CANCEL]], resize_keyboard=True)
    )
    return OWNER_CONTACT


async def owner_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.contact:
        context.user_data["contact"] = update.message.contact.phone_number
    else:
        text = update.message.text.strip() if update.message.text else ""
        if not await validate_input_limits(update, text, max_words=10, max_chars=50):
            return OWNER_CONTACT
        context.user_data["contact"] = text

    user_id = update.effective_user.id

    # Fixed 50 birr fee
    fee = strings.FIXED_FEE
    context.user_data["fee"] = fee

    # Join photo IDs with comma
    photos_str = ",".join(context.user_data.get("photos", [])) if context.user_data.get("photos") else None

    # Determine property purpose for property listings (sell vs rent)
    property_purpose = None
    if context.user_data.get("listing_type") == 'property':
        sub = context.user_data.get("sub_role", "")
        if sub == strings.ROLE_SELLER:
            property_purpose = 'sell'
        elif sub == strings.ROLE_LANDLORD:
            property_purpose = 'rent'

    listing_id = _create_pending_submission(
        context,
        user_id,
        context.user_data["title"],
        context.user_data["location"],
        context.user_data["price"],
        photos_str,
        context.user_data["contact"],
        fee_amount=fee,
        listing_type=context.user_data.get("listing_type", "property"),
        property_purpose=property_purpose,
    )
    context.user_data["listing_id"] = listing_id

    payment_prompt = (
        strings.OWNER_ASK_PAYMENT_SERVICE
        if context.user_data.get("listing_type") == "service"
        else strings.OWNER_ASK_PAYMENT_PROPERTY
    )
    try:
        await update.message.reply_text(
            payment_prompt,
            reply_markup=ReplyKeyboardMarkup([[strings.CANCEL]], resize_keyboard=True),
            parse_mode='HTML'
        )
    except BadRequest as e:
        logger.error(f"BadRequest sending payment prompt; falling back to plain text. error={e}")
        await update.message.reply_text(
            payment_prompt,
            reply_markup=ReplyKeyboardMarkup([[strings.CANCEL]], resize_keyboard=True),
            parse_mode=None
        )
    return OWNER_PAYMENT


async def owner_submit_txid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        payment_photo_id = update.message.photo[-1].file_id
        txid = f"photo:{payment_photo_id}"
        display_txid = "[ክፍያ ስክሪንሾት ተልኳል / Screenshot]"
    else:
        payment_photo_id = None
        txid = update.message.text.strip() if update.message.text else ""
        if not await validate_input_limits(update, txid, max_words=10, max_chars=100):
            return OWNER_PAYMENT
        display_txid = txid

    listing_id = context.user_data.get("listing_id")
    if not listing_id:
        await update.message.reply_text(
            "❌ የክፍያ ማረጋገጫ ማስተላለፍ አልተቻለም። እንደገና ይጀምሩ /start",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        return CHOOSING_ROLE

    database.update_listing_txid(listing_id, txid)

    # Notify Admin
    owner = update.effective_user.username or update.effective_user.first_name

    listing_type = context.user_data.get("listing_type", "property")
    sub_role = context.user_data.get("sub_role", "")
    if listing_type == "service":
        listing_type_am = "አገልግሎት"
    elif sub_role == strings.ROLE_SELLER:
        listing_type_am = "ሽያጭ"
    elif sub_role == strings.ROLE_LANDLORD:
        listing_type_am = "ኪራይ"
    else:
        listing_type_am = "ያልታወቀ"

    admin_msg = strings.ADMIN_APPROVE_REQ.format(
        owner=owner,
        title=context.user_data["title"],
        city=context.user_data.get("city", "አልተገለጸም"),
        neighborhood=context.user_data.get("neighborhood", "አልተገለጸም"),
        contact=context.user_data["contact"],
        price=context.user_data["price"],
        listing_type_am=listing_type_am,
        txid=display_txid
    )

    keyboard = [
        [
            InlineKeyboardButton(strings.ADMIN_APPROVE, callback_data=f"approve_{listing_id}"),
            InlineKeyboardButton(strings.ADMIN_REJECT, callback_data=f"reject_{listing_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    photo_ids = context.user_data.get("photos", [])

    for admin_id in ADMIN_IDS:
        if payment_photo_id:
            try:
                await context.bot.send_photo(chat_id=admin_id, photo=payment_photo_id, caption="💳 የክፍያ ማረጋገጫ (Payment Proof)")
            except Exception as e:
                logger.error(f"Failed to send payment photo to admin {admin_id}: {e}")
        try:
            if photo_ids:
                if len(photo_ids) == 1:
                    await context.bot.send_photo(chat_id=admin_id, photo=photo_ids[0], caption=admin_msg, reply_markup=reply_markup)
                else:
                    from telegram import InputMediaPhoto
                    media = [InputMediaPhoto(media=photo_ids[0], caption=admin_msg)]
                    for pid in photo_ids[1:]:
                        media.append(InputMediaPhoto(media=pid))
                    await context.bot.send_media_group(chat_id=admin_id, media=media)
                    await context.bot.send_message(chat_id=admin_id, text="መቆጣጠሪያ:", reply_markup=reply_markup)
            else:
                await context.bot.send_message(chat_id=admin_id, text=admin_msg, reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")

    await update.message.reply_text(strings.OWNER_PAYMENT_PENDING, reply_markup=get_main_keyboard())
    return CHOOSING_ROLE


# ─── Seeker Flow ──────────────────────────────────────────────────────────────

async def seeker_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_conversation_state(context)
    role_text = update.message.text
    if role_text == strings.ROLE_BUYER:
        context.user_data["seeker_listing_type"] = 'property'
        context.user_data["seeker_property_purpose"] = 'sell'
    elif role_text == strings.ROLE_RENTER:
        context.user_data["seeker_listing_type"] = 'property'
        context.user_data["seeker_property_purpose"] = 'rent'
    elif role_text == strings.ROLE_SERVICE_SEEKER:
        context.user_data["seeker_listing_type"] = 'service'
        context.user_data["seeker_property_purpose"] = None
    else:
        context.user_data["seeker_listing_type"] = None
        context.user_data["seeker_property_purpose"] = None

    await update.message.reply_text(
        strings.SEEKER_MENU_MSG, reply_markup=get_seeker_menu_keyboard()
    )
    return SEEKER_MENU


async def seeker_ask_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    listing_type = context.user_data.get("seeker_listing_type", "property")
    # When an owner views looking-for listings, listing_type is 'looking_for'
    # Determine service vs property from the purpose
    is_service = (listing_type == "service") or (
        listing_type == "looking_for" and context.user_data.get("seeker_property_purpose") == "service"
    )
    if is_service:
        categories = [
            [strings.SERVICE_CATEGORY_HOUSE],
            [strings.SERVICE_CATEGORY_VEHICLE],
            [strings.SERVICE_CATEGORY_ELECTRONICS],
            [strings.SERVICE_CATEGORY_COSMETICS],
            [strings.SERVICE_CATEGORY_OTHER],
            ["ሁሉም"]
        ]
    else:
        categories = [
            [strings.CATEGORY_HOUSE],
            [strings.CATEGORY_VEHICLE],
            [strings.CATEGORY_FURNITURE],
            [strings.CATEGORY_ELECTRONICS],
            [strings.CATEGORY_COSMETICS],
            [strings.CATEGORY_OTHER],
            ["ሁሉም"]
        ]
    categories.append([strings.CANCEL])

    await update.message.reply_text(
        strings.SEEKER_ASK_CATEGORY,
        reply_markup=ReplyKeyboardMarkup(categories, resize_keyboard=True, one_time_keyboard=True)
    )
    return SEEKER_CATEGORY


async def seeker_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cat = update.message.text
    if "ሁሉም" in cat:
        cat = None
    context.user_data["seeker_category"] = cat
    context.user_data.pop("seeker_city", None)
    context.user_data.pop("seeker_neighborhood", None)
    keyboard = ReplyKeyboardMarkup(location_options.get_city_keyboard(), resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(strings.SEEKER_ASK_CITY, reply_markup=keyboard)
    return SEEKER_CITY


async def view_all_listings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("seeker_city", None)
    context.user_data.pop("seeker_neighborhood", None)
    keyboard = ReplyKeyboardMarkup(location_options.get_city_keyboard(), resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(strings.SEEKER_ASK_CITY, reply_markup=keyboard)
    return SEEKER_CITY


async def seeker_browse_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    selected_value = update.message.text.strip()
    seeker_city = context.user_data.get("seeker_city")

    if not seeker_city:
        if selected_value not in location_options.CITY_OPTIONS:
            keyboard = ReplyKeyboardMarkup(location_options.get_city_keyboard(), resize_keyboard=True, one_time_keyboard=True)
            await update.message.reply_text(strings.SEEKER_ASK_CITY, reply_markup=keyboard)
            return SEEKER_CITY

        context.user_data["seeker_city"] = selected_value
        neighborhood_keyboard = location_options.get_neighborhood_keyboard(selected_value)
        keyboard = ReplyKeyboardMarkup(neighborhood_keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(strings.SEEKER_ASK_SEARCH, reply_markup=keyboard)
        return SEEKER_CITY

    # Neighborhood was selected
    city_value = seeker_city
    valid_neighborhoods = location_options.get_neighborhoods_for_city(city_value)
    if selected_value not in valid_neighborhoods:
        neighborhood_keyboard = location_options.get_neighborhood_keyboard(city_value)
        keyboard = ReplyKeyboardMarkup(neighborhood_keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(strings.SEEKER_ASK_SEARCH, reply_markup=keyboard)
        return SEEKER_CITY

    city = seeker_city
    neighborhood = selected_value
    context.user_data.pop("seeker_city", None)
    context.user_data.pop("seeker_neighborhood", None)

    if context.user_data.get("in_looking_for_post"):
        context.user_data["looking_for_city"] = city
        context.user_data["looking_for_neighborhood"] = neighborhood
        await update.message.reply_text(
            strings.SEEKER_ASK_LOOKING_FOR,
            reply_markup=ReplyKeyboardMarkup([[strings.CANCEL]], resize_keyboard=True),
            parse_mode='HTML'
        )
        return SEEKER_LOOKING_FOR_DESC

    if context.user_data.get("in_looking_for_search"):
        listings = database.get_listings_by_city(
            city,
            listing_type='looking_for',
            property_purpose=context.user_data.get("seeker_property_purpose"),
            category=context.user_data.get("seeker_category"),
        )
        if neighborhood and neighborhood != "ሁሉም":
            listings = [
                listing for listing in listings
                if neighborhood in (listing[3] or "")
            ]

        if not listings:
            await update.message.reply_text(strings.SEEKER_NO_MATCH)
            return SEEKER_MENU

        context.user_data['current_listings'] = listings
        context.user_data['is_for_owner'] = False
        await send_listing_page(update, context, 0)
        return SEEKER_MENU

    listings = database.get_listings_by_city(
        city,
        listing_type=context.user_data.get("seeker_listing_type"),
        property_purpose=context.user_data.get("seeker_property_purpose"),
        category=context.user_data.get("seeker_category"),
    )
    if neighborhood and neighborhood != "ሁሉም":
        listings = [
            listing for listing in listings
            if neighborhood in (listing[3] or "")
        ]

    if not listings:
        await update.message.reply_text(strings.SEEKER_NO_MATCH)
        return SEEKER_MENU

    context.user_data['current_listings'] = listings
    context.user_data['is_for_owner'] = False
    await send_listing_page(update, context, 0)
    return SEEKER_MENU


async def search_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("seeker_city", None)
    context.user_data.pop("seeker_neighborhood", None)
    keyboard = ReplyKeyboardMarkup(location_options.get_city_keyboard(), resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(strings.SEEKER_ASK_CITY, reply_markup=keyboard)
    return SEEKER_CITY


async def execute_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip() if update.message.text else ""
    if not await validate_input_limits(update, query, max_words=15, max_chars=100):
        return SEARCH_QUERY

    if ',' in query:
        city_query, neighborhood_query = [part.strip() for part in query.split(',', 1)]
    else:
        city_query, neighborhood_query = query, None

    listings = database.search_listings_by_location(
        city_query, neighborhood_query,
        listing_type=context.user_data.get("seeker_listing_type"),
        property_purpose=context.user_data.get("seeker_property_purpose"),
        category=context.user_data.get("seeker_category"),
    )
    if not listings:
        await update.message.reply_text(strings.SEEKER_NO_MATCH)
        return SEEKER_MENU

    context.user_data['current_listings'] = listings
    context.user_data['is_for_owner'] = False
    await send_listing_page(update, context, 0)
    return SEEKER_MENU


# ─── "Looking For" (Seeker post a request) ────────────────────────────────────

async def seeker_looking_for_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Seeker clicked 'Looking For' — skip purpose if already known."""
    for key in [
        "looking_for_desc", "looking_for_price", "looking_for_contact",
        "looking_for_city", "looking_for_neighborhood", "looking_for_purpose",
        "looking_for_listing_id", "seeker_category", "seeker_city",
        "seeker_neighborhood", "current_listings", "is_for_owner",
    ]:
        context.user_data.pop(key, None)

    context.user_data["in_looking_for_post"] = True
    context.user_data["in_looking_for_search"] = False

    listing_type = context.user_data.get("seeker_listing_type")
    prop_purpose = context.user_data.get("seeker_property_purpose")

    if listing_type == 'service':
        context.user_data["looking_for_purpose"] = 'service'
    elif prop_purpose == 'sell':
        context.user_data["looking_for_purpose"] = 'buy'
    elif prop_purpose == 'rent':
        context.user_data["looking_for_purpose"] = 'rent'
    else:
        context.user_data["looking_for_purpose"] = None

    return await seeker_ask_category(update, context)





async def seeker_looking_for_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save the description/price text and ask for contact."""
    desc = update.message.text.strip() if update.message.text else ""
    if not desc:
        await update.message.reply_text(strings.SEEKER_ASK_LOOKING_FOR, parse_mode='HTML')
        return SEEKER_LOOKING_FOR_DESC
    if not await validate_input_limits(update, desc, max_words=100, max_chars=500):
        return SEEKER_LOOKING_FOR_DESC
    context.user_data["looking_for_desc"] = desc
    # Ask for price/budget separately
    await update.message.reply_text(
        strings.SEEKER_ASK_LOOKING_FOR_PRICE,
        reply_markup=ReplyKeyboardMarkup([[strings.CANCEL]], resize_keyboard=True)
    )
    return SEEKER_LOOKING_FOR_PRICE


async def seeker_looking_for_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save the price/budget and ask for contact."""
    price = update.message.text.strip() if update.message.text else ""
    if not price:
        await update.message.reply_text(strings.SEEKER_ASK_LOOKING_FOR_PRICE)
        return SEEKER_LOOKING_FOR_PRICE
    if not await validate_input_limits(update, price, max_words=15, max_chars=100):
        return SEEKER_LOOKING_FOR_PRICE
    context.user_data["looking_for_price"] = price
    await update.message.reply_text(
        strings.SEEKER_ASK_CONTACT_FOR_LOOKING,
        reply_markup=ReplyKeyboardMarkup([[strings.CANCEL]], resize_keyboard=True)
    )
    return SEEKER_LOOKING_FOR_CONTACT


async def seeker_looking_for_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save contact, create a pending DB listing, then show the 50-birr payment prompt."""
    if update.message.contact:
        contact = update.message.contact.phone_number
    else:
        contact = update.message.text.strip() if update.message.text else ""
        if not await validate_input_limits(update, contact, max_words=10, max_chars=50):
            return SEEKER_LOOKING_FOR_CONTACT

    user_id = update.effective_user.id
    desc = context.user_data.get("looking_for_desc", "")
    price = context.user_data.get("looking_for_price", "")
    category = context.user_data.get("seeker_category") or "ሁሉም"

    city = context.user_data.get("looking_for_city", "")
    neighborhood = context.user_data.get("looking_for_neighborhood", "")
    location = f"{city} - {neighborhood}" if neighborhood and neighborhood != "ሁሉም" else city

    # Store in DB as a 'looking_for' listing so admin can approve/reject
    # title stores: category + description, price stores: budget
    listing_id = _create_pending_submission(
        context,
        user_id,
        title=f"🔎 ፈላጊ — {category} — {desc}",
        location=location,
        price=price,
        photos_str=None,
        contact=contact,
        fee_amount=strings.FIXED_FEE,
        listing_type='looking_for',
        property_purpose=context.user_data.get("looking_for_purpose"),
    )
    context.user_data["looking_for_listing_id"] = listing_id
    context.user_data["looking_for_contact"] = contact

    # Show 50-birr payment prompt
    try:
        await update.message.reply_text(
            strings.SEEKER_ASK_PAYMENT_LOOKING_FOR,
            reply_markup=ReplyKeyboardMarkup([[strings.CANCEL]], resize_keyboard=True),
            parse_mode='HTML'
        )
    except BadRequest as e:
        logger.error(f"BadRequest sending looking-for payment prompt: {e}")
        await update.message.reply_text(
            strings.SEEKER_ASK_PAYMENT_LOOKING_FOR,
            reply_markup=ReplyKeyboardMarkup([[strings.CANCEL]], resize_keyboard=True),
        )
    return LOOKING_FOR_PAYMENT


async def seeker_looking_for_txid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive payment screenshot/txid and notify admins with Approve/Reject buttons."""
    if update.message.photo:
        payment_photo_id = update.message.photo[-1].file_id
        txid = f"photo:{payment_photo_id}"
        display_txid = "[ክፍያ ስክሪንሾት ተልኳል / Screenshot]"
    else:
        payment_photo_id = None
        txid = update.message.text.strip() if update.message.text else ""
        if not await validate_input_limits(update, txid, max_words=10, max_chars=100):
            return LOOKING_FOR_PAYMENT
        display_txid = txid

    listing_id = context.user_data.get("looking_for_listing_id")
    if not listing_id:
        await update.message.reply_text("❌ ስህተት ተፈጥሯል። እንደገና ይሞክሩ /start")
        return CHOOSING_ROLE

    database.update_listing_txid(listing_id, txid)

    # Build admin notification
    seeker_name = update.effective_user.username or update.effective_user.first_name
    desc = context.user_data.get("looking_for_desc", "")
    category = context.user_data.get("seeker_category") or "ሁሉም"
    contact = context.user_data.get("looking_for_contact", "")

    purpose_val = context.user_data.get("looking_for_purpose", "")
    purpose_am = {"buy": "ግዢ (Buy)", "rent": "ኪራይ (Rent)", "service": "አገልግሎት (Service)"}.get(purpose_val, purpose_val)

    admin_msg = strings.SEEKER_LOOKING_FOR_ADMIN.format(
        seeker=seeker_name,
        category=category,
        city=context.user_data.get("looking_for_city", "አልተገለጸም"),
        neighborhood=context.user_data.get("looking_for_neighborhood", "አልተገለጸም"),
        purpose=purpose_am,
        price=context.user_data.get("looking_for_price", "ያልተገለጸም"),
        description=desc,
        contact=contact,
        txid=display_txid,
    )

    approve_reject = InlineKeyboardMarkup([[
        InlineKeyboardButton(strings.ADMIN_APPROVE, callback_data=f"approve_{listing_id}"),
        InlineKeyboardButton(strings.ADMIN_REJECT, callback_data=f"reject_{listing_id}"),
    ]])

    for admin_id in ADMIN_IDS:
        if payment_photo_id:
            try:
                await context.bot.send_photo(
                    chat_id=admin_id,
                    photo=payment_photo_id,
                    caption="💳 የክፍያ ማረጋገጫ — ፈላጊ ጥያቄ (Payment Proof)"
                )
            except Exception as e:
                logger.error(f"Failed to send looking-for payment photo to admin {admin_id}: {e}")
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=admin_msg,
                reply_markup=approve_reject,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id} about looking-for: {e}")

    await update.message.reply_text(
        strings.SEEKER_LOOKING_FOR_SENT,
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )
    return CHOOSING_ROLE


# ─── Listing Display ──────────────────────────────────────────────────────────

async def _build_gallery_web_app_url(context, photo_ids):
    """Create a Telegram Mini App URL that opens a swipeable gallery for the supplied photos."""
    if not photo_ids:
        return None

    mini_app_url = (os.getenv("MINI_APP_URL") or "").strip()
    if not mini_app_url:
        return None

    photo_urls = []
    for photo_id in photo_ids:
        try:
            file = await context.bot.get_file(photo_id)
            file_path = getattr(file, "file_path", None)
            if file_path:
                photo_urls.append(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}")
        except Exception as e:
            logger.warning(f"Failed to resolve Telegram photo URL for {photo_id}: {e}")

    if not photo_urls:
        return None

    joined_photos = "|".join(photo_urls)
    separator = "&" if "?" in mini_app_url else "?"
    return f"{mini_app_url}{separator}photos={quote(joined_photos)}"


def _is_public_gallery_url(url):
    """Return True when a gallery URL is reachable by Telegram inline keyboard buttons."""
    if not url:
        return False
    try:
        parsed = urlparse(url)
    except ValueError:
        return False

    if parsed.scheme not in ("http", "https"):
        return False

    host = (parsed.hostname or "").lower()
    return host not in {"localhost", "127.0.0.1", "0.0.0.0"}


async def post_listing_to_channel(context, listing, listing_type_val, property_purpose_val, channel_id=None):
    """Post a single main listing to the channel with a gallery button for additional photos."""
    channel_id = channel_id or CHANNEL_ID
    if not channel_id:
        return

    listing_id = None
    if isinstance(listing, dict):
        listing_id = listing.get("id")
    elif isinstance(listing, (list, tuple)) and listing:
        listing_id = listing[0]

    if listing_id is not None and database.is_listing_channel_notified(listing_id):
        logger.info(f"Skipping duplicate channel post for listing {listing_id}")
        return

    if listing_id is not None:
        persisted_listing = database.get_listing_by_id(listing_id)
        if persisted_listing is not None and not database.reserve_listing_channel_notification(listing_id):
            logger.info(f"Another channel post is already being processed for listing {listing_id}")
            return

    listing_type_am = get_listing_type_display_name(listing_type_val, property_purpose_val, listing[2] if len(listing) > 2 else None)
    listing_type_title = get_listing_title(listing_type_val, property_purpose_val, listing[2] if len(listing) > 2 else None)

    created_at = get_listing_created_at(listing) or "ያልተገለጸ"
    text = strings.LISTING_TEMPLATE.format(
        listing_type_title=listing_type_title,
        title=listing[2],
        location=listing[3],
        price=listing[4],
        contact=listing[6],
        listing_type_am=listing_type_am,
        date=created_at,
    )

    bot_username = (await context.bot.get_me()).username
    bot_link = f"https://t.me/{bot_username}"
    view_text = f"\n\n🔗 ወደ ቦቱ ለመግባት: {bot_link}"

    if listing[5]:
        photo_ids = listing[5].split(",") if listing[5] else []
    else:
        photo_ids = []

    deep_link_url = f"https://t.me/{bot_username}?start=view_{listing_id}" if listing_id else bot_link

    try:
        if photo_ids:
            extra_count = len(photo_ids) - 1
            if extra_count > 0:
                caption = text + view_text + f"\n\n📸 +{extra_count} ተጨማሪ ፎቶዎች"
                keyboard_buttons = [
                    [InlineKeyboardButton(f"📸 ሁሉንም ፎቶዎች ይመልከቱ (+{extra_count})", url=deep_link_url)],
                    [InlineKeyboardButton("ወደ ቦቱ ይግቡ", url=bot_link)]
                ]
            else:
                caption = text + view_text
                keyboard_buttons = [[InlineKeyboardButton("ወደ ቦቱ ይግቡ", url=bot_link)]]

            channel_reply_markup = InlineKeyboardMarkup(keyboard_buttons)
            sent_msg = await context.bot.send_photo(
                chat_id=channel_id,
                photo=photo_ids[0],
                caption=caption,
                parse_mode='HTML',
                reply_markup=channel_reply_markup,
            )
            if listing_id is not None:
                database.set_channel_message_id(listing_id, sent_msg.message_id)
        else:
            keyboard_buttons = [[InlineKeyboardButton("ወደ ቦቱ ይግቡ", url=bot_link)]]
            channel_reply_markup = InlineKeyboardMarkup(keyboard_buttons)
            sent_msg = await context.bot.send_message(chat_id=channel_id, text=text + view_text, parse_mode='HTML', reply_markup=channel_reply_markup)
            if listing_id is not None:
                database.set_channel_message_id(listing_id, sent_msg.message_id)

        if listing_id is not None:
            database.mark_listing_channel_notified(listing_id)
    except Exception as e:
        if listing_id is not None:
            database.clear_listing_channel_notification(listing_id)
        logger.exception(f"Failed to post listing {listing[0]} to channel {channel_id}: {e}")
        raise


async def send_listing_page(update: Update, context: ContextTypes.DEFAULT_TYPE, current_idx: int):
    listings = context.user_data.get('current_listings', [])

    if not listings:
        listings = database.get_all_listings()
        context.user_data['current_listings'] = listings
        context.user_data['is_for_owner'] = False
        logger.info(f"DEBUG: Reloaded {len(listings)} listings from DB for pagination")

    if not listings or current_idx < 0 or current_idx >= len(listings):
        return

    for_owner = context.user_data.get('is_for_owner', False)
    is_admin = update.effective_user.id in ADMIN_IDS
    item = listings[current_idx]
    listing_id = item[0]

    from telegram import InputMediaPhoto

    listing_type_val = get_listing_type_from_row(item)
    property_purpose_val = get_property_purpose_from_row(item)

    status_msg = ""
    if for_owner or is_admin:
        status_map = {
            'pending': '⏳ Pending',
            'paid': '✅ Active',
            'rented': '🔒 Unlisted',
            'expired': '⏳ Expired',
        }
        status_value = get_listing_status_from_row(item)
        status_text = status_map.get(status_value, status_value or "Unknown")

        tx_val = get_listing_transaction_id_from_row(item) or ""
        tx_val = str(tx_val) if tx_val is not None else ""
        if tx_val.startswith("photo:"):
            tx_info = "\n🎫 TXID: [ክፍያ ስክሪንሾት (Screenshot)]"
        else:
            tx_info = f"\n🎫 TXID: {tx_val}" if tx_val else ""

        status_msg = f"\n📊 Status: {status_text}{tx_info}"

    page_indicator = f"\n\n📄 {current_idx + 1}/{len(listings)}"

    if listing_type_val == 'looking_for':
        loc = item[3] or ""
        if " - " in loc:
            city_part, neigh_part = loc.split(" - ", 1)
        else:
            city_part, neigh_part = loc, "ሁሉም"

        purpose_map = {"buy": "ግዢ (Buy)", "rent": "ኪራይ (Rent)", "service": "አገልግሎት (Service)"}
        purpose_am = purpose_map.get(property_purpose_val or "", property_purpose_val or "ያልተገለጸ")

        title_raw = item[2] or ""
        title_parts = title_raw.split(" — ")
        if len(title_parts) >= 3:
            category_val = title_parts[1]
            desc_val = " — ".join(title_parts[2:])
        elif len(title_parts) == 2:
            category_val = title_parts[1]
            desc_val = "ያልተገለጸ"
        else:
            category_val = title_raw
            desc_val = "ያልተገለጸ"

        created_at = get_listing_created_at(item) or "ያልተገለጸ"
        text = strings.LOOKING_FOR_LISTING_TEMPLATE.format(
            looking_for_title=html.escape(get_looking_for_title(property_purpose_val)),
            category=html.escape(str(category_val)),
            purpose=html.escape(str(purpose_am)),
            city=html.escape(str(city_part.strip())),
            neighborhood=html.escape(str(neigh_part.strip())),
            price=html.escape(str(item[4] or "ያልተገለጸ")),
            description=html.escape(str(desc_val)),
            contact=html.escape(str(item[6] or "ያልተገለጸ")),
            date=html.escape(str(created_at))
        ) + status_msg + page_indicator
    else:
        listing_type_am = get_listing_type_display_name(listing_type_val, property_purpose_val, item[2] if len(item) > 2 else None)
        listing_type_title = get_listing_title(listing_type_val, property_purpose_val, item[2] if len(item) > 2 else None)

        created_at = get_listing_created_at(item) or "ያልተገለጸ"
        text = strings.LISTING_TEMPLATE.format(
            listing_type_title=html.escape(str(listing_type_title)),
            title=html.escape(str(item[2] or "")),
            location=html.escape(str(item[3] or "")),
            price=html.escape(str(item[4] or "")),
            contact=html.escape(str(item[6] or "")),
            listing_type_am=html.escape(str(listing_type_am)),
            date=html.escape(str(created_at))
        ) + status_msg + page_indicator

    nav_row = []
    if current_idx > 0:
        nav_row.append(InlineKeyboardButton(strings.BTN_PREV, callback_data=f"page_{current_idx-1}"))
    if current_idx < len(listings) - 1:
        nav_row.append(InlineKeyboardButton(strings.BTN_NEXT, callback_data=f"page_{current_idx+1}"))

    keyboard = []
    if nav_row:
        keyboard.append(nav_row)

    if is_admin:
        keyboard.append([InlineKeyboardButton(strings.ADMIN_DELETE, callback_data=f"delete_{item[0]}")])

    if for_owner:
        listing_type = get_listing_type_from_row(item)
        if item[8] == 'expired' and listing_type == 'service':
            keyboard.append([InlineKeyboardButton(strings.OWNER_RENEW_BTN, callback_data=f"renew_{item[0]}")])
        elif item[8] != 'rented':
            keyboard.append([InlineKeyboardButton(strings.OWNER_UNLIST_BTN, callback_data=f"unlist_{item[0]}")])
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    photo_ids = [p.strip() for p in item[5].split(",") if p and p.strip()] if item[5] else []

    tx_val = get_listing_transaction_id_from_row(item)
    tx_val = str(tx_val) if tx_val is not None else ""
    if is_admin and tx_val.startswith("photo:"):
        payment_photo = tx_val.split(":", 1)[1].strip()
        if payment_photo:
            photo_ids.append(payment_photo)

    chat_id = update.effective_chat.id
    func = context.bot.send_photo
    func_text = context.bot.send_message
    func_media_group = context.bot.send_media_group

    send_args = {"chat_id": chat_id}

    caption_text = text[:997] + "..." if len(text) > 1000 else text

    if len(photo_ids) > 1:
        media = [InputMediaPhoto(media=photo_ids[0], caption=caption_text, parse_mode='HTML')]
        for pid in photo_ids[1:]:
            media.append(InputMediaPhoto(media=pid))

        try:
            sent_messages = await func_media_group(media=media, **send_args)
            context.user_data['last_media_group_ids'] = [m.message_id for m in sent_messages]

            if keyboard:
                await func_text(text="መቆጣጠሪያ (Controls):", reply_markup=reply_markup, **send_args)
            if len(text) > 1000:
                await func_text(text=text, parse_mode='HTML', **send_args)
        except Exception as e:
            logger.error(f"Failed to send media group for listing {listing_id}: {e}")
            context.user_data['last_media_group_ids'] = []
            try:
                await func(photo=photo_ids[0], caption=caption_text, reply_markup=reply_markup, parse_mode='HTML', **send_args)
                for pid in photo_ids[1:]:
                    try:
                        await func(photo=pid, **send_args)
                    except Exception as pe:
                        logger.warning(f"Failed to send fallback photo {pid}: {pe}")
            except Exception as fe:
                logger.error(f"Fallback single photo failed for listing {listing_id}: {fe}")
                await func_text(text=text, reply_markup=reply_markup, parse_mode='HTML', **send_args)
    elif len(photo_ids) == 1:
        context.user_data['last_media_group_ids'] = []
        try:
            await func(photo=photo_ids[0], caption=caption_text, reply_markup=reply_markup, parse_mode='HTML', **send_args)
            if len(text) > 1000:
                await func_text(text=text, parse_mode='HTML', **send_args)
        except Exception as e:
            logger.error(f"Failed to send photo for listing {listing_id}: {e}")
            await func_text(text=text, reply_markup=reply_markup, parse_mode='HTML', **send_args)
    else:
        context.user_data['last_media_group_ids'] = []
        await func_text(text=text, reply_markup=reply_markup, parse_mode='HTML', **send_args)


# ─── Callbacks ────────────────────────────────────────────────────────────────

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    log_msg = f"DEBUG: Callback query received: {query.data} from {update.effective_user.id}"
    logger.info(log_msg)
    print(log_msg)
    await query.answer()

    if await check_and_send_timeout_notice(update, context):
        return

    # Subscription check
    if query.data == "check_subscription":
        return await handle_check_subscription(update, context)

    if query.data.startswith("page_"):
        idx = int(query.data.split("_")[1])
        try:
            last_media_ids = context.user_data.get('last_media_group_ids', [])
            for mid in last_media_ids:
                try:
                    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=mid)
                except:
                    pass
            context.user_data['last_media_group_ids'] = []

            await query.message.delete()
        except:
            pass
        await send_listing_page(update, context, idx)

    elif query.data.startswith("deletealert_"):
        alert_id = int(query.data.split("_")[1])
        database.delete_alert(alert_id, update.effective_user.id)
        try:
            await query.edit_message_text(strings.ALERT_DELETED_MSG)
        except:
            pass

    elif query.data.startswith("delete_"):
        if update.effective_user.id not in ADMIN_IDS:
            return

        listing_id = query.data.split("_")[1]

        # Delete the channel message before removing the listing from DB
        if CHANNEL_ID:
            channel_msg_id = database.get_channel_message_id(listing_id)
            if channel_msg_id:
                try:
                    await context.bot.delete_message(chat_id=CHANNEL_ID, message_id=channel_msg_id)
                except Exception as e:
                    logger.warning(f"Failed to delete channel message {channel_msg_id} for listing {listing_id}: {e}")

        database.delete_listing(listing_id)
        if query.message.photo:
            await query.edit_message_caption(caption=f"{query.message.caption}\n\n❌ {strings.ADMIN_DELETE_CONFIRM}")
        else:
            await query.edit_message_text(text=f"{query.message.text}\n\n❌ {strings.ADMIN_DELETE_CONFIRM}")

    elif query.data.startswith("unlist_"):
        listing_id = int(query.data.split("_")[1])
        listing = database.get_listing_by_id(listing_id)
        if not listing or listing[1] != update.effective_user.id:
            return

        database.unlist_listing(listing_id)

        # Delete the listing from the channel
        if CHANNEL_ID:
            channel_msg_id = database.get_channel_message_id(listing_id)
            if channel_msg_id:
                try:
                    await context.bot.delete_message(chat_id=CHANNEL_ID, message_id=channel_msg_id)
                except Exception as e:
                    logger.warning(f"Failed to delete channel message {channel_msg_id} for listing {listing_id}: {e}")

        if query.message.photo:
            await query.edit_message_caption(caption=f"{query.message.caption}\n\n{strings.OWNER_UNLIST_CONFIRM}")
        else:
            await query.edit_message_text(text=f"{query.message.text}\n\n{strings.OWNER_UNLIST_CONFIRM}")

    elif query.data.startswith("renew_"):
        listing_id = int(query.data.split("_")[1])
        listing = database.get_listing_by_id(listing_id)
        if not listing or listing[1] != update.effective_user.id:
            return
        if len(listing) > 12 and listing[12] != 'service':
            return
        database.renew_listing(listing_id)
        context.user_data["listing_id"] = listing_id
        await context.bot.send_message(chat_id=update.effective_chat.id, text=strings.OWNER_RENEW_PROMPT)
        return OWNER_PAYMENT

    elif query.data.startswith("approve_"):
        if update.effective_user.id not in ADMIN_IDS:
            return

        listing_id = int(query.data.split("_")[1])
        if mark_admin_action_processed(context, listing_id, "approve"):
            return

        listing = database.get_listing_by_id(listing_id)
        if not listing:
            return

        current_status = get_listing_status_from_row(listing)
        if current_status == 'paid':
            try:
                await query.edit_message_text(text=f"{query.message.text}\n\n✅ {strings.ADMIN_APPROVE_CONFIRM}")
            except Exception:
                pass
            return

        database.approve_listing(listing_id)

        listing = database.get_listing_by_id(listing_id)
        if listing:
            owner_id = listing[1]
            listing_type_val = get_listing_type_from_row(listing)

            if listing_type_val == 'looking_for':
                try:
                    await context.bot.send_message(chat_id=owner_id, text=strings.SEEKER_LOOKING_FOR_APPROVED, parse_mode='HTML')
                except:
                    pass

                if CHANNEL_ID:
                    try:
                        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                        property_purpose_val = get_property_purpose_from_row(listing)
                        purpose_am = {"buy": "ግዢ (Buy)", "rent": "ኪራይ (Rent)", "service": "አገልግሎት (Service)"}.get(property_purpose_val or "", "ያልተገለጸ")

                        # listing[2] = title (we used title as description for looking_for)
                        # listing[3] = location (city - neighborhood)
                        # listing[6] = contact
                        loc = listing[3] or ""
                        city_part, neigh_part = loc.split(" - ", 1) if " - " in loc else (loc, "ያልተገለጸ")
                        title_parts = (listing[2] or "").split(" — ", 1)
                        category_part = title_parts[1] if len(title_parts) > 1 else title_parts[0]
                        desc_part = listing[4] or ""  # price field stores description for looking_for

                        post_text = strings.LOOKING_FOR_CHANNEL_POST.format(
                            looking_for_title=get_looking_for_title(property_purpose_val),
                            seeker=str(owner_id),
                            city=city_part.strip(),
                            neighborhood=neigh_part.strip(),
                            purpose=purpose_am,
                            category=category_part.strip(),
                            description=desc_part,
                            contact=listing[6] or "ያልተገለጸ"
                        )

                        bot_username = (await context.bot.get_me()).username
                        bot_link = f"https://t.me/{bot_username}"
                        lf_keyboard = [[InlineKeyboardButton("ወደ ቦቱ ይግቡ", url=bot_link)]]
                        lf_reply_markup = InlineKeyboardMarkup(lf_keyboard)

                        if listing[0] is not None and not database.reserve_listing_channel_notification(listing[0]):
                            logger.info(f"Skipping duplicate looking-for channel post for listing {listing[0]}")
                            return

                        try:
                            sent_msg = await context.bot.send_message(chat_id=CHANNEL_ID, text=post_text, parse_mode='HTML', reply_markup=lf_reply_markup)
                            if listing[0] is not None:
                                database.set_channel_message_id(listing[0], sent_msg.message_id)
                                database.mark_listing_channel_notified(listing[0])
                        except Exception as lf_error:
                            if listing[0] is not None:
                                database.clear_listing_channel_notification(listing[0])
                            raise lf_error
                    except Exception as e:
                        logger.error(f"Failed to post looking_for to channel: {e}")
            else:
                try:
                    await context.bot.send_message(chat_id=owner_id, text=strings.OWNER_PAYMENT_SUCCESS)
                except:
                    pass

                if CHANNEL_ID:
                    try:
                        property_purpose_val = get_property_purpose_from_row(listing)
                        await post_listing_to_channel(context, listing, listing_type_val, property_purpose_val, channel_id=CHANNEL_ID)

                        # Fire search alerts
                        alert_users = database.get_matching_alerts(
                            category=listing[2] or "",
                            location=listing[3] or "",
                            property_purpose=property_purpose_val
                        )
                        for uid in alert_users:
                            try:
                                await context.bot.send_message(
                                    chat_id=uid,
                                    text=strings.ALERT_NOTIFICATION_MSG.format(title=listing[2]),
                                    parse_mode='HTML'
                                )
                            except Exception as alert_err:
                                logger.warning(f"Could not notify alert user {uid}: {alert_err}")
                    except Exception as e:
                        logger.error(f"Failed to post to channel {CHANNEL_ID}: {e}")

        try:
            await query.edit_message_text(text=f"{query.message.text}\n\n✅ {strings.ADMIN_APPROVE_CONFIRM}")
        except Exception:
            pass

    elif query.data.startswith("reject_"):
        if update.effective_user.id not in ADMIN_IDS:
            return
        listing_id = query.data.split("_")[1]
        if mark_admin_action_processed(context, listing_id, "reject"):
            return
        listing = database.get_listing_by_id(listing_id)
        if listing:
            owner_id = listing[1]
            try:
                await context.bot.send_message(chat_id=owner_id, text=strings.OWNER_LISTING_REJECTED)
            except Exception as e:
                logger.error(f"Failed to notify owner {owner_id} about rejection: {e}")

        # Delete the channel message before removing the listing from DB
        if CHANNEL_ID:
            channel_msg_id = database.get_channel_message_id(listing_id)
            if channel_msg_id:
                try:
                    await context.bot.delete_message(chat_id=CHANNEL_ID, message_id=channel_msg_id)
                except Exception as e:
                    logger.warning(f"Failed to delete channel message {channel_msg_id} for listing {listing_id}: {e}")

        database.delete_listing(listing_id)
        await query.edit_message_text(text=f"{query.message.text}\n\n❌ {strings.CANCEL_MSG}")


# ─── Admin Features ───────────────────────────────────────────────────────────

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text(strings.ADMIN_ONLY)
        return

    users = database.get_all_users()
    total = database.get_total_user_count()
    roles = [u[2] for u in users]
    owners_count = roles.count('owner') + roles.count('admin')
    seekers_count = total - owners_count

    all_listings = database.execute_query("SELECT listing_type, status FROM listings", fetchall=True)
    active_property = sum(1 for r in (all_listings or []) if r[1] == 'paid' and r[0] in ('property', None))
    active_service = sum(1 for r in (all_listings or []) if r[1] == 'paid' and r[0] == 'service')
    active_looking = sum(1 for r in (all_listings or []) if r[1] == 'paid' and r[0] == 'looking_for')
    pending_count = sum(1 for r in (all_listings or []) if r[1] == 'pending')
    total_active = active_property + active_service + active_looking

    await update.message.reply_text(
        strings.ADMIN_STATS.format(
            total=total,
            active=total_active,
            active_property=active_property,
            active_service=active_service,
            active_looking=active_looking,
            pending=pending_count,
            owners=owners_count,
            seekers=seekers_count
        ),
        parse_mode='HTML'
    )


async def admin_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View all listings waiting for admin approval."""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text(strings.ADMIN_ONLY)
        return

    pending_listings = database.get_pending_listings_with_txid()

    if not pending_listings:
        await update.message.reply_text(strings.ADMIN_NO_PENDING)
        return

    await update.message.reply_text(strings.ADMIN_PENDING_TITLE, parse_mode='HTML')

    context.user_data['current_listings'] = pending_listings
    context.user_data['is_for_owner'] = True
    await send_listing_page(update, context, 0)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        strings.HELP_MSG,
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )


async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text(strings.ADMIN_ONLY)
        return ConversationHandler.END

    await update.message.reply_text(strings.ADMIN_BROADCAST_PROMPT, reply_markup=ReplyKeyboardMarkup([[strings.CANCEL]], resize_keyboard=True))
    return ADMIN_BROADCAST


async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return ConversationHandler.END

    msg_text = update.message.text
    if msg_text == strings.CANCEL:
        return await cancel(update, context)

    users = database.get_all_users()
    count = 0
    for user in users:
        try:
            await update.message.copy_message(chat_id=user[0])
            count += 1
        except Exception as e:
            logger.error(f"Failed to send broadcast to {user[0]}: {e}")

    await update.message.reply_text(strings.ADMIN_BROADCAST_DONE.format(count=count), reply_markup=get_main_keyboard())
    return CHOOSING_ROLE


# ─── Health Check ─────────────────────────────────────────────────────────────

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        return


def run_health_check_server():
    port = int(os.getenv("PORT", 7860))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logger.info(f"Health check server started on port {port}")
    server.serve_forever()


def _normalize_webhook_url(webhook_url):
    if not webhook_url.startswith("http"):
        webhook_url = f"https://{webhook_url}"

    url_path = f"/{BOT_TOKEN}"
    if not webhook_url.endswith(url_path):
        webhook_url = f"{webhook_url.rstrip('/')}{url_path}"

    return webhook_url, url_path


def _resolve_webhook_url():
    webhook_url = (os.getenv("WEBHOOK_URL") or "").strip()
    if webhook_url:
        return webhook_url
    # Railway injects RAILWAY_PUBLIC_DOMAIN when a public URL is enabled
    railway_domain = (os.getenv("RAILWAY_PUBLIC_DOMAIN") or "").strip()
    if railway_domain:
        return railway_domain
    return None


def _start_webhook(application: Application, port: int) -> None:
    webhook_url = _resolve_webhook_url()
    if not webhook_url:
        raise ValueError(
            "WEBHOOK_URL environment variable is required when BOT_UPDATE_MODE=webhook. "
            "On Railway, enable a public domain (Settings → Networking) or set WEBHOOK_URL "
            "to your app URL (e.g. your-app.up.railway.app)."
        )

    webhook_url, url_path = _normalize_webhook_url(webhook_url)

    logger.info(f"Starting bot in WEBHOOK mode on port {port}...")
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=url_path,
        webhook_url=webhook_url,
        secret_token=os.getenv("WEBHOOK_SECRET") or None,
    )


def _start_polling(application: Application) -> None:
    logger.warning("=" * 60)
    logger.warning("No WEBHOOK_URL found. Starting bot in POLLING mode...")
    logger.warning("WARNING: Polling mode DELETES the production webhook!")
    logger.warning("If your bot is deployed on Railway, it will STOP receiving")
    logger.warning("updates there until you redeploy or manually set webhook.")
    logger.warning("=" * 60)
    threading.Thread(target=run_health_check_server, daemon=True).start()

    logger.info("Bot is now polling for updates...")
    application.run_polling(
        poll_interval=1.0,
        timeout=20,
        bootstrap_retries=5,
        drop_pending_updates=True,
    )


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    database.init_db()

    async def post_init(application: Application):
        me = await application.bot.get_me()
        msg = f"BOT IDENTITY: Bot is running as @{me.username} (ID: {me.id})"
        logger.info(msg)
        print(msg)

        from telegram import BotCommand
        await application.bot.set_my_commands([
            BotCommand("start", "ጀምር")
        ])

        async def debug_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
            d_msg = f"GLOBAL DEBUG: Received update: {update.to_dict()}"
            logger.info(d_msg)
            print(d_msg)

        application.add_handler(CallbackQueryHandler(debug_all), group=-1)

    persistence_path = os.getenv("PERSISTENCE_PATH", "bot_data.pickle")
    persistence_dir = os.path.dirname(os.path.abspath(persistence_path))
    if persistence_dir:
        os.makedirs(persistence_dir, exist_ok=True)
    persistence = PicklePersistence(filepath=persistence_path)

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .persistence(persistence)
        .post_init(post_init)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .write_timeout(30.0)
        .build()
    )

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_ROLE: [
                MessageHandler(filters.Text(strings.ROLE_SELLER), owner_start),
                MessageHandler(filters.Text(strings.ROLE_LANDLORD), owner_start),
                MessageHandler(filters.Text(strings.ROLE_BUYER), seeker_start),
                MessageHandler(filters.Text(strings.ROLE_RENTER), seeker_start),
                MessageHandler(filters.Text(strings.ROLE_SERVICE_PROVIDER), owner_start),
                MessageHandler(filters.Text(strings.ROLE_SERVICE_SEEKER), seeker_start),
                MessageHandler(filters.Text(strings.HELP_BTN), help_command),
                CallbackQueryHandler(handle_callback),
            ],
            OWNER_MENU: [
                MessageHandler(filters.Text(strings.OWNER_ADD_NEW), owner_add_new),
                MessageHandler(filters.Text(strings.OWNER_MANAGE), owner_manage),
                MessageHandler(filters.Text(strings.OWNER_VIEW_LOOKING_FOR), owner_view_looking_for),
                MessageHandler(filters.Text(strings.BACK), start),
                CallbackQueryHandler(handle_callback),
            ],
            OWNER_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Text(strings.CANCEL), owner_category)],
            OWNER_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Text(strings.CANCEL), owner_title)],
            OWNER_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Text(strings.CANCEL), owner_city)],
            OWNER_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Text(strings.CANCEL), owner_price)],
            OWNER_PHOTO: [
                MessageHandler(filters.PHOTO, owner_photo),
                CommandHandler("skip", owner_skip_photo),
                MessageHandler(filters.Text(strings.SKIP), owner_skip_photo),
                MessageHandler(filters.Text(strings.DONE_PHOTOS_BTN), owner_done_photo),
                MessageHandler(filters.Text(strings.DONE), owner_done_photo),
                MessageHandler((filters.TEXT | filters.CONTACT) & ~filters.COMMAND & ~filters.Text(strings.CANCEL), owner_photo_text),
            ],
            OWNER_CONTACT: [MessageHandler((filters.TEXT | filters.CONTACT) & ~filters.COMMAND & ~filters.Text(strings.CANCEL), owner_contact)],
            OWNER_PAYMENT: [MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND & ~filters.Text(strings.CANCEL), owner_submit_txid)],
            # Seeker
            SEEKER_MENU: [
                MessageHandler(filters.Text(strings.SEEKER_SEARCH), seeker_ask_category),
                MessageHandler(filters.Text(strings.SEEKER_LOOKING_FOR), seeker_looking_for_start),
                MessageHandler(filters.Text(strings.BACK), start),
                CallbackQueryHandler(handle_callback),
            ],
            SEEKER_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Text(strings.CANCEL), seeker_category)],
            SEEKER_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Text(strings.CANCEL), seeker_browse_city)],
            SEARCH_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Text(strings.CANCEL), execute_search)],
            ADMIN_BROADCAST: [MessageHandler(filters.ALL & ~filters.COMMAND & ~filters.Text(strings.CANCEL), broadcast_message)],
            # Looking For flow
            SEEKER_LOOKING_FOR_PURPOSE: [
                MessageHandler(filters.ALL, seeker_looking_for_start)
            ],
            SEEKER_LOOKING_FOR_DESC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Text(strings.CANCEL), seeker_looking_for_description)
            ],
            SEEKER_LOOKING_FOR_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Text(strings.CANCEL), seeker_looking_for_price)
            ],
            SEEKER_LOOKING_FOR_CONTACT: [
                MessageHandler((filters.TEXT | filters.CONTACT) & ~filters.COMMAND & ~filters.Text(strings.CANCEL), seeker_looking_for_contact)
            ],
            LOOKING_FOR_PAYMENT: [
                MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND & ~filters.Text(strings.CANCEL), seeker_looking_for_txid)
            ],
            # Timeout
            ConversationHandler.TIMEOUT: [MessageHandler(filters.ALL, timeout_handler)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            MessageHandler(filters.Text(strings.CANCEL), cancel),
            CommandHandler("start", start)
        ],
        conversation_timeout=900,  # 15 minutes
        persistent=True,
        name="main_conversation",
        per_message=False,
    )

    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(handle_callback), group=1)
    application.add_handler(CommandHandler("admin", admin_stats))
    application.add_handler(CommandHandler("stats", admin_stats))
    application.add_handler(CommandHandler("admin_pending", admin_pending))
    application.add_handler(CommandHandler("pending", admin_pending))
    application.add_handler(CommandHandler("broadcast", broadcast_start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_post_timeout_message))

    # Schedule daily listings checks
    job_queue = application.job_queue
    if job_queue:
        from datetime import time, timezone, timedelta
        eat_tz = timezone(timedelta(hours=3))  # East Africa Time (UTC+3)
        async def expire_listings_job(context: ContextTypes.DEFAULT_TYPE):
            database.expire_old_listings()

        job_queue.run_daily(
            expire_listings_job,
            time=time(hour=3, minute=0, tzinfo=eat_tz)
        )

    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.error(msg="Exception while handling an update:", exc_info=context.error)
    application.add_error_handler(error_handler)

    update_mode = (os.getenv("BOT_UPDATE_MODE") or "webhook").strip().lower()
    port = int(os.getenv("PORT", 7860))

    if update_mode == "webhook":
        _start_webhook(application, port)
    elif update_mode == "polling":
        _start_polling(application)
    else:
        raise ValueError(
            f"Invalid BOT_UPDATE_MODE={update_mode!r}. Use 'webhook' or 'polling'."
        )


if __name__ == "__main__":
    main()
