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
        "/gen <first|second|third|fourth> <amount> - Generate cards with specified format and amount\n"
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

    if len(context.args) != 2:
        await update.message.reply_text("Usage: /gen <first|second|third|fourth> <amount>")
        return

    input_data = context.args[0].split('|')
    if len(input_data) < 3 or len(input_data) > 4:
        await update.message.reply_text("Usage: /gen <first|second|third|fourth> <amount>")
        return

    first, second, third = input_data[:3]
    fourth = input_data[3] if len(input_data) == 4 else 'xx'
    try:
        count = int(context.args[1])
    except ValueError:
        await update.message.reply_text("Amount should be a number.")
        return

    def generate_card_number(prefix, length):
        card_number = [int(d) for d in str(prefix)]
        while len(card_number) < (length - 1):
            card_number.append(random.randint(0, 9))
        
        partial_number = ''.join(map(str, card_number))
        for check_digit in range(10):
            if is_luhn_valid(int(partial_number + str(check_digit))):
                card_number.append(check_digit)
                break
        return ''.join(map(str, card_number))

    def generate_expiration_date(exp_month, exp_year):
        month = exp_month if exp_month != 'xx' else str(random.randint(1, 12)).zfill(2)
        year = exp_year if exp_year != 'xx' else str(random.randint(25, 32))
        return f"{month}|{year}"

    def generate_cvv(cvv):
        return cvv if cvv != 'xx' else str(random.randint(100, 999)).zfill(3)

    card_length = 16
    cards = []

    for _ in range(count):
        card_number = generate_card_number(first, card_length)
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

        bin_data = load_bin_data(BIN_FILE_PATH)
        bin_info = bin_data.get(first[:6], {})
        if not bin_info:
            await update.message.reply_text(f"No information found for BIN {first[:6]}")
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
    all_bins = list(bin_data.keys())
    
    if not all_bins:
        await update.message.reply_text("No BINs found in the data.")
        return

    num_bins = min(len(all_bins), 5)
    selected_bins = random.sample(all_bins, num_bins)
    
    card_numbers = []
    card_length = 16
    
    for bin_number in selected_bins:
        card_numbers.extend(generate_test_cards(bin_number, card_length, count // num_bins))
    
    if count < 20:
        for card in card_numbers:
            await update.message.reply_text(card)
    else:
        with open("gen.txt", "w") as file:
            for card in card_numbers:
                file.write(card + "\n")
        
        with open("gen.txt", "rb") as file:
            await update.message.reply_document(document=file, filename="gen.txt")
        await update.message.reply_text(f"Generated {count} cards from multiple random BINs.")

async def generate_from_visa_bins(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    if not is_registered(user_id):
        await update.message.reply_text("You need to register first using /register.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("Usage: /gv <amount>")
        return

    try:
        count = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Amount should be a number.")
        return

    bin_data = load_bin_data(BIN_FILE_PATH)
    visa_bins = [bin_number for bin_number in bin_data if bin_number.startswith('4')]
    
    if not visa_bins:
        await update.message.reply_text("No Visa BINs found in the data.")
        return

    num_bins = min(len(visa_bins), 5)
    selected_bins = random.sample(visa_bins, num_bins)
    
    card_numbers = []
    card_length = 16
    
    for bin_number in selected_bins:
        card_numbers.extend(generate_test_cards(bin_number, card_length, count // num_bins))
    
    if count < 20:
        for card in card_numbers:
            await update.message.reply_text(card)
    else:
        with open("gen.txt", "w") as file:
            for card in card_numbers:
                file.write(card + "\n")
        
        with open("gen.txt", "rb") as file:
            await update.message.reply_document(document=file, filename="gen.txt")
        await update.message.reply_text(f"Generated {count} Visa cards.")

async def generate_from_mastercard_bins(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    if not is_registered(user_id):
        await update.message.reply_text("You need to register first using /register.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("Usage: /gm <amount>")
        return

    try:
        count = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Amount should be a number.")
        return

    bin_data = load_bin_data(BIN_FILE_PATH)
    mastercard_bins = [bin_number for bin_number in bin_data if bin_number.startswith('5')]
    
    if not mastercard_bins:
        await update.message.reply_text("No Mastercard BINs found in the data.")
        return

    num_bins = min(len(mastercard_bins), 5)
    selected_bins = random.sample(mastercard_bins, num_bins)
    
    card_numbers = []
    card_length = 16
    
    for bin_number in selected_bins:
        card_numbers.extend(generate_test_cards(bin_number, card_length, count // num_bins))
    
    if count < 20:
        for card in card_numbers:
            await update.message.reply_text(card)
    else:
        with open("gen.txt", "w") as file:
            for card in card_numbers:
                file.write(card + "\n")
        
        with open("gen.txt", "rb") as file:
            await update.message.reply_document(document=file, filename="gen.txt")
        await update.message.reply_text(f"Generated {count} Mastercard cards.")

async def generate_from_amex_bins(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    if not is_registered(user_id):
        await update.message.reply_text("You need to register first using /register.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("Usage: /ga <amount>")
        return

    try:
        count = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Amount should be a number.")
        return

    bin_data = load_bin_data(BIN_FILE_PATH)
    amex_bins = [bin_number for bin_number in bin_data if bin_number.startswith('3')]
    
    if not amex_bins:
        await update.message.reply_text("No American Express BINs found in the data.")
        return

    num_bins = min(len(amex_bins), 5)
    selected_bins = random.sample(amex_bins, num_bins)
    
    card_numbers = []
    card_length = 15
    
    for bin_number in selected_bins:
        card_numbers.extend(generate_test_cards(bin_number, card_length, count // num_bins))
    
    if count < 20:
        for card in card_numbers:
            await update.message.reply_text(card)
    else:
        with open("gen.txt", "w") as file:
            for card in card_numbers:
                file.write(card + "\n")
        
        with open("gen.txt", "rb") as file:
            await update.message.reply_document(document=file, filename="gen.txt")
        await update.message.reply_text(f"Generated {count} American Express cards.")

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
    country_bins = [bin_number for bin_number, data in bin_data.items() if data['isoCode2'] == country_code]
    
    if not country_bins:
        await update.message.reply_text(f"No BINs found for country code {country_code}.")
        return

    num_bins = min(len(country_bins), 5)
    selected_bins = random.sample(country_bins, num_bins)
    
    card_numbers = []
    card_length = 16
    
    for bin_number in selected_bins:
        card_numbers.extend(generate_test_cards(bin_number, card_length, count // num_bins))
    
    if count < 20:
        for card in card_numbers:
            await update.message.reply_text(card)
    else:
        with open("gen.txt", "w") as file:
            for card in card_numbers:
                file.write(card + "\n")
        
        with open("gen.txt", "rb") as file:
            await update.message.reply_document(document=file, filename="gen.txt")
        await update.message.reply_text(f"Generated {count} cards from bins of country code {country_code}.")

async def binlookup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /bn <bin>")
        return

    bin_number = context.args[0]
    bin_data = load_bin_data(BIN_FILE_PATH)

    if bin_number not in bin_data:
        await update.message.reply_text(f"No information found for BIN {bin_number}.")
        return

    bin_info = bin_data[bin_number]
    bin_details = (
        f"BIN: {bin_info['BIN']}\n"
        f"Brand: {bin_info['Brand']}\n"
        f"Type: {bin_info['Type']}\n"
        f"Category: {bin_info['Category']}\n"
        f"Issuer: {bin_info['Issuer']}\n"
        f"Country: {bin_info['CountryName']}"
    )
    await update.message.reply_text(f"BIN Information:\n{bin_details}")

async def cmds(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    commands = (
        "/start - Start the bot\n"
        "/register - Register to use the bot\n"
        "/gen <first|second|third|fourth> <amount> - Generate cards with specified format and amount\n"
        "/gg <amount> - Generate cards from random bins\n"
        "/gv <amount> - Generate cards from Visa bins\n"
        "/gm <amount> - Generate cards from Mastercard bins\n"
        "/ga <amount> - Generate cards from American Express bins\n"
        "/gc <country_code> <amount> - Generate cards from bins of a specific country\n"
        "/bn <bin> - Lookup BIN information\n"
        "/cmds - Show this help message"
    )
    await update.message.reply_text(f"Here are the commands you can use:\n{commands}")

def main() -> None:
    application = Application.builder().token("7528445359:AAEpk_rd_cgRrFRWkOobdwVFYUFrxZsiKyM").build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("register", register))
    application.add_handler(CommandHandler("gen", generate))
    application.add_handler(CommandHandler("gg", generate_from_random_bins))
    application.add_handler(CommandHandler("gv", generate_from_visa_bins))
    application.add_handler(CommandHandler("gm", generate_from_mastercard_bins))
    application.add_handler(CommandHandler("ga", generate_from_amex_bins))
    application.add_handler(CommandHandler("gc", generate_from_country_bins))
    application.add_handler(CommandHandler("bn", binlookup))
    application.add_handler(CommandHandler("cmds", cmds))
    
    application.run_polling()

if __name__ == "__main__":
    main()
