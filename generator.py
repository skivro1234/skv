import csv
import random
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os

BIN_FILE_PATH = 'bin-list-data.csv'  # Path to your CSV file
VIDEO_FILE_PATH = 'ice.mp4'  # Path to your welcome video
USERS_FILE_PATH = 'bot_users.txt'

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

def generate_test_cards(bin_number, length, count, fixed_expiration_date=None, fixed_cvv=None):
    cards = []
    for _ in range(count):
        card_number = generate_credit_card_number(bin_number, length)
        expiration_date = fixed_expiration_date or generate_expiration_date()
        cvv = fixed_cvv or generate_cvv()
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
        await update.message.reply_text("Welcome back! Use /gen <bin> <amount> to generate credit card details.")
        return

    with open(VIDEO_FILE_PATH, 'rb') as video:
        await update.message.reply_video(video, caption="Welcome! Please register using /register to use the bot.")
        await update.message.reply_text("To use the bot, please register with the /register command.")

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if is_registered(user_id):
        await update.message.reply_text("You are already registered.")
        return

    with open(USERS_FILE_PATH, "a") as file:
        file.write(f"{user_id}\n")
    await update.message.reply_text("You have been registered successfully!")
    commands = (
        "/start - Start the bot\n"
        "/register - Register to use the bot\n"
        "/gen <bin> <amount> - Generate cards with BIN and amount\n"
        "/gg <amount> - Generate cards from random bins\n"
        "/gv <amount> - Generate cards from Visa bins\n"
        "/gm <amount> - Generate cards from Mastercard bins\n"
        "/ga <amount> - Generate cards from American Express bins\n"
        "/gc <country_code> <amount> - Generate cards from bins of a specific country\n"
        "/bn <bin> - Lookup BIN information\n"
        "/cmds - Show this help message"
    )
    await update.message.reply_text(f"Here are the commands you can use:\n{commands}")

async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    if not is_registered(user_id):
        await update.message.reply_text("You need to register first using /register.")
        return

    if len(context.args) == 1:
        params = context.args[0].split('|')
        if len(params) == 4:
            bin_number = params[0][:6]
            expiration_date = params[1]
            year = params[2]
            cvv = params[3]

            if len(expiration_date) != 2 or not expiration_date.isdigit():
                await update.message.reply_text("Expiration month must be two digits.")
                return

            if len(year) != 4 or not year.isdigit():
                await update.message.reply_text("Expiration year must be four digits.")
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
        
        if count < 20:
            for card in card_numbers:
                await update.message.reply_text(card)
        else:
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

    bin_number = random.choice(bin_list)
    card_length = 16
    card_numbers = generate_test_cards(bin_number, card_length, count)

    if count < 20:
        for card in card_numbers:
            await update.message.reply_text(card)
    else:
        with open("gen.txt", "w") as file:
            for card in card_numbers:
                file.write(card + "\n")

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

async def generate_from_specific_bins(update: Update, context: ContextTypes.DEFAULT_TYPE, bin_type) -> None:
    user_id = update.effective_user.id

    if not is_registered(user_id):
        await update.message.reply_text("You need to register first using /register.")
        return

    if len(context.args) != 1:
        await update.message.reply_text(f"Usage: /{bin_type} <amount>")
        return

    try:
        count = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Amount should be a number.")
        return

    bin_data = load_bin_data(BIN_FILE_PATH)
    bin_list = [bin_number for bin_number, details in bin_data.items() if details['Brand'].upper() == bin_type.upper()]
    
    if not bin_list:
        await update.message.reply_text(f"No BINs found for the brand {bin_type}.")
        return

    bin_number = random.choice(bin_list)
    card_length = 16
    card_numbers = generate_test_cards(bin_number, card_length, count)

    if count < 20:
        for card in card_numbers:
            await update.message.reply_text(card)
    else:
        with open("gen.txt", "w") as file:
            for card in card_numbers:
                file.write(card + "\n")

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

async def generate_from_country_bins(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    bin_list = [bin_number for bin_number, details in bin_data.items() if details['isoCode2'].upper() == country_code]

    if not bin_list:
        await update.message.reply_text(f"No BINs found for the country code {country_code}.")
        return

    bin_number = random.choice(bin_list)
    card_length = 16
    card_numbers = generate_test_cards(bin_number, card_length, count)

    if count < 20:
        for card in card_numbers:
            await update.message.reply_text(card)
    else:
        with open("gen.txt", "w") as file:
            for card in card_numbers:
                file.write(card + "\n")

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

# Command handlers
async def cmds(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    if not is_registered(user_id):
        await update.message.reply_text("You need to register first using /register.")
        return

    commands = (
        "/start - Start the bot\n"
        "/register - Register to use the bot\n"
        "/gen <bin> <amount> - Generate cards with BIN and amount\n"
        "/gg <amount> - Generate cards from random bins\n"
        "/gv <amount> - Generate cards from Visa bins\n"
        "/gm <amount> - Generate cards from Mastercard bins\n"
        "/ga <amount> - Generate cards from American Express bins\n"
        "/gc <country_code> <amount> - Generate cards from bins of a specific country\n"
        "/bn <bin> - Lookup BIN information\n"
        "/cmds - Show this help message"
    )
    await update.message.reply_text(f"Here are the commands you can use:\n{commands}")

# Application setup
def main():
    application = Application.builder().token("YOUR_BOT_TOKEN_HERE").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("register", register))
    application.add_handler(CommandHandler("gen", generate))
    application.add_handler(CommandHandler("gg", generate_from_random_bins))
    application.add_handler(CommandHandler("gv", lambda u, c: generate_from_specific_bins(u, c, 'VISA')))
    application.add_handler(CommandHandler("gm", lambda u, c: generate_from_specific_bins(u, c, 'MASTERCARD')))
    application.add_handler(CommandHandler("ga", lambda u, c: generate_from_specific_bins(u, c, 'AMEX')))
    application.add_handler(CommandHandler("gc", generate_from_country_bins))
    application.add_handler(CommandHandler("bn", lambda u, c: lookup_bin(u, c)))
    application.add_handler(CommandHandler("cmds", cmds))

    application.run_polling()

if __name__ == "__main__":
    main()
