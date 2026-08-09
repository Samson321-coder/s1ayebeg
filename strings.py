# strings.py
# Amharic translations for the Telegram Rental Bot

WELCOME_MSG = (
    "✨ <b>እንኳን በደህና መጡ!</b> ✨\n\n"
    "🏠 ይህ ቦት በኢትዮጵያ ሻጮችን፣ አከራዮችን፣ እና አገልግሎት ሰጪዎችን ከ ገዢዎች፣ ተከራዮች፣ እና አገልግሎት ፈላጊዎች ጋር በቀላሉ ያገናኛል።\n\n"
    "👇 <i>ከታች ካሉት አማራጮች አንዱን ይምረጡ፦</i>\n\n"
    # "ተጨማሪ መረጃ t.me/gebeya_mereja_266 Telegram Channel ላይ ይመልከቱ"   
)     

# ── Channel subscription ──────────────────────────────────────────────────────
SUBSCRIBE_PROMPT = (
    # "📢 <b>እባክዎን ለቀጠናችን ቻናል ይጠቀሙ!</b>\n\n"
    # "📢 <b>እባክዎን ቀጣዩን ቻናል ይጠቀሙ!</b>\n\n"
    "ቦቱን ለመጠቀም እንድሁም ተጨማሪ መረጃ እንድደርሶ <b>@gebeya_mereja_266</b> ቻናላችንን ይቀላቀሉ (Join ያድርጉ)፣ ቀጥለው <b>✅ ተቀላቀልኩ</b> ን ይጫኑ።"
)
SUBSCRIBE_BTN = "✅ ተቀላቀልኩ — ቀጥል"
SUBSCRIBE_CHANNEL_URL = "https://t.me/gebeya_mereja_266"  
NOT_SUBSCRIBED_MSG = (
    # "❌ <b>ቻናሉን እስካልተቀላቀሉ ቦቱ አይሰራም።</b>\n\n" 
    # "❌ <b>ቻናሉን እስካልተቀላቀሉ ቦቱ አይሰራም።</b>\n\n" 
    "ቦቱን ለመጠቀም እንድሁም ተጨማሪ መረጃ እንድደርሶ እባክዎን @gebeya_mereja_266 ቻናላችንን ይቀላቀሉ (Join ያድርጉ) ከዚያ <b>✅ ተቀላቀልኩ</b> ን ይጫኑ።"
)
SUBSCRIBED_OK = "✅ እናመሰግናለን! አሁን ቦቱን መጠቀም ይችላሉ።"

ROLE_OWNER = "ሻጭ/አከራይ/አገልግሎት ሰጪ"
ROLE_SEEKER = "ተከራይ/ገዢ/አገልግሎት ፈላጊ"
# Split roles for clearer buttons
ROLE_SELLER = "🛍️ ሻጭ"
ROLE_LANDLORD = "🔑 አከራይ"
ROLE_BUYER = "🛒 ገዢ"
ROLE_RENTER = "🏠 ተከራይ"
ROLE_SERVICE_PROVIDER = "🛠️ አገልግሎት ሰጪ"
ROLE_SERVICE_SEEKER = "🔍 አገልግሎት ፈላጊ"
# Owner Flow
OWNER_MENU_MSG = "ምን ማድረግ ይፈልጋሉ?"
OWNER_ADD_NEW = "አዲስ ምዝገባ መጀመር"
OWNER_MANAGE = "የተመዘገቡትን ማየት"
OWNER_NO_LISTINGS = "ምንም የተመዘገበ ነገር የሎትም።"
OWNER_UNLIST_BTN = "❌ አጥፋ"
# OWNER_UNLIST_CONFIRM = "ዝርዝሩ በተሳካ ሁኔታ ተነስቷል።"
OWNER_UNLIST_CONFIRM = "ጠፍቷል።"

OWNER_START = "የንብረቱን/የአገልግሎቱን አይነት አጭር መግለጫ ይጻፉ (ለምሳሌ፦ ባለ 2 ክፍል ኮንዶሚኒየም፣ የቧንቧ ጥገና፣ ...)"
OWNER_VIEW_LOOKING_FOR = "🔍 የፈላጊዎችን ፍላጎት እይ"

# Category selection
OWNER_ASK_CATEGORY = "📂 ምድብ ይምረጡ:"
# Property categories
CATEGORY_HOUSE = "🏠 ቤት/መሬት"
CATEGORY_VEHICLE = "🚗 ተሽከርካሪ"
CATEGORY_FURNITURE = "🛋️ የቤት ፅቃ"
CATEGORY_ELECTRONICS = "📱 ኤሌክትሮንክስ"
CATEGORY_COSMETICS = "👗 ፋሽን/ዉበት"
CATEGORY_OTHER = "📦 ሌላ"
# Service categories
SERVICE_CATEGORY_HOUSE = "🔧 ቤት ነክ"
SERVICE_CATEGORY_VEHICLE = "🚗 ተሽከርካሪ ነክ"
SERVICE_CATEGORY_ELECTRONICS = "📱 ኤሌክትሮንክስ ነክ"
SERVICE_CATEGORY_COSMETICS = "👗 ፋሽን/ዉበት ነክ"
SERVICE_CATEGORY_OTHER = "📦 ሌላ"

OWNER_ASK_TYPE = 'ከሚከተሉት አማራጮች አንዱን ይምረጡ'
LISTING_SERVICE = "አገልግሎት ሰጪ"
LISTING_PROPERTY = "ሻጭ/አከራይ"

OWNER_ASK_CITY = "ንብረቱ/አገልግሎቱ በየትኛው ከተማ ይገኛል? ከታች ካለው ዝርዝር ይምረጡ።"
OWNER_ASK_LOCATION = "ክፍለ ከተማዉ/ሰፈሩ የት ነው? ከታች ካለው ዝርዝር ይምረጡ።"
OWNER_ASK_PRICE = "ዋጋዉ ስንት ነው? (በቁጥር ወይም በቃላት ይጻፉ ― ለምሳሌ፦ 3500 ወይም «ሶስት ሺ አምስት መቶ ብር»)"

# ── Photo Upload ──────────────────────────────────────────────────────────────
OWNER_ASK_PHOTO = (
    "📷 <b>የንብረቱን/የአገልግሎቱን ፎቶ ይላኩ (እስከ {max_photos} ፎቶዎች)።</b>\n\n"
    "• ፎቶዎችን አንድ በ አንድ ይላኩ።\n"
    "• ሁሉም ፎቶዎች ሲያልቁ <b>📸 ፎቶ መጫን ጨርሻለሁ</b> ን ይጫኑ።\n"
    "• ፎቶ ከሌለዎት /skip ይጫኑ ወይም 'ዝለል' ይጻፉ።"
)
PHOTO_ADDED_MSG = "✅ ፎቶ {count} ተቀብሏል! ተጨማሪ ፎቶ ካለ ይላኩ፣ ካለቀ 📸 <b>ፎቶ መጫን ጨርሻለሁ</b> ን ይጫኑ።"
PHOTO_LIMIT_REACHED_AUTO_ADVANCE = (
    "✅ <b>ከፍተኛው የፎቶዎች ብዛት ({max_photos}) ደርሷል!</b>\n\n"
    "ወደ ቀጣዩ ደረጃ በራስ-ሰር ተሸጋግሯል።"
)
DONE_PHOTOS_BTN = "📸 ፎቶ መጫን ጨርሻለሁ"

PHOTO_UPLOADED = "ፎቶ ተልኳል።"
DONE = "ጨርሻለሁ"
OWNER_ASK_CONTACT = "ስልክ ቁጥርዎን ያስገቡ"

# Fixed fee = 50 birr (no percentage)
FIXED_FEE = 50

OWNER_ASK_PAYMENT_SERVICE = (
    "🙏 <b>ምዝገባው ሊጠናቀቅ ጥቂት ቀርቶታል!</b>\n\n"
    "በቦቱ ላይ ሆኖ ለፈላጊዎች እንዲታይ የአገልግሎት ምዝገባ ክፍያ <b>50 ብር</b> ብቻ ይከፍሉ።\n\n"
    "💰 <b>የክፍያ መጠን፦ 50 ብር</b>\n"
    "⏳ <b>ዝርዝሩ ለ30 ቀናት ያህል ብቻ ይቆያል።</b>\n"
    "👤 <b>ስም፦ ሳምሶን ማሬ</b>\n"
    "   <b>የኢትዮጵያ ንግድ ባንክ አካዉንት ቁጥር፦ 1000174738533</b>\n\n"
    "👇 <i>ክፍያውን ከፈጸሙ በኋላ፣ የክፍያ ስክሪንሾት (Screenshot) ወይም የትራንዛክሽን ቁጥር (Transaction ID) እዚህ ይላኩ፦</i>"
)
OWNER_ASK_PAYMENT_PROPERTY = (
    "🙏 <b>ምዝገባው ሊጠናቀቅ ጥቂት ቀርቶታል!</b>\n\n"
    "በቦቱ ላይ ሆኖ ለፈላጊዎች እንዲታይ የምዝገባ ክፍያ <b>50 ብር</b> ብቻ ይከፍሉ።\n\n"
    "💰 <b>የክፍያ መጠን፦ 50 ብር</b>\n"
    "👤 <b>ስም፦ ሳምሶን ማሬ</b>\n"
    "   <b>የኢትዮጵያ ንግድ ባንክ አካዉንት ቁጥር፦ 1000174738533</b>\n\n"
    "👇 <i>ክፍያውን ከፈጸሙ በኋላ፣ የክፍያ ስክሪንሾት (Screenshot) ወይም የትራንዛክሽን ቁጥር (Transaction ID) እዚህ ይላኩ፦</i>"
)
OWNER_RENEW_BTN = "🔄 እንደገና ይክፈሉ"
OWNER_RENEW_PROMPT = "ዝርዝሩ ከ30 ቀናት በኋላ እንዲቀጥል በድጋግሚ ክፍያ ይላኩ (50 ብር)። የክፍያ ስክሪንሾት ወይም TXID ይላኩ፦"
PAYMENT_GUIDE = "እባክዎን የክፍያ ስክሪንሾት (Screenshot) ወይም የትራንዛክሽን ቁጥር (Transaction ID) በትክክል ያስገቡ።"
OWNER_PAYMENT_PENDING = "ክፍያዎ በተሳካ ሁኔታ ተመዝግቧል! ✅ አስተዳዳሪው ሲያጸድቀው ዝርዝርዎ በቦቱ ላይ ይወጣል። እናመሰግናለን።"
OWNER_PAYMENT_SUCCESS = "እንኳን ደስ አለዎት! 🎉 ዝርዝርዎ በአስተዳዳሪው ጸድቆ ለፈላጊዎች ክፍት ሆኗል።"
OWNER_LISTING_REJECTED = "❌ ዝርዝርዎ አልተፈቀደም። ምክንያቱን ለማወቅ በ 0985605005 ይደውሉ።"
OWNER_SUCCESS = "በተሳካ ሁኔታ ተመዝግቧል! ✅"

# Seeker Flow
SEEKER_MENU_MSG = "ምን ማድረግ ይፈልጋሉ?"
SEEKER_SEARCH = "🔍 በከተማ, ክፍለ ከተማ/ሰፈር ፈልግ"
# SEEKER_LOOKING_FOR = "🔎 እየፈለኩትን ይላኩ (Looking For)"
SEEKER_LOOKING_FOR = "🔎 ፍላጎቶን ይላኩ"
SEEKER_VIEW_ALL = "ሁሉንም ዝርዝሮች እይ"
SEEKER_ASK_CATEGORY = "📂 ምድብ ይምረጡ:"
SEEKER_ASK_SEARCH = "ክፍለ ከተማ/ሰፈር ከታች ካለው ዝርዝር ይምረጡ።"
SEEKER_ASK_CITY = "📍 ከተማ ከታች ካለው ዝርዝር ይምረጡ።"
SEEKER_NO_LISTINGS = "ምንም የተመዘገበ መረጃ አልተገኘም።"
SEEKER_NO_MATCH = "በዚህ አካባቢ የተመዘገበ መረጃ አልተገኘም።"

# Looking For flow
SEEKER_ASK_LOOKING_FOR = (
    "🔎 <b>ፍላጎቶን ይግለጹ:</b>\n\n"
    "• ምን ዓይነት ንብረት/አገልግሎት እንደሚፈልጉ ይጻፉ\n"
    "  (ለምሳሌ፦ «ባለ 2 ክፍል ቤት ቦሌ አካባቢ»)\n"
    "ጥያቄዎ ለሻጮች/አከራዮች/አገልግሎት ሰጪዎች  የሚታይ ይሆናል።"
)
SEEKER_ASK_LOOKING_FOR_PRICE = "💰 የዋጋ ገደብዎን ይጻፉ (ለምሳሌ፦ 5000 ብር ድረስ ወይም 'በስምምነት')"
SEEKER_LOOKING_FOR_SENT = (
    # "✅ <b>ጥያቄዎ ክፍያ ተቀብሏል!</b>\n\n"
    "✅ <b>ጥያቄዎ ደርሶናል!</b>\n\n"
    "አስተዳዳሪው ሲያጸድቀው ጥያቄዎ ለሻጮች/አከራዮች/አገልግሎት ሰጪዎች ይቀርባል።\n"
    "ሲጸድቅ ማሳወቂያ ይደርስዎታል። እናመሰግናለን!"
)
SEEKER_LOOKING_FOR_APPROVED = (
    "✅ <b>ጥያቄዎ ጸድቋል!</b>\n\n"
    "ጥያቄዎ ለሻጮች/አከራዮች/አገልግሎት ሰጪዎች ቀርቧል።\n"
    "ብዙም ሳይቆይ ሊደወልሎ ይችላል።"
)
SEEKER_LOOKING_FOR_ADMIN = (
    "🔍 <b>ፍላጎት — ክፍያ ተፈጽሟል!</b>\n\n"
    "ከ: {seeker}\n"
    "📂 ምድብ: {category}\n"
    "📋 መግለጫ: {description}\n"
    "📍 ከተማ: {city}\n"
    "📍 ክፍለ ከተማ/ሰፈር: {neighborhood}\n"
    "📌 ዓላማ/አይነት: {purpose}\n"
    "💰 ዋጋ: {price}\n"
    "📞 ስልክ: {contact}\n"
    "ክፍያ: 50 ብር (ቋሚ)\n"
    "TxID: {txid}"
)
SEEKER_ASK_CONTACT_FOR_LOOKING = "📞 ስልክ ቁጥርዎን ያስገቡ (ሻጭ/አከራይ/አገልግሎት ሰጪ እንድያናግርዎ):"
SEEKER_ASK_PAYMENT_LOOKING_FOR = (
    "🙏 <b>ጥያቄዎ ሊጠናቀቅ ጥቂት ቀርቶታል!</b>\n\n"
    "ጥያቄዎ ለሻጮች/አከራዮች/ለአገልግሎት ሰጪዎች እንዲደርስ የምዝገባ ክፍያ <b>50 ብር</b> ብቻ ይክፈሉ።\n\n"
    "💰 <b>የክፍያ መጠን፦ 50 ብር</b>\n"
    "👤 <b>ስም፦ ሳምሶን ማሬ</b>\n"
    "   <b>የኢትዮጵያ ንግድ ባንክ አካዉንት ቁጥር፦ 1000174738533</b>\n\n"
    "👇 <i>ክፍያውን ከፈጸሙ በኋላ፣ የክፍያ ስክሪንሾት (Screenshot) ወይም የትራንዛክሽን ቁጥር (Transaction ID) እዚህ ይላኩ፦</i>"
)
SEEKER_ASK_PURPOSE = "ከታች ካሉት አማራጮች ይምረጡ:"
PURPOSE_BUY = "🛒 ግዢ"
PURPOSE_RENT = "🏠 ኪራይ"
PURPOSE_SERVICE = "🛠️ አገልግሎት"

# Listing Template
LISTING_TEMPLATE = (
    "🌟 <b>{listing_type_title}</b>\n\n"
    "📋 መግለጫ፦ <b>{title}</b>\n"
    "📌 ዓላማ/አይነት፦ <b>{listing_type_am}</b>\n"
    # "📍 ቦታ፦ <b>{location}</b>\n"
    "📍 ከተማ/ክፍለ ከተማ/ሰፈር፦ <b>{location}</b>\n"
    "💰 ዋጋ፦ <b>{price}</b>\n"
    "📞 ስልክ፦ {contact}\n"
    "📅 የተመዘገበበት፦ {date}"
)

LOOKING_FOR_LISTING_TEMPLATE = (
    "🔎 <b>{looking_for_title}</b>\n\n"
    "📂 ምድብ፦ <b>{category}</b>\n"
    "📝 መግለጫ፦\n{description}\n"
    "🛋️ ዓላማ/አይነት፦ <b>{purpose}</b>\n"
    "📌 ከተማ፦ <b>{city}</b>\n"
    "📍 ክፍለ ከተማ/ሰፈር፦ <b>{neighborhood}</b>\n"
    "💰 ዋጋ፦ <b>{price}</b>\n"
    "📞 ስልክ፦ {contact}\n"
    "📅 የተመዘገበበት፦ {date}"
)

LOOKING_FOR_CHANNEL_POST = (
    "🔎 <b>{looking_for_title}</b>\n\n"
    "👤 ፈላጊ። {seeker}\n"
    "📂 ምድብ፦ {category}\n\n"
    "📝 መግለጫ፦\n{description}\n"
    "🛋️ ዓላማ/አይነት፦ {purpose}\n"
    "📌 ከተማ፦ {city}\n"
    "📍 ክፍለ ከተማ/ሰፈር፦ {neighborhood}\n"
    "📞 ስልክ፦ {contact}"
)

# Admin
ADMIN_DELETE = "🗑️ ሰርዝ (Admin)"
# ADMIN_DELETE_CONFIRM = "ዝርዝሩ በተሳካ ሁኔታ ተሰርዟል።"
ADMIN_DELETE_CONFIRM = "ተሰርዟል።"
ADMIN_TITLE = "--- የአስተዳዳሪ ክፍል ---"
ADMIN_APPROVE_REQ = "🆕 አዲስ ክፍያ ተመዝግቧል!\n\nባለቤት፦ {owner}\nርዕስ፦ {title}\nከተማ፦ {city}\nክፍለ ከተማ/ሰፈር፦ {neighborhood}\nዓላማ/አይነት፦ {listing_type_am}\nስልክ፦ {contact}\nዋጋ፦ {price}\nክፍያ፦ 50 ብር (ቋሚ)\nTxID፦ {txid}"
ADMIN_APPROVE = "✅ አጽድቅ"
ADMIN_REJECT = "❌ ውድቅ አድርግ"
ADMIN_APPROVE_CONFIRM = "ዝርዝሩ ጸድቋል! ለፈላጊዎች የቀረበ ነው።"
ADMIN_BROADCAST_PROMPT = "📢 እባክዎን ለሁሉም ተጠቃሚዎች የሚላከውን መልእክት ይጻፉ።"
ADMIN_BROADCAST_DONE = "✅ መልእክቱ ለ {count} ተጠቃሚዎች ተልኳል።"
ADMIN_STATS = (
    "📊 <b>― የአስተዳዳሪ ዳሽቦርድ ―</b>\n\n"
    "👥 ጠቅላላ ተጠቃሚዎች፦ <b>{total}</b>\n\n"
    "🏠 ንቁ ዝርዝሮች (ንብረት/ኪራይ)፦ <b>{active_property}</b>\n"
    "🛠️ ንቁ አገልግሎት ዝርዝሮች፦ <b>{active_service}</b>\n"
    "🔎 ንቁ «ፍላጎት» ጥያቄዎች፦ <b>{active_looking}</b>\n"
    "⏳ ሊጸድቁ እየጠበቁ ያሉ፦ <b>{pending}</b>\n\n"
    "👤 ሻጮች/አከራዮች (ግምት)፦ <b>{owners}</b>\n"
    "👤 ገዢዎች/ተከራዮች (ግምት)፦ <b>{seekers}</b>"
)
ADMIN_ONLY = "❌ ይህ ትዕዛዝ ለአስተዳዳሪዎች ብቻ ነው።"
ADMIN_PENDING_TITLE = "⏳ <b>ከክፍያ ጋር የቀረቡ ዝርዝሮች፦</b>"
ADMIN_NO_PENDING = "✅ ምንም የሚጠበቁ ክፍያዎች የሉም።"
OWNER_ASK_DATE_FILTER = "የማጣሪያ ጊዜ ይምረጡ:"
FILTER_24_HOURS = "ባለፉት 24 ሰዓታት"
FILTER_7_DAYS = "ባለፉት 7 ቀናት"
FILTER_ALL_TIME = "ሁሉም ጊዜ"

# Common
BACK = "ተመለስ ⬅️"
CANCEL = "አቋርጥ ❌"
SKIP = "ዝለል"
CANCEL_MSG = "ክዋኔው ተሰርዟል።"
BTN_NEXT = "ቀጣይ ➡️"
BTN_PREV = "⬅️ ወደኋላ"
HELP_BTN = "መመሪያ/እርዳታ ℹ️"
VIEW_ALL_PHOTOS_BTN = "📸 View all photos"
TIMEOUT_MSG = "⏳ ጊዜው ስላለቀ ክዋኔው ተቋርጧል። እንደገና ይጀምሩ። /start"

# Input Validation
PRICE_INVALID = "❌ ያስገቡት ዋጋ ትክክል አይደለም። ዋጋ በቁጥር ወይም በቃላት ያስገቡ (ለምሳሌ፦ 3500 ወይም «ሶስት ሺ»)"
WORD_LIMIT_EXCEEDED = "❌ የቃላት ብዛት ከ {max_words} በላይ መሆን የለበትም። (ያስገቡት የቃላት ብዛት፦ {count})\nእባክዎን አጭር አድርገው በድጋሚ ያስገቡ።"
CHAR_LIMIT_EXCEEDED = "❌ የፊደላት/ቁጥሮች ብዛት ከ {max_chars} በላይ መሆን የለበትም። (ያስገቡት ብዛት፦ {count})\nእባክዎን አጭር አድርገው በድጋሚ ያስገቡ።"


# Help
HELP_MSG = (
    "📖 <b>የቦቱ አጠቃቀም መመሪያ</b>\n\n"

    "<b>🏠 ለሻጮች፣ አከራዮች፣ እና አገልግሎት ሰጪዎች:</b>\n"
    "• /start ን ጽፈዉ enter ካሉ በኃላ 'ሻጭ፣ አከራይ፣ ወይም አገልግሎት ሰጪ' ን ይምረጡ\n"
    "• የንብረቱን/የአገልግሎቱን አጭር መግለጫ፣ ዓላማ/አይነት፣ ከተማ/ክፍለ ከተማ/ሰፈር፣ ዋጋ፣ ፎቶ እና ስልክ ያስገቡ\n"
    "• የምዝገባ ክፍያ ለሻጮች እና አከራዮች <b>50 ብር</b> ብቻ (ቋሚ) ስሆን ለአገልግሎት ሰጪዎች በወር <b>50 ብር</b> ብቻ ነው\n"
    "• ዝርዝርዎ አስተዳዳሪው ክፍያዎን ካረጋገጠ በኋላ ለፈላጊዎች ይቀርባል\n"
    "• ንብረቶ ከተሸጠ/ከተከራየ ወይም አገልግሎት መስጠት ካልፈለጉ ለፈላጊዎች እንዳይታይ 'ሻጭ፣ አከራይ፣ ወይም አገልግሎት ሰጪ' ዉስጥ በመግባት 'የተመዘገቡትን ማይት' ን በመጫን ካሎት ዝርዝሮች ዉስጥ 'አጥፋ' ን በመጫን ያጥፉ\n\n"

    "<b>🔍 ለገዢዎች፣ ተከራዮች፣ እና አገልግሎት ፈላጊዎች:</b>\n"
    "• /start ን ጽፈዉ enter ካሉ በኃላ 'ገዢ፣ ተከራይ፣ ወይም አገልግሎት ፈላጊ' ን ይምረጡ\n"
    "• 'ሁሉንም ዝርዝሮች' ይመልከቱ ወይም 'በከተማ/ክፍለ ከተማ/ሰፈር' ይፈልጉ\n"
    "• ከተመቸዎ፣ ባለቤቱን ስልክ ደውለው ያናግሩ\n"
    "• «ፍላጎቶን ይላኩ» ን ተጠቅመው ምን እንደሚፈልጉ ይጻፉ — ሻጮች/አከራዮች/አገልግሎት ሰጪዎች ያናግሩዎታል\n\n"

    # "<b>ማስታወቂያ ማስነገር ለምፈልጉ:</b>\n"
    # "• በርካታ ተከታዮች ባሉት 'ገበያ መረጃ' የTelegram Channel ማስታወቂያ ማስነገር ከፈለጉ በ 0985605005 ይደዉሉ\n\n"

    # "<b>ለበለጠ መረጃ:</b>\n"
    # "• 0985605005\n\n"

    # "<b>📌 ሌሎች ትዕዛዞች:</b>\n"
    # "• /cancel - ወቅታዊ ክዋኔ ለማቋረጥ\n"
    # "• /help - ይህን ገጽ ለማሳየት\n\n"

    "<b>ተጨማሪ መረጃ</b>\n"
    "• t.me/gebeya_mereja_266 Telegram Channel ላይ ይመልከቱ"
)
