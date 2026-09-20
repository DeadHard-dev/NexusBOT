import os
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
import logging

# Отключаем лишний спам в логах от веб-сервера
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# --- 1. ЛЕГКИЙ ВЕБ-СЕРВЕР ДЛЯ RENDER ---
app = Flask('')
@app.route('/')
def home(): 
    return "OK", 200

@app.route('/healthz')
def health(): 
    return "OK", 200

def run(): 
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

def keep_alive(): 
    Thread(target=run, daemon=True).start()

# --- 2. НАСТРОЙКА ИНТЕНТОВ БОТА ---
class Bot(commands.Bot):
    def __init__(self):
        # Включаем абсолютно все интенты для гарантированного запуска
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(PersistentApplyView())

bot = Bot()

# --- 3. ОКНО АНКЕТЫ (MODAL) ---
class ApplicationModal(discord.ui.Modal, title="Анкета на вступление"):
    q1 = discord.ui.TextInput(label="Как вас зовут и сколько вам лет?", placeholder="Иван, 18", min_length=2)
    q2 = discord.ui.TextInput(label="Почему хотите именно к нам?", style=discord.TextStyle.paragraph, placeholder="Расскажите о себе...")
    q3 = discord.ui.TextInput(label="Ваш ник в игре / аккаунт", placeholder="NickName", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        ADMIN_CHANNEL_ID = int(os.environ.get("ADMIN_CHANNEL_ID", 0))
        channel = bot.get_channel(ADMIN_CHANNEL_ID)
        
        if not channel:
            await interaction.response.send_message("Ошибка: Не найден канал модераторов!", ephemeral=True)
            return

        embed = discord.Embed(title=f"Новая заявка от {interaction.user}", color=discord.Color.blue())
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="Имя и возраст:", value=self.q1.value, inline=False)
        embed.add_field(name="О себе:", value=self.q2.value, inline=False)
        embed.add_field(name="Ник:", value=self.q3.value or "Не указано", inline=False)

        view = AdminActionView(interaction.user)
        await channel.send(embed=embed, view=view)
        await interaction.response.send_message("Ваша заявка отправлена модераторам!", ephemeral=True)

# --- 4. КНОПКИ ДЛЯ АДМИНОВ ---
class AdminActionView(discord.ui.View):
    def __init__(self, applicant: discord.User):
        super().__init__(timeout=None)
        self.applicant = applicant

    @discord.ui.button(label="Принять", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        ROLE_ID = int(os.environ.get("ROLE_ID", 0))
        role = interaction.guild.get_role(ROLE_ID)
        member = interaction.guild.get_member(self.applicant.id)
        
        if member and role:
            await member.add_roles(role)
            try: await self.applicant.send(f"Ваша заявка на сервере {interaction.guild.name} одобрена!")
            except: pass
            await interaction.response.send_message(f"✅ {interaction.user.mention} одобрил {self.applicant.mention}", ephemeral=False)
            self.stop()
        else:
            await interaction.response.send_message("Ошибка: не удалось выдать роль.", ephemeral=True)

    @discord.ui.button(label="Отклонить", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        try: await self.applicant.send(f"Ваша заявка на сервере {interaction.guild.name} отклонена.")
        except: pass
        await interaction.response.send_message(f"❌ {interaction.user.mention} отклонил {self.applicant.mention}", ephemeral=False)
        self.stop()

# --- 5. КНОПКА ПОДАЧИ ЗАЯВКИ ---
class PersistentApplyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📋 Подать заявку", style=discord.ButtonStyle.primary, custom_id="persistent_apply_button")
    async def apply_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ApplicationModal())

# --- 6. КОМАНДЫ БОТА ---
@bot.command()
@commands.has_permissions(administrator=True)
async def setup_apply(ctx):
    embed = discord.Embed(
        title="Набор на сервер", 
        description="Нажмите на кнопку ниже, чтобы заполнить анкету.", 
        color=discord.Color.green()
    )
    await ctx.send(embed=embed, view=PersistentApplyView())

@bot.event
async def on_ready():
    print(f"Робот {bot.user} успешно запущен и подключен!")

# --- ЗАПУСК ---
keep_alive()
bot.run(os.environ.get("DISCORD_TOKEN"))
