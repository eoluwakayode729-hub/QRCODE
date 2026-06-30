import logging
import io
import re
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
from qrcode.image.styles.colormasks import SolidFillColorMask
from PIL import Image, ImageDraw
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

from config import Config

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Color options
COLORS = {
    'black': '#000000',
    'blue': '#1E90FF',
    'green': '#32CD32',
    'red': '#FF4444',
    'purple': '#9B59B6',
    'orange': '#FF8C00',
    'pink': '#FF69B4',
    'teal': '#008080',
    'yellow': '#FFD700',
    'white': '#FFFFFF'
}

# Size options
SIZES = {
    'small': 300,
    'medium': 500,
    'large': 800,
    'xlarge': 1000
}

# Generate QR code
def generate_qr(data, size=500, color='#000000', bg_color='#FFFFFF', 
               error_correction='M', version=1, box_size=10, border=2):
    """Generate QR code with customizations"""
    
    # Set error correction level
    error_levels = {
        'L': qrcode.constants.ERROR_CORRECT_L,
        'M': qrcode.constants.ERROR_CORRECT_M,
        'Q': qrcode.constants.ERROR_CORRECT_Q,
        'H': qrcode.constants.ERROR_CORRECT_H
    }
    
    # Create QR code instance
    qr = qrcode.QRCode(
        version=version,
        error_correction=error_levels.get(error_correction, qrcode.constants.ERROR_CORRECT_M),
        box_size=box_size,
        border=border,
    )
    
    qr.add_data(data)
    qr.make(fit=True)
    
    # Create image with custom colors
    qr_img = qr.make_image(
        fill_color=color,
        back_color=bg_color,
        image_factory=StyledPilImage,
        module_drawer=RoundedModuleDrawer(),
        color_mask=SolidFillColorMask(front_color=color, back_color=bg_color)
    )
    
    # Resize image
    if size != qr_img.size[0]:
        qr_img = qr_img.resize((size, size), Image.Resampling.LANCZOS)
    
    return qr_img

# Save image to bytes
def image_to_bytes(image):
    """Convert PIL Image to bytes"""
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG', optimize=True)
    img_byte_arr.seek(0)
    return img_byte_arr

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("📝 Generate QR", callback_data='generate'),
            InlineKeyboardButton("🎨 Customize", callback_data='customize')
        ],
        [
            InlineKeyboardButton("📋 Examples", callback_data='examples'),
            InlineKeyboardButton("❓ Help", callback_data='help')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        "🎯 *Welcome to QuickQR Bot!*\n\n"
        "I create QR codes for:\n"
        "✅ URLs & Links\n"
        "✅ Text Messages\n"
        "✅ WiFi Networks\n"
        "✅ Contact Details\n"
        "✅ And more!\n\n"
        "*How to use:*\n"
        "1. Send me any text or URL\n"
        "2. Or use /generate to customize\n"
        "3. Choose size and color\n"
        "4. Get your QR code instantly!\n\n"
        "Just send me anything to get started!"
    )
    
    if update.message:
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

# Generate QR command
async def generate_qr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /generate command or button click"""
    query = update.callback_query if update.callback_query else None
    
    if query:
        await query.answer()
    
    # Check if there's data to encode
    user_data = context.user_data
    if 'qr_data' in user_data and user_data['qr_data']:
        await process_qr_generation(update, context)
        return
    
    keyboard = [
        [InlineKeyboardButton("📝 Enter Text", callback_data='enter_text')],
        [InlineKeyboardButton("🔗 Enter URL", callback_data='enter_url')],
        [InlineKeyboardButton("📶 WiFi Network", callback_data='wifi')],
        [InlineKeyboardButton("👤 vCard Contact", callback_data='vcard')],
        [InlineKeyboardButton("🎨 Customize Colors", callback_data='customize')],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        "🎯 *Generate QR Code*\n\n"
        "What would you like to encode?\n\n"
        "*Options:*\n"
        "• Text - Any message\n"
        "• URL - Website link\n"
        "• WiFi - Network credentials\n"
        "• vCard - Contact information\n\n"
        "Or simply send me any text/URL!"
    )
    
    if query:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

# Customize command
async def customize_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle customize button"""
    query = update.callback_query
    await query.answer()
    
    # Get current settings
    settings = context.user_data.get('qr_settings', {
        'size': 'medium',
        'color': 'black',
        'bg_color': 'white',
        'error': 'M'
    })
    
    keyboard = [
        [
            InlineKeyboardButton(f"📏 Size: {settings['size'].capitalize()}", callback_data='size_menu'),
            InlineKeyboardButton(f"🎨 Color: {settings['color'].capitalize()}", callback_data='color_menu')
        ],
        [
            InlineKeyboardButton(f"🔲 Background: {settings['bg_color'].capitalize()}", callback_data='bg_menu'),
            InlineKeyboardButton(f"🔄 Error: {settings['error']}", callback_data='error_menu')
        ],
        [
            InlineKeyboardButton("✅ Apply & Generate", callback_data='generate')
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data='main_menu')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🎨 *Customize QR Code*\n\n"
        "Adjust the settings below to customize your QR code.\n"
        "After customizing, click 'Apply & Generate'.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Size menu
async def size_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [
            InlineKeyboardButton("📐 Small (300px)", callback_data='size_small'),
            InlineKeyboardButton("📐 Medium (500px)", callback_data='size_medium')
        ],
        [
            InlineKeyboardButton("📐 Large (800px)", callback_data='size_large'),
            InlineKeyboardButton("📐 X-Large (1000px)", callback_data='size_xlarge')
        ],
        [
            InlineKeyboardButton("🔙 Back to Customize", callback_data='customize')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📏 *Select Size*\n\n"
        "Choose the size of your QR code:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Color menu
async def color_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [
            InlineKeyboardButton("⬛ Black", callback_data='color_black'),
            InlineKeyboardButton("🔵 Blue", callback_data='color_blue'),
            InlineKeyboardButton("🟢 Green", callback_data='color_green')
        ],
        [
            InlineKeyboardButton("🔴 Red", callback_data='color_red'),
            InlineKeyboardButton("🟣 Purple", callback_data='color_purple'),
            InlineKeyboardButton("🟠 Orange", callback_data='color_orange')
        ],
        [
            InlineKeyboardButton("💗 Pink", callback_data='color_pink'),
            InlineKeyboardButton("🩵 Teal", callback_data='color_teal'),
            InlineKeyboardButton("🟡 Yellow", callback_data='color_yellow')
        ],
        [
            InlineKeyboardButton("⚪ White", callback_data='color_white')
        ],
        [
            InlineKeyboardButton("🔙 Back to Customize", callback_data='customize')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🎨 *Select Color*\n\n"
        "Choose the main color for your QR code:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Background color menu
async def bg_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [
            InlineKeyboardButton("⬛ Black", callback_data='bg_black'),
            InlineKeyboardButton("⬜ White", callback_data='bg_white')
        ],
        [
            InlineKeyboardButton("🟦 Blue", callback_data='bg_blue'),
            InlineKeyboardButton("🟩 Green", callback_data='bg_green')
        ],
        [
            InlineKeyboardButton("🟥 Red", callback_data='bg_red'),
            InlineKeyboardButton("🟨 Yellow", callback_data='bg_yellow')
        ],
        [
            InlineKeyboardButton("🔙 Back to Customize", callback_data='customize')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🔲 *Select Background Color*\n\n"
        "Choose the background color for your QR code:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Error correction menu
async def error_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [
            InlineKeyboardButton("L (7% recovery)", callback_data='error_L'),
            InlineKeyboardButton("M (15% recovery)", callback_data='error_M')
        ],
        [
            InlineKeyboardButton("Q (25% recovery)", callback_data='error_Q'),
            InlineKeyboardButton("H (30% recovery)", callback_data='error_H')
        ],
        [
            InlineKeyboardButton("🔙 Back to Customize", callback_data='customize')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🔄 *Error Correction Level*\n\n"
        "Higher levels can recover more data if the QR code is damaged:\n"
        "• L - Low (7% recovery)\n"
        "• M - Medium (15% recovery)\n"
        "• Q - Quartile (25% recovery)\n"
        "• H - High (30% recovery)\n\n"
        "Select a level:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Examples menu
async def examples_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [
            InlineKeyboardButton("🔗 URL Example", callback_data='example_url'),
            InlineKeyboardButton("📝 Text Example", callback_data='example_text')
        ],
        [
            InlineKeyboardButton("📶 WiFi Example", callback_data='example_wifi'),
            InlineKeyboardButton("👤 vCard Example", callback_data='example_vcard')
        ],
        [
            InlineKeyboardButton("🔙 Back to Menu", callback_data='main_menu')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📋 *Example QR Codes*\n\n"
        "Click any example to see how it works:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Handle text/URL messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user messages containing text or URLs"""
    text = update.message.text.strip()
    
    if not text:
        await update.message.reply_text("❌ Please send some text or a URL.")
        return
    
    # Store the data
    context.user_data['qr_data'] = text
    await process_qr_generation(update, context)

# Process QR generation
async def process_qr_generation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process QR code generation"""
    data = context.user_data.get('qr_data')
    
    if not data:
        await update.message.reply_text("❌ No data provided. Please send text or a URL.")
        return
    
    # Get settings
    settings = context.user_data.get('qr_settings', {
        'size': 'medium',
        'color': 'black',
        'bg_color': 'white',
        'error': 'M'
    })
    
    # Get size in pixels
    size = SIZES.get(settings['size'], 500)
    
    # Get colors (convert to hex)
    color = COLORS.get(settings['color'], '#000000')
    bg_color = COLORS.get(settings['bg_color'], '#FFFFFF')
    
    # Check if it's a URL
    is_url = re.match(r'^https?://', data)
    
    # Show processing message
    if update.message:
        await update.message.reply_text("⏳ Generating your QR code...")
        chat_id = update.message.chat_id
    else:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("⏳ Generating your QR code...")
        chat_id = query.message.chat_id
    
    try:
        # Generate QR code
        qr_image = generate_qr(
            data=data,
            size=size,
            color=color,
            bg_color=bg_color,
            error_correction=settings['error']
        )
        
        # Convert to bytes
        image_bytes = image_to_bytes(qr_image)
        
        # Prepare caption
        caption = (
            f"✅ *QR Code Generated!*\n\n"
            f"📌 *Type:* {'URL' if is_url else 'Text'}\n"
            f"📏 *Size:* {size}px\n"
            f"🎨 *Color:* {settings['color'].capitalize()}\n"
            f"🔲 *Background:* {settings['bg_color'].capitalize()}\n"
            f"🔄 *Error Level:* {settings['error']}\n\n"
            f"📋 *Data encoded:*\n`{data[:100]}{'...' if len(data) > 100 else ''}`"
        )
        
        # Create keyboard
        keyboard = [
            [
                InlineKeyboardButton("📋 Copy Data", callback_data=f'copy_{data[:50]}'),
                InlineKeyboardButton("🔄 Generate New", callback_data='generate')
            ],
            [
                InlineKeyboardButton("🎨 Customize", callback_data='customize'),
                InlineKeyboardButton("🔙 Menu", callback_data='main_menu')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send QR code
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=image_bytes,
            caption=caption,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        # Clear the data
        context.user_data['qr_data'] = None
        
    except Exception as e:
        logger.error(f"QR generation error: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ Failed to generate QR code: {str(e)}\nPlease try again."
        )

# WiFi QR generator
async def wifi_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Ask for WiFi details
    context.user_data['waiting_for_wifi'] = True
    
    keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data='generate')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📶 *WiFi QR Code*\n\n"
        "Send me your WiFi details in this format:\n"
        "`SSID,Password`\n\n"
        "Example: `MyWiFi,MyPassword123`\n\n"
        "Or: `MyWiFi,MyPassword,WPA2` (with security type)",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# vCard QR generator
async def vcard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Ask for contact details
    context.user_data['waiting_for_vcard'] = True
    
    keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data='generate')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "👤 *vCard QR Code*\n\n"
        "Send me your contact details in this format:\n"
        "`Name,Phone,Email,Company`\n\n"
        "Example: `John Doe,+1234567890,john@email.com,Acme Inc`\n\n"
        "You can also just send a phone number or email.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Handle WiFi input
async def handle_wifi_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('waiting_for_wifi'):
        return
    
    parts = update.message.text.split(',')
    
    if len(parts) < 2:
        await update.message.reply_text(
            "❌ Invalid format!\n"
            "Please use: `SSID,Password`\n"
            "Example: `MyWiFi,MyPassword123`",
            parse_mode='Markdown'
        )
        return
    
    ssid = parts[0].strip()
    password = parts[1].strip()
    security = parts[2].strip() if len(parts) > 2 else 'WPA2'
    
    # Create WiFi QR data
    wifi_data = f"WIFI:T:{security};S:{ssid};P:{password};;"
    context.user_data['qr_data'] = wifi_data
    context.user_data['waiting_for_wifi'] = False
    
    await process_qr_generation(update, context)

# Handle vCard input
async def handle_vcard_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('waiting_for_vcard'):
        return
    
    parts = update.message.text.split(',')
    
    if len(parts) < 1:
        await update.message.reply_text(
            "❌ Invalid format!\n"
            "Please use: `Name,Phone,Email,Company`",
            parse_mode='Markdown'
        )
        return
    
    name = parts[0].strip()
    phone = parts[1].strip() if len(parts) > 1 else ''
    email = parts[2].strip() if len(parts) > 2 else ''
    company = parts[3].strip() if len(parts) > 3 else ''
    
    # Create vCard data
    vcard_data = f"""BEGIN:VCARD
VERSION:3.0
FN:{name}
TEL:{phone}
EMAIL:{email}
ORG:{company}
END:VCARD"""
    
    context.user_data['qr_data'] = vcard_data
    context.user_data['waiting_for_vcard'] = False
    
    await process_qr_generation(update, context)

# Help handler
async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    
    help_text = (
        "❓ *Help & Commands*\n\n"
        "*How to use:*\n"
        "1. Send any text or URL\n"
        "2. Or use /generate for options\n"
        "3. Customize with /customize\n\n"
        "*Commands:*\n"
        "/start - Show main menu\n"
        "/generate - Generate QR code\n"
        "/customize - Change settings\n"
        "/help - Show help\n"
        "/cancel - Cancel operation\n\n"
        "*What you can encode:*\n"
        "🔗 URLs and links\n"
        "📝 Text messages\n"
        "📶 WiFi networks\n"
        "👤 Contact details\n"
        "💳 Payment info\n\n"
        "*Customization:*\n"
        "🎨 10+ Colors\n"
        "📏 4 Sizes (300-1000px)\n"
        "🔄 Error correction levels\n"
        "🔲 Background colors"
    )
    
    if query:
        await query.edit_message_text(help_text, parse_mode='Markdown')
    else:
        await update.message.reply_text(help_text, parse_mode='Markdown')

# Copy handler
async def copy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split('_', 1)[1]
    
    await query.message.reply_text(
        f"📋 *Data copied to clipboard!*\n\n"
        f"`{data}`\n\n"
        f"*Note:* Please select and copy the text manually.",
        parse_mode='Markdown'
    )

# Main menu handler
async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await start(update, context)

# Button handler
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == 'main_menu':
        await main_menu_handler(update, context)
    elif data == 'generate':
        await generate_qr_command(update, context)
    elif data == 'customize':
        await customize_command(update, context)
    elif data == 'examples':
        await examples_menu(update, context)
    elif data == 'help':
        await help_handler(update, context)
    elif data == 'enter_text':
        context.user_data['waiting_for_text'] = True
        await query.edit_message_text(
            "📝 *Enter Text*\n\n"
            "Please send me the text you want to encode as a QR code.",
            parse_mode='Markdown'
        )
    elif data == 'enter_url':
        context.user_data['waiting_for_url'] = True
        await query.edit_message_text(
            "🔗 *Enter URL*\n\n"
            "Please send me the URL you want to encode as a QR code.\n"
            "Example: `https://example.com`",
            parse_mode='Markdown'
        )
    elif data == 'wifi':
        await wifi_handler(update, context)
    elif data == 'vcard':
        await vcard_handler(update, context)
    elif data.startswith('size_'):
        size = data.split('_')[1]
        settings = context.user_data.get('qr_settings', {})
        settings['size'] = size
        context.user_data['qr_settings'] = settings
        await query.edit_message_text(f"✅ Size set to: *{size.capitalize()}*", parse_mode='Markdown')
        await customize_command(update, context)
    elif data.startswith('color_'):
        color = data.split('_')[1]
        settings = context.user_data.get('qr_settings', {})
        settings['color'] = color
        context.user_data['qr_settings'] = settings
        await query.edit_message_text(f"✅ Color set to: *{color.capitalize()}*", parse_mode='Markdown')
        await customize_command(update, context)
    elif data.startswith('bg_'):
        bg = data.split('_')[1]
        settings = context.user_data.get('qr_settings', {})
        settings['bg_color'] = bg
        context.user_data['qr_settings'] = settings
        await query.edit_message_text(f"✅ Background set to: *{bg.capitalize()}*", parse_mode='Markdown')
        await customize_command(update, context)
    elif data.startswith('error_'):
        error = data.split('_')[1]
        settings = context.user_data.get('qr_settings', {})
        settings['error'] = error
        context.user_data['qr_settings'] = settings
        await query.edit_message_text(f"✅ Error level set to: *{error}*", parse_mode='Markdown')
        await customize_command(update, context)
    elif data.startswith('example_'):
        example_type = data.split('_')[1]
        examples = {
            'url': 'https://github.com',
            'text': 'Hello, this is a QR code!',
            'wifi': 'WIFI:T:WPA2;S:MyWiFi;P:MyPassword123;;',
            'vcard': 'BEGIN:VCARD\nVERSION:3.0\nFN:John Doe\nTEL:+1234567890\nEMAIL:john@email.com\nEND:VCARD'
        }
        context.user_data['qr_data'] = examples.get(example_type, 'Example QR Code')
        await process_qr_generation(update, context)
    elif data.startswith('copy_'):
        await copy_handler(update, context)

# Cancel handler
async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['waiting_for_wifi'] = False
    context.user_data['waiting_for_vcard'] = False
    context.user_data['waiting_for_text'] = False
    context.user_data['waiting_for_url'] = False
    context.user_data['qr_data'] = None
    
    await update.message.reply_text(
        "❌ Operation cancelled.\n"
        "Type /start to go back to the main menu."
    )

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")

def main():
    """Start the bot"""
    application = Application.builder().token(Config.BOT_TOKEN).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("generate", generate_qr_command))
    application.add_handler(CommandHandler("customize", customize_command))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("cancel", cancel_handler))
    
    # Callback query handler
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Message handlers
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        handle_message
    ))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    logger.info("🤖 QR Code Generator Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
