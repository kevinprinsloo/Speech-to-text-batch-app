import streamlit as st
import os
import subprocess
import json
import time
from pathlib import Path
import base64
from streamlit_extras.app_logo import add_logo
from streamlit_extras.colored_header import colored_header
from PIL import Image
import docx2txt
from PyPDF2 import PdfReader
import io
from pydub import AudioSegment
import yaml
from azure.storage.blob import BlobServiceClient
from urllib.parse import quote

# Load configuration from config.yaml
with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

CONNECTION_STRING = config["connection_string"]
CONTAINER_NAME = config["container_name_input"]
CONVERTED_CONTAINER_NAME = "convertedinput"

def run_pipeline_step(step):
    try:
        result = subprocess.run(["python", step], capture_output=True, text=True, check=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def get_binary_file_downloader_html(bin_file, file_label='File'):
    with open(bin_file, 'rb') as f:
        data = f.read()
    bin_str = base64.b64encode(data).decode()
    href = f'<a href="data:application/octet-stream;base64,{bin_str}" download="{os.path.basename(bin_file)}">Download {file_label}</a>'
    return href

# Initialize session state
if 'page' not in st.session_state:
    st.session_state.page = 'upload'
if 'file_path' not in st.session_state:
    st.session_state.file_path = None
if 'processing_complete' not in st.session_state:
    st.session_state.processing_complete = False
if 'file_type' not in st.session_state:
    st.session_state.file_type = None

def set_page(page):
    st.session_state.page = page

def convert_mp4_to_wav(input_file, output_file):
    try:
        audio = AudioSegment.from_file(input_file, format="mp4")
        mono_audio = audio.set_channels(1)
        mono_audio = mono_audio.set_frame_rate(16000)  # Set to 16kHz
        mono_audio.export(output_file, format="wav")
        print(f"Converted {input_file} to mono WAV and saved as {output_file}")
        return True
    except Exception as e:
        print(f"Error converting {input_file} to mono WAV: {e}")
        return False

def upload_blob(blob_service_client, container_name, blob_name, upload_file_path):
    sanitized_blob_name = quote(blob_name, safe='')
    container_client = blob_service_client.get_container_client(container_name)
    try:
        container_client.create_container()
    except Exception as e:
        print(f"Container {container_name} already exists or could not be created: {e}")

    blob_client = blob_service_client.get_blob_client(container=container_name, blob=sanitized_blob_name)
    with open(upload_file_path, "rb") as data:
        blob_client.upload_blob(data, overwrite=True)
    print(f"Uploaded {upload_file_path} to {container_name}/{sanitized_blob_name}")

    
def main():
    # Define custom color scheme
    primary_color = "#4F8BF9"
    background_color = "#F0F2F6"
    secondary_background_color = "#FFFFFF"
    text_color = "#262730"
    font = "sans serif"
    
    # Configure the page
    st.set_page_config(
        page_title="Enterprise Audio Processor",
        page_icon="🎚️",
        layout="centered",
        initial_sidebar_state="expanded",
    )
    
    logo = Image.open("public/Agilisys_logo.jpeg")
    st.sidebar.image(logo, use_column_width=True)

    # Apply custom theme
    st.markdown(f"""
        <style>
        .reportview-container {{
            background-color: {background_color};
            color: {text_color};
        }}
        .sidebar .sidebar-content {{
            background-color: {secondary_background_color};
        }}
        .Widget>label {{
            color: {text_color};
            font-family: {font};
        }}
        .stButton>button {{
            color: {secondary_background_color};
            background-color: {primary_color};
            font-family: {font};
        }}
        .stProgress > div > div > div > div {{
            background-color: {primary_color};
        }}
        </style>
        """, unsafe_allow_html=True)

    # Load external CSS
    with open('styles/style.css', encoding='utf-8') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

    # Add a professional title
    st.title("Enterprise Audio Processor")
    st.markdown("---")  # Add a horizontal line for visual separation

    colored_header(
        label="Audio Processing Pipeline",
        description="Upload a WAV file and process it through our advanced pipeline.",
        color_name="blue-70",
    )

    if st.session_state.page == 'upload':
        upload_page()
    elif st.session_state.page == 'process':
        process_page()
    elif st.session_state.page == 'transcript':
        transcript_page()
    elif st.session_state.page == 'json_transcript':
        json_transcript_page()
    elif st.session_state.page == 'text_transcript':
        text_transcript_page()
        
def upload_page():
    st.header("Upload File")
    file_type = st.radio("Select file type:", ("WAV", "MP4", "JSON", "Word Document", "PDF"))
    
    uploaded_file = st.file_uploader("Choose a file", type={"WAV": "wav", "MP4": "mp4", "JSON": "json", "Word Document": "docx", "PDF": "pdf"}[file_type])

    if uploaded_file is not None:
        input_dir = Path("input")
        input_dir.mkdir(exist_ok=True)

        file_path = input_dir / uploaded_file.name
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        st.session_state.file_path = str(file_path)
        st.session_state.file_type = file_type
        st.success(f"File {uploaded_file.name} has been uploaded successfully.")

        if st.button("Process File"):
            if file_type in ["WAV", "MP4"]:
                set_page('process')
            elif file_type == "JSON":
                with st.spinner("Processing JSON file..."):
                    processed_json_path = process_json_file(str(file_path))
                    st.session_state.file_path = processed_json_path
                    st.session_state.processing_complete = True
                set_page('json_transcript')
            else:
                set_page('text_transcript')
            st.experimental_rerun()
            
def process_json_file(input_file_path):
    output_file_name = "speaker_conversation.json"
    output_file_path = os.path.join(os.path.dirname(input_file_path), output_file_name)

    # Load the JSON file
    with open(input_file_path, 'r') as file:
        data = json.load(file)

    # Extract speaker conversation with timestamps
    speakers_conversation = [
        {
            "speaker": f"speaker_{phrase['speaker']}", 
            "text": phrase["nBest"][0]["display"],
            "timestamp": phrase["offset"]
        }
        for phrase in data["recognizedPhrases"]
        if phrase["speaker"] in [1, 2]
    ]

    # Prepare the conversation in a JSON structure
    conversation_json = {
        "conversation": speakers_conversation
    }

    # Save the JSON structure to a file
    with open(output_file_path, 'w') as output_file:
        json.dump(conversation_json, output_file, indent=4)

    return output_file_path

def json_transcript_page():
    st.header("Conversation Transcript")

    if not st.session_state.processing_complete:
        st.warning("Please upload and process a file first.")
        if st.button("Go to Upload Page"):
            set_page('upload')
            st.experimental_rerun()
        return

    json_file = Path(st.session_state.file_path)
    
    if json_file.exists():
        with open(json_file, "r", encoding="utf-8") as f:
            json_content = json.load(f)
        
        # Display a summary of the JSON content
        st.subheader("Summary")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Speakers", len(set(utterance['speaker'] for utterance in json_content['conversation'])))
        with col2:
            st.metric("Total Utterances", len(json_content['conversation']))
        
        # Display the full JSON content in an expandable section
        with st.expander("View Full JSON"):
            st.json(json_content)
        
        # Initialize start_time in session state if not present
        if 'start_time' not in st.session_state:
            st.session_state.start_time = 0

        # Custom CSS for conversation layout
        st.markdown("""
        <style>
        .conversation-container {
            display: flex;
            align-items: flex-start;
            margin-bottom: 15px;
        }
        .speaker-box {
            width: 80px;
            padding: 5px;
            margin-right: 10px;
            border-radius: 5px;
            text-align: center;
            font-weight: bold;
            font-size: 0.8em;
        }
        .timestamp-box {
            width: 80px;
            padding: 5px;
            margin-right: 10px;
            text-align: center;
            font-size: 0.8em;
        }
        .text-box {
            flex-grow: 1;
            padding: 5px;
            border-radius: 5px;
            font-size: 0.9em;
        }
        .speaker-1 {
            background-color: #e6f3ff;
            border: 1px solid #b3d9ff;
        }
        .speaker-2 {
            background-color: #fff0e6;
            border: 1px solid #ffd9b3;
        }
        .stButton button {
            width: 80px;
            padding: 5px;
            font-size: 0.8em;
            height: auto;
            min-height: 0px;
            line-height: 1.5;
            margin: 0;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Display a formatted conversation with clickable timestamps
        st.subheader("Formatted Conversation")
        for utterance in json_content['conversation']:
            speaker_class = "speaker-1" if utterance['speaker'] == "speaker_1" else "speaker-2"
            timestamp = utterance['timestamp']
            
            col1, col2, col3 = st.columns([2, 2, 8])
            with col1:
                st.markdown(f"<div class='speaker-box {speaker_class}'>{utterance['speaker']}</div>", unsafe_allow_html=True)
            with col2:
                if st.button(f"{timestamp}", key=f"ts_{timestamp}", help="Click to jump to this timestamp"):
                    st.session_state.start_time = timestamp_to_seconds(timestamp)
                    st.experimental_rerun()
            with col3:
                st.markdown(f"<div class='text-box {speaker_class}'>{utterance['text']}</div>", unsafe_allow_html=True)
        
        # Add download button for conversation JSON
        st.markdown(get_binary_file_downloader_html(json_file, 'Conversation JSON'), unsafe_allow_html=True)
    else:
        st.warning("JSON file not found.")

    # Custom HTML for buttons in a row
    st.markdown("""
    <div class="button-container">
        <form action="#" method="POST">
            <button class="stButton button" name="process_another" style="width: 100px;">Process Another File</button>
        </form>
        <form action="#" method="POST">
            <button class="stButton button" name="upload_page" style="width: 100px;">Go to Upload Page</button>
        </form>
    </div>
    """, unsafe_allow_html=True)

    # Handle button clicks
    if st.session_state.get("process_another"):
        set_page('upload')
        st.session_state.processing_complete = False
        st.experimental_rerun()
    
    if st.session_state.get("upload_page"):
        set_page('upload')
        st.experimental_rerun()

def timestamp_to_seconds(timestamp):
    # Convert timestamp to seconds (you may need to adjust this based on your timestamp format)
    # For example, if timestamp is in format "PT1M30.5S":
    import re
    minutes = int(re.findall(r'(\d+)M', timestamp)[0]) if 'M' in timestamp else 0
    seconds = float(re.findall(r'(\d+(?:\.\d+)?)S', timestamp)[0])
    return minutes * 60 + seconds

        
def text_transcript_page():
    st.header("Text Transcript")

    file_path = Path(st.session_state.file_path)
    
    if file_path.exists():
        if st.session_state.file_type == "Word Document":
            text_content = docx2txt.process(file_path)
        else:  # PDF
            with open(file_path, "rb") as f:
                pdf_reader = PdfReader(f)
                text_content = ""
                for page in pdf_reader.pages:
                    text_content += page.extract_text()

        # Display the text content
        st.subheader("Transcript Content")
        st.text_area("Full Transcript", text_content, height=300)

        # Convert text to JSON format
        json_content = {"conversation": [{"speaker": "Unknown", "text": text_content}]}

        # Display the JSON content in an expandable section
        with st.expander("View JSON Format"):
            st.json(json_content)

        # Add download buttons
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(get_binary_file_downloader_html(file_path, 'Original File'), unsafe_allow_html=True)
        with col2:
            json_file = file_path.with_suffix('.json')
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(json_content, f, ensure_ascii=False, indent=2)
            st.markdown(get_binary_file_downloader_html(json_file, 'JSON Format'), unsafe_allow_html=True)
    else:
        st.warning("File not found.")

    if st.button("Process Another File"):
        set_page('upload')
        st.session_state.processing_complete = False
        st.experimental_rerun()

def process_page():
    st.header("Processing Audio")
    
    progress_placeholder = st.empty()
    
    with progress_placeholder.container():
        progress_bar = st.progress(0)
        status_text = st.empty()

        gif_path = "public/processing.gif"
        if os.path.exists(gif_path):
            st.image(gif_path, use_column_width=True)
        else:
            st.warning("Processing GIF not found. Please check the 'public' folder.")

        if st.session_state.file_type == "MP4":
            status_text.markdown("<h3>Converting MP4 to WAV</h3>", unsafe_allow_html=True)
            wav_file_path = st.session_state.file_path.replace('.mp4', '.wav')
            if convert_mp4_to_wav(st.session_state.file_path, wav_file_path):
                st.session_state.file_path = wav_file_path
                st.session_state.file_type = "WAV"
                progress_bar.progress(0.2)
            else:
                st.error("Failed to convert MP4 to WAV. Please try again.")
                return

        steps = [
            ("Analysing File", "local_convert_and_upload.py"),
            ("AI Transcription", "main_transcribe.py"),
            ("Processing Results", "download_transcript.py"),
            ("Saving Results", "postprocess_transcript.py")
        ]

        start_progress = 0.2 if st.session_state.file_type == "MP4" else 0

        for i, (step_name, script_name) in enumerate(steps):
            status_text.markdown(f"<h3>{step_name}</h3>", unsafe_allow_html=True)
            success, output = run_pipeline_step(script_name)
            
            if not success:
                st.error(f"Error in {step_name}: {output}")
                break
            
            progress_bar.progress(start_progress + (i + 1) * (1 - start_progress) / len(steps))
            time.sleep(0.5)  # For visual effect

        if success:
            status_text.markdown("<h2>Pipeline completed successfully! 🎉</h2>", unsafe_allow_html=True)
            progress_bar.progress(100)
            st.session_state.processing_complete = True
            time.sleep(2)  # Give user time to see completion message
            set_page('transcript')
            st.experimental_rerun()
        else:
            status_text.markdown("<h2>Pipeline failed. Check the errors above.</h2>", unsafe_allow_html=True)


def transcript_page():
    st.header("Conversation Transcript")

    if not st.session_state.processing_complete:
        st.warning("Please upload and process an audio file first.")
        if st.button("Go to Upload Page"):
            set_page('upload')
            st.experimental_rerun()
        return

    output_dir = Path("output")
    json_file = output_dir / "speaker_conversation.json"
    
    # Use the uploaded file path from the session state
    audio_file = Path(st.session_state.file_path) if st.session_state.file_path else None

    if json_file.exists() and audio_file and audio_file.exists():
        with open(json_file, "r", encoding="utf-8") as f:
            json_content = json.load(f)
        
        # Display a summary of the JSON content
        st.subheader("Summary")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Speakers", len(set(utterance['speaker'] for utterance in json_content['conversation'])))
        with col2:
            st.metric("Total Utterances", len(json_content['conversation']))
        
        # Display the full JSON content in an expandable section
        with st.expander("View Full JSON"):
            st.json(json_content)
        
        # Initialize start_time in session state if not present
        if 'start_time' not in st.session_state:
            st.session_state.start_time = 0

        # Add audio player
        st.audio(str(audio_file), start_time=st.session_state.start_time)

        # Custom CSS for conversation layout
        st.markdown("""
        <style>
        .conversation-container {
            display: flex;
            align-items: center;
            margin-bottom: 5px;
        }
        .speaker-box {
            width: 80px;
            padding: 2px 5px;
            margin-right: 5px;
            border-radius: 5px;
            text-align: center;
            font-weight: bold;
            font-size: 0.8em;
        }
        .timestamp-box {
            width: 80px;
            padding: 0;
            margin-right: 5px;
        }
        .text-box {
            flex-grow: 1;
            padding: 5px;
            border-radius: 5px;
            font-size: 0.9em;
        }
        .speaker-1 {
            background-color: #e6f3ff;
            border: 1px solid #b3d9ff;
        }
        .speaker-2 {
            background-color: #fff0e6;
            border: 1px solid #ffd9b3;
        }
        .stButton button {
            width: 80px;
            padding: 2px 5px;
            font-size: 0.8em;
            height: auto;
            min-height: 0px;
            line-height: 1.5;
            margin: 0;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Display a formatted conversation with clickable timestamps
        st.subheader("Formatted Conversation")
        for utterance in json_content['conversation']:
            speaker_class = "speaker-1" if utterance['speaker'] == "speaker_1" else "speaker-2"
            timestamp = utterance['timestamp'].replace('PT', '').replace('S', '')  # Remove 'PT' and 'S'
            time_in_seconds = sum(float(x) * 60 ** i for i, x in enumerate(reversed(timestamp.split('M'))))
            
            col1, col2, col3 = st.columns([2, 2, 8])
            with col1:
                st.markdown(f"<div class='speaker-box {speaker_class}'>{utterance['speaker']}</div>", unsafe_allow_html=True)
            with col2:
                if st.button(f"{timestamp.replace('M', 'm ')}s", key=f"ts_{time_in_seconds}", help="Click to jump to this timestamp"):
                    st.session_state.start_time = time_in_seconds
                    st.experimental_rerun()
            with col3:
                st.markdown(f"<div class='text-box {speaker_class}'>{utterance['text']}</div>", unsafe_allow_html=True)
        
        # Add download button for conversation JSON
        st.markdown(get_binary_file_downloader_html(json_file, 'Conversation JSON'), unsafe_allow_html=True)
    else:
        st.warning("Required files not found.")

    # Use Streamlit buttons instead of HTML buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Process Another File", key="process_another"):
            set_page('upload')
            st.session_state.processing_complete = False
            st.experimental_rerun()
    
    with col2:
        if st.button("Go to Upload Page", key="upload_page"):
            set_page('upload')
            st.experimental_rerun()

    # Additional CSS to ensure all buttons are the same size
    st.markdown("""
    <style>
    .stButton button {
        width: 100%;
        padding: 5px;
        font-size: 0.8em;
        height: auto;
        min-height: 0px;
    }
    </style>
    """, unsafe_allow_html=True)
        
if __name__ == "__main__":
    main()