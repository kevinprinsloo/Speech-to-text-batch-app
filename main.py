import subprocess
import logging
import sys
import yaml
from pathlib import Path
from tqdm import tqdm
import time

# Set up logging to write to a file
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    filename="pipeline.log",
    filemode="w"
)

def load_config(config_file):
    with open(config_file, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)

def run_script(script_name, progress_bar):
    tqdm.write(f"Running {script_name}")
    try:
        result = subprocess.run(["python", script_name], capture_output=True, text=True, check=True)
        tqdm.write(f"Finished running {script_name}")
        logging.info(result.stdout)  # Log the standard output to file
    except subprocess.CalledProcessError as e:
        tqdm.write(f"Error running {script_name}")
        logging.error(f"Error running {script_name}:")
        logging.error(e.stderr)
        raise
    except Exception as e:
        tqdm.write(f"Unexpected error running {script_name}")
        logging.error(f"Unexpected error running {script_name}: {str(e)}")
        raise

def main():
    # Load configuration
    config = load_config("config.yaml")

    # Ensure output directory exists
    Path(config["download_folder"]).mkdir(parents=True, exist_ok=True)

    # Pipeline execution
    steps = [
        "local_convert_and_upload.py",
        "main_transcribe.py",
        "download_transcript.py",
        "postprocess_transcript.py"
    ]

    try:
        with tqdm(total=len(steps), desc="Pipeline Progress", unit="step") as progress_bar:
            for step in steps:
                run_script(step, progress_bar)
                progress_bar.update(1)
                time.sleep(0.5)  # Add a small delay for better visual feedback

        tqdm.write("\nPipeline completed successfully!")
    except Exception as e:
        tqdm.write(f"\nPipeline failed: {str(e)}")
        tqdm.write("Check the pipeline.log file for more information.")
        sys.exit(1)

if __name__ == "__main__":
    main()