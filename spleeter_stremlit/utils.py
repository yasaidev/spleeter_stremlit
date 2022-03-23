import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Tuple

import youtube_dl
from spleeter.separator import Codec, Separator


class ProcessingMode(Enum):
    # mode enum
    SINGLE = "Split a single audio file"
    MULTIPLE = "Split multiple audio files"
    COMBINE = "Combine splited audio"


@dataclass
class SpleeterStems:
    name: str
    stems: list
    label: str


class SpleeterMode(Enum):
    # mode enum
    TWOSTEMS: SpleeterStems = SpleeterStems(
        name="2stems",
        stems=["vocals", "accompaniment"],
        label="2stems: vocals and accompaniment"
    )
    FOURSTEMS: SpleeterStems = SpleeterStems(
        name="4stems",
        stems=["vocals", "drums", "bass", "other"],
        label="4stems: vocals, drums, bass and other"
    )
    FIVESTEMS: SpleeterStems = SpleeterStems(
        name="5stems",
        stems=["vocals", "drums", "bass", "piano", "other"],
        label="5stems: vocals, drums, bass, piano and other"
    )


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


def split_audio(audio_file: str, split_mode: SpleeterMode,
                codec: Codec, bitrate: int, output_path: Path, mwf: bool = False):
    print((output_path /
          f'{Path(audio_file).stem}/vocals.{codec.value}').absolute())
    # check if audio file exists
    if os.path.exists(output_path/f'{Path(audio_file).stem}/vocals.{codec.value}'):
        pass

    else:
        # split audio file by using spleeter
        separator = Separator(
            params_descriptor=f'spleeter:{split_mode.value.name}',
            MWF=mwf, multiprocess=False

        )
        separator.separate_to_file(
            audio_file, bitrate=bitrate, destination=output_path, codec=codec,)

    # return output file path list
    return Path(output_path/f'{Path(audio_file).stem}/').glob(f'*.{codec.value}')
