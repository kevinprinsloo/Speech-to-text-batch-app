import yaml
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta, timezone
import logging
import sys
import requests
import os

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format="%(asctime)s %(message)s",
    datefmt="%m/%d/%Y %I:%M:%S %p %Z",
)

def load_config(config_file):
    with open(config_file, 'r') as file:
        config = yaml.safe_load(file)
    return config

def generate_blob_sas_url(connection_string, container_name, blob_name, permission, expiry_duration_hours):
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    sas_token = generate_blob_sas(
        account_name=blob_service_client.account_name,
        container_name=container_name,
        blob_name=blob_name,
        account_key=blob_service_client.credential.account_key,
        permission=permission,
        expiry=datetime.now().replace(tzinfo=timezone.utc) + timedelta(hours=expiry_duration_hours)
    )
    sas_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{container_name}/{blob_name}?{sas_token}"
    return sas_url

def download_blob(sas_url, download_file_path):
    try:
        response = requests.get(sas_url, stream=True)
        response.raise_for_status()  # Ensure the request was successful

        # Ensure the directory exists
        os.makedirs(os.path.dirname(download_file_path), exist_ok=True)

        with open(download_file_path, "wb") as download_file:
            for chunk in response.iter_content(chunk_size=8192):
                download_file.write(chunk)

        logging.info(f"Blob downloaded to {download_file_path} successfully.")
    except Exception as e:
        logging.error(f"An error occurred while downloading the blob: {e}")

def get_content_url_blob(connection_string, container_name, transcription_id):
    try:
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client(container_name)
        
        # List blobs in the container to find the contenturl_0.json file within the transcription ID folder
        prefix = f"{transcription_id}/"
        blobs = container_client.list_blobs(name_starts_with=prefix)
        for blob in blobs:
            if blob.name.endswith("contenturl_0.json"):
                return blob.name
        logging.error(f"No contenturl_0.json file found for transcription ID {transcription_id}")
        return None
    except Exception as e:
        logging.error(f"An error occurred while listing the blobs: {e}")
        return None

def download_transcriptions(config):
    with open('transcription_ids.txt', 'r') as file:
        transcription_ids = [line.strip() for line in file.readlines()]

    for transcription_id in transcription_ids:
        blob_name = get_content_url_blob(
            config['connection_string'],
            config['output_container_name'],
            transcription_id
        )

        if blob_name:
            sas_url = generate_blob_sas_url(
                config['connection_string'],
                config['output_container_name'],
                blob_name,
                BlobSasPermissions(read=True),
                1  # 1 hour expiry
            )
            local_download_path = os.path.join(config['download_folder'], f"{transcription_id}_contenturl_0.json")
            download_blob(sas_url, local_download_path)

if __name__ == "__main__":
    config = load_config('config.yaml')
    download_transcriptions(config)
