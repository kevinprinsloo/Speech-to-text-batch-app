import os
import yaml
from pydub import AudioSegment
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from datetime import datetime, timezone, timedelta
from urllib.parse import quote

# Load configuration from config.yaml
with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

CONNECTION_STRING = config["connection_string"]
CONTAINER_NAME = config["container_name_input"]
BLOB_NAME = config["blob_name"]
DOWNLOAD_FILE_PATH = config["download_file_path"]
CONVERTED_CONTAINER_NAME = "convertedinput"

def download_blob(blob_service_client, container_name, blob_name, download_file_path):
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    with open(download_file_path, "wb") as download_file:
        download_file.write(blob_client.download_blob().readall())
    print(f"Downloaded {blob_name} to {download_file_path}")

def convert_to_mono(input_file, output_file):
    try:
        audio = AudioSegment.from_wav(input_file)
        mono_audio = audio.set_channels(1)
        mono_audio.export(output_file, format="wav")
        print(f"Converted {input_file} to mono and saved as {output_file}")
    except Exception as e:
        print(f"Error converting {input_file} to mono: {e}")

def upload_blob(blob_service_client, container_name, blob_name, upload_file_path):
    # Encode the blob name to ensure it's valid
    sanitized_blob_name = quote(blob_name, safe='')

    # Ensure the container exists
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
    try:
        blob_service_client = BlobServiceClient.from_connection_string(CONNECTION_STRING)

        # Step 1: Download the original WAV file
        download_blob(blob_service_client, CONTAINER_NAME, BLOB_NAME, DOWNLOAD_FILE_PATH)

        # Step 2: Convert the WAV file to mono
        converted_file_path = "Call3_separated_16k_pharmacy_call_mono.wav"
        convert_to_mono(DOWNLOAD_FILE_PATH, converted_file_path)

        # Step 3: Upload the converted WAV file to a new blob folder
        upload_blob(blob_service_client, CONVERTED_CONTAINER_NAME, os.path.basename(converted_file_path), converted_file_path)
    except Exception as e:
        print(f"Error in processing: {e}")

if __name__ == "__main__":
    main()