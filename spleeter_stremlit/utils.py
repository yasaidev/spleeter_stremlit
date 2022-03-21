import os
from typing import Tuple

import youtube_dl
from spleeter.separator import Separator


def download_youtube_as_mp3(youtube_url: str, output_path: str) -> Tuple[bool, str]:
    # get audio file name from youtube url by using youtube-dl
    youtube_title = youtube_dl.YoutubeDL({}).extract_info(
        youtube_url, download=False)["title"]

    is_exist = True

    # check if audio file already exists
    if not os.path.exists(output_path + youtube_title + ".mp3"):
        is_exist = False
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl':  output_path + "%(title)s.%(ext)s",
            'postprocessors': [
                {'key': 'FFmpegExtractAudio',
                 'preferredcodec': 'mp3',
                 'preferredquality': '192'},
                {'key': 'FFmpegMetadata'},
            ],
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])

    return (is_exist, output_path + youtube_title + '.mp3')


def split_audio(audio_file: str, mode: str, output_path: str):
    # split audio file by using spleeter
    separator = Separator('spleeter:2stems')
    separator.separate_to_file(audio_file, output_path)
