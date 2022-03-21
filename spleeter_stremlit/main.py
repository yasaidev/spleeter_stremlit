import random

import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, DataReturnMode, GridUpdateMode

from utils import download_youtube_as_mp3, split_audio

# page states ---------------------------------------------------------------
if 'is_youtube_downloading' not in st.session_state:
    st.session_state.is_youtube_downloading = False
if 'audio_files' not in st.session_state:
    st.session_state.audio_files = []

audio_files = st.session_state.audio_files

# states updater -------------------------------------------------------------


def add_audio_files(audio_file: str):
    if(audio_file not in audio_files):
        st.session_state.audio_files = audio_files + [audio_file]


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
    add_audio_files(audio_file)

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
        is_exist, file_name = download_youtube_as_mp3(url, "./upload_files/")

        if(file_name in audio_files):
            st.warning("This file is already in the list")
        elif(is_exist):
            st.info("File already downloaded")
            add_audio_files(file_name)
        else:
            st.success("File downloaded successfully")
            add_audio_files(file_name)


with st.sidebar.form("youtube_dl_form"):
    quality_val = st.slider("Transrate sampling rate", 1, 512, 192)
    youtube_url = st.text_input("Enter a youtube url", "")

    # Every form must have a submit button.
    submitted = st.form_submit_button("Download")
    if submitted:
        youtube_dl_wrapper(youtube_url)

if st.sidebar.button("test"):
    st.session_state.audio_files = audio_files + [f'{random.random()}test']

# sidebar end --------------------------------------------------------------

# main page -------------------------------------------------------------------

st.title("Spleeter WEB UI")

with st.container():
    st.write("""
    #### Split audio file
    """)
    with st.form("spleenter"):
        selected_music = st.selectbox(
            "select a audio file", st.session_state.audio_files)
        st.audio(selected_music)
        select_instruments = st.multiselect("Select instruments", [
            "vocals", "drums", "bass", "piano", "other"])

        if st.form_submit_button("Split"):
            st.info("Splitting...")
            split_audio(selected_music, select_instruments, "./split_files/")
            st.write(f"Selected instruments: {select_instruments}")
            st.success("Splitted successfully")
