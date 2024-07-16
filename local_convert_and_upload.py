import os
import yaml
from pydub import AudioSegment
from azure.storage.blob import BlobServiceClient
from urllib.parse import quote

# Load configuration from config.yaml
with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

CONNECTION_STRING = config["connection_string"]
CONVERTED_CONTAINER_NAME = "convertedinput"
LOCAL_WAV_FOLDER = config["local_wav_folder"]  # Add this to your config.yaml


def convert_to_mono(input_file, output_file):
    try:
        audio = AudioSegment.from_wav(input_file)
        mono_audio = audio.set_channels(1)
        mono_audio.export(output_file, format="wav")
        print(f"Converted {input_file} to mono and saved as {output_file}")
    except Exception as e:
        print(f"Error converting {input_file} to mono: {e}")


def upload_blob(blob_service_client, container_name, blob_name, upload_file_path):
    sanitized_blob_name = quote(blob_name, safe="")

    container_client = blob_service_client.get_container_client(container_name)
    try:
        container_client.create_container()
    except Exception as e:
        print(f"Container {container_name} already exists or could not be created: {e}")

    blob_client = blob_service_client.get_blob_client(
        container=container_name, blob=sanitized_blob_name
    )
    with open(upload_file_path, "rb") as data:
        blob_client.upload_blob(data, overwrite=True)
    print(f"Uploaded {upload_file_path} to {container_name}/{sanitized_blob_name}")


def main():
    try:
        blob_service_client = BlobServiceClient.from_connection_string(
            CONNECTION_STRING
        )

        # Process all WAV files in the local folder
        for filename in os.listdir(LOCAL_WAV_FOLDER):
            if filename.endswith(".wav"):
                input_file_path = os.path.join(LOCAL_WAV_FOLDER, filename)

                # Convert to mono
                mono_filename = f"mono_{filename}"
                mono_file_path = os.path.join(LOCAL_WAV_FOLDER, mono_filename)
                convert_to_mono(input_file_path, mono_file_path)

                # Upload converted file
                upload_blob(
                    blob_service_client,
                    CONVERTED_CONTAINER_NAME,
                    mono_filename,
                    mono_file_path,
                )

                # Optionally, remove the mono file after upload
                os.remove(mono_file_path)
                print(f"Removed local file: {mono_file_path}")

    except Exception as e:
        print(f"Error in processing: {e}")


if __name__ == "__main__":
    main()
