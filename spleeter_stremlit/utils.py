import os
import shutil
from dataclasses import dataclass
from enum import Enum
from importlib.resources import path
from pathlib import Path
from typing import Generator, List, Tuple

import youtube_dl
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


def download_youtube_as_mp3(youtube_url: str, output_path: Path) -> Tuple[Path, bool]:
    """
    Download youtube video as mp3
    Args:
        youtube_url: str: youtube url
        output_path: Path: output path
    Returns:
        Tuple[bool, str]: (is_exist, output_file_path)
    """
    youtube_title = youtube_dl.YoutubeDL({}).extract_info(
        youtube_url, download=False)["title"]

    is_exist = True

    # check if audio file already exists
    if not os.path.exists(output_path / f"{youtube_title}.mp3"):
        is_exist = False
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl':  str(output_path.absolute()) + "/%(title)s.%(ext)s",
            'postprocessors': [
                {'key': 'FFmpegExtractAudio',
                 'preferredcodec': 'mp3',
                 'preferredquality': '192'},
                {'key': 'FFmpegMetadata'},
            ],
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])

    return output_path / f"{youtube_title}.mp3", is_exist


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
