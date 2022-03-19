import streamlit as st

st.title("Spleeter WEB UI")

st.write("""
audio file
""")

# audio file uploader
audio_files = st.file_uploader("Choose an audio file", type=[
                               "wav", "mp3"], accept_multiple_files=True)

st.write(audio_files)
