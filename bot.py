import os
import discord
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

tickets = {}


def build_embed(data):
    embed = discord.Embed(
        title="🆘 Szukam pomocy z attunem",
        color=discord.Color.blue()
    )

    embed.add_field(name="👤 Gracz", value=data["nick"], inline=True)
    embed.add_field(name="⭐ Level", value=data["level"], inline=True)
    embed.add_field(name="🏰 Dungeon", value=data["dungeon"], inline=False)
    embed.add_field(name="🕒 Dostępność", value=data["availability"], inline=False)

    same_list = "\n".join(f"• {x}" for x in data["same"])
    help_list = "\n".join(f"• {x}" for x in data["helpers"]) if data["helpers"] else "Brak"

    embed.add_field(
        name=f"👥 Robią ten sam dungeon ({len(data["same"])})",
        value=same_list,
        inline=False
    )

    embed.add_field(
        name=f"🛡️ Pomagający ({len(data["helpers"])})",
        value=help_list,
        inline=False
    )

    if data.get("closed"):
        embed.set_footer(text="Zgłoszenie zostało zamknięte")

    return embed


class TicketButtons(discord.ui.View):
    def __init__(self, message_id):
        super().__init__(timeout=None)
        self.message_id = message_id

    @discord.ui.button(label="🟦 Mam to samo", style=discord.ButtonStyle.primary, custom_id="same_attune")
    async def same(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = tickets[self.message_id]
        user = interaction.user.display_name

        if data.get("closed"):
            await interaction.response.send_message("To zgłoszenie jest już zamknięte.", ephemeral=True)
            return

        if user in data["helpers"]:
            await interaction.response.send_message("Jesteś już zapisany jako pomagający.", ephemeral=True)
            return

        if user not in data["same"]:
            data["same"].append(user)

        await interaction.response.edit_message(embed=build_embed(data), view=self)

    @discord.ui.button(label="🟩 Pomogę", style=discord.ButtonStyle.success, custom_id="help_attune")
    async def help(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = tickets[self.message_id]
        user = interaction.user.display_name

        if data.get("closed"):
            await interaction.response.send_message("To zgłoszenie jest już zamknięte.", ephemeral=True)
            return

        if user in data["same"]:
            await interaction.response.send_message("Jesteś już zapisany jako osoba robiąca ten dungeon.", ephemeral=True)
            return

        if user not in data["helpers"]:
            data["helpers"].append(user)

        await interaction.response.edit_message(embed=build_embed(data), view=self)

    @discord.ui.button(label="⬜ Wypisz się", style=discord.ButtonStyle.secondary, custom_id="leave_attune")
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = tickets[self.message_id]
        user = interaction.user.display_name

        if data.get("closed"):
            await interaction.response.send_message("To zgłoszenie jest już zamknięte.", ephemeral=True)
            return

        if user == data["author"]:
            await interaction.response.send_message(
                "Autor zgłoszenia nie może się wypisać. Możesz zamknąć zgłoszenie.",
                ephemeral=True
            )
            return

        if user in data["same"]:
            data["same"].remove(user)

        if user in data["helpers"]:
            data["helpers"].remove(user)

        await interaction.response.edit_message(embed=build_embed(data), view=self)

    @discord.ui.button(label="🔒 Zamknij zgłoszenie", style=discord.ButtonStyle.danger, custom_id="close_attune")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = tickets[self.message_id]

        if interaction.user.id != data["author_id"]:
            await interaction.response.send_message(
                "Tylko autor zgłoszenia może je zamknąć.",
                ephemeral=True
            )
            return

        data["closed"] = True

        embed = build_embed(data)
        embed.title = "✅ Zgłoszenie zamknięte"
        embed.color = discord.Color.dark_grey()

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)


class AttuneForm(discord.ui.Modal, title="Nowe zgłoszenie attune"):
    nick = discord.ui.TextInput(label="Nick w grze", max_length=50)

    level = discord.ui.TextInput(label="Level", max_length=10)

    dungeon = discord.ui.TextInput(
        label="Dungeon, na który szukasz pomocy",
        max_length=100
    )

    availability = discord.ui.TextInput(
        label="Dostępność",
        style=discord.TextStyle.paragraph,
        max_length=200
    )

    async def on_submit(self, interaction: discord.Interaction):
        data = {
            "nick": self.nick.value,
            "level": self.level.value,
            "dungeon": self.dungeon.value,
            "availability": self.availability.value,
            "same": [self.nick.value],
            "helpers": [],
            "author": self.nick.value,
            "author_id": interaction.user.id,
            "closed": False
        }

        embed = build_embed(data)

        await interaction.response.send_message(
            "✅ Zgłoszenie zostało utworzone.",
            ephemeral=True
        )

        message = await interaction.channel.send(embed=embed)

        tickets[message.id] = data

        await message.edit(view=TicketButtons(message.id))


class AttunePanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="📝 Szukam pomocy",
        style=discord.ButtonStyle.green,
        custom_id="create_attune"
    )
    async def create_attune(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AttuneForm())


@bot.event
async def on_ready():
    print(f"Bot zalogowany jako {bot.user}")

    bot.add_view(AttunePanel())

    try:
        synced = await bot.tree.sync()
        print(f"Zsynchronizowano {len(synced)} komend")
    except Exception as e:
        print(e)


@bot.tree.command(
    name="panel",
    description="Tworzy panel pomocy attune"
)
async def panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🛡️ Attune Helper",
        description=(
            "Masz problem z dungeonem potrzebnym do attunu?\n\n"
            "Kliknij przycisk poniżej, aby utworzyć zgłoszenie. Inni gracze będą mogli dołączyć do Ciebie lub zgłosić się do pomocy.\n\n"
            "**Jak to działa?**\n"
            "• Kliknij **📝 Szukam pomocy**\n"
            "• Wypełnij krótki formularz\n"
            "• Bot opublikuje Twoje zgłoszenie\n"
            "• Inni klikają **Mam to samo** lub **Pomogę**\n"
            "• Gdy zmienią Ci się plany, użyj **Wypisz się**"
        ),
        color=discord.Color.green()
    )

    await interaction.response.send_message(embed=embed, view=AttunePanel())


bot.run(TOKEN)