import hashlib
import os
import re
import shutil
import zipfile
from dataclasses import dataclass
from enum import Enum
from gc import callbacks
from importlib.resources import path
from pathlib import Path
from typing import Callable, Generator, List, Tuple

import yt_dlp as youtube_dl
from spleeter.separator import Codec, Separator


class ProcessingMode(Enum):
    # mode enum
    SINGLE = "Split a single audio file"
    MULTIPLE = "Split multiple audio files at once"
    # COMBINE = "Combine splited audio"


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


@dataclass
class SpleeterSettings:
    """
    Settings for spleeter
    Attributes:
        split_mode (SpleeterMode): Spleeter mode
        codec (Codec): Codec to use
        bitrate (int): Bitrate to use
        usemwf (bool): Use multi-channel Wiener filtering (default: False)
        use16kHZ (bool): Use 16kHz sampling rate (default: False for 11kHz)
        duration (int): Duration in seconds
    """
    split_mode: SpleeterMode
    codec: Codec
    bitrate: int
    usemwf: bool = False
    use16kHZ: bool = False
    duration: int = 600


def get_title_from_youtube_url(youtube_url: str) -> str:
    """
    Get title from youtube url
    Args:
        youtube_url: str: youtube url
    Returns:
        str: title
    """
    # check if youtube url is playlist
    if youtube_url.startswith("https://www.youtube.com/playlist?list="):
        return "playlist: " + youtube_dl.YoutubeDL({}).extract_info(
            youtube_url, download=False)["title"]
    # check if youtube url is video in playlist
    elif(re.search(r'watch\?v=.*\&list=', youtube_url)):
        return youtube_dl.YoutubeDL({}).extract_info(
            youtube_url, download=False,)["entries"][0]["title"]
    # check if youtube url is video
    else:
        return youtube_dl.YoutubeDL({}).extract_info(
            youtube_url, download=False)["title"]


def strip_ansi_escape_codes(s):
    ansi_escape = re.compile(r'\x1b[^m]*m')
    return ansi_escape.sub('', s)


def youtube_dl_percent_str_to_float(percent_str: str) -> float:
    """
    Convert youtube-dl percent string to float
    Args:
        percent_str: str: youtube-dl percent string
    Returns:
        float: float
    """
    return float(strip_ansi_escape_codes(percent_str).replace('%', '').strip())/100


@dataclass
class YoutubeItemData:
    title: str
    url: str


def progress_float_formatter(hookdata, current_num=1, total_num=1):
    progress = (youtube_dl_percent_str_to_float(
        hookdata["_percent_str"])+100*(current_num-1))/(total_num*100)

    if progress > 1.0:
        return 1
    else:
        return progress


def download_youtube_as_mp3(youtube_url: str, output_path: Path,
                            progress_callback: Callable[[float], None],
                            bit_rate: int = 192, ) -> List[Path]:
    """
    Download youtube video as mp3
    Args:
        youtube_url: str: youtube url
        output_path: Path: output path
        progress_callback: Callable[[float], None]: progress callback
    Returns:
        Tuple[bool, str]: (is_exist, output_file_path)
    """
    youtube_item_list: List[YoutubeItemData]

    # check if youtube url is playlist
    if youtube_url.startswith("https://www.youtube.com/playlist?list="):
        playlist_info = youtube_dl.YoutubeDL({}).extract_info(
            youtube_url, download=False)["entries"]
        youtube_title_list = [
            YoutubeItemData(
                title=playlist_info[i]["title"],
                url=playlist_info[i]["webpage_url"]
            ) for i in range(len(playlist_info))
        ]
    # check if youtube url is video in playlist
    elif(re.search(r'watch\?v=.*\&list=', youtube_url)):
        # remove playlist id
        youtube_url = re.sub(r'\&list=.*', '', youtube_url)
        youtube_title_list = [
            YoutubeItemData(
                title=youtube_dl.YoutubeDL({}).extract_info(
                    youtube_url, download=False,)["title"],
                url=youtube_url
            )]
    # check if youtube url is video
    else:
        youtube_title_list = [
            YoutubeItemData(
                title=youtube_dl.YoutubeDL({}).extract_info(
                    youtube_url, download=False,)["title"],
                url=youtube_url
            )]
    current_num = 1

    def progress_hook(x): return progress_callback(
        youtube_dl_percent_str_to_float(x["_percent_str"])
    )

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl':  str(output_path.absolute()) + "/%(title)s.%(ext)s",
        'progress_hooks': [progress_hook],
        'postprocessors': [
            {'key': 'FFmpegExtractAudio',
             'preferredcodec': 'mp3',
             'preferredquality': bit_rate},
            {'key': 'FFmpegMetadata'},
        ],
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        for youtube_item in youtube_title_list:
            current_num += 1
            if os.path.exists(output_path / f"{youtube_item.title}.mp3"):
                continue
            ydl.download([youtube_item.url])

    progress_callback(1.0)
    return [output_path / f"{youtube_item.title}.mp3" for youtube_item in youtube_title_list]


def get_split_audio(config: SpleeterSettings,
                    audio_file: Path,
                    output_path: Path) -> Tuple[Generator[Path, None, None], bool]:
    """
    Split audio file
    Args:
        SpleeterSettings: SpleeterSettings: spleeter settings
    Returns:
        Tuple[Generator[Path, None, None], bool]: (output_files, is_exist)
    """

    is_exist = False
    output_path_base = Path(
        output_path/f"{audio_file.stem}/{config.split_mode.value.name}{'-16kHz' if config.use16kHZ else '-11kHz'}{'' if config.usemwf else '-noMWF'}/")
    print("output_path_base:" + str(output_path_base))

    # check if audio file exists
    if os.path.exists(output_path_base/f"{audio_file.stem}_vocals.{config.codec.value}"):
        print(
            f"{audio_file.stem} [{config.split_mode.value.name}{'-16kHz' if config.use16kHZ else ''}] : already splited")
        is_exist = True

    else:
        # create output path
        os.makedirs(str(output_path_base.absolute()), exist_ok=True)

        # split audio file by using spleeter
        separator = Separator(
            params_descriptor=f"spleeter:{config.split_mode.value.name}{'-16kHz' if config.use16kHZ else ''}",
            MWF=config.usemwf, multiprocess=False
        )
        separator.separate_to_file(
            str(audio_file),
            bitrate=f"{config.bitrate}k",
            destination=str(output_path),
            codec=config.codec,
            filename_format=f"{{filename}}/{config.split_mode.value.name}{'-16kHz' if config.use16kHZ else '-11kHz'}{'' if config.usemwf else '-noMWF'}/{{filename}}_{{instrument}}.{{codec}}",
            duration=config.duration
        )

    # return output file path list
    return output_path_base.glob(f'*.{config.codec.value}'), is_exist


def get_audio_separated_zip(config: SpleeterSettings,
                            audio_file: Path,
                            output_path: Path) -> Path:
    """
    Get separated audio zip file
    Args:
        audio_file: Path: audio file path
        output_path: Path: audio file path
        config: SpleeterSettings: spleeter settings
    Returns:
        Path: separated audio zip file path (EX: output_path/RYDEEN/RYDEEN_4stem.zip)
    """
    zip_file_basepath = Path(
        output_path/f"{audio_file.stem}/{audio_file.stem}_{config.split_mode.value.name}{'-16kHz' if config.use16kHZ else ''}")
    zip_file_path = zip_file_basepath.parent / \
        Path(zip_file_basepath.name + ".zip")

    # check if separated audio zip file already exists
    if os.path.exists(zip_file_path):
        print(
            f"{audio_file.stem} [{config.split_mode.value.name}] : already zipped")

    # get split audio path list and zip them
    else:
        separated_audio_path_list, is_exist = get_split_audio(
            config, audio_file, output_path)
        separated_audio_path_parent: Path = separated_audio_path_list.__next__().parent
        # zip separated audio folder
        shutil.make_archive(
            str(zip_file_basepath), 'zip', str(separated_audio_path_parent))

    return zip_file_path

# https://stackoverflow.com/questions/46229764/python-zip-multiple-directories-into-one-zip-file


def zipdir(path: Path, ziph):
    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file),
                       os.path.relpath(os.path.join(root, file),
                                       os.path.join(path, "..", "..")))


def zipit(dir_list, zip_name):
    zipf = zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED)
    for dir in dir_list:
        zipdir(dir, zipf)
    zipf.close()


def get_multi_audio_separated_zip(config: SpleeterSettings,
                                  audio_file_list: List[Path],
                                  output_path: Path,
                                  progress_callback: Callable[[float], None]) -> Path:
    """
    Get separated multiple audio into one zip file
    Args:
        audio_file_list: List[Path]: audio file path list
        output_path: Path: audio file path
        config: SpleeterSettings: spleeter settings
        progress_callback: Callable[[None], float]: pass progress as float
    Returns:
        Path: separated audio zip file path (EX: output_path/5files-2stems_[filename's_hash].zip)
    """
    progress_max = float(len(audio_file_list)) + 1.0
    progress_count = 0.0
    progress_callback(0.0)
    # get hash of audio file list from each filename
    audio_file_list_hash = hashlib.sha256(
        str(audio_file_list.sort()).encode()).hexdigest()[:6]

    zip_file_basepath = Path(
        output_path/f"{len(audio_file_list)}files-{config.split_mode.value.name}{'-16kHz' if config.use16kHZ else ''}_{audio_file_list_hash}")
    zip_file_path = zip_file_basepath.parent / \
        Path(zip_file_basepath.name + ".zip")

    # check if separated audio zip file already exists
    if os.path.exists(zip_file_path):
        print(
            f"{zip_file_path.name} : already zipped")

    # get split audio path list and zip them
    else:
        separated_audio_parent_path_list = []
        for audio_file in audio_file_list:
            separated_audio_path_gen, is_exist_ = get_split_audio(
                config, audio_file, output_path)
            separated_audio_parent_path_list.append(
                separated_audio_path_gen.__next__().parent)
            progress_count += 1
            progress_callback(progress_count/progress_max)

        # zip all separated audio parent folder
        zipit(separated_audio_parent_path_list, str(zip_file_path))

    progress_callback(1.0)
    return zip_file_path
