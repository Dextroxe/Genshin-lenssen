import discord
import asyncio
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
from utility.GenshinApp import genshin_app

class GenshinTool(commands.Cog, name='Genshin_tool'):
    def __init__(self, bot):
        self.bot = bot

    # Use the specified redemption code for the user
    @app_commands.command(
        name='redeem',
        description='Redeem code with Hoyolab')
    @app_commands.rename(code='redemption_code')
    @app_commands.describe(code='Please enter the redemption code to use')
    async def slash_redeem(self, interaction: discord.Interaction, code: str):
        asyncio.create_task(interaction.response.defer())
        result = await genshin_app.redeemCode(str(interaction.user.id), code)
        await interaction.edit_original_message(content=result)

    # Sign in for users at Hoyolab
    @app_commands.command(
        name='daily_check_in',
        description='Receive Hoyolab Daily Check-in Rewards')
    @app_commands.rename(game='game')
    @app_commands.choices(game=[
        Choice(name=' Genshin', value=0), 
        Choice(name='Genshin Impact + Honkai Impact 3', value=1)])
    async def slash_daily(self, interaction: discord.Interaction, game: int = 0):
        asyncio.create_task(interaction.response.defer())
        result = await genshin_app.claimDailyReward(str(interaction.user.id), honkai=bool(game))
        await interaction.edit_original_message(content=result)

async def setup(client: commands.Bot):
    await client.add_cog(GenshinTool(client))