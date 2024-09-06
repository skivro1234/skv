import csv
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
import os

BIN_FILE_PATH = 'bin-list-data.csv'
VIDEO_FILE_PATH = 'ice.mp4'
USERS_FILE_PATH = 'bot_users.txt'
CHANNEL_ID = '@skivro_channel'  # Replace with your channel username or ID

# Load CSV data
def load_bin_data(file_path):
    bin_data = {}
    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            bin_data[row['BIN']] = row
    return bin_data

# Generate credit card number, expiration date, CVV, etc.
def luhn_checksum(card_number):
    def digits_of(n):
        return [int(d) for d in str(n)]
    digits = digits_of(card_number)
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    checksum = sum(odd_digits)
    for d in even_digits:
        checksum += sum(digits_of(d * 2))
    return checksum % 10

def is_luhn_valid(card_number):
    return luhn_checksum(card_number) == 0

def generate_credit_card_number(prefix, length):
    card_number = [int(d) for d in str(prefix)]
    while len(card_number) < (length - 1):
        card_number.append(random.randint(0, 9))
    
    partial_number = ''.join(map(str, card_number))
    for check_digit in range(10):
        if is_luhn_valid(int(partial_number + str(check_digit))):
            card_number.append(check_digit)
            break

    return ''.join(map(str, card_number))

def generate_expiration_date():
    month = str(random.randint(1, 12)).zfill(2)
    year = str(random.randint(25, 30))
    return f"{month}|{year}"

def generate_cvv():
    return str(random.randint(100, 999))

def generate_test_cards(bin_number, length, count):
    cards = []
    for _ in range(count):
        card_number = generate_credit_card_number(bin_number, length)
        expiration_date = generate_expiration_date()
        cvv = generate_cvv()
        cards.append(f"{card_number}|{expiration_date}|{cvv}")
    return cards

def is_registered(user_id):
    if not os.path.exists(USERS_FILE_PATH):
        return False
    with open(USERS_FILE_PATH, "r") as file:
        return str(user_id) in file.read().splitlines()

def check_subscription(user_id):
    # This function should check if the user is a member of the channel
    # For demonstration, let's assume it's always True. Replace with actual check
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if is_registered(user_id):
        await update.message.reply_text("Welcome back! Use /gen <bin> <amount> to generate credit card details.")
        return

    keyboard = [
        [InlineKeyboardButton("Subscribe to Channel", url=f"https://t.me/{CHANNEL_ID}")],
        [InlineKeyboardButton("Register", callback_data='register')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    with open(VIDEO_FILE_PATH, 'rb') as video:
        await update.message.reply_video(video, caption="Welcome! Please subscribe to the channel and then register using the buttons below.", reply_markup=reply_markup)

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    if check_subscription(user_id):
        if is_registered(user_id):
            await update.message.reply_text("You are already registered.")
            return

        with open(USERS_FILE_PATH, "a") as file:
            file.write(f"{user_id}\n")

        await update.message.reply_text("You have been registered successfully! Use the following commands:\n\n"
                                        "/gen <bin> <amount> - Generate credit card details\n"
                                        "/gc <country_code> <amount> - Generate credit cards from a specific country\n"
                                        "/gg <amount> - Generate credit cards from random brands\n"
                                        "/bn <bin> - Lookup BIN details")

    else:
        await update.message.reply_text("You need to subscribe to the channel before registering.")

async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    if not is_registered(user_id):
        await update.message.reply_text("You need to register first using /register.")
        return

    if len(context.args) == 1:
        params = context.args[0].split('|')
        if len(params) == 3:
            bin_number = params[0][:6]
            expiration_date = params[1]
            cvv = params[2]

            if len(expiration_date) != 2 or not expiration_date.isdigit():
                await update.message.reply_text("Expiration month must be two digits.")
                return

            if len(cvv) != 3 or not cvv.isdigit():
                await update.message.reply_text("CVV must be three digits.")
                return

            card_number = generate_credit_card_number(bin_number, 16)
            card_info = f"{card_number}|{expiration_date}|{cvv}"

            with open("gen.txt", "w") as file:
                file.write(card_info + "\n")

            bin_data = load_bin_data(BIN_FILE_PATH)
            bin_info = bin_data.get(bin_number, {})
            if not bin_info:
                await update.message.reply_text(f"No information found for BIN <code>{bin_number}</code>.", parse_mode="HTML")
                return
            
            bin_details = (
                f"BIN: <code>{bin_info['BIN']}</code>\n"
                f"Brand: <code>{bin_info['Brand']}</code>\n"
                f"Type: <code>{bin_info['Type']}</code>\n"
                f"Category: <code>{bin_info['Category']}</code>\n"
                f"Issuer: <code>{bin_info['Issuer']}</code>\n"
                f"Country: <code>{bin_info['CountryName']}</code>"
            )

            with open("gen.txt", "rb") as file:
                await update.message.reply_document(document=file, filename="gen.txt")
            await update.message.reply_text(f"BIN Information:\n{bin_details}", parse_mode="HTML")

        else:
            await update.message.reply_text("Usage: /gen <bin>|<exp_month>|<exp_year>|<cvv>")
            return

    else:
        if len(context.args) != 2:
            await update.message.reply_text("Usage: /gen <bin> <amount>")
            return

        bin_number = context.args[0][:6]
        try:
            count = int(context.args[1])
        except ValueError:
            await update.message.reply_text("Amount should be a number.")
            return

        card_length = 16
        card_numbers = generate_test_cards(bin_number, card_length, count)
        
        if len(card_numbers) <= 20:
            cards_message = "\n".join([f"<code>{card}</code>" for card in card_numbers])
            await update.message.reply_text(f"Generated Cards:\n{cards_message}", parse_mode="HTML")
        else:
            with open("gen.txt", "w") as file:
                for card in card_numbers:
                    file.write(card + "\n")

            bin_data = load_bin_data(BIN_FILE_PATH)
            bin_info = bin_data.get(bin_number, {})
            if not bin_info:
                await update.message.reply_text(f"No information found for BIN <code>{bin_number}</code>.", parse_mode="HTML")
                return
            
            bin_details = (
                f"BIN: <code>{bin_info['BIN']}</code>\n"
                f"Brand: <code>{bin_info['Brand']}</code>\n"
                f"Type: <code>{bin_info['Type']}</code>\n"
                f"Category: <code>{bin_info['Category']}</code>\n"
                f"Issuer: <code>{bin_info['Issuer']}</code>\n"
                f"Country: <code>{bin_info['CountryName']}</code>"
            )

            with open("gen.txt", "rb") as file:
                await update.message.reply_document(document=file, filename="gen.txt")
            await update.message.reply_text(f"BIN Information:\n{bin_details}", parse_mode="HTML")

async def generate_from_random_bins(update: Update, context: ContextTypes.DEFAULT_TYPE, prefixes) -> None:
    user_id = update.effective_user.id

    if not is_registered(user_id):
        await update.message.reply_text("You need to register first using /register.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("Usage: /gg <amount>")
        return

    try:
        count = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Amount should be a number.")
        return

    bin_data = load_bin_data(BIN_FILE_PATH)
    bin_list = [bin_number for bin_number in bin_data if any(bin_number.startswith(prefix) for prefix in prefixes)]
    
    if not bin_list:
        await update.message.reply_text("No BINs found for the selected brands.")
        return

    generated_cards = []
    while count > 0:
        bin_number = random.choice(bin_list)
        num_to_generate = min(count, 20)
        card_numbers = generate_test_cards(bin_number, 16, num_to_generate)
        generated_cards.extend(card_numbers)
        count -= num_to_generate

    if len(generated_cards) <= 20:
        cards_message = "\n".join([f"<code>{card}</code>" for card in generated_cards])
        await update.message.reply_text(f"Generated Cards:\n{cards_message}", parse_mode="HTML")
    else:
        with open("gen.txt", "w") as file:
            for card in generated_cards:
                file.write(card + "\n")

        bin_info = bin_data.get(bin_number, {})
        if not bin_info:
            await update.message.reply_text(f"No information found for BIN <code>{bin_number}</code>.", parse_mode="HTML")
            return

        bin_details = (
            f"BIN: <code>{bin_info['BIN']}</code>\n"
            f"Brand: <code>{bin_info['Brand']}</code>\n"
            f"Type: <code>{bin_info['Type']}</code>\n"
            f"Category: <code>{bin_info['Category']}</code>\n"
            f"Issuer: <code>{bin_info['Issuer']}</code>\n"
            f"Country: <code>{bin_info['CountryName']}</code>"
        )

        with open("gen.txt", "rb") as file:
            await update.message.reply_document(document=file, filename="gen.txt")
        await update.message.reply_text(f"BIN Information:\n{bin_details}", parse_mode="HTML")

async def generate_from_country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    if not is_registered(user_id):
        await update.message.reply_text("You need to register first using /register.")
        return

    if len(context.args) != 2:
        await update.message.reply_text("Usage: /gc <country_code> <amount>")
        return

    country_code = context.args[0].upper()
    try:
        count = int(context.args[1])
    except ValueError:
        await update.message.reply_text("Amount should be a number.")
        return

    bin_data = load_bin_data(BIN_FILE_PATH)
    bin_list = [bin_number for bin_number, details in bin_data.items() if details['isoCode2'] == country_code]

    if not bin_list:
        await update.message.reply_text(f"No BINs found for country code <code>{country_code}</code>.", parse_mode="HTML")
        return

    generated_cards = []
    while count > 0:
        bin_number = random.choice(bin_list)
        num_to_generate = min(count, 20)
        card_numbers = generate_test_cards(bin_number, 16, num_to_generate)
        generated_cards.extend(card_numbers)
        count -= num_to_generate

    if len(generated_cards) <= 20:
        cards_message = "\n".join([f"<code>{card}</code>" for card in generated_cards])
        await update.message.reply_text(f"Generated Cards:\n{cards_message}", parse_mode="HTML")
    else:
        with open("gen.txt", "w") as file:
            for card in generated_cards:
                file.write(card + "\n")

        bin_info = bin_data.get(bin_number, {})
        if not bin_info:
            await update.message.reply_text(f"No information found for BIN <code>{bin_number}</code>.", parse_mode="HTML")
            return

        bin_details = (
            f"BIN: <code>{bin_info['BIN']}</code>\n"
            f"Brand: <code>{bin_info['Brand']}</code>\n"
            f"Type: <code>{bin_info['Type']}</code>\n"
            f"Category: <code>{bin_info['Category']}</code>\n"
            f"Issuer: <code>{bin_info['Issuer']}</code>\n"
            f"Country: <code>{bin_info['CountryName']}</code>"
        )

        with open("gen.txt", "rb") as file:
            await update.message.reply_document(document=file, filename="gen.txt")
        await update.message.reply_text(f"BIN Information:\n{bin_details}", parse_mode="HTML")

async def bin_lookup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /bn <bin>")
        return

    bin_number = context.args[0][:6]
    bin_data = load_bin_data(BIN_FILE_PATH)
    bin_info = bin_data.get(bin_number, {})

    if not bin_info:
        await update.message.reply_text(f"No information found for BIN <code>{bin_number}</code>.", parse_mode="HTML")
        return

    bin_details = (
        f"BIN: <code>{bin_info['BIN']}</code>\n"
        f"Brand: <code>{bin_info['Brand']}</code>\n"
        f"Type: <code>{bin_info['Type']}</code>\n"
        f"Category: <code>{bin_info['Category']}</code>\n"
        f"Issuer: <code>{bin_info['Issuer']}</code>\n"
        f"Country: <code>{bin_info['CountryName']}</code>"
    )
    
    await update.message.reply_text(f"BIN Information:\n{bin_details}", parse_mode="HTML")

def main() -> None:
    application = Application.builder().token('7334774517:AAFneU67ZvYc8yyID0NPjBiYOMIV_X8GHv0').build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("register", register))
    application.add_handler(CommandHandler("gen", generate))
    application.add_handler(CommandHandler("gc", generate_from_country))
    application.add_handler(CommandHandler("gg", generate_from_random_bins, filters=Filters.regex(r'^\d+$')))
    application.add_handler(CommandHandler("bn", bin_lookup))

    application.run_polling()

if __name__ == '__main__':
    main()
