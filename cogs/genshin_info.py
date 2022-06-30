import datetime
import discord
import genshin
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Sequence
from discord import app_commands
from discord.ext import commands
from discord.app_commands import Choice
from utility.GenshinApp import genshin_app
from utility.draw import drawRecordCard, drawAbyssCard
from utility.utils import log
from utility.config import config
from utility.emoji import emoji
from utility import Enka

class GenshinInfo(commands.Cog, name='Genshin_Impact_Information'):
    def __init__(self, bot):
        self.bot = bot

    # Obtain user's instant note information (resin, realm currency , dispatch...etc.)
    @app_commands.command(
        name='notes',
        description='Real-Time Notes is here for Resin, Realm currency, exploration dispatch and many more.')
    async def slash_notes(self, interaction: discord.Interaction):
        result = await genshin_app.getRealtimeNote(str(interaction.user.id))
        if isinstance(result, str):
            await interaction.response.send_message(result)
        else:
            await interaction.response.send_message(embed=result)
    
    # Abyss Records
    @app_commands.command(
        name='abyss-craft',
        description='Query for the spiral Abyss')
    @app_commands.checks.cooldown(1, config.slash_cmd_cooldown)
    @app_commands.rename(season='period', floor='floor')
    @app_commands.describe(
        season='Select current or previous record',
        floor='Select the display method of floor person records')
    @app_commands.choices(
        season=[Choice(name='Previous abyss cycle', value=0),
                 Choice(name='Latest abyss cycle', value=1)],
         floor=[Choice(name='Show all floors', value=0),
                Choice(name='Show last floor', value=1)])
    async def slash_abyss(self, interaction: discord.Interaction, season: int = 1, floor: int = 2):
        asyncio.create_task(interaction.response.defer())
        previous = True if season == 0 else False
        result = await genshin_app.getSpiralAbyss(str(interaction.user.id), previous)
        if isinstance(result, str):
            await interaction.edit_original_message(content=result)
            return

        embed = genshin_app.parseAbyssOverview(result)
        embed.title = f'{interaction.user.display_name} Spiral Abyss Info'
        if floor == 0: # [text] show all floors
            embed = genshin_app.parseAbyssFloor(embed, result, True)

            embed.set_image(url="https://theclick.gg/wp-content/uploads/2021/07/Spiral_Abyss-genshin.png")
            embed.set_thumbnail(url="https://theclick.gg/wp-content/uploads/2021/07/Spiral_Abyss-genshin.png")
            embed.set_footer (text='``Challenge different floors of the tower and defeat the enemies within to win Abyssal Stars. Do this, and the Spiral Abyss may yet look upon your hard work and bestow rewards upon you.``',icon_url="https://theclick.gg/wp-content/uploads/2021/07/Spiral_Abyss-genshin.png")
            await interaction.edit_original_message(embed=embed)
        # elif floor == 1: # [text] only show the last layer
        #     embed = genshin_app.parseAbyssFloor(embed, result, False)
            await interaction.edit_original_message(embed=embed)
        elif floor == 1: # [image] only show the last layer``
            try:
                fp = drawAbyssCard(result)
            except Exception as e:
                log.error(f'[exception][{interaction.user.id}][slash_abyss]: {e}')
                await interaction.edit_original_message(content='An error occurred, image creation failed')
            else:
                embed.set_thumbnail(url=interaction.user.display_avatar.url)
                fp.seek(0)
                file = discord.File(fp, filename='image.jpeg')
                embed.set_image(url='attachment://image.jpeg')
                await interaction.edit_original_message(embed=embed, attachments=[file])
    
    @slash_abyss.error
    async def on_slash_abyss_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(f'The interval for using the command is {config.slash_cmd_cooldown}seconds, please try again later~', ephemeral=True)

    # Get user traveler's notes
    @app_commands.command(
        name="diary",
        description="Check Traveler's Notes (Primogems & Mora Income)")
    @app_commands.rename(month='month')
    @app_commands.describe(month='Please select the month to query')
    @app_commands.choices(month=[
            Choice(name='This month', value=0),
            Choice(name='last month', value=-1)])
            # Choice(name='last month', value=-2)])
    async def slash_diary(self, interaction: discord.Interaction, month: int):
        month = datetime.datetime.now().month + month
        month = month + 12 if month < 1 else month
        result = await genshin_app.getTravelerDiary(str(interaction.user.id), month)
        if type(result) == discord.Embed:
            await interaction.response.send_message(embed=result)
        else:
            await interaction.response.send_message(result)

    # Generate personal record card
    @app_commands.command(name='summary_card', description='Generating Personal embed Profile with cute pic :)')
    @app_commands.checks.cooldown(1, config.slash_cmd_cooldown)
    async def slash_card(self, interaction: discord.Interaction):
        await interaction.response.defer()
        result = await genshin_app.getRecordCard(str(interaction.user.id))

        if isinstance(result, str):
            await interaction.edit_original_message(content=result)
            return
        
        avatar_bytes = await interaction.user.display_avatar.read()
        card = result[0]
        userstats = result[1]
        try:
            fp = drawRecordCard(avatar_bytes, card, userstats)
        except Exception as e:
            log.error(f'[exception][{interaction.user.id}][slash_card]: {e}')
            await interaction.edit_original_message(content='An error occurred, card creation failed')
        else:
            fp.seek(0)
            await interaction.edit_original_message(attachments=[discord.File(fp=fp, filename='image.jpeg')])
            fp.close()

    @slash_card.error
    async def on_slash_card_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(f'The interval for generating cards is {config.slash_cmd_cooldown}The interval for generating cards is~', ephemeral=True)

    class CharactersDropdown(discord.ui.Select):
        """Drop-down menu to select role"""
        def __init__(self, previous_interaction: discord.Interaction, characters: Sequence[genshin.models.Character], index: int = 1):
            options = [discord.SelectOption(
                    label=f'★{character.rarity} Lv.{character.level} {character.name}',
                    value=str(i),
                    emoji=emoji.elements.get(character.element.lower())
                ) for i, character in enumerate(characters)
            ]
            super().__init__(placeholder=f'choose your character (No. 1 {index}~{index + len(characters) - 1} name)', min_values=1, max_values=1, options=options)
            self.characters = characters
            self.previous_interaction = previous_interaction
        
        async def callback(self, interaction: discord.Interaction):
            try:
                await interaction.response.defer()
                embed = genshin_app.parseCharacter(self.characters[int(self.values[0])])
                embed.title = f"{self.previous_interaction.user.display_name}'s Character"
                await self.previous_interaction.edit_original_message(content=None, embed=embed)
            except Exception as e:
                log.info(f'[exception][{interaction.user.id}]CharactersDropdown > callback: {e}')
    
    class CharactersDropdownView(discord.ui.View):
        """Displays the View of the role drop-down menu, and divides the menu according to the upper limit of 25 menu fields."""
        def __init__(self, previous_interaction: discord.Interaction, characters: Sequence[genshin.models.Character]):
            super().__init__(timeout=180)
            max_row = 25
            for i in range(0, len(characters), max_row):
                self.add_item(GenshinInfo.CharactersDropdown(previous_interaction, characters[i:i+max_row], i+1))
    
    # List of all personal roles
    @app_commands.command(name='my_characters', description='Show all my characters publicly')
    async def slash_character(self, interaction: discord.Interaction):
        asyncio.create_task(interaction.response.defer())
        result = await genshin_app.getCharacters(str(interaction.user.id))

        if isinstance(result, str):
            await interaction.edit_original_message(content=result)
            return
        
        view = self.CharactersDropdownView(interaction, result)
        await interaction.edit_original_message(content='Please select a Character:', view=view)
        await view.wait()
        await interaction.edit_original_message(view=None)

    # Character showcase
    @app_commands.command(name='profile_characters', description='Query the public character showcase of the player with the specified UID')
    @app_commands.describe(uid="The UID of the player to be queried, if the helper has saved the data, you don't need to fill in this field to check yourself"
    )
    async def slash_showcase(self, interaction: discord.Interaction, uid: Optional[int] = None):
        asyncio.create_task(interaction.response.defer())
        uid = uid or genshin_app.getUID(str(interaction.user.id))
        log.info(f'[instruction][{interaction.user.id}]character showcase: uid={uid}')
        if uid == None:
            await interaction.edit_original_message(content='The user information cannot be found in the little helper, please directly enter the UID to be queried in the command uid parameter')
        elif len(str(uid)) != 9 or str(uid)[0] not in ['1', '2', '5', '6', '7', '8', '9']:
            await interaction.edit_original_message(content='The entered UID is in the wrong format')
        else:
            showcase = Enka.Showcase()
            try:
                await showcase.getEnkaData(uid)
            except Enka.ShowcaseNotPublic as e:
                embed = showcase.getPlayerOverviewEmbed()
                embed.description += f"\n{e}"
                await interaction.edit_original_message(embed=embed)
            except Exception as e:
                await interaction.edit_original_message(content=f"{e}")
                log.info(f'[exception][{interaction.user.id}] Character Showcase: {e}')
            else:
                view = Enka.ShowcaseView(showcase)
                embed = showcase.getPlayerOverviewEmbed()
                await interaction.edit_original_message(embed=embed, view=view)
                await view.wait()
                await interaction.edit_original_message(view=None)

async def setup(client: commands.Bot):
    await client.add_cog(GenshinInfo(client))