import json
import os
import aiohttp
import asyncio
import logging
from collections import defaultdict
from dotenv import load_dotenv
from openai import AsyncOpenAI

# Load environment variables from .env file
load_dotenv()

# Set up your OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    logging.error("OpenAI API key not found. Ensure it is set in the environment variables.")
    raise ValueError("OpenAI API key not found. Ensure it is set in the environment variables.")

# Initialize OpenAI client
client = AsyncOpenAI(api_key=api_key)

# Configure logging
log_file_path = r'C:\Users\lmaefos\Code Stuffs\CDE_detective\process_log.log'
logging.basicConfig(level=logging.DEBUG,  # Set logging level to DEBUG
                    filename=log_file_path, 
                    filemode='w', 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Function to read JSON file
def read_json(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        logging.error(f"Error reading JSON file {file_path}: {e}")
        return {}

# Function to write JSON file
def write_json(data, file_path):
    try:
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=4)
        logging.info(f"Data written to {file_path}")
    except Exception as e:
        logging.error(f"Error writing JSON to file {file_path}: {e}")

# Function to create a prompt for a module
def create_module_prompt(module_name, module_entries):
    module_prompt = "\n\n".join([
        f"Entry {entry_number}: {json.dumps(entry, indent=2)}"
        for entry_number, entry in enumerate(module_entries, start=1)
    ])
    prompt = f"Please analyze the following entries for the module '{module_name}' and determine if they correspond to the HEAL Core Common Data Elements (CDE) list. For each entry, specify the 'standards_mapping_type', 'standards_mapping_label', and 'confidence_level'. Respond in JSON format.\n\n{module_prompt}"
    return prompt

# Function to group entries by module name (no longer needed in this form)
def group_entries_by_module(entries):
    return entries

# Function to process a module
async def process_module(session, module_name, module_entries):
    assistant_response = []

    for entry in module_entries:
        try:
            prompt = create_module_prompt(module_name, [entry])
            logging.debug(f"Prompt for entry '{entry['name']}' in module '{module_name}': {prompt}")

            response = await client.chat.completions.create(
                model="gpt-4-0613",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant designed to output JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=1000,
                n=1,
                stop=None
            )

            # Log the entire response for debugging
            logging.debug(f"Response for module '{module_name}', entry '{entry['name']}']: {response}")

            if response.choices:
                try:
                    match_response = json.loads(response.choices[0].message['content'])
                    logging.debug(f"Match response for entry '{entry['name']}']: {match_response}")
                    assistant_response.append({
                        "name": entry['name'],
                        "standards_mapping_type": match_response.get('standards_mapping_type', "No CDE match"),
                        "standards_mapping_label": match_response.get('standards_mapping_label', "No CRF match"),
                        "confidence_level": match_response.get('confidence_level', "No CDE match")
                    })
                except (KeyError, IndexError, TypeError, json.JSONDecodeError) as e:
                    logging.error(f"Error parsing response for entry '{entry['name']}']: {e}")
                    assistant_response.append({
                        "name": entry['name'],
                        "standards_mapping_type": "No CDE match",
                        "standards_mapping_label": "No CRF match",
                        "confidence_level": "No CDE match"
                    })
            else:
                assistant_response.append({
                    "name": entry['name'],
                    "standards_mapping_type": "No CDE match",
                    "standards_mapping_label": "No CRF match",
                    "confidence_level": "No CDE match"
                })
        except Exception as e:
            logging.error(f"Error processing entry '{entry['name']}' in module '{module_name}']: {e}")
            assistant_response.append({
                "name": entry['name'],
                "standards_mapping_type": "No CDE match",
                "standards_mapping_label": "No CRF match",
                "confidence_level": "No CDE match"
            })

    return {
        "module_name": module_name,
        "entries": assistant_response
    }

# Function to process entries asynchronously by module
async def process_entries(entries):
    processed_modules = []
    async with aiohttp.ClientSession() as session:
        tasks = [
            process_module(session, module_name, module_entries)
            for module_name, module_entries in entries.items()
        ]
        try:
            module_results = await asyncio.gather(*tasks)
            processed_modules.extend(module_results)
        except Exception as e:
            logging.error(f"Error processing entries: {e}")
    return processed_modules

# Main function to orchestrate the processing
def main(input_file, output_file, master_cde_file):
    try:
        # Read the input JSON file
        data_dictionary = read_json(input_file)
        logging.debug(f"Data dictionary loaded: {data_dictionary}")  # Debug print
        
        # Ensure data_dictionary is a dictionary
        if not isinstance(data_dictionary, dict):
            logging.error(f"Data dictionary is not a dictionary: {type(data_dictionary)}")
            return
        
        # Read the master CDE list
        master_cde_list = read_json(master_cde_file)
        logging.debug(f"Master CDE list loaded: {master_cde_list}")  # Debug print
        
        # Process entries asynchronously by module
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(process_entries(data_dictionary))
        logging.debug(f"Processing results: {results}")  # Debug print
        
        # Write the results to the output JSON file
        write_json(results, output_file)
    except Exception as e:
        logging.error(f"Error in main function: {e}")

# Run the main function
if __name__ == '__main__':
    main(
        r'C:\Users\lmaefos\Code Stuffs\CDE_detective\SAMPLE_DataDictionary_ForTesting.json', # modify input path as needed
        r'C:\Users\lmaefos\Code Stuffs\CDE_detective\SAMPLE_DataDictionary_output.json', # modify output path as needed
        r'C:\Users\lmaefos\Code Stuffs\CDE_detective\KnowledgeBase\All_HEALPAINCDEsDD_JSON.json' # modify knowledgebase path as needed
    )