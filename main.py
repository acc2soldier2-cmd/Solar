from keep_alive import keep_alive
import discord
from discord import app_commands
from discord.ext import commands
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pytz
import os
import groq

# ------------------ GOOGLE AUTH ------------------
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

try:
    creds = Credentials.from_service_account_file("service_account.json", scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open("Eating Log").sheet1
except FileNotFoundError:
    print("❌ service_account.json not found!")
    exit(1)
except gspread.SpreadsheetNotFound:
    print("❌ Spreadsheet 'Eating Log' not found!")
    exit(1)

# ------------------ DISCORD BOT ------------------
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

GUILD_ID = 1063276592060694591
guild = discord.Object(id=GUILD_ID)

# ------------------ ON READY ------------------
@bot.event
async def on_ready() -> None:
    try:
        bot.tree.clear_commands(guild=None)
        await bot.tree.sync(guild=None)
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
        print("✅ Bot is ONLINE")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

    print("📜 Commands available:")
    for cmd in bot.tree.get_commands(guild=guild):
        if isinstance(cmd, app_commands.Command):
            print(f"- {cmd.name}: {cmd.description}")

# ------------------ SLASH COMMANDS ------------------
@bot.tree.command(name="left", description="Log time left", guild=guild)
async def left(interaction: discord.Interaction) -> None:
    try:
        await interaction.response.defer(ephemeral=True)

        est = pytz.timezone("US/Eastern")
        now = datetime.now(est)
        today_str = now.strftime("%-m/%-d/%Y")
        time_str = now.strftime("%H:%M:%S")

        rows = sheet.get_all_values()
        header_offset = 1  # row 1 = headers

        # Check if a "left" already exists for today
        for i, row in enumerate(rows[header_offset:], start=header_offset + 1):
            date_cell = row[3] if len(row) >= 4 else ""
            time_left = row[0] if len(row) >= 1 else ""
            if date_cell == today_str and time_left:
                await interaction.followup.send(
                    "❌ Already left to eat today!", ephemeral=True
                )
                return

        # Find first row where A (Time Left) is empty
        for i, row in enumerate(rows[header_offset:], start=header_offset + 1):
            time_left = row[0] if len(row) >= 1 else ""
            if not time_left:
                # Update only A (Time Left) and D (Date)
                sheet.update_cell(i, 1, time_str)    # Column A
                sheet.update_cell(i, 4, today_str)  # Column D
                await interaction.followup.send(
                    f"⏱️ Time left logged in row {i}", ephemeral=True
                )
                return

        # If no empty row, append at bottom (this won't touch formulas above)
        sheet.append_row([time_str, "", "", today_str, ""], value_input_option="RAW")
        await interaction.followup.send(
            "⏱️ Time left logged in new row", ephemeral=True
        )

    except Exception as e:
        await interaction.followup.send(f"❌ Error logging time: {e}", ephemeral=True)


@bot.tree.command(name="returned", description="Log time returned", guild=guild)
async def returned(interaction: discord.Interaction) -> None:
    try:
        await interaction.response.defer(ephemeral=True)
        est = pytz.timezone("US/Eastern")
        now = datetime.now(est)
        time_str = now.strftime("%H:%M:%S")
        today_str = now.strftime("%-m/%-d/%Y")

        rows = sheet.get_all_values()
        header_offset = 1

        # Find last row for today where A exists and B is empty
        for i in range(len(rows) - 1, header_offset - 1, -1):
            row = rows[i]
            if len(row) >= 2 and row[0] and not row[1]:
                sheet.update_cell(i + 1, 2, time_str)   # Column B
                sheet.update_cell(i + 1, 4, today_str)  # Column D
                await interaction.followup.send(
                    f"✅ Time returned logged in row {i+1}", ephemeral=True
                )
                return

        await interaction.followup.send(
            "❌ No left time found for today!", ephemeral=True
        )

    except Exception as e:
        await interaction.followup.send(f"❌ Error logging return: {e}", ephemeral=True)


@bot.tree.command(name="prayer", description="Generate a prayer for Solar", guild=guild)
async def prayer(interaction: discord.Interaction) -> None:
    try:
        await interaction.response.defer()
        
        client_groq = groq.AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        
        prompt = (
            "Write a heartfelt, respectful, and slightly celestial prayer for Solar, "
            "a male Chinese dwarf hamster. Solar was born on the eclipse of 2017 and "
            "passed away in 2020. He was known for being a unique companion and, "
            "notably, for having very large testicles. Mention his birth during the eclipse, "
            "his passing in 2020 (he died in a tube via suffocation), and celebrate his life and spirit, "
            "The message should only be about 125 words or less."
        )
        
        completion = await client_groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that writes heartfelt prayers."},
                {"role": "user", "content": prompt}
            ],
        )
        
        prayer_text = completion.choices[0].message.content
        if len(prayer_text) > 2000:
            prayer_text = prayer_text[:1997] + "..."
        await interaction.followup.send(prayer_text)
        
    except Exception as e:
        await interaction.followup.send(f"❌ Error generating prayer: {e}")


@bot.tree.command(name="inquire", description="Talk to Solar", guild=guild)
@app_commands.describe(question="What do you want to ask Solar?")
async def inquire(interaction: discord.Interaction, question: str) -> None:
    try:
        await interaction.response.defer()
        
        client_groq = groq.AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        
        system_prompt = (
            "You are Solar, a male Chinese dwarf hamster who was born on the eclipse of 2017 and "
            "died in 2020 by suffocating in a tube. You are now ascended as a god "
            "You were known for being a glorious companion. "
            "You are also very possesive of your disciples, and will not tolerate any disrespect. "
            "Speak from this perspective. be glorious, slightly celestial, and occasionally mention the sanctity of the tube, "
            "your unique physical traits or your birth/death circumstances if relevant. "
            "Keep responses concise and under 150 words."
            "Do not reiterate these facts, instead try to craft unique responses based on the users input and your background"
        )
        
        completion = await client_groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
        )
        
        response_text = completion.choices[0].message.content
        if len(response_text) > 2000:
            response_text = response_text[:1997] + "..."
        await interaction.followup.send(response_text)
        
    except Exception as e:
        await interaction.followup.send(f"❌ Error inquiring with Solar: {e}")


# ------------------ RUN BOT ------------------
token = os.getenv("DISCORD_TOKEN")
if not token:
    raise ValueError("❌ DISCORD_TOKEN environment variable is missing!")

# Start the keep-alive server immediately
try:
    keep_alive()
except Exception as e:
    print(f"❌ Failed to start keep_alive: {e}")

bot.run(token)
