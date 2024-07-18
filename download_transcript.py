import yaml
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta, timezone
import logging
import sys
import requests
import os

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')

def load_config(config_file):
    with open(config_file, 'r') as file:
        config = yaml.safe_load(file)
    return config

# Load configuration from config.yaml
config = load_config('config.yaml')
OUTPUT_CONTAINER_NAME = config["output_container_name"]

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
        response.raise_for_status()

        os.makedirs(os.path.dirname(download_file_path), exist_ok=True)

        with open(download_file_path, "wb") as download_file:
            for chunk in response.iter_content(chunk_size=8192):
                download_file.write(chunk)

        logging.info(f"Blob downloaded to {download_file_path} successfully.")
    except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while downloading the blob: {e}")
        logging.error(f"Response status code: {e.response.status_code if e.response else 'N/A'}")
        logging.error(f"Response content: {e.response.content if e.response else 'N/A'}")
        raise

def get_content_url_blob(connection_string, container_name):
    try:
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client(container_name)
        
        blobs = list(container_client.list_blobs(name_starts_with=''))
        logging.info(f"Found {len(blobs)} blobs in container {container_name}")
        
        for blob in blobs:
            if blob.name.endswith("contenturl_0.json"):
                logging.info(f"Found content URL blob: {blob.name}")
                return blob.name
        
        logging.error(f"No contenturl_0.json file found in container {container_name}")
        return None
    except Exception as e:
        logging.error(f"An error occurred while listing the blobs: {e}")
        return None

def download_transcriptions(config):
    try:
        with open('current_file_info.txt', 'r') as file:
            unique_id, blob_name = file.read().strip().split(',')
        logging.info(f"Processing file with unique_id: {unique_id}, blob_name: {blob_name}")

        content_blob_name = get_content_url_blob(
            config['connection_string'],
            OUTPUT_CONTAINER_NAME
        )

        if content_blob_name:
            logging.info(f"Found content blob: {content_blob_name}")
            sas_url = generate_blob_sas_url(
                config['connection_string'],
                OUTPUT_CONTAINER_NAME,
                content_blob_name,
                BlobSasPermissions(read=True),
                1
            )
            local_download_path = os.path.join(config['download_folder'], f"{unique_id}_transcript.json")
            download_blob(sas_url, local_download_path)
            
            if os.path.exists(local_download_path):
                logging.info(f"Transcript downloaded successfully to {local_download_path}")
            else:
                logging.error(f"Failed to download transcript to {local_download_path}")
        else:
            logging.error("No content URL blob found")
    except Exception as e:
        logging.error(f"Error in downloading transcriptions: {e}")
        raise

if __name__ == "__main__":
    config = load_config('config.yaml')
    download_transcriptions(config)