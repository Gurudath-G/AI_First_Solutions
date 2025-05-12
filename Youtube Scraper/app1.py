import streamlit as st
import datetime
import requests
import isodate
import wave
import os
import re
from googleapiclient.discovery import build
from streamlit_webrtc import webrtc_streamer, WebRtcMode
import av
import speech_recognition as sr

# ----------------------------- CONFIG -----------------------------
YOUTUBE_API_KEY = "AIzaSyDQl-s3s5WtcA3_QaVxhU8NFpOSPNCnck0"
GEMINI_API_KEY = "AIzaSyDapMLrn1e502zd-MvYMez_Mvr9m5fqODQ"
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

# ----------------------------- SESSION -----------------------------
if "query" not in st.session_state:
    st.session_state.query = ""
if "voice_done" not in st.session_state:
    st.session_state.voice_done = False

# ----------------------------- PAGE SETUP -----------------------------
st.set_page_config(page_title="🎤 YouTube Finder with AI", layout="centered")
st.title("🎬 YouTube Video Finder with Voice/Text + AI")
st.markdown("Search YouTube using **Text or Mic Input** in **English or Hindi**.\nReturns the most relevant video using **Gemini AI**.")

# ----------------------------- INPUT MODE -----------------------------
input_mode = st.radio("Choose Input Mode", ["Text", "Voice (Mic)"])

# ----------------------------- TEXT INPUT -----------------------------
if input_mode == "Text":
    query = st.text_input("🔤 Enter your query:")
    st.session_state.query = query

# ----------------------------- VOICE INPUT -----------------------------
elif input_mode == "Voice (Mic)":
    st.markdown("🎙 Click **Start**, speak, and then click **Stop and Transcribe**.")

    class AudioProcessor:
        def __init__(self):
            self.frames = []

        def recv(self, frame: av.AudioFrame):
            pcm = frame.to_ndarray().tobytes()
            self.frames.append(pcm)
            return frame

    ctx = webrtc_streamer(
        key="voice",
        mode=WebRtcMode.SENDONLY,
        audio_receiver_size=1024,
        media_stream_constraints={"audio": True, "video": False},
    )

    if ctx.state.playing:
        st.session_state.frames = []

        if "audio_processor" not in st.session_state:
            st.session_state.audio_processor = AudioProcessor()

        audio_processor = st.session_state.audio_processor

        if ctx.audio_receiver:
            try:
                frame = ctx.audio_receiver.get_frame(timeout=1)
                if frame is not None:
                    audio_processor.recv(frame)
            except:
                pass

    # Stop and Transcribe button to save and transcribe the audio
    if st.button("🛑 Stop and Transcribe"):
        audio_path = "mic_input.wav"
        with wave.open(audio_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(48000)
            wf.writeframes(b''.join(st.session_state.audio_processor.frames))

        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_path) as source:
            audio_data = recognizer.record(source)
            try:
                transcript = recognizer.recognize_google(audio_data, language="hi-IN")
                st.session_state.query = transcript
                st.session_state.voice_done = True
                st.success(f"🎤 You said: {transcript}")
            except sr.UnknownValueError:
                st.error("Could not understand audio.")
            except sr.RequestError as e:
                st.error(f"Google API error: {e}")

    # Show submit button only after transcription
    if st.session_state.voice_done:
        if st.button("🔍 Submit Voice Query"):
            st.info(f"Query: {st.session_state.query}")

# ----------------------------- SEARCH TRIGGER -----------------------------
if st.session_state.query and st.button("🔍 Search YouTube"):
    query = st.session_state.query
    st.info("🔍 Searching YouTube...")

    today = datetime.datetime.utcnow()
    two_weeks_ago = today - datetime.timedelta(days=14)

    # YouTube search
    search_response = youtube.search().list(
        q=query,
        part="id,snippet",
        maxResults=20,
        type="video",
        publishedAfter=two_weeks_ago.isoformat("T") + "Z"
    ).execute()

    video_ids = [item["id"]["videoId"] for item in search_response["items"]]

    def get_video_details(video_ids):
        titles, links = [], []
        response = youtube.videos().list(
            part="snippet,contentDetails",
            id=",".join(video_ids)
        ).execute()
        for item in response["items"]:
            try:
                duration = isodate.parse_duration(item["contentDetails"]["duration"]).total_seconds() / 60
                if 4 <= duration <= 20:
                    titles.append(item["snippet"]["title"])
                    links.append(f"https://www.youtube.com/watch?v={item['id']}")
            except:
                continue
        return titles, links

    titles, links = get_video_details(video_ids)

    if not titles:
        st.warning("⚠️ No videos found in the 4–20 min range from the past 14 days.")
    else:
        st.info("🤖 Analyzing titles using Gemini...")

        def analyze_titles_gemini(query, titles, links):
            url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
            headers = {"Content-Type": "application/json"}
            prompt = f"""
You are an AI that ranks video titles by relevance.

Query: "{query}"

Titles:
{chr(10).join([f"{i+1}. {title}" for i, title in enumerate(titles)])}

Choose the best one and output:
1. Title
2. Reason
3. Index
"""
            data = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.3},
            }

            response = requests.post(f"{url}?key={GEMINI_API_KEY}", json=data, headers=headers)
            content = response.json()['candidates'][0]['content']['parts'][0]['text']

            match = re.search(r"(?i)index.*?(\d+)", content)
            idx = int(match.group(1)) - 1 if match else 0
            return titles[idx], links[idx], content

        best_title, best_link, reason = analyze_titles_gemini(query, titles, links)

        st.success("✅ Best Matching Video")
        st.markdown(f"**📌 Title:** {best_title}")
        st.markdown(f"🔗 [Watch on YouTube]({best_link})")
        st.markdown("🧠 **Why this video?**")
        st.markdown(f"> {reason}")
