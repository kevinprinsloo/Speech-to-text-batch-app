import json
import os

# Define the input and output file paths
input_folder = "output"
input_file_name = "e4e68a13-c191-459a-b947-a5e45b9f8c71_contenturl_0.json"
output_file_name = "speaker_conversation.json"

input_file_path = os.path.join(input_folder, input_file_name)
output_file_path = os.path.join(input_folder, output_file_name)

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

print(f"Conversation saved to {output_file_path}")