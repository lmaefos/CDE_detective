import openai
import json
import os
import aiohttp
import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up your OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")
assistant_id = 'asst_6m8K0EdsjJmbXdYOdcaJmnp6'  # replace as needed

# Initialize OpenAI client
client = openai.Client(api_key=api_key)

# Configure logging
log_file_path = r'C:\Users\lmaefos\Code Stuffs\CDE_detective\format_log.log'
logging.basicConfig(level=logging.INFO, filename=log_file_path, 
                    filemode='w', format='%(asctime)s - %(levelname)s - %(message)s')

# Function to read JSON file
def read_json(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

# Function to write JSON file
def write_json(data, file_path):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)
    print(f"Data written to {file_path}")

# Function to create a prompt for formatting a module
def create_format_prompt(module_name, raw_response):
    prompt = f"Format the following raw response for the module '{module_name}' according to the HEAL Core Common Data Elements (CDE) categorization:\n{raw_response}"
    return prompt

# Asynchronous function to process a module
async def process_module(session, module_name, raw_response):
    prompt = create_format_prompt(module_name, raw_response)
    
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
        
        # Log the raw response for debugging
        logging.info(f"Raw response for module '{module_name}': {response_json}")
        
        # Return formatted response content
        response_content = response_json['choices'][0]['message']['content'].strip()
        
        return {
            "module_name": module_name,
            "formatted_response": response_content
        }

# Function to process entries asynchronously by module
async def process_entries(data):
    async with aiohttp.ClientSession() as session:
        tasks = [
            process_module(session, module["module_name"], module["raw_response"])
            for module in data
        ]
        module_results = await asyncio.gather(*tasks)
    return module_results

# Function to extract details from formatted response
def extract_details_from_response(formatted_response):
    details = json.loads(formatted_response)  # Assuming formatted_response is already in JSON format
    return details

# Function to format JSON response
def format_json_response(data):
    formatted_response = []
    for module in data:
        module_name = module["module_name"]
        formatted_response_content = module["formatted_response"]
        entries = extract_details_from_response(formatted_response_content)
        formatted_response.append({
            "module_name": module_name,
            "entries": entries
        })
    return formatted_response

# Main function to orchestrate the JSON formatting
def main(input_file, output_file):
    # Read the input JSON file
    data = read_json(input_file)
    print(f"Data loaded: {data}")  # Debug print
    
    # Process entries asynchronously by module
    loop = asyncio.get_event_loop()
    formatted_results = loop.run_until_complete(process_entries(data))
    print(f"Processing results: {formatted_results}")  # Debug print
    
    # Format the JSON response using the formatted results
    formatted_response = format_json_response(formatted_results)
    print(f"Formatted response: {formatted_response}")  # Debug print
    
    # Write the formatted response to the output JSON file
    write_json(formatted_response, output_file)

# Run the main function
if __name__ == '__main__':
    main(
        r'C:\Users\lmaefos\Code Stuffs\CDE_detective\SAMPLE_DataDictionary_output.json', # input file path
        r'C:\Users\lmaefos\Code Stuffs\CDE_detective\FINAL_Formatted_Output.json' # output file path
    )