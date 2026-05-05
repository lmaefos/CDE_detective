# Goal
To create the **CDE-ID Detective** workflow: a tool that detects, harmonizes, and verifies the use of HEAL Common Data Elements (CDEs) in study data dictionaries submitted under NIH DMSP compliance.  

Because study teams often do not explicitly label their data with HEAL CDEs, the workflow uses AI-powered matching to compare case report forms (CRFs) and variable descriptions against the HEAL Core CDE knowledge base. It then incorporates **two levels of human verification** to ensure proposed matches are accurate and trustworthy before saving as “confirmed matches.”

# Steps to Achieve This Goal

**Knowledge Base Setup**
- Import a structured knowledge base including:
  - Common abbreviations and alternate CRF names  
  - CRF descriptions and purposes  
  - Full HEAL Core CDE Data Dictionary (variables, descriptions, permissible values, notes)  
- Store these resources as JSON or Python data structures for quick reference.

**Load the Submitted Data Dictionary**
- Read the study team’s data dictionary into a structured DataFrame.  
- Capture all CRFs, variables, and descriptions for downstream comparison.  

**CRF-Level Matching**
- Compare submitted CRF names against known HEAL Core CRFs.  
- Suggest potential matches with confidence scores, accounting for abbreviations and fuzzy naming.  

**Variable-Level Semantic Matching**
- For each CRF candidate, compare variables against HEAL Core variables.  
- Use semantic similarity (OpenAI API + function calling) to detect matches based on descriptions, not just names.  
- Produce confidence scores for each variable match.  

**Harmonization & Error Resilience**
- Process in configurable chunks (50 rows prestep, 20 rows harmonization).  
- Use async parallelization (`asyncio.gather`) for speed.  
- Implement retry logic with exponential backoff to handle API rate limits.  
- Include fallback mechanisms so errors don’t halt the workflow.  

**Human Verification Gates**
- **Level 1 (CLI Quiz):** Reviewer validates/edits proposed matches one by one.  
- **Level 2 (Spreadsheet Review):** Reviewer bulk-checks and finalizes all Level 1–confirmed rows.  
- Confirmed results are marked and saved for final export.  

**Generate Outputs**
- **Form Match Report:** Each submitted form with its matched HEAL Core CRFs + confidence levels.  
- **Variable Match Report:** Each variable with proposed HEAL CDE match + semantic scores.  
- **Final Confirmed Workbook:** A curated Excel/CSV with reviewer-approved matches.  
- **Audit Logs:** Processing logs, retries, and reviewer decisions for traceability.  

# Key Output Goals
- Clear mapping between study CRFs and HEAL Core CRFs  
- Verified variable-level matches with confidence scores  
- Human-verified “confirmed matches” for final compliance and reuse  

This structured, semi-automated workflow reduces the manual burden on data stewards while ensuring high-quality, reliable CDE alignment.
