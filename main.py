import os
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask
from threading import Thread

# --- 1. ВЕБ-СЕРВЕР ДЛЯ ОБХОДА ОГРАНИЧЕНИЙ RENDER ---
app = Flask('')
@app.route('/')
def home(): return "Бот онлайн!"

def run(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
def keep_alive(): Thread(target=run).start()

# --- 2. НАСТРОЙКА БОТА ---
class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Регистрируем кнопку, чтобы она не пропадала после перезапуска бота
        self.add_view(PersistentApplyView())

bot = Bot()

# --- 3. ОКНО АНКЕТЫ (MODAL) ---
class ApplicationModal(discord.ui.Modal, title="Анкета на вступление"):
    # Поля анкеты (можно менять вопросы здесь)
    q1 = discord.ui.TextInput(label="Как вас зовут и сколько вам лет?", placeholder="Иван, 18", min_length=2)
    q2 = discord.ui.TextInput(label="Почему хотите именно к нам?", style=discord.TextStyle.paragraph, placeholder="Расскажите немного о себе...")
    q3 = discord.ui.TextInput(label="Ваш ник в игре / аккаунт", placeholder="NickName#1234", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        # Находим канал, куда бот будет присылать заявки для админов
        # ЗАМЕНИТЕ ID НИЖЕ НА ID ВАШЕГО ТЕКСТОВОГО КАНАЛА ДЛЯ МОДЕРАТОРОВ
        ADMIN_CHANNEL_ID = int(os.environ.get("ADMIN_CHANNEL_ID", 0))
        channel = bot.get_channel(ADMIN_CHANNEL_ID)
        
        if not channel:
            await interaction.response.send_message("Ошибка: Не настроен канал для модераторов!", ephemeral=True)
            return

        # Красиво оформляем заявку
        embed = discord.Embed(title=f"Новая заявка от {interaction.user}", color=discord.Color.blue())
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="Имя и возраст:", value=self.q1.value, inline=False)
        embed.add_field(name="О себе / Почему мы:", value=self.q2.value, inline=False)
        embed.add_field(name="Доп. контакты:", value=self.q3.value or "Не указано", inline=False)
        embed.set_footer(text=f"ID пользователя: {interaction.user.id}")

        # Добавляем кнопки управления для админов
        view = AdminActionView(interaction.user)

        await channel.send(embed=embed, view=view)
        await interaction.response.send_message("Ваша заявка успешно отправлена на рассмотрение модераторам!", ephemeral=True)

# --- 4. КНОПКИ ДЛЯ АДМИНОВ ---
class AdminActionView(discord.ui.View):
    def __init__(self, applicant: discord.User):
        super().__init__(timeout=None)
        self.applicant = applicant

    @discord.ui.button(label="Принять", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        # ЗАМЕНИТЕ ID НИЖЕ НА ID РОЛИ, КОТОРУЮ НАДО ВЫДАТЬ
        ROLE_ID = int(os.environ.get("ROLE_ID", 0))
        role = interaction.guild.get_role(ROLE_ID)
        
        member = interaction.guild.get_member(self.applicant.id)
        if member and role:
            await member.add_roles(role)
            try: await self.applicant.send(f"Поздравляем! Ваша заявка на сервере {interaction.guild.name} была одобрена!")
            except: pass
            await interaction.response.send_message(f"✅ {interaction.user.mention} одобрил заявку от {self.applicant.mention}", ephemeral=False)
            self.stop()
        else:
            await interaction.response.send_message("Не удалось выдать роль (пользователь вышел или неверный ID роли).", ephemeral=True)

    @discord.ui.button(label="Отклонить", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        try: await self.applicant.send(f"К сожалению, ваша заявка на сервере {interaction.guild.name} была отклонена.")
        except: pass
        await interaction.response.send_message(f"❌ {interaction.user.mention} отклонил заявку от {self.applicant.mention}", ephemeral=False)
        self.stop()

# --- 5. КНОПКА ПОДАЧИ ЗАЯВКИ ДЛЯ ОБЩЕГО КАНАЛА ---
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
    """Команда для создания сообщения с кнопкой подачи заявки"""
    embed = discord.Embed(
        title="Набор на сервер", 
        description="Нажмите на кнопку ниже, чтобы заполнить анкету и получить доступ к серверу.", 
        color=discord.Color.green()
    )
    await ctx.send(embed=embed, view=PersistentApplyView())

@bot.event
async def on_ready():
    print(f"Робот {bot.user} запущен!")
    try:
        synced = await bot.tree.sync()
        print(f"Синхронизировано команд: {len(synced)}")
    except Exception as e:
        print(e)

# --- ЗАПУСК ---
keep_alive()
bot.run(os.environ.get("DISCORD_TOKEN"))
