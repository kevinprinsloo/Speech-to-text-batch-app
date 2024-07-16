# Speech Services Batch Transcription API Project

This project demonstrates how to use the Speech Services Batch Transcription API from Python. The necessary client library is included in this repository.

## Setup Instructions

### 1. Clone the repository

First, clone the repository to your local machine and navigate to the project directory:

```bash
git clone https://github.com/yourusername/your-repo-name.git
cd your-repo-name
```

### 2. Install the required packages
Install the required Python packages using pip:

```bash
pip install -r requirements.txt
```

### 3. Install the swagger_client package
The client library for the Speech Services API is included in the `swagger_client` folder. Install it using `pip`:

```bash
pip install ./swagger_client
```


### 4. Verify the installation
To ensure the swagger_client package was installed correctly, run the following command:

```bash
python -c "import swagger_client"
```

If there are no errors, the installation was successful.

### Usage

Include instructions here on how to use your code. For example:

1. Update the configuration file with your API key and other necessary details.
2. Run the main script:


```bash
python main.py
```

## Project Structure

```bash
project-folder/
├── swagger_client/           # Generated client library files
│   ├── __init__.py
│   └── ... (other library files)
├── main.py                   # Main script to run
├── requirements.txt          # List of required Python packages
├── README.md                 # This file
└── .gitignore                # Git ignore file
```






