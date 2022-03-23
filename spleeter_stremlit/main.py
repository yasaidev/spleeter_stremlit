import os
from pathlib import Path
from turtle import onclick
from typing import List

import streamlit as st
from spleeter.separator import Codec

from utils import (ProcessingMode, SpleeterMode, download_youtube_as_mp3,
                   split_audio)

# global variables
UPLOAD_DIR = Path("./upload_files/")
OUTPUT_DIR = Path("./output/")

# page states ---------------------------------------------------------------
if 'is_youtube_downloading' not in st.session_state:
    st.session_state.is_youtube_downloading = False
if 'audio_files' not in st.session_state:
    st.session_state.audio_files = []
if 'output_files' not in st.session_state:
    st.session_state.output_files = []
if 'selected_audio' not in st.session_state:
    st.session_state.selected_audio = None

audio_files: List[Path] = st.session_state.audio_files
# states updater -------------------------------------------------------------


def add_audio_files(audio_file: Path):
    if(audio_file not in audio_files):
        st.session_state.audio_files = audio_files + [audio_file]


def save_uploaded_file(upload_file) -> Path:
    # check if already uploaded
    # if(os.path.exists(UPLOAD_DIR / upload_file.name)):
    #     st.warning("This file is already in the list")
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = UPLOAD_DIR / upload_file.name
    with open(file_path, 'wb') as f:
        f.write(upload_file.read())
    return file_path


def show_audio(audio_file: Path):
    print(audio_file)


# sidebar start --------------------------------------------------------------
st.sidebar.write("""
## Audio upload
""")

st.sidebar.write("""
### from local audio file
""")

# audio file uploader
upload_files = st.sidebar.file_uploader("Choose an audio file", type=[
    "wav", "mp3"], accept_multiple_files=True)

for audio_file in upload_files:
    upload_path = save_uploaded_file(audio_file)
    add_audio_files(upload_path)


# youtubedl mp3
# text input area for youtube url
st.sidebar.write("""
### from YouTube url
""")


def youtube_dl_wrapper(url):
    if(url == ""):
        st.warning("Please enter a valid url")
    else:
        st.info("Downloading...")
        is_exist, file_name = download_youtube_as_mp3(url, UPLOAD_DIR)
        file_path = Path(file_name)
        # check if already uploaded in audio_file
        if(len(filter(lambda x: x.absolute().name == file_path.absolute().name) != 0)):
            st.warning("This file is already in the list")
        elif(is_exist):
            st.info("File already downloaded")
            add_audio_files(file_name)
        else:
            st.success("File downloaded successfully")
            add_audio_files(file_name)


with st.sidebar.form("youtube_dl_form"):
    quality_val = st.slider("Bitrate", 1, 512, 192,
                            )
    youtube_url = st.text_input("Enter a youtube url", "")

    # Every form must have a submit button.
    submitted = st.form_submit_button("Download")
    if submitted:
        youtube_dl_wrapper(youtube_url)

# sidebar end --------------------------------------------------------------

# main page -------------------------------------------------------------------

st.title("Spleeter WEB UI")

current_mode = st.selectbox(
    "Mode", ProcessingMode, format_func=lambda x: x.value)


if(current_mode == ProcessingMode.SINGLE):

    st.write("""
    #### Mode: Split single audio file
    """)

    selected_music = None
    select_stems = None
    select_codec = None
    select_bitrate = None

    with st.form("spleenter"):
        selected_music = st.selectbox(
            "select a audio file", st.session_state.audio_files, format_func=lambda x: x.name, key="selected_audio")

        select_stems = st.selectbox(
            "Selected split mode", SpleeterMode, format_func=lambda x: x.value.label)

        col1, col2 = st.columns(2)
        with col1:
            select_codec = st.selectbox(
                "Codec", list(Codec), format_func=lambda x: x.value, index=1)
        with col2:
            select_bitrate = st.slider(
                "Bitrate", 1, 512, 192)

        if st.form_submit_button("Split"):
            st.session_state.output_files = split_audio(
                str(selected_music), select_stems,
                select_codec, select_bitrate, OUTPUT_DIR)

    with st.container():
        st.write("#### Output")
        if(st.session_state.selected_audio != None and select_stems != None):
            col1, col2 = st.columns(2)
            col1.metric("Audio", st.session_state.selected_audio.name)
            col2.metric("Mode", select_stems.value.name)

        for i, audio_file in enumerate(st.session_state.output_files):
            st.caption(audio_file.name)
            st.audio(str(audio_file))
