import json
import re
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import requests
from io import BytesIO
from telegram import ParseMode
from telegram import ChatAction
import datetime
import pytz
import time

TOKEN = '6944444483:AAEVTb5PoDzQTBaiAcqnfxQRG58bZEuTyKc'
target_channel_username = '-1002043346027'
forward_group_ids = ['-1001996113668']
upch_id = '-1001940633610'

def upload_file_to_gofile(file_io, file_name):
    upload_url = 'https://store3.gofile.io/uploadFile'
    files = {'file': (file_name, file_io, 'application/octet-stream')}
    response = requests.post(upload_url, files=files)

    if response.status_code == 200:
        file_link = response.json().get('data', {}).get('downloadPage')
        return file_link
    else:
        return null_link

def get_json_data(epidu):
    json_url = f"https://api.biliintl.com/intl/gateway/web/v2/subtitle?s_locale=en_SG&platform=web&episode_id={epidu}"
    json_response = requests.get(json_url)
    json_data = json_response.json()
    print(json_data)
    return json_data

def extract_epidu_from_message(message_text):
    start_index = message_text.find("Episode ID=") + len("Episode ID=")
    end_index = message_text.find("\n", start_index)
    epidu = message_text[start_index:end_index].strip()
    return epidu

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('The bot is active.')

def convert_to_srt(json_data):
    srt_content = ""
    subtitle_list = json_data.get("body", [])

    for index, subtitle in enumerate(subtitle_list, start=1):
        start_time = int(subtitle["from"] * 1000)
        end_time = int(subtitle["to"] * 1000)

        srt_content += f"{index}\n"
        srt_content += f"{milliseconds_to_srt_time_format(start_time)} --> {milliseconds_to_srt_time_format(end_time)}\n"
        srt_content += f"{subtitle['content']}\n\n"

    return srt_content


def convert_to_ass(json_data):
    ass_content = "[Script Info]\nTitle: Bilibili Subtitle\nScriptType: v4.00+\n"
    ass_content += "WrapStyle: 0\nScaledBorderAndShadow: yes\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
    ass_content += "Style: FLIT - Dialogue,Arial,28,&H00FFFFFF,&H0000FFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,1,1,2,10,10,10,1\n"
    ass_content += "Style: Subtitle - top,Noto Sans Light,26,&H00FFFFFF,&HAFFFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,1.5,0,8,20,20,20,1\n\n"
    ass_content += "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    subtitle_list = json_data.get("body", [])

    for index, subtitle in enumerate(subtitle_list, start=1):
        start_time = int(subtitle["from"] * 1000)
        end_time = int(subtitle["to"] * 1000)
        subs = subtitle['content']
        subst = subs.replace('\n', '\\N')
        parts = subst.split('\\N', 1)
        first_part = parts[0]
        special_characters = [':', ',', ';', '-', '”', '"', "'", "&", '?', '(', ')', '@', '!', '#', '%', '=', '*', '~', '—', '[', ']']

        second_part = parts[1] if len(parts) > 1 else ""

        if all(char.isupper() or char.isspace() for char in first_part) or (any(char.isspace() or char.isdigit() or char in special_characters for char in first_part) and first_part.isupper()):
            ass_content += f"Dialogue: 0,{milliseconds_to_ass_time_format(start_time)},{milliseconds_to_ass_time_format(end_time)},Subtitle - top,,0,0,0,,{first_part}\n"
            if second_part:
                ass_content += f"Dialogue: 0,{milliseconds_to_ass_time_format(start_time)},{milliseconds_to_ass_time_format(end_time)},FLIT - Dialogue,,0,0,0,,{second_part}\n"
        else:
            ass_content += f"Dialogue: 0,{milliseconds_to_ass_time_format(start_time)},{milliseconds_to_ass_time_format(end_time)},FLIT - Dialogue,,0,0,0,,{subst}\n"
    return ass_content

def milliseconds_to_ass_time_format(milliseconds):
    total_seconds = milliseconds / 1000
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}.{milliseconds:03d}"

def get_anime_name_romaji(season_id):
    anime_name_romaji_mapping = {
        '2090295': 'Sousou no Frieren',
        '2089932': 'Shangri-La Frontier',
        '2090761': 'Ragna Crimson',
        '2090049': 'Spy x Family Season 2',
        '2097690': "碰之道",
        '2095969': "指尖相触 恋恋不舍",
        '2084237': "欢迎来到实力至上主义的教室",
        '2097389': "弱势角色友崎君",
        '2096149': "佐佐木与文鸟小哔",
        '2095811': "秒杀外挂太强了异世界的家伙们根本就不是对手",
        '2096429': "事与愿违的不死冒险者",
    }
    return anime_name_romaji_mapping.get(season_id)

def load_anime_names():
    try:
        with open('season_id_mapping.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def get_anime_name(season_id, anime_names_mapping=None):
    if anime_names_mapping is None:
        anime_names_mapping = load_anime_names()
    return anime_names_mapping.get(season_id)

def load_used_epidu_json():
    try:
        with open("used_ep_ids.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

used_epidu_set = set()
def save_used_epidu_json():
    with open("used_ep_ids.json", "w") as file:
        json.dump(list(used_epidu_set), file)

def handle_channel_posts(update: Update, context: CallbackContext) -> None:
    try:

        if update.channel_post.chat_id != int(target_channel_username):
            return

        epidu = extract_epidu_from_message(update.channel_post.text)
        if epidu in used_epidu_set:
            context.bot.send_message(chat_id=update.channel_post.chat_id, text=f"Epidu {epidu} has already been processed.")
            return

        used_epidu_set.add(epidu)
        print(epidu)
        json_data = get_json_data(epidu)
        print(json_data)
        subtitle_entry = json_data.get('data', {}).get('video_subtitle', [])[0]
        if subtitle_entry.get('lang_key') == 'en':
            if 'ass' in subtitle_entry and subtitle_entry['ass']:
                subtitle_url = subtitle_entry['ass']['url']
                file_extension = '.ass'
            else:
                subtitle_url = subtitle_entry['srt']['url']
                file_extension = '.json'

            subtitle_response = requests.get(subtitle_url)
            subtitle_content = subtitle_response.content
            info_url = subtitle_url
            short_title = re.search(r'Short Title=(.+)', update.channel_post.text)
            print(short_title)
            long_title_match = re.search(r'Long Title=(.+)', update.channel_post.text)
            print(long_title_match)
            episode_id = re.search(r'Episode ID=(\d+)', update.channel_post.text)
            print(episode_id)
            season_id = re.search(r'Season ID=(\d+)', update.channel_post.text)
            upload_time = re.search(r'Publish Time=(.+)', update.channel_post.text)
            if short_title and episode_id and season_id:
                short_title = short_title.group(1)
                episode_id = episode_id.group(1)
                season_id = season_id.group(1)
                anime_name = get_anime_name(season_id)
                upload_time = upload_time.group(1)
                long_title = long_title_match.group(1) if long_title_match else ""
                if not long_title.strip():
                      long_title = ""

                file_name = f"{anime_name}-{short_title}_BG"
                short_title = short_title.replace('E', '').replace('.', '•')
                long_title = long_title.replace('.', '')
                hash = '#'
                anime_name_romaji = get_anime_name_romaji(season_id)
                anime_rm = anime_name_romaji
                if anime_name_romaji is not None:
                     anime_name_romaji = anime_name_romaji.replace(' ', '+')
                     search_data = f"{anime_name_romaji}+-+{short_title}"
                     msg_datash = f"[Download torrent](https://ouo.si/search?c=_&q={search_data})\n"
                else:
                     anime_name_romaji = ""
                     search_data = f"{anime_name_romaji}"
                     msg_datash = f"[Search torrent](https://ouo.si/search?c=_&q={search_data})\n"

                if file_extension == '.ass':
                   subtype = 'Advanced SubStationAlpha v4+'
                if file_extension == '.json':
                   subtype = 'Web Json'

                text_message = (
                        f"\n_From:_ [B-Global](https://www.bilibili.tv/en/play/{season_id}/{episode_id})\n"
                        f"_Anime name:_ `{anime_name}`\n"
                        f"_Episode:_ `{short_title}`\n"
                        f"_Title:_ `{long_title}`\n"
                        f"_Subtitle format:_ [{subtype}]({info_url})\n\n"
                        f"{msg_datash}"
                )

                file_io = BytesIO(subtitle_content)
                file_io.name = f"{file_name}{file_extension}"

                document_message = context.bot.send_document(chat_id=target_channel_username, document=file_io, caption=text_message, parse_mode=ParseMode.MARKDOWN)
                document_file = context.bot.get_file(document_message.document.file_id)
                document_io = BytesIO()
                document_file.download(out=document_io)

                if file_extension == '.json':
                    subtitle_data = json.loads(subtitle_content.decode('utf-8'))
                    converted_content = convert_to_ass(subtitle_data)
                    subtitle_content = converted_content.encode('utf-8')
                    file_extension = '.ass'

                try:
                    go_io = BytesIO(subtitle_content)
                    go_name = f"{file_name}{file_extension}.xz"
                    file_link = upload_file_to_gofile(go_io, go_name)
                    if file_link:
                       text_message += f"[Download subtitle]({file_link})"
                except:
                     text_message += "Download subtitle"

                document_io = BytesIO(subtitle_content)
                document_io.name = f"{file_name}{file_extension}"
                try:
                   context.bot.send_document(chat_id=upch_id, document=document_io, caption=text_message, parse_mode=ParseMode.MARKDOWN)

                except Exception as e:
                    print(f"{str(e)}")

                for group_id in forward_group_ids:
                    context.bot.send_chat_action(chat_id=group_id, action=ChatAction.UPLOAD_DOCUMENT)
                    document_io = BytesIO(subtitle_content)
                    document_io.name = f"{file_name}{file_extension}"
                    if subtitle_content:
                       context.bot.send_document(chat_id=group_id, document=document_io, caption=text_message, parse_mode=ParseMode.MARKDOWN)
                    else:
                        context.bot.send_message(chat_id=group_id, text="The subtitle file is empty\\n")

            else:
                context.bot.send_message(chat_id=update.channel_post.chat_id, text="Could not extract required information from the channel post")

        else:
            context.bot.send_message(chat_id=update.channel_post.chat_id, text="The subtitle is not in English")
            for group_id in forward_group_ids:
                context.bot.send_message(chat_id=group_id, text="The subtitle is not in English\ne:404")

    except Exception as e:
        context.bot.send_message(chat_id=update.channel_post.chat_id, text=f"An error occurred: {str(e)}")

    finally:
           save_used_epidu_json()

if __name__ == '__main__':
    updater = Updater(TOKEN)

    dp = updater.dispatcher
    dp.add_handler(MessageHandler(Filters.chat_type.channel & ~Filters.command, handle_channel_posts))

    updater.start_polling()
    updater.idle()
