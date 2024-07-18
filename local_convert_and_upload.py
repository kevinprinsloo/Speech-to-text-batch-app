import os
import yaml
import uuid
from pydub import AudioSegment
from azure.storage.blob import BlobServiceClient
from urllib.parse import quote
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')

# Load configuration from config.yaml
with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

CONNECTION_STRING = config["connection_string"]
CONVERTED_CONTAINER_NAME = "convertedinput"
LOCAL_WAV_FOLDER = config["local_wav_folder"]

def convert_to_mono(input_file, output_file):
    try:
        audio = AudioSegment.from_wav(input_file)
        mono_audio = audio.set_channels(1)
        mono_audio.export(output_file, format="wav")
        logging.info(f"Converted {input_file} to mono and saved as {output_file}")
    except Exception as e:
        logging.error(f"Error converting {input_file} to mono: {e}")
        raise

def upload_blob(blob_service_client, container_name, blob_name, upload_file_path):
    container_client = blob_service_client.get_container_client(container_name)
    try:
        container_client.create_container()
    except Exception as e:
        logging.warning(f"Container {container_name} already exists or could not be created: {e}")

    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    try:
        with open(upload_file_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)
        logging.info(f"Uploaded {upload_file_path} to {container_name}/{blob_name}")
    except Exception as e:
        logging.error(f"Error uploading {upload_file_path}: {e}")
        raise
    
    return blob_name

def main():
    try:
        blob_service_client = BlobServiceClient.from_connection_string(CONNECTION_STRING)
        
        for filename in os.listdir(LOCAL_WAV_FOLDER):
            if filename.endswith(".wav"):
                input_file_path = os.path.join(LOCAL_WAV_FOLDER, filename)
                mono_filename = f"mono_{filename}"
                mono_file_path = os.path.join(LOCAL_WAV_FOLDER, mono_filename)
                convert_to_mono(input_file_path, mono_file_path)
                
                unique_id = str(uuid.uuid4())
                blob_name = f"{unique_id}_{mono_filename}"
                uploaded_blob_name = upload_blob(blob_service_client, CONVERTED_CONTAINER_NAME, blob_name, mono_file_path)
                os.remove(mono_file_path)
                logging.info(f"Removed local file: {mono_file_path}")
                
                with open("current_file_info.txt", "w") as file:
                    file.write(f"{unique_id},{uploaded_blob_name}")
                
                logging.info(f"Saved file info: unique_id={unique_id}, blob_name={uploaded_blob_name}")
                
                # Verify the blob exists
                blob_client = blob_service_client.get_blob_client(container=CONVERTED_CONTAINER_NAME, blob=uploaded_blob_name)
                if blob_client.exists():
                    logging.info(f"Verified blob exists: {uploaded_blob_name}")
                else:
                    logging.error(f"Blob does not exist: {uploaded_blob_name}")

    except Exception as e:
        logging.error(f"Error in processing: {e}")
        raise

if __name__ == "__main__":
    main()