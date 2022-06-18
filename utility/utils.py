import logging
import genshin
import re
import json
from datetime import datetime
from data.game.characters import characters_map

__file_handler = logging.FileHandler('data/error.log', encoding='utf-8')
__file_handler.setLevel(logging.WARNING)
__console_handler = logging.StreamHandler()
__console_handler.setLevel(logging.INFO)
__formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s', '%Y-%m-%d %H:%M:%S')
__file_handler.setFormatter(__formatter)
__console_handler.setFormatter(__formatter)
logging.getLogger().setLevel(logging.INFO)
logging.getLogger().addHandler(__file_handler)
logging.getLogger().addHandler(__console_handler)
log = logging

def getCharacterName(character: genshin.models.BaseCharacter) -> str:
    chinese_name = None
    if (id := str(character.id)) in characters_map:
        chinese_name = characters_map[id].get('name')
    return chinese_name if chinese_name != None else character.name

def trimCookie(cookie: str) -> str:
    try:
        new_cookie = ' '.join([
            re.search('ltoken=[0-9A-Za-z]{20,}', cookie).group(),
            re.search('ltuid=[0-9]{3,}', cookie).group(),
            re.search('cookie_token=[0-9A-Za-z]{20,}', cookie).group(),
            re.search('account_id=[0-9]{3,}', cookie).group()
        ])
    except:
        new_cookie = None
    return new_cookie

__server_dict = {'os_usa': 'US server', 'os_euro': 'Europea server', 'os_asia': 'Asia server', 'os_cht': 'Taiwan, Hong Kong and Macau',
     '1': 'Sky Island', '2': 'Sky Island', '5': 'World Tree', '6': 'America server', '7': 'Europea server', '8': ' Asia server', '9': 'Taiwan, Hong Kong and Macau'}
def getServerName(key: str) -> str:
    return __server_dict.get(key)

__weekday_dict = {0: 'on Monday', 1: 'Tuesday', 2: 'Wednesday', 3: 'Thursday', 4: 'Friday', 5: 'Saturday', 6: 'Sunday'}
def getDayOfWeek(time: datetime) -> str:
    delta = time.date() - datetime.now().astimezone().date()
    if delta.days == 0:
        return 'today'
    elif delta.days == 1:
        return 'tomorrow'
    return __weekday_dict.get(time.weekday())

class UserLastUseTime:
    def __init__(self) -> None:
        try:
            with open('data/last_use_time.json', 'r', encoding="utf-8") as f:
                self.data: dict[str, str] = json.load(f)
        except:
            self.data: dict[str, str]  = { }

    def update(self, user_id: str) -> None:
        """Update user last used time"""
        self.data[user_id] = datetime.now().isoformat()
    
    def deleteUser(self, user_id: str) -> None:
        self.data.pop(user_id, None)

    def checkExpiry(self, user_id: str, now: datetime, diff_days: int = 30) -> bool:
        """Check if the user has not used the service for a certain period of time
        param user_id: User Discord ID
        param now: the current time
        param diff_days: how many days the difference is
        """
        last_time = self.data.get(user_id)
        if last_time == None:
            self.update(user_id)
            return False
        interval = now - datetime.fromisoformat(last_time)
        return True if interval.days > diff_days else False

    def save(self) -> None:
        try:
            with open('data/last_use_time.json', 'w', encoding="utf-8") as f:
                json.dump(self.data, f)
        except Exception as e:
            log.error(f'[exception][System]UserLastUseTime > save: {e}')

user_last_use_time = UserLastUseTime()