import os
from pathlib import Path
from typing import Generator, List

import streamlit as st
from spleeter.separator import Codec

from utils import (ProcessingMode, SpleeterMode, SpleeterSettings,
                   download_youtube_as_mp3, get_audio_separated_zip,
                   get_multi_audio_separated_zip, get_split_audio)

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
if 'spleeter_settings' not in st.session_state:
    st.session_state.spleeter_settings = None
if 'selected_music_file' not in st.session_state:
    st.session_state.selected_music_file = None
if 'selected_music_files' not in st.session_state:
    st.session_state.selected_music_files = None
# states updater -------------------------------------------------------------


def add_audio_files(audio_file: Path):
    if(audio_file not in st.session_state.audio_files):
        st.session_state.audio_files.append(audio_file)


def save_uploaded_file(upload_file) -> Path:
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    escaped_file_path = Path(upload_file.name)

    # check if upload_file name last charactor is not space charactor
    if(escaped_file_path.stem[-1] == " "):
        escaped_file_path = escaped_file_path.parent / \
            f"{escaped_file_path.stem[:-1]}{escaped_file_path.suffix}"

    file_path = UPLOAD_DIR / escaped_file_path
    print(f"upload file:{file_path}")
    with open(file_path, 'wb') as f:
        f.write(upload_file.read())

    return file_path


# sidebar start --------------------------------------------------------------
st.sidebar.write("""
# Audio upload
""")

st.sidebar.write("""
# From local audio file
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
# From YouTube url
""")


def youtube_dl_wrapper(url, bitrate):
    if(url == ""):
        st.warning("Please enter a valid url")
    else:
        st.info("Downloading...")
        file_name, is_exist = download_youtube_as_mp3(url, UPLOAD_DIR, bitrate)
        file_path = Path(file_name)
        # check if already uploaded in audio_file
        if(is_exist):
            st.warning("File already downloaded")
            add_audio_files(file_name)
        else:
            st.success("File downloaded successfully")
            add_audio_files(file_name)


with st.sidebar.form("youtube_dl_form"):
    youtube_url = st.text_input("Enter a youtube url", "")
    quality_val = st.slider("Bitrate", 1, 512, 192)
    # Every form must have a submit button.
    submitted = st.form_submit_button("Download")
    if submitted:
        youtube_dl_wrapper(youtube_url, quality_val)

st.sidebar.write("# Reload already uploaded audio files")
if st.sidebar.button("Reload"):
    st.sidebar.info("Reloading...")
    for file in Path(UPLOAD_DIR).glob("*"):
        add_audio_files(file)
    st.sidebar.success("Done!")

# sidebar end --------------------------------------------------------------

# main page -------------------------------------------------------------------

st.title("Spleeter WEB UI")

current_mode = st.selectbox(
    "Mode", ProcessingMode, format_func=lambda x: x.value)

selected_music: Path
select_stems: SpleeterMode
select_codec: Codec
select_bitrate: int
output_files_generator: Generator[Path, None, None]

# single file mode ------------------------------------------------------------
if(current_mode == ProcessingMode.SINGLE):
    with st.form("single_mode"):
        st.subheader("Mode: "+current_mode.value)
        selected_music = st.selectbox(
            "Select an audio file", st.session_state.audio_files, help="To select audio, you have to upload or download an audio file at least once",
            format_func=lambda x: x.name)

        select_stems = st.selectbox(
            "Selected split mode", SpleeterMode, format_func=lambda x: x.value.label)

        with st.expander("Detail Settings"):
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Output audio settings")
                select_codec = st.selectbox(
                    "Codec", list(Codec), format_func=lambda x: x.value, index=1)
                select_bitrate = st.slider(
                    "Bitrate", 1, 512, 192)
            with col2:
                st.subheader("Spleetor processing settings")
                use_mwf: bool = st.checkbox(
                    "Use multi-channel Wiener filtering", value=True, help="Use multi-channel Wiener filtering to improve the quality of the output audio, but this may increase the processing time")
                use_16kHz: bool = st.checkbox(
                    "Use 16kHz model (instead of 11kHz)", value=True, help="Use 16kHz model is better for high quality audio than 11kHz, but it may increase the processing time")
                duaration_minutes: int = st.slider(
                    "Max duration minutes", 0, 60, 10, help="Max duration minutes of the audio to be processed. If the audio is longer than the duration, the audio will be ignored.")

        if st.form_submit_button("Split"):
            # check if settings are selected:
            if(selected_music == None or select_stems == None):
                st.error("Please select an audio file.")

            else:
                current_settings = SpleeterSettings(
                    select_stems,
                    select_codec,
                    select_bitrate,
                    use_mwf,
                    use_16kHz,
                    duaration_minutes*60
                )
                st.session_state.spleeter_settings = current_settings
                st.session_state.selected_music_file = selected_music
                st.session_state.output_files = []
                with st.spinner('Wait for spleeter processing...'):
                    output_files_generator, is_exist = get_split_audio(
                        st.session_state.spleeter_settings,
                        selected_music,
                        OUTPUT_DIR)
                    for x in output_files_generator:
                        st.session_state.output_files.append(x)
                st.success("Done!")

    with st.container():
        st.subheader("Output")
        if(st.session_state.selected_music_file != None and select_stems != None):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.caption("Audio:")
                st.write(st.session_state.selected_music_file.name)
            with col2:
                st.caption("Mode:")
                st.write(
                    f"{select_stems.value.name}{'-16kHz' if use_16kHz else '-11kHz'}{'-mwf' if use_mwf else '-no-mwf'}")
            with col3:
                st.caption("Zip:")
                zip_file_path = get_audio_separated_zip(
                    audio_file=st.session_state.selected_music_file,
                    output_path=OUTPUT_DIR,
                    config=st.session_state.spleeter_settings,
                )
                with open(zip_file_path, 'rb') as f:
                    st.download_button(
                        label="Download",
                        data=f,
                        file_name=zip_file_path.name,
                    )
            st.caption("Original audio: " +
                       st.session_state.selected_music_file.name)
            st.audio(str(selected_music))

            for i, audio_file in enumerate(st.session_state.output_files):
                st.caption(audio_file.name)
                st.audio(str(audio_file))

# multiple file mode -----------------------------------------------------------
elif(current_mode == ProcessingMode.MULTIPLE):
    with st.form("multiple_mode"):
        st.subheader("Mode: "+current_mode.value)
        selected_musics = st.multiselect(
            "Select audio files", st.session_state.audio_files, help="To select audio, you have to upload or download an audio file at least once", default=st.session_state.audio_files, format_func=lambda x: x.name)

        select_stems = st.selectbox(
            "Selected split mode", SpleeterMode, format_func=lambda x: x.value.label)

        with st.expander("Detail Settings"):
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Output audio settings")
                select_codec = st.selectbox(
                    "Codec", list(Codec), format_func=lambda x: x.value, index=1)
                select_bitrate = st.slider(
                    "Bitrate", 1, 512, 192)
            with col2:
                st.subheader("Spleetor processing settings")
                use_mwf: bool = st.checkbox(
                    "Use multi-channel Wiener filtering", value=True, help="Use multi-channel Wiener filtering to improve the quality of the output audio, but this may increase the processing time")
                use_16kHz: bool = st.checkbox(
                    "Use 16kHz model (instead of 11kHz)", value=True, help="Use 16kHz model is better for high quality audio than 11kHz, but it may increase the processing time")
                duaration_minutes: int = st.slider(
                    "Max duration minutes", 0, 60, 10, help="Max duration minutes of the audio to be processed. If the audio is longer than the duration, the audio will be ignored.")

        if st.form_submit_button("Split"):
            # check if settings are selected:
            if(len(selected_musics) == 0 or select_stems == None):
                st.error("Please select audio files.")

            else:
                current_settings = SpleeterSettings(
                    select_stems,
                    select_codec,
                    select_bitrate,
                    use_mwf,
                    use_16kHz,
                    duaration_minutes*60
                )
                st.session_state.spleeter_settings = current_settings
                st.session_state.selected_music_files = selected_musics
                st.session_state.output_files = []
                with st.spinner('Wait for spleeter processing...'):
                    progress = st.progress(0)
                    output_zip_path = get_multi_audio_separated_zip(
                        st.session_state.spleeter_settings,
                        selected_musics,
                        OUTPUT_DIR,
                        progress_callback=progress.progress)
                st.success("Done!")

    with st.container():
        st.subheader("Output")
        if(bool(st.session_state.selected_music_files)):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.caption("Selected Audio files:")
                # show as st table
                st.table([str(x.name)
                         for x in st.session_state.selected_music_files])
            with col2:
                st.caption("Mode:")
                st.write(
                    f"{select_stems.value.name}{'-16kHz' if use_16kHz else '-11kHz'}{'-mwf' if use_mwf else '-no-mwf'}")
            with col3:
                st.caption("Zip:")
                output_zip_path = get_multi_audio_separated_zip(
                    st.session_state.spleeter_settings,
                    selected_musics,
                    OUTPUT_DIR,
                    progress_callback=lambda x: x)
                with open(output_zip_path, 'rb') as f:
                    st.download_button(
                        label="Download",
                        data=f,
                        file_name=output_zip_path.name,
                    )
