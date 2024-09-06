import csv
import random
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os
import csv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os

BIN_FILE_PATH = 'bin-list-data.csv'  # Path to your CSV file
VIDEO_FILE_PATH = 'ice.mp4'  # Path to your welcome video
USERS_FILE_PATH = 'bot_users.txt'
def load_bin_data(file_path):
    bin_data = {}
    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            bin_data[row['BIN']] = row
    return bin_data

# Load CSV data
def load_bin_data(file_path):
    bin_data = {}
    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            bin_data[row['BIN']] = row
    return bin_data

# Generate credit card number using Luhn algorithm
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

def generate_expiration_date(month='xx', year='xx'):
    if month == 'xx':
        month = str(random.randint(1, 12)).zfill(2)
    if year == 'xx':
        year = str(random.randint(25, 32))
    return f"{month}|{year}"

def generate_cvv(cvv='xx'):
    return cvv if cvv != 'xx' else str(random.randint(100, 999)).zfill(3)

# Generate test cards
def generate_test_cards(bin_number, length, count, fixed_expiration_date=None, fixed_cvv=None):
    cards = []
    for _ in range(count):
        card_number = generate_credit_card_number(bin_number, length)
        expiration_date = fixed_expiration_date or generate_expiration_date()
        cvv = fixed_cvv or generate_cvv()
        cards.append(f"{card_number}|{expiration_date}|{cvv}")
    return cards

# Check if user is registered
def is_registered(user_id):
    if not os.path.exists(USERS_FILE_PATH):
        return False
    with open(USERS_FILE_PATH, "r") as file:
        return str(user_id) in file.read().splitlines()

# /start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if is_registered(user_id):
        await update.message.reply_text("Welcome back! Use /gen <bin> <amount> to generate credit card details.")
        return

    with open(VIDEO_FILE_PATH, 'rb') as video:
        await update.message.reply_video(video, caption="Welcome! Please register using /register to use the bot.")
        await update.message.reply_text("To use the bot, please register with the /register command.")

# /register command handler
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
        "/gen <first|second|third|fourth> [<amount>] - Generate cards with BIN and amount\n"
        "/gg <amount> - Generate cards from random bins\n"
        "/gv <amount> - Generate cards from Visa bins\n"
        "/gm <amount> - Generate cards from Mastercard bins\n"
        "/ga <amount> - Generate cards from American Express bins\n"
        "/gc <country_code> <amount> - Generate cards from bins of a specific country\n"
        "/bn <bin> - Lookup BIN information\n"
        "/cmds - Show this help message"
    )
    await update.message.reply_text(f"Here are the commands you can use:\n{commands}")

# Generate cards with /gen command
async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    if not is_registered(user_id):
        await update.message.reply_text("You need to register first using /register.")
        return

    if len(context.args) < 1:
        await update.message.reply_text("Usage: /gen <first|second|third|fourth> [<amount>]")
        return

    input_data = context.args[0].split('|')
    if len(input_data) < 3 or len(input_data) > 4:
        await update.message.reply_text("Usage: /gen <first|second|third|fourth> [<amount>]")
        return

    first, second, third = input_data[:3]
    fourth = input_data[3] if len(input_data) == 4 else 'xx'

    try:
        count = int(context.args[1]) if len(context.args) > 1 else 10000
    except ValueError:
        await update.message.reply_text("Amount should be a number.")
        return

    card_length = 16
    cards = []

    for _ in range(count):
        card_number = generate_credit_card_number(first, card_length)
        expiration_date = generate_expiration_date(second, third)
        cvv = generate_cvv(fourth)
        cards.append(f"{card_number}|{expiration_date}|{cvv}")

    if count < 20:
        for card in cards:
            await update.message.reply_text(card)
    else:
        with open("gen.txt", "w") as file:
            for card in cards:
                file.write(card + "\n")

        bin_info = load_bin_data(BIN_FILE_PATH)
        bin_details = bin_info.get(first[:6], {})
        if not bin_details:
            await update.message.reply_text(f"No information found for BIN {first[:6]}")
            return
        
        bin_details_text = (
            f"BIN: {bin_details['BIN']}\n"
            f"Brand: {bin_details['Brand']}\n"
            f"Type: {bin_details['Type']}\n"
            f"Category: {bin_details['Category']}\n"
            f"Issuer: {bin_details['Issuer']}\n"
            f"Country: {bin_details['CountryName']}"
        )

        with open("gen.txt", "rb") as file:
            await update.message.reply_document(document=file, filename="gen.txt")
        await update.message.reply_text(f"BIN Information:\n{bin_details_text}")

# Generate cards from random BINs (Visa, Mastercard, etc.)
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

    card_length = 16
    card_numbers = []
    
    for _ in range(count):
        bin_number = random.choice(bin_list)
        card_number = generate_credit_card_number(bin_number, card_length)
        expiration_date = generate_expiration_date()
        cvv = generate_cvv()
        card_numbers.append(f"{card_number}|{expiration_date}|{cvv}")

    if count < 20:
        for card in card_numbers:
            await update.message.reply_text(card)
    else:
        with open("gen.txt", "w") as file:
            for card in card_numbers:
                file.write(card + "\n")
        await update.message.reply_document(document=open("gen.txt", "rb"), filename="gen.txt")
async def bin_lookup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /bn <first 6 digits of BIN>")
        return

    bin_number = context.args[0]
    if len(bin_number) != 6 or not bin_number.isdigit():
        await update.message.reply_text("Please provide the first 6 digits of a BIN number.")
        return

    bin_data = load_bin_data(BIN_FILE_PATH)
    bin_details = bin_data.get(bin_number)

    if not bin_details:
        await update.message.reply_text(f"No information found for BIN {bin_number}")
    else:
        bin_details_text = (
            f"BIN: {bin_details['BIN']}\n"
            f"Brand: {bin_details['Brand']}\n"
            f"Type: {bin_details['Type']}\n"
            f"Category: {bin_details['Category']}\n"
            f"Issuer: {bin_details['Issuer']}\n"
            f"Issuer Phone: {bin_details['IssuerPhone']}\n"
            f"Issuer URL: {bin_details['IssuerUrl']}\n"
            f"Country: {bin_details['CountryName']} ({bin_details['isoCode2']})"
        )
        await update.message.reply_text(f"BIN Information:\n{bin_details_text}")

# Add command handler for /bn
application = Application.builder().token("YOUR TELEGRAM BOT TOKEN").build()
application.add_handler(CommandHandler("bn", bin_lookup))

# Start the bot
if __name__ == "__main__":
    application.run_polling()
# /gg command for random BINs
async def gg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await generate_from_random_bins(update, context, prefixes=["4", "5", "6", "37", "34"])

# /gv command for Visa
async def gv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await generate_from_random_bins(update, context, prefixes=["4"])

# /gm command for Mastercard
async def gm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await generate_from_random_bins(update, context, prefixes=["5"])

# /ga command for American Express
async def ga(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await generate_from_random_bins(update, context, prefixes=["37", "34"])

# /cmds command to show all commands
async def cmds(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    commands = (
        "/start - Start the bot\n"
        "/register - Register to use the bot\n"
        "/gen <first|second|third|fourth> [<amount>] - Generate cards with BIN and amount\n"
        "/gg <amount> - Generate cards from random bins\n"
        "/gv <amount> - Generate cards from Visa bins\n"
        "/gm <amount> - Generate cards from Mastercard bins\n"
        "/ga <amount> - Generate cards from American Express bins\n"
        "/gc <country_code> <amount> - Generate cards from bins of a specific country\n"
        "/bn <bin> - Lookup BIN information\n"
        "/cmds - Show this help message"
    )
    await update.message.reply_text(f"Here are the commands you can use:\n{commands}")

# Main function to start the bot
def main():
    application = Application.builder().token("7528445359:AAEpk_rd_cgRrFRWkOobdwVFYUFrxZsiKyM").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("register", register))
    application.add_handler(CommandHandler("gen", generate))
    application.add_handler(CommandHandler("gg", gg))
    application.add_handler(CommandHandler("gv", gv))
    application.add_handler(CommandHandler("gm", gm))
    application.add_handler(CommandHandler("ga", ga))
    application.add_handler(CommandHandler("cmds", cmds))

    application.run_polling()

if __name__ == "__main__":
    main()
