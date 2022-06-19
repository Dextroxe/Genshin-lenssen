import discord
from discord import Embed, app_commands
from discord.app_commands import Choice
from discord.ext import commands
from typing import Optional
from utility.GenshinApp import genshin_app
from datetime import datetime

class Setting(commands.Cog, name='setting'):
    def __init__(self, bot):
        self.bot = bot

    # Form to submit cookies
    class CookieModal(discord.ui.Modal, title='Submit_cookies'):
        cookie = discord.ui.TextInput(
            label='Your cookie',
            placeholder='Please paste the cookie obtained from the webpage".',
            style=discord.TextStyle.long,
            required=True,
            min_length=100,
            max_length=1500
        )
        async def on_submit(self, interaction: discord.Interaction):
            result = await genshin_app.setCookie(str(interaction.user.id), self.cookie.value)
            await interaction.response.send_message(result, ephemeral=True)
        
        async def on_error(self, error: Exception, interaction: discord.Interaction):
            await interaction.response.send_message('Facing some unexpected issue, please try again!!', ephemeral=True)

    # Set user cookies
    @app_commands.command(
        name="setup",
        description='To set a cookie, you must use this directive to set a cookie before using it for the first time:)')
    @app_commands.rename(option='options-')
    @app_commands.choices(option=[
        Choice(name='how to get cookies for setup sus? ', value=0),
        Choice(name='Submit the obtained Cookie here if u have it!', value=1),
        Choice(name='Show use and storage of cookies of the Genshin lessen XD', value=2)])
    async def slash_cookie(self, interaction: discord.Interaction, option: int):
        if option == 0:
            help_msg = (
            "```1. First copy the entire code from **Above** of this embedded article\n\n"
             "2. open Hoyolab login account <https://www.hoyolab.com> on PC or mobile phone use Chrome(any browser) to \n\n"
             "3. Enter `java` in the address bar first, then paste the code(no space needed btw them), make sure the beginning of the URL becomes `javascript:`\n\n"
             "4. Press Enter, the page will change to display your cookies, select all and copy\n\n"
             "5. Submit the result here, use: `/setup submission to submit the obtained cookie`\n\n```")
            help_link=("https://i.imgur.com/CzUeQji.gif")
            footer_text=("Genshin-lenssen")
            code_msg = "```script:d=document.cookie; c=d.includes('account_id') || alert('Expired or invalid cookies, please log out and log in again!'); c && document.write(d)```"
           #customize your embeds
            embed_help = discord.Embed(title='Genshin lessen Cookie Usage and Storage Notice', description=help_msg,color=0xD2E1E1)
            embed_help.set_image(url=help_link)
            embed_help.timestamp = datetime.utcnow()
            embed_help.set_footer(text='\u200b',icon_url="https://i.imgur.com/Y0eIQKOt.png")
            await interaction.response.send_message(content=code_msg)
            await interaction.followup.send(embed=embed_help)
        elif option == 1:
            await interaction.response.send_modal(self.CookieModal())
        elif option == 2:
            msg = ('· The content of the cookie contains your personal identification code, not the account number and password\n'
                 '· Therefore, it cannot be used to log in to the game or change the account password. The content of the cookie looks like this:'
                 '`ltoken=xxxx ltuid=1234 cookie_token=yyyy account_id=1122`\n'
                 '· Genshin lessen saves and uses cookies in order to obtain your Genshin information and provide services on the Hoyolab website\n'
                 '· The Genshin lessen saves the data in the independent environment of the cloud host, and only connects to the Discord and Hoyolab servers\n'
                 '· For more detailed instructions, you can click on the personal file of the Genshin lessen to view the Baja description text. If you still have doubts, please do not use the Genshin lessen\n'
                 '· When submitting a cookie to Genshin lessen, it means that you have agreed to Genshin lessen to save and use your information\n'
                 '·You can delete the data saved in the helper at any time, please use the `/clear data` command without hesitation\n')
            embed = discord.Embed(title='Genshin lessen Cookie Usage and Storage Notice', description=msg,color=0xD2E1E1)
            await interaction.response.send_message(embed=embed)

    # Set the UID of Yuanshen, and save the specified UID when there are multiple characters in the account
    @app_commands.command(
        name='uid_setting',
        description='When there are multiple roles in the account, the specified UID needs to be saved.')
    @app_commands.describe(uid='Please enter the UID of the main character of "Yuanjin" to be saved')
    async def slash_uid(self, interaction: discord.Interaction, uid: int):
        await interaction.response.defer(ephemeral=True)
        result = await genshin_app.setUID(str(interaction.user.id), str(uid), check_uid=True)
        await interaction.edit_original_message(content=result)

    # Clear data confirmation button
    class ConfirmButton(discord.ui.View):
        def __init__(self, *, timeout: Optional[float] = 30):
            super().__init__(timeout=timeout)
            self.value = None
        
        @discord.ui.button(label='Cancel', style=discord.ButtonStyle.grey)
        async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.defer()
            self.value = False
            self.stop()
        
        @discord.ui.button(label='Sure', style=discord.ButtonStyle.red)
        async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.defer()
            self.value = True
            self.stop()
    
    # Delete saved profile
    @app_commands.command(
        name='clear_data',
        description='Delete all personal data of the user saved in the Genshin lessen')
    async def slash_clear(self, interaction: discord.Interaction):
        view = self.ConfirmButton()
        await interaction.response.send_message('Are you sure you want to delete?', view=view, ephemeral=True)
        
        await view.wait()
        if view.value == True:
            result = genshin_app.clearUserData(str(interaction.user.id))
            await interaction.edit_original_message(content=result, view=None)
        else:
            await interaction.edit_original_message(content='cancel the order', view=None)

async def setup(client: commands.Bot):
    await client.add_cog(Setting(client))