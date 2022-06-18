import json
import asyncio
import discord
from datetime import datetime
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands, tasks
from utility.config import config
from utility.utils import log, user_last_use_time
from utility.GenshinApp import genshin_app

class Schedule(commands.Cog, name='Automation(BETA)'):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.__daily_reward_filename = 'data/schedule_daily_reward.json'
        self.__resin_notifi_filename = 'data/schedule_resin_notification.json'
        try:
            with open(self.__daily_reward_filename, 'r', encoding='utf-8') as f:
                self.__daily_dict: dict[str, dict[str, str]] = json.load(f)
        except:
            self.__daily_dict: dict[str, dict[str, str]] = { }
        try:
            with open(self.__resin_notifi_filename, 'r', encoding='utf-8') as f:
                self.__resin_dict: dict[str, dict[str, str]] = json.load(f)
        except:
            self.__resin_dict: dict[str, dict[str, str]] = { }
        
        self.schedule.start()
    
    class ChooseGameButton(discord.ui.View):
        """Select the button to automatically sign in to the game"""
        def __init__(self, author: discord.Member, *, timeout: float = 30):
            super().__init__(timeout=timeout)
            self.value = None
            self.author = author
        
        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            return interaction.user.id == self.author.id
        
        @discord.ui.button(label='Genshin', style=discord.ButtonStyle.blurple)
        async def option1(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.defer()
            self.value = 'Genshin'
            self.stop()
        
        @discord.ui.button(label='Genshin+Honkai 3', style=discord.ButtonStyle.blurple)
        async def option2(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.defer()
            self.value = 'Genshin+Honkai'
            self.stop()

    class DailyMentionButton(discord.ui.View):
        """Whether to tag users for daily check-in"""
        def __init__(self, author: discord.Member, *, timeout: float = 30):
            super().__init__(timeout=timeout)
            self.value = True
            self.author = author
        
        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            return interaction.user.id == self.author.id
        
        @discord.ui.button(label='it is good!', style=discord.ButtonStyle.blurple)
        async def option1(self, interaction: discord.Interaction, button: discord.ui.button):
            await interaction.response.defer()
            self.value = True
            self.stop()
        
        @discord.ui.button(label='Need not', style=discord.ButtonStyle.blurple)
        async def option2(self, interaction: discord.Interaction, button: discord.ui.button):
            await interaction.response.defer()
            self.value = False
            self.stop()

    # Set up automatic scheduling function
    @app_commands.command(
        name='schedule',
        description='Set up automation functions (Hoyolab daily check-in, resin full reminder)')
    @app_commands.rename(function='function', switch='switch')
    @app_commands.describe(
        function='Select the function to automate',
        switch='Choose to turn this feature on or off')
    @app_commands.choices(
        function=[Choice(name='Show_instructions_for_use', value='help'),
                  Choice(name='Daily_automatic_check-in', value='daily'),
                  Choice(name='Resin_full_reminder', value='resin')],
        switch=[Choice(name='enable_function', value=1),
                Choice(name='turn_off_function', value=0)])
    async def slash_schedule(self, interaction: discord.Interaction, function: str, switch: int):
        log.info(f'[instruction][{interaction.user.id}]schedule(function={function}, switch={switch})')
        if function == 'help': # Instructions for using the scheduling function
            msg = ('· The schedule will execute the function at a specific time, and the execution result will be pushed to the channel of the set command\n'
             '· Before setting, please confirm that the genshin-lessen has the permission to speak in the channel. If the push message fails, the genshin-lessen will automatically remove the scheduling settings\n'
             '· To change the push channel, please reset the command once on the new channel\n\n'
            f'· Daily check-in: automatic forum check-in between {config.auto_daily_reward_time}~{config.auto_daily_reward_time+1} points every day, please use the `/daily daily check-in` command before setting to confirm that the helper can check in correctly for you\n'
            f'·Resin reminder: check every two hours, when the resin exceeds {config.auto_check_resin_threshold}, a reminder will be sent. Before setting, please use the `/notes instant note` command to confirm that the assistant can read your resin information\n')
            await interaction.response.send_message(embed=discord.Embed(title='Instructions for using the scheduling function', description=msg))
            return
        
        # Confirm whether the user has cookie data before setting
        check, msg = genshin_app.checkUserData(str(interaction.user.id))
        if check == False:
            await interaction.response.send_message(msg)
            return
        if function == 'daily': # Daily automatic check-in
            if switch == 1: # Turn on sign-in
                choose_game_btn = self.ChooseGameButton(interaction.user)
                await interaction.response.send_message('Please select a game to automatically sign in to:', view=choose_game_btn)
                await choose_game_btn.wait()
                if choose_game_btn.value == None: 
                    await interaction.edit_original_message(content='Cancelled', view=None)
                    return
                
                daily_mention_btn = self.DailyMentionButton(interaction.user)
                await interaction.edit_original_message(content=f'I hope the genshin-lessen will tag you when you check in automatically every day({interaction.user.mention})?', view=daily_mention_btn)
                await daily_mention_btn.wait()
                
                # add user
                self.__add_user(str(interaction.user.id), str(interaction.channel_id), self.__daily_dict, self.__daily_reward_filename, mention=daily_mention_btn.value)
                if choose_game_btn.value == 'Genshin + Honkai 3': # Added Honkai Impact 3 users
                    self.__add_honkai_user(str(interaction.user.id), self.__daily_dict, self.__daily_reward_filename)
                await interaction.edit_original_message(content=f'{choose_game_btn.value}Daily automatic check-in has been turned on, and a genshin-lessen when checking in{"會" if daily_mention_btn.value else "Will not"}tag you', view=None)
            elif switch == 0: # Turn off check-in
                self.__remove_user(str(interaction.user.id), self.__daily_dict, self.__daily_reward_filename)
                await interaction.response.send_message('Daily automatic check-in is turned off')
        elif function == 'resin': # Resin full reminder
            if switch == 1: # Turn on the check resin function
                self.__add_user(str(interaction.user.id), str(interaction.channel_id), self.__resin_dict, self.__resin_notifi_filename)
                await interaction.response.send_message('Resin full reminder is on')
            elif switch == 0: # Turn off check resin function
                self.__remove_user(str(interaction.user.id), self.__resin_dict, self.__resin_notifi_filename)
                await interaction.response.send_message('Resin full reminder is off')

    loop_interval = 10
    @tasks.loop(minutes=loop_interval)
    async def schedule(self):
        now = datetime.now()
        # Automatic check-in at {config.auto_daily_reward_time} points every day
        if now.hour == config.auto_daily_reward_time and now.minute < self.loop_interval:
            log.info('[schedule][System]schedule: Daily automatic check-in starts')
            # make a copy to avoid conflicts
            daily_dict = dict(self.__daily_dict)
            total, honkai_count = 0, 0
            for user_id, value in daily_dict.items():
                channel = self.bot.get_channel(int(value['channel']))
                has_honkai = False if value.get('honkai') == None else True
                check, msg = genshin_app.checkUserData(user_id, update_use_time=False)
                if channel == None or check == False:
                    self.__remove_user(user_id, self.__daily_dict, self.__daily_reward_filename)
                    continue
                result = await genshin_app.claimDailyReward(user_id, honkai=has_honkai, schedule=True)
                total += 1
                honkai_count += int(has_honkai)
                try:
                    if value.get('mention') == 'False':
                        user = await self.bot.fetch_user(int(user_id))
                        await channel.send(f'[automatic check-in] {user.display_name}: {result}')
                    else:
                        await channel.send(f'[automatic check-in] <@{user_id}> {result}')
                except Exception as e:
                    log.error(f'[schedule][{user_id}]Automatic check-in:{e}')
                    self.__remove_user(user_id, self.__daily_dict, self.__daily_reward_filename)
                await asyncio.sleep(config.auto_loop_delay)
            log.info(f'[schedule][System]schedule: Daily automatic check-in ends, total {total} people sign in, which {honkai_count} People also sign in collapse 3')
        
        # Resin checks every two hours and staggered from daily check-in times
        if abs(now.hour - config.auto_daily_reward_time) % 2 == 1 and now.minute < self.loop_interval:
            log.info('[schedule][System]schedule: Automatic resin check starts')
            resin_dict = dict(self.__resin_dict)
            count = 0
            for user_id, value in resin_dict.items():
                channel = self.bot.get_channel(int(value['channel']))
                check, msg = genshin_app.checkUserData(user_id, update_use_time=False)
                if channel == None or check == False:
                    self.__remove_user(user_id, self.__resin_dict, self.__resin_notifi_filename)
                    continue
                result = await genshin_app.getRealtimeNote(user_id, schedule=True)
                count += 1
                if result != None:
                    try:
                        if isinstance(result, str):
                            await channel.send(f'<@{user_id}>, an error occurred while automatically checking the resin:{result}')
                        else:
                            await channel.send(f'<@{user_id}>, The resin is (about to) overflow!', embed=result)
                    except:
                        self.__remove_user(user_id, self.__resin_dict, self.__resin_notifi_filename)
                await asyncio.sleep(config.auto_loop_delay)
            log.info(f'[schedule][System]schedule: Automatic checking of resin end,{count} person checked')
        
        user_last_use_time.save() # Regularly store the last usage time data of the user
        # Daily deletion of outdated user data
        if now.hour == 1 and now.minute < self.loop_interval:
            genshin_app.deleteExpiredUserData()

    @schedule.before_loop
    async def before_schedule(self):
        await self.bot.wait_until_ready()

    def __add_user(self, user_id: str, channel: str, data: dict, filename: str, *, mention: bool = True) -> None:
        data[user_id] = { }
        data[user_id]['channel'] = channel
        if mention == False:
            data[user_id]['mention'] = 'False'
        self.__saveScheduleData(data, filename)
    
    def __add_honkai_user(self, user_id: str, data: dict, filename: str) -> None:
        """Join Honkai 3 to sign in to an existing user, please confirm that you already have the user's information before using it"""
        if data.get(user_id) != None:
            data[user_id]['honkai'] = 'True'
            self.__saveScheduleData(data, filename)

    def __remove_user(self, user_id: str, data: dict, filename: str) -> None:
        try:
            del data[user_id]
        except:
            log.info(f'[exception][System]Schedule > __remove_user(user_id={user_id}): User does not exist')
        else:
            self.__saveScheduleData(data, filename)
    
    def __saveScheduleData(self, data: dict, filename: str):
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f)
        except:
            log.error(f'[exception][System]Schedule > __saveScheduleData(filename={filename}): Archive failed')

async def setup(client: commands.Bot):
    await client.add_cog(Schedule(client))