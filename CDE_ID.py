import openai
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up your OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client
client = openai.Client(api_key=api_key)

# Function to read JSON file
def read_json(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

# Function to write JSON file
def write_json(data, file_path):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

# Function to process each entry using the assistant
def process_entries(entries, master_cde_list):
    processed_entries = []

    for entry_number, entry in enumerate(entries, start=1):
        entry_data = {
            "entry_data": {
                "entry_number": entry_number,
                "data": entry
            },
            "master_cde_list": master_cde_list
        }

        # Create a prompt for the OpenAI API
        prompt = f"Analyze the entry to match it with the HEAL Core Common Data Elements (CDE) list:\n{json.dumps(entry_data, indent=2)}"

        response = client.chat.completions.create(
            model='gpt-4o-2024-05-13',  # Updated model name
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500
        )

        # Print the response structure for debugging
        print(f"Response for entry {entry_number}: {response}")

        # Extract the content correctly
        message_content = response.choices[0].message.content.strip()
        processed_entries.append(message_content)

    return processed_entries

# Main function to orchestrate the processing
def main(input_file, output_file, master_cde_file):
    # Read the input JSON file
    data_dictionary = read_json(input_file)
    
    # Read the master CDE list
    master_cde_list = read_json(master_cde_file)
    
    # Process each entry and get the results
    results = process_entries(data_dictionary, master_cde_list)
    
    # Write the results to the output JSON file
    write_json(results, output_file)

# Run the main function
if __name__ == '__main__':
    main(r'C:\Users\lmaefos\Code Stuffs\CDE_detective\PRECICEV2_DD_JSON.json', 'output.json', r'C:\Users\lmaefos\Code Stuffs\CDE_detective\KnowledgeBase\All_HEALPAINCDEsDD_JSON.json')
