import json
import os
import logging
import yaml

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')

# Load configuration from config.yaml
with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

input_folder = config["download_folder"]

try:
    with open('current_file_info.txt', 'r') as file:
        unique_id, sanitized_blob_name = file.read().strip().split(',')

    input_file_name = f"{unique_id}_transcript.json"
    output_file_name = f"{unique_id}_speaker_conversation.json"

    input_file_path = os.path.join(input_folder, input_file_name)
    output_file_path = os.path.join(input_folder, output_file_name)

    logging.info(f"Checking for input file: {input_file_path}")
    
    if not os.path.exists(input_file_path):
        logging.error(f"Input file {input_file_path} not found")
        # List files in the input folder
        files_in_folder = os.listdir(input_folder)
        logging.info(f"Files in {input_folder}: {files_in_folder}")
        raise FileNotFoundError(f"Input file {input_file_path} not found")

    with open(input_file_path, 'r') as file:
        data = json.load(file)

    speakers_conversation = [
        {
            "speaker": f"speaker_{phrase['speaker']}", 
            "text": phrase["nBest"][0]["display"],
            "timestamp": phrase["offset"]
        }
        for phrase in data["recognizedPhrases"]
        if phrase["speaker"] in [1, 2]
    ]

    conversation_json = {
        "conversation": speakers_conversation
    }

    with open(output_file_path, 'w') as output_file:
        json.dump(conversation_json, output_file, indent=4)

    logging.info(f"Conversation saved to {output_file_path}")
except Exception as e:
    logging.error(f"Error in postprocessing transcript: {e}")
    raise