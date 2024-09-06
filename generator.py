import csv
import random
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

BIN_FILE_PATH = 'bin-list-data.csv'  # Replace with the actual path to your CSV file
VIDEO_FILE_PATH = 'ice.mp4'  # Replace with the actual path to your welcome video
USERS_FILE_PATH = 'bot_users.txt'

def load_bin_data(file_path):
    bin_data = {}
    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            bin_data[row['BIN']] = row
    return bin_data

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if is_registered(user_id):
        await update.message.reply_text("Welcome back! Use /gen <bin> <amount> to generate credit card details.\n\nAvailable commands:\n/register - Register to use the bot\n/gen <bin> <amount> - Generate credit card details\n/gg <amount> - Generate random credit cards\n/gv <amount> - Generate Visa credit cards\n/gm <amount> - Generate Mastercard credit cards\n/ga <amount> - Generate American Express credit cards\n/gc <country_code> <amount> - Generate credit cards from a specific country\n/bn <bin> - Lookup BIN information\n/cmds - List available commands")
        return

    with open(VIDEO_FILE_PATH, 'rb') as video:
        await update.message.reply_video(video, caption="Welcome! Please register to use the bot.")

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    if is_registered(user_id):
        await update.message.reply_text("You are already registered.")
        return

    with open(USERS_FILE_PATH, "a") as file:
        file.write(f"{user_id}\n")
    await update.message.reply_text("You have been registered successfully!")
    await list_commands(update, context)

async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    if not is_registered(user_id):
        await update.message.reply_text("You need to register first using /register.")
        return

    if len(context.args) == 2:
        bin_number = context.args[0][:6]
        try:
            count = int(context.args[1])
        except ValueError:
            await update.message.reply_text("Amount should be a number.")
            return

        if len(bin_number) != 6:
            await update.message.reply_text("BIN should be 6 digits.")
            return

        card_length = 16
        card_numbers = generate_test_cards(bin_number, card_length, count)
        
        with open("gen.txt", "w") as file:
            for card in card_numbers:
                file.write(card + "\n")

        bin_data = load_bin_data(BIN_FILE_PATH)
        bin_info = bin_data.get(bin_number, {})
        if not bin_info:
            await update.message.reply_text(f"No information found for BIN {bin_number}")
            return
        
        bin_details = (
            f"BIN: {bin_info['BIN']}\n"
            f"Brand: {bin_info['Brand']}\n"
            f"Type: {bin_info['Type']}\n"
            f"Category: {bin_info['Category']}\n"
            f"Issuer: {bin_info['Issuer']}\n"
            f"Country: {bin_info['CountryName']}"
        )

        with open("gen.txt", "rb") as file:
            await update.message.reply_document(document=file, filename="gen.txt")
        await update.message.reply_text(f"BIN Information:\n{bin_details}")

    else:
        await update.message.reply_text("Usage: /gen <bin> <amount>")
        return

async def generate_from_random_bins(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    bin_list = [bin_number for bin_number in bin_data.keys() if any(bin_number.startswith(prefix) for prefix in ['41', '42'])]
    
    if not bin_list:
        await update.message.reply_text("No BINs found for the specified prefixes.")
        return

    bin_number = random.choice(bin_list)
    card_length = 16
    card_numbers = generate_test_cards(bin_number, card_length, count)

    with open("gen.txt", "w") as file:
        for card in card_numbers:
            file.write(card + "\n")

    bin_info = bin_data.get(bin_number, {})
    bin_details = (
        f"BIN: {bin_info['BIN']}\n"
        f"Brand: {bin_info['Brand']}\n"
        f"Type: {bin_info['Type']}\n"
        f"Category: {bin_info['Category']}\n"
        f"Issuer: {bin_info['Issuer']}\n"
        f"Country: {bin_info['CountryName']}"
    )

    with open("gen.txt", "rb") as file:
        await update.message.reply_document(document=file, filename="gen.txt")
    await update.message.reply_text(f"BIN Information:\n{bin_details}")

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
    bin_list = [bin_number for bin_number in bin_data.keys() if bin_data[bin_number]['CountryCode'].upper() == country_code]
    
    if not bin_list:
        await update.message.reply_text(f"No BINs found for country code {country_code}.")
        return

    bin_number = random.choice(bin_list)
    card_length = 16
    card_numbers = generate_test_cards(bin_number, card_length, count)

    with open("gen.txt", "w") as file:
        for card in card_numbers:
            file.write(card + "\n")

    bin_info = bin_data.get(bin_number, {})
    bin_details = (
        f"BIN: {bin_info['BIN']}\n"
        f"Brand: {bin_info['Brand']}\n"
        f"Type: {bin_info['Type']}\n"
        f"Category: {bin_info['Category']}\n"
        f"Issuer: {bin_info['Issuer']}\n"
        f"Country: {bin_info['CountryName']}"
    )

    with open("gen.txt", "rb") as file:
        await update.message.reply_document(document=file, filename="gen.txt")
    await update.message.reply_text(f"BIN Information:\n{bin_details}")

async def list_commands(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    commands = (
        "/start - Welcome message\n"
        "/register - Register to use the bot\n"
        "/gen <bin> <amount> - Generate credit card details\n"
        "/gg <amount> - Generate random credit cards\n"
        "/gv <amount> - Generate Visa credit cards\n"
        "/gm <amount> - Generate Mastercard credit cards\n"
        "/ga <amount> - Generate American Express credit cards\n"
        "/gc <country_code> <amount> - Generate credit cards from a specific country\n"
        "/bn <bin> - Lookup BIN information\n"
        "/cmds - List available commands"
    )
    await update.message.reply_text(f"Available commands:\n{commands}")

def main() -> None:
    application = Application.builder().token('7528445359:AAEpk_rd_cgRrFRWkOobdwVFYUFrxZsiKyM').build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('register', register))
    application.add_handler(CommandHandler('gen', generate))
    application.add_handler(CommandHandler('gg', generate_from_random_bins))
    application.add_handler(CommandHandler('gv', lambda update, context: generate_from_random_bins(update, context, ['4'])))
    application.add_handler(CommandHandler('gm', lambda update, context: generate_from_random_bins(update, context, ['51', '52', '53', '54', '55'])))
    application.add_handler(CommandHandler('ga', lambda update, context: generate_from_random_bins(update, context, ['34', '37'])))
    application.add_handler(CommandHandler('gc', generate_from_country))
    application.add_handler(CommandHandler('bn', lambda update, context: update.message.reply_text("BIN lookup is not implemented in this snippet.")))
    application.add_handler(CommandHandler('cmds', list_commands))

    application.run_polling()

if __name__ == '__main__':
    main()
