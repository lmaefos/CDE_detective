# Goal
To create a tool that identifies and verifies the use of HEAL Common Data Elements (CDEs) in data dictionaries submitted by study teams. Often, study teams don’t explicitly label their data using HEAL CDEs, so this tool will analyze the submitted data dictionary to detect potential matches with HEAL Core CDEs by comparing forms (CRFs) and variable descriptions. The tool should generate a report showing the likelihood that specific CDEs are being used, based on semantic and structural similarities.

Steps to Achieve This Goal
Here’s a summary of the approach you outlined, with each step to implement in the script:

Knowledge Base Setup:

Import a structured knowledge base, including:
Common abbreviations and alternate names for each CRF.
Descriptions and purposes for each CRF.
The detailed Core CDE Data Dictionary, with variables, descriptions, permissible values, and any notes.
Store these as JSON files or Python data structures that the script can reference.
Load the Submitted Data Dictionary:

Read the study team's data dictionary into a structured format (e.g., a Pandas DataFrame).
Create a summary or pivot table that lists all CRFs (or forms) included in the submitted dictionary, along with any variables and descriptions.
Initial CRF Matching:

Use the knowledge base to compare the list of CRF names in the study’s data dictionary against known HEAL Core CRFs.
For each form in the study’s dictionary, provide a list of potential HEAL CRF matches, along with a confidence level based on name similarity (taking into account common abbreviations).
Variable-Level Semantic Matching:

For forms with a potential CRF match, check each variable to see if it matches variables from the corresponding HEAL Core CDE Data Dictionary.
Use semantic similarity (e.g., using OpenAI’s API) to compare variable descriptions, even if the names differ. The goal is to determine if the descriptions align with those in the HEAL CDE Data Dictionary.
Generate a confidence score for each variable, indicating how closely it matches the HEAL CDE definition.
Generate Report:

The final output should be a report that includes:
A list of forms in the study’s data dictionary and their matched HEAL CRFs (if any), along with confidence scores.
For each form match, a list of variables with potential HEAL CDE matches and their semantic match scores.
This report will allow you to see how well the submitted data aligns with HEAL CDE standards and which CDEs might be in use.
Key Output Goals
Form Match Report: A summary of each form in the study’s data dictionary, with any HEAL CRF matches and associated confidence levels.

Variable Match Report: For each matched form, a list of variables and their potential HEAL CDE matches, along with semantic match confidence scores.

This structured approach will help you automate the identification of HEAL CDEs, even when study teams use alternate names or labels for forms and variables. 