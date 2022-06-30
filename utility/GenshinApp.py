import asyncio
import json
import discord
import genshin
from datetime import datetime, timedelta
from typing import Sequence, Union, Tuple
from .emoji import Emoji, emoji
from .utils import log, getCharacterName, trimCookie, getServerName, getDayOfWeek, user_last_use_time
from .config import config
from discord.emoji import Emoji


def Conv_month(num):
    month = {1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June',
             7: 'July', 8: 'August', 9: 'September', 10: 'October', 11: 'November', 12: 'December'}
    return month[num]


class GenshinApp:
    def __init__(self) -> None:
        try:
            with open('data/user_data.json', 'r', encoding="utf-8") as f:
                self.__user_data: dict[str, dict[str, str]] = json.load(f)
        except:
            self.__user_data: dict[str, dict[str, str]] = {}

    async def setCookie(self, user_id: str, cookie: str) -> str:

        """Set user cookies

        ------
        Parameters
        user_id `str`: user Discord ID
        cookie `str`: Hoyolab cookie
        ------
        Returns
        `str`: Reply to message to user
        """
        log.info(f'[instruction][{user_id}]setCookie: cookie={cookie}')
        user_id = str(user_id)
        cookie = trimCookie(cookie)
        if cookie == None:
            return f'Invalid cookie, please re-enter (enter `/cookie settings` to display instructions)'
        client = genshin.Client(lang='en-us')
        client.set_cookies(cookie)
        try:
            accounts = await client.get_game_accounts()
        except genshin.errors.GenshinException as e:
            log.info(
                f'[exception][{user_id}]setCookie: [retcode]{e.retcode} [Exceptions]{e.original}')
            result = e.original
        else:
            if len(accounts) == 0:
                log.info(
                    f'[News][{user_id}]setCookie: There are no roles in the account')
                result = 'There is no role in the account, cancel the setting of cookies'
            else:
                self.__user_data[user_id] = {}
                self.__user_data[user_id]['cookie'] = cookie
                log.info(
                    f'[News][{user_id}]setCookie: Cookie set successfully')

                if len(accounts) == 1 and len(str(accounts[0].uid)) == 9:
                    await self.setUID(user_id, str(accounts[0].uid))
                    result = f'Cookie has been set, role UID: {accounts[0].uid} Saved!'
                else:
                    result = f'Shared in account{len(accounts)}roles\n```'
                    for account in accounts:
                        result += f'UID:{account.uid} AR:{account.level} Name:{account.nickname}\n'
                    result += f'```\nPlease use `/uid setting` to specify the character to save Genshin Impact (Example: `/uid setting 812345678`)'
                    self.__saveUserData()
        finally:
            return result

    async def setUID(self, user_id: str, uid: str, *, check_uid: bool = False) -> str:
        """Set the UID of Yuanshen, and save the specified UID when there are multiple characters in the account

        ------
        Parameters
        user_id `str`: User Discord ID
        uid `str`: Genshin Impact UID to be saved
        check_uid `bool`: `True`Indicates to check if this UID is valid `False` Indicates direct storage without checking
        ------
        Returns
        `str`: Reply to message to user
        """
        log.info(
            f'[instruction][{user_id}]setUID: uid={uid}, check_uid={check_uid}')
        if not check_uid:
            self.__user_data[user_id]['uid'] = uid
            self.__saveUserData()
            return f'Character UID: {uid} has been set'
        check, msg = self.checkUserData(user_id, checkUID=False)
        if check == False:
            return msg
        if len(uid) != 9:
            return f'The UID length is wrong, please re-enter the correct UID of Genshin Impact'

        # Check if UID exists
        client = self.__getGenshinClient(user_id)
        try:
            accounts = await client.get_game_accounts()
        except Exception as e:
            log.error(f'[exception][{user_id}]setUID: {e}')
            return 'Failed to confirm account information, please reset cookies or try again later'
        else:
            if int(uid) in [account.uid for account in accounts]:
                self.__user_data[user_id]['uid'] = uid
                self.__saveUserData()
                log.info(f'[News][{user_id}]setUID: {uid} set up')
                return f'Character UID: {uid} set up'
            else:
                log.info(
                    f'[News][{user_id}]setUID: Could not find character profile for this UID')
                return f'The character information for this UID cannot be found, please confirm whether the input is correct'

    def getUID(self, user_id: str) -> Union[int, None]:
        if user_id in self.__user_data.keys():
            return int(self.__user_data[user_id].get('uid'))
        return None

    async def getRealtimeNote(self, user_id: str, *, schedule=False) -> Union[None, str, discord.Embed]:
        """Obtain user instant notes (resin, Dongtianbao money, parameter quality changer, dispatch, daily, weekly)

        ------
        Parameters
        user_id `str`: User Discord ID
        schedule `bool`: Whether to check resin for scheduling, when set to `True`, the instant note result will 
        only be returned when the resin exceeds the set standard
        ------
        Returns
        `None | str | Embed`: When the resin is automatically checked, `None` is returned 
        if it is not overflowing normally; an error message `str` is returned when an exception occurs, 
        and the query result `discord.Embed` is returned under normal conditions
        """
        if not schedule:
            log.info(f'[instruction][{user_id}]getRealtimeNote')
        check, msg = self.checkUserData(
            user_id, update_use_time=(not schedule))
        if check == False:
            return msg

        uid = self.__user_data[user_id]['uid']
        client = self.__getGenshinClient(user_id)
        try:
            notes = await client.get_genshin_notes(int(uid))
        except genshin.errors.DataNotPublic:
            log.info(f'[exception][{user_id}]getRealtimeNote: DataNotPublic')
            return 'The instant note function is not enabled, please enable the instant note function from the Hoyolab website or app first'
        except genshin.errors.InvalidCookies as e:
            log.info(
                f'[exception][{user_id}]getRealtimeNote: [retcode]{e.retcode} [Exceptions]{e.original}')
            return 'The cookie has expired, please reset the cookie'
        except genshin.errors.GenshinException as e:
            log.info(
                f'[exception][{user_id}]getRealtimeNote: [retcode]{e.retcode} [Exceptions]{e.original}')
            return e.original
        except Exception as e:
            log.error(f'[exception][{user_id}]getRealtimeNote: {e}')
            return str(e)
        else:
            if schedule == True and notes.current_resin < config.auto_check_resin_threshold:
                return None
            else:
                msg = f'{getServerName(uid[0])} {uid.replace(uid[3:-3], "&&&", 1)}\n'
                msg += f'~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~~-~-~-~-~\n'
                msg += self.__parseNotes(notes, shortForm=schedule)
                # According to the amount of resin, with 80 as the dividing line, the embed color changes from green (0x28c828) to yellow (0xc8c828), and then to red (0xc82828)
                r = notes.current_resin
                color = 0x28c828 + 0x010000 * \
                    int(0xa0 * r / 80) if r < 80 else 0xc8c828 - \
                    0x000100 * int(0xa0 * (r - 80) / 80)
                embed = discord.Embed(description=msg, color=color)
                return embed

    async def redeemCode(self, user_id: str, code: str) -> str:
        """Use the specified redemption code for the user

        ------
        Parameters
        user_id `str`: User Discord ID
        code `str`: Hoyolab redemption code
        ------
        Returns
        `str`: Reply to user's message
        """
        log.info(f'[instruction][{user_id}]redeemCode: code={code}')
        check, msg = self.checkUserData(user_id)
        if check == False:
            return msg
        client = self.__getGenshinClient(user_id)

        try:
            await client.redeem_code(code, int(self.__user_data[user_id]['uid']), lang="en-us")
        except genshin.errors.GenshinException as e:
            log.info(
                f'[exception][{user_id}]redeemCode: [retcode]{e.retcode} [Exceptions]{e.original}')
            result = e.original
        except Exception as e:
            log.error(f'[exception][{user_id}]redeemCode: [Exceptions]{e}')
            result = f'{e}'
        else:
            result = f'Redeem code {code}  successful!'
        finally:
            return result

    async def claimDailyReward(self, user_id: str, *, honkai: bool = False, schedule=False) -> str:
        """Sign in for users at Hoyolab

        ------
        Parameters
        user_id `str`: User Discord ID
        honkai `bool`: whether to also sign in Honkai 3
        schedule `bool`: whether to check in automatically for the schedule
        ------
        Returns
        `str`:Reply to user's message
        """
        if not schedule:
            log.info(
                f'[instruction][{user_id}]claimDailyReward: honkai={honkai}')
        check, msg = self.checkUserData(
            user_id, update_use_time=(not schedule))
        if check == False:
            return msg
        client = self.__getGenshinClient(user_id)

        game_name = {genshin.Game.GENSHIN: 'Genshin',
                     genshin.Game.HONKAI: 'Honaki 3'}

        async def claimReward(game: genshin.Game, retry: int = 3) -> str:
            try:
                reward = await client.claim_daily_reward(game=game)
            except genshin.errors.AlreadyClaimed:
                return f"{game_name[game]}Today's reward has been received!"
            except genshin.errors.GenshinException as e:
                log.info(
                    f'[exception][{user_id}]claimDailyReward: {game_name[game]}[retcode]{e.retcode} [Exceptions]{e.original}')
                if e.retcode == 0 and retry > 0:
                    await asyncio.sleep(0.5)
                    return await claimReward(game, retry - 1)
                if e.retcode == -10002 and game == genshin.Game.HONKAI:
                    return 'Honkai 3 failed to sign in, no character information was found, please confirm whether the captain has bound the new HoYoverse pass'
                return f'{game_name[game]}Failed to sign in: [retcode]{e.retcode} [content]{e.original}'
            except Exception as e:
                log.error(
                    f'[exception][{user_id}]claimDailyReward: {game_name[game]}[Exceptions]{e}')
                return f'{game_name[game]}Failed to sign in: {e}'
            else:
                return f'{game_name[game]}Sign in done successfully, got {reward.amount}x {reward.name}！'

        result = await claimReward(genshin.Game.GENSHIN)
        if honkai:
            result = result + ' ' + await claimReward(genshin.Game.HONKAI)

        # Hoyolab community check-in
        try:
            await client.check_in_community()
        except genshin.errors.GenshinException as e:
            log.info(
                f'[exception][{user_id}]claimDailyReward: Hoyolab[retcode]{e.retcode} [Exceptions]{e.original}')
        except Exception as e:
            log.error(
                f'[exception][{user_id}]claimDailyReward: Hoyolab[Exceptions]{e}')

        return result

    async def getSpiralAbyss(self, user_id: str, previous: bool = False) -> Union[str, genshin.models.SpiralAbyss]:
        """Get Spiral Abyss information

        ------
       Parameters
         user_id `str`: User Discord ID
         previous `bool`: `True` to query the information of the previous issue, `False` to query the information of the current issue
         ------
         Returns
         `Union[str, SpiralAbyss]`: return error message `str` when exception occurs, return query result `SpiralAbyss` under normal conditions
        """
        log.info(
            f'[instruction][{user_id}]getSpiralAbyss: previous={previous}')
        check, msg = self.checkUserData(user_id)
        if check == False:
            return msg
        client = self.__getGenshinClient(user_id)
        try:
            abyss = await client.get_genshin_spiral_abyss(int(self.__user_data[user_id]['uid']), previous=previous)
        except genshin.errors.GenshinException as e:
            log.error(
                f'[exception][{user_id}]getSpiralAbyss: [retcode]{e.retcode} [Exceptions]{e.original}')
            return e.original
        except Exception as e:
            log.error(f'[exception][{user_id}]getSpiralAbyss: [Exceptions]{e}')
            return f'{e}'
        else:
            return abyss

    async def getTravelerDiary(self, user_id: str, month: int) -> Union[str, discord.Embed]:
        """Get user traveler's notes

        ------
        Parameters:
        user_id `str`: User Discord ID
         month `int`: the month to query
         ------
         Returns:
         `Union[str, discord.Embed]`: return error message `str` when exception occurs, return query result `discord.Embed` under normal conditions
        """
        log.info(f'[instruction][{user_id}]getTravelerDiary: month={month}')
        check, msg = self.checkUserData(user_id)
        if check == False:
            return msg
        client = self.__getGenshinClient(user_id)
        try:
            diary = await client.get_diary(int(self.__user_data[user_id]['uid']), month=month)
        except genshin.errors.GenshinException as e:
            log.error(
                f'[exception][{user_id}]getTravelerDiary: [retcode]{e.retcode} [exception]{e.original}')
            result = e.original
        except Exception as e:
            log.error(
                f'[exception][{user_id}]getTravelerDiary: [exception]{e}')
            result = f'{e}'
        else:
            d = diary.data
            result = discord.Embed(
                title=f"{diary.nickname}'s Notes for {Conv_month(month)}",
                description=f'Primogems income compared to last month {"increased" if d.primogems_rate > 0 else "reduced"} to {abs(d.primogems_rate)}%, Mora income compared to last month {"increased" if d.mora_rate > 0 else "reduced"} to {abs(d.mora_rate)}%',
                color=0xfd96f4
            )
            result.add_field(
                name='Obtained this month',
                value=f'{emoji.items.primogem}This month {d.current_primogems} ({round(d.current_primogems/160)}{emoji.items.intertwined_fate}) || Last month {d.last_primogems} ({round(d.last_primogems/160)}{emoji.items.intertwined_fate})\n'
                f'{emoji.items.mora}This month {format(d.current_mora, ",")} ||  Last month {format(d.last_mora, ",")}',
                inline=False
            )
            # Divide the note rough composition into two fields
            for i in range(0, 2):
                msg = ''
                length = len(d.categories)
                for j in range(round(length/2*i), round(length/2*(i+1))):
                    msg += f'{d.categories[j].name[0:15]}: {d.categories[j].percentage}%\n'
                result.add_field(
                    name=f'Primogems Income Composition ({i+1})', value=msg, inline=True)
        finally:
            return result

    async def getRecordCard(self, user_id: str) -> Union[str, Tuple[genshin.models.RecordCard, genshin.models.PartialGenshinUserStats]]:
        """Get user record card

        ------
         Parameters:
         user_id `str`: User Discord ID
         ------
         Returns:
         `str | (RecordCard, PartialGenshinUserStats)`: Error message `str` is returned when an exception occurs, and query results are returned under normal conditions `(RecordCard, PartialGenshinUserStats)`
        """
        log.info(f'[instruction][{user_id}]getRecordCard')
        check, msg = self.checkUserData(user_id)
        if check == False:
            return msg
        client = self.__getGenshinClient(user_id)
        try:
            cards = await client.get_record_cards()
            userstats = await client.get_partial_genshin_user(int(self.__user_data[user_id]['uid']))
        except genshin.errors.GenshinException as e:
            log.error(
                f'[exception][{user_id}]getRecordCard: [retcode]{e.retcode} [exception]{e.original}')
            return e.original
        except Exception as e:
            log.error(f'[exception][{user_id}]getRecordCard: [exception]{e}')
            return str(e)
        else:
            for card in cards:
                if card.uid == int(self.__user_data[user_id]['uid']):
                    return (card, userstats)
            return "Can't find Genshin record card"

    async def getCharacters(self, user_id: str) -> Union[str, Sequence[genshin.models.Character]]:
        """Get all user role data

         ------
         Parameters:
         user_id `str`: User Discord ID
         ------
         Returns:
         `str | Sequence[Character]`: When an exception occurs, the error message `str` is returned, and the query result `Sequence[Character]` is returned under normal conditions.
        """
        log.info(f'[instruction][{user_id}]getCharacters')
        check, msg = self.checkUserData(user_id)
        if check == False:
            return msg
        client = self.__getGenshinClient(user_id)
        try:
            characters = await client.get_genshin_characters(int(self.__user_data[user_id]['uid']))
        except genshin.errors.GenshinException as e:
            log.error(
                f'[exception][{user_id}]getCharacters: [retcode]{e.retcode} [exception]{e.original}')
            return e.original
        except Exception as e:
            log.error(f'[exception][{user_id}]getCharacters: [exception]{e}')
            return str(e)
        else:
            return characters

    def checkUserData(self, user_id: str, *, checkUID=True, update_use_time=True) -> Tuple[bool, str]:
        """Check if user-related data has been saved in the database

         ------
         Parameters
         user_id `str`: User Discord ID
         checkUID `bool`: whether to check UID
         update_use_time `bool`: whether to update the user's last use time
         ------
         Returns
         `bool`: `True` checks successfully, the data exists in the database; `False` fails, the data does not exist in the database
         `str`: message to the user when the check fails
        """
        if user_id not in self.__user_data.keys():
            log.info(f'[News][{user_id}]checkUserData: User not found')
            return False, f'Cannot find the user, please set a cookie first (enter `/cookie setting` to display the description)'
        else:
            if 'cookie' not in self.__user_data[user_id].keys():
                log.info(f'[News][{user_id}]checkUserData: Cookie not foundv')
                return False, f"Can't find cookie, please set cookie first (enter `/cookie setting` to display instructions)"
            if checkUID and 'uid' not in self.__user_data[user_id].keys():
                log.info(
                    f'[News][{user_id}]checkUserData: Character UID not found')
                return False, f'Cannot find character UID, please set UID first (use `/uid setting` to set UID)'
        if update_use_time:
            user_last_use_time.update(user_id)
        return True, None

    def clearUserData(self, user_id: str) -> str:
        """Permanently delete user data from the database

         ------
         Parameters
         user_id `str`: User Discord ID
         ------
         Returns:
         `str`: the message to reply to the user
        """
        log.info(f'[instruction][{user_id}]clearUserData')
        try:
            del self.__user_data[user_id]
            user_last_use_time.deleteUser(user_id)
        except:
            return 'Deletion failed, user data not found'
        else:
            self.__saveUserData()
            return 'User data has all been deleted'

    def deleteExpiredUserData(self) -> None:
        """Delete users that have not been used for more than 30 days"""
        now = datetime.now()
        count = 0
        user_data = dict(self.__user_data)
        for user_id in user_data.keys():
            if user_last_use_time.checkExpiry(user_id, now, 30) == True:
                self.clearUserData(user_id)
                count += 1
        log.info(
            f'[News][System]deleteExpiredUserData: {len(user_data)} users checked, deleted {count} expired users')

    def parseAbyssOverview(self, abyss: genshin.models.SpiralAbyss) -> discord.Embed:
        """Analyze the abyss overview data, including date, number of layers, number of battles, total number of stars...etc.

         ------
         Parameters
         abyss `SpiralAbyss`: Deep Spiral Information
         ------
         Returns
         `discord.Embed`: discord embed format
        """
        result = discord.Embed(
            description=f'Info of Abyss cycle -> {abyss.season}th cycle    &    Date: {abyss.start_time.astimezone().strftime("%Y.%m.%d")} to {abyss.end_time.astimezone().strftime("%Y.%m.%d")}', color=0x6959c1)
        def get_char(c): return ' ' if len(
            c) == 0 else f'{getCharacterName(c[0])}: {c[0].value}'
        result.add_field(
            name=f'Deepest descension: {abyss.max_floor}, Battles: {"👑" if abyss.total_stars == 36 and abyss.total_battles == 12 else abyss.total_battles}, ★ earned: {abyss.total_stars}',
            value=f'[mobs defeats] {get_char(abyss.ranks.most_kills)}\n'
            f'[highest damage dealt] {get_char(abyss.ranks.strongest_strike)}\n'
            f'[highest damage taken] {get_char(abyss.ranks.most_damage_taken)}\n'
            f'[Burst unleashed] {get_char(abyss.ranks.most_bursts_used)}\n'
            f'[Skill casts] {get_char(abyss.ranks.most_skills_used)}',
            inline=False
        )
        return result

    def parseAbyssFloor(self, embed: discord.Embed, abyss: genshin.models.SpiralAbyss, full_data: bool = False) -> discord.Embed:
        """Analyze each floor of the abyss, add the number of stars on each floor and the character data used to the embed

         ------
         Parameters
         embed `discord.Embed`: Embed data obtained from the `parseAbyssOverview` function
         abyss `SpiralAbyss`: Deep Spiral Information
         full_data `bool`: `True` means parsing all floors; `False` means parsing only the last level
         ------
         Returns
         `discord.Embed`: discord embed format
        """
        for floor in abyss.floors:
            if full_data == False and floor is not abyss.floors[-1]:
                continue
            for chamber in floor.chambers:
                name = f'{floor.floor}-{chamber.chamber} ★{chamber.stars}'
                # Get the character name of the upper and lower half layers of the abyss
                chara_list = [[], []]
                for i, battle in enumerate(chamber.battles):
                    for chara in battle.characters:
                        chara_list[i].append(getCharacterName(chara))
                value = f'[{",".join(chara_list[0])}] || \n[{",".join(chara_list[1])}]\n'
                embed.add_field(name=name, value=value)
        return embed

    def parseCharacter(self, character: genshin.models.Character) -> discord.Embed:
        """Analyze characters, including zodiac, level, favor, weapons, Artifacts

         ------
         Parameters
         character `Character`: character profile
         ------
         Returns
         `discord.Embed`: discord embed format
        """
        color = {'pyro': 0xfb4120, 'electro': 0xbf73e7, 'hydro': 0x15b1ff,
                 'cryo': 0x70daf1, 'dendro': 0xa0ca22, 'anemo': 0x5cd4ac, 'geo': 0xfab632}
        embed = discord.Embed(color=color.get(character.element.lower()))
        embed.set_thumbnail(url=character.icon)
        embed.add_field(name=f'★{character.rarity} {character.name}', inline=True,
                        value=f'Constellation: {character.constellation}\n Character lvl: {character.level}\n Friendship lvl: {character.friendship}')

        weapon = character.weapon
        embed.add_field(name=f'★{weapon.rarity} {weapon.name}', inline=True,
                        value=f'refinement lvl: {weapon.refinement}\n Weapon lvl: {weapon.level}')

        if character.constellation > 0:
            number = {1: 'First', 2: 'Second', 3: 'Third',
                      4: 'Fourth', 5: 'Fifth', 6: 'Sixth'}
            msg = '\n'.join(
                [f'Constellation: {number[constella.pos]} <> Name: {constella.name}' for constella in character.constellations if constella.activated])
            embed.add_field(name='Constellation', inline=False, value=msg)

        if len(character.artifacts) > 0:
            msg = '\n'.join(
                [f'{artifact.pos_name}: {artifact.name} ({artifact.set.name})' for artifact in character.artifacts])
            embed.add_field(name='Artifacts', inline=False, value=msg)

        return embed

    def __parseNotes(self, notes: genshin.models.Notes, shortForm: bool = False) -> str:
        result = ''
        # Original resin
        msg = "is reclaimable "
        result += f'{emoji.notes.resin} Current original resin {notes.current_resin}|{notes.max_resin}\n'
        if notes.current_resin >= notes.max_resin:
            recover_time = 'Now! {enjoy<:search:987357570308124672>}'
        else:
            day_msg = msg+getDayOfWeek(notes.resin_recovery_time)
            recover_time = f'{day_msg} {notes.resin_recovery_time.strftime("%H : %M")}'
        result += f'{emoji.notes.resin} Original resin  will be stuffed {recover_time}\n'
        # daily, weekly
        if not shortForm:
            result += f'{emoji.notes.commission} Daily commisions left : {notes.max_commissions - notes.completed_commissions} \n'
            result += f"{emoji.notes.enemies_of_note} Weekly discount left: {notes.remaining_resin_discounts} \n"
        result += f'~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-\n'
        # realm currency
        result += f'{emoji.notes.realm_currency} Current Realm Currency {notes.current_realm_currency}|{notes.max_realm_currency}\n'
        if notes.max_realm_currency > 0:
            if notes.current_realm_currency >= notes.max_realm_currency:
                recover_time = 'is ready to be claim! <:search:987357570308124672>'
            else:
                day_msg = msg+getDayOfWeek(notes.realm_currency_recovery_time)
                recover_time = f'{day_msg} {notes.realm_currency_recovery_time.strftime("%H : %M")}'
            result += f'{emoji.notes.realm_currency} Realm Currency  {recover_time}\n'
        # parametric transformer analyzer remaining time
        if notes.transformer_recovery_time != None:
            t = notes.remaining_transformer_recovery_time
            if t.days > 0:
                recover_time = f'in remaining {t.days} Days'
            elif t.hours > 0:
                recover_time = f'in remaining {t.hours} Hours'
            elif t.minutes > 0:
                recover_time = f'in remaining {t.minutes} Minutes'
            elif t.seconds > 0:
                recover_time = f'in remaining {t.seconds} Seconds'
            else:
                recover_time = 'Now! <:search:987357570308124672>'
            result += f'{emoji.notes.transformer} Parametric transformer can be used {recover_time}\n'
        # Explore Dispatch Remaining Time
        if not shortForm:
            result += f'~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-\n'
            exped_finished = 0
            exped_msg = ''
            for expedition in notes.expeditions:
                exped_msg += f"<:exp:987399117418401842>  {getCharacterName(expedition.character)}'s"
                # {emoji.notes.exped}
                if expedition.finished:
                    exped_finished += 1
                    exped_msg += 'completed!\n'
                else:
                    day_msg = getDayOfWeek(expedition.completion_time)
                    exped_msg += f' expeditions: {day_msg} {expedition.completion_time.strftime("%H:%M")}\n'
            result += f"__- - Right now **{exped_finished} Expeditions** are completed - - \n\n__"
            # {len(notes.expeditions)}\
            result += exped_msg

        return result

    def __saveUserData(self) -> None:
        try:
            with open('data/user_data.json', 'w', encoding='utf-8') as f:
                json.dump(self.__user_data, f)
        except:
            log.error(
                '[exception][System]GenshinApp > __saveUserData: Archive failed')

    def __getGenshinClient(self, user_id: str) -> genshin.Client:
        uid = self.__user_data[user_id].get('uid')
        if uid != None and uid[0] in ['1', '2', '5']:
            client = genshin.Client(
                region=genshin.Region.OVERSEAS, lang='en-us')
        else:
            client = genshin.Client(lang='en-us')
        client.set_cookies(self.__user_data[user_id]['cookie'])
        client.default_game = genshin.Game.GENSHIN
        return client


genshin_app = GenshinApp()
