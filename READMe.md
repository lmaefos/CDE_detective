# Pain HEAL CDE ID
This script analyzes each module in a JSON data dictionary to match it with the HEAL Core Common Data Elements (CDE) list. The analysis determines if the module or specific entries within it correspond to the HEAL CDEs.

## Features
- Analyzes modules to determine correspondence with HEAL CDEs.
- Uses OpenAI's GPT model to perform semantic analysis.
- Processes entries asynchronously for improved performance.
- Logs detailed responses for debugging.

## Requirements
- Python 3.x
- openai
- aiohttp
- asyncio
- logging
- python-dotenv

## Installation
Install the required packages using pip:

'''bash
pip install openai aiohttp python-dotenv

## Parameters
- input_file: Path to the input JSON file containing the data dictionary.
- output_file: Path to the output JSON file.
- master_cde_file: Path to the JSON file containing the master CDE list.

## Notes
- I took the HEAL Pain Core CDE list from [HEAL Pain Core CDE list](https://heal.nih.gov/data/common-data-elements) to create a compiled list of all HEAL Pain Core CDEs. This compiled list is an Excel file, following the data frame structure as indicated on the website.
- In order to use OpenAI's file retrieval (or to use AI in identifying CDE use), I had to transform that megafile (referenced in the bullet point above) into a JSON format, as that is the required file retrieval format needed for the AI to perform advanced analysis. See JSONconverter_forHEALCDEDD_v2024_06-25 for the Python script used to automate this process.
- Additionally, it is necessary to [transform the submitted data dictionary into a JSON format](#csv-to-json-converter) for the AI to perform cross-analysis.
- Ensure your OpenAI API key is set in the environment variables by creating a .env file with the following content:

'''makefile
OPENAI_API_KEY=your_openai_api_key_here

- The script logs detailed responses to process_log.log for debugging purposes.
- The script uses asyncio for asynchronous processing to improve performance when dealing with large data dictionaries.

# CSV to JSON Converter
This script converts a CSV or Excel file into a JSON file, with additional functionality to handle delimited values in specified columns. The JSON output is grouped by a specified primary key column ('module' in this case).

## Features
Converts CSV or Excel files to JSON format.
Replaces blank fields with null.
Automatically detects columns with delimited values and converts them to arrays.
Groups entries by a specified primary key column ('module').

## Requirements
- Python 3.x
- pandas
- numpy
- openpyxl (if processing Excel files)

## Installation
Install the required packages using pip:

'''bash
pip install pandas numpy openpyxl

## Parameters
- file_path: Path to the input CSV or Excel file.
- output_json_path: Path to the output JSON file.
- columns_to_split (optional): A dictionary where the keys are column names and the values are delimiters to split the strings in those columns. If not - provided, the script will automatically detect columns that need to be split.
- delimiters (optional): A list of delimiters to check for array fields. The default is [';', '|'].