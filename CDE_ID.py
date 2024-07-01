import openai
import json
import os
import aiohttp
import asyncio
import logging
from collections import defaultdict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up your OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client
client = openai.Client(api_key=api_key)

# Configure logging
logging.basicConfig(level=logging.INFO, filename='process_log.log', 
                    filemode='w', format='%(asctime)s - %(levelname)s - %(message)s')

# Function to write JSON file
def write_json(data, file_path):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

# Function to create a module-level prompt
def create_module_prompt(module_name, module_entries):
    module_prompt = "\n\n".join([
        f"Entry {entry_number}: {json.dumps(entry, indent=2)}"
        for entry_number, entry in module_entries
    ])
    prompt = f"Analyze the following entries for the module '{module_name}' to determine if the module or specific entries within it correspond to the HEAL Core Common Data Elements (CDE) list:\n{module_prompt}"
    return prompt

# Asynchronous function to process a module
async def process_module(session, module_name, module_entries):
    prompt = create_module_prompt(module_name, module_entries)
    
    async with session.post(
        'https://api.openai.com/v1/chat/completions',
        headers={'Authorization': f'Bearer {api_key}'},
        json={
            'model': 'gpt-4o-2024-05-13',  # Updated model name
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': 1500
        }
    ) as response:
        response_json = await response.json()
        
        # Log the response structure for debugging
        logging.info(f"Response for module '{module_name}': {response_json}")
        
        response_content = response_json['choices'][0]['message']['content'].strip()
        
        # Assume the response content will be sufficient to determine if the module matches HEAL CDEs
        return {
            'module_name': module_name,
            'response': response_content
        }

# Function to group entries by module name
def group_entries_by_module(entries):
    grouped_entries = defaultdict(list)
    for entry_number, entry in enumerate(entries, start=1):
        module_name = entry.get('module_name')  # Assuming each entry has a 'module_name' key
        grouped_entries[module_name].append((entry_number, entry))
    return grouped_entries

# Function to process entries asynchronously by module
async def process_entries(entries):
    grouped_entries = group_entries_by_module(entries)
    processed_modules = []
    async with aiohttp.ClientSession() as session:
        tasks = [
            process_module(session, module_name, module_entries)
            for module_name, module_entries in grouped_entries.items()
        ]
        module_results = await asyncio.gather(*tasks)
        processed_modules.extend(module_results)
    return processed_modules

# Main function to orchestrate the processing
def main(input_file, output_file, master_cde_file):
    # Read the input JSON file
    data_dictionary = read_json(input_file)
    
    # Read the master CDE list
    master_cde_list = read_json(master_cde_file)
    
    # Process entries asynchronously by module
    loop = asyncio.get_event_loop()
    results = loop.run_until_complete(process_entries(data_dictionary))
    
    # Write the results to the output JSON file
    write_json(results, output_file)

# Run the main function
if __name__ == '__main__':
    main(
        r'C:\Users\lmaefos\Code Stuffs\CDE_detective\PRECICEV2_DD_JSON.json',
        'output.json',
        r'C:\Users\lmaefos\Code Stuffs\CDE_detective\KnowledgeBase\All_HEALPAINCDEsDD_JSON.json'
    )