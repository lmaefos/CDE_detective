# Goal

To create the **CDE-ID Detective** workflow: a specification-driven, AI-assisted workflow that identifies, harmonizes, and reconciles potential HEAL Common Data Element (CDE) usage in study data dictionaries submitted under NIH DMSP compliance.

Because study teams often use local variable names, abbreviated form names, incomplete descriptions, or inconsistent encodings, CDE usage is not always obvious from the submitted data dictionary alone. The workflow combines deterministic Python logic, curated HEAL CDE knowledge base records, bounded LLM interpretation, and human-in-the-loop review to produce structured, auditable candidate CDE mappings.

The current v5 workflow combines the pre-step CRF identification, variable-level concept and encoding matching, and final reconciliation/adjudication into one notebook-driven pipeline.

# Current Workflow Overview

## 1. Configuration-Driven Setup

The workflow is controlled through `config_prestep.ini`, including:

- Input file and worksheet paths
- Output file paths
- Knowledge base paths
- Original study data dictionary column names
- Acronym normalization rules
- Concept retrieval thresholds
- Encoding fidelity thresholds
- Protected-family guardrails
- LLM model settings
- Recon/adjudication settings
- Prompt instructions

The workflow uses the configured study data dictionary columns rather than assuming standard column names. For example, the current config maps:

- `crf_column = section`
- `variable_column = name`
- `description_column = description`
- `ENCODING_COLUMN = enumLabels`

# Knowledge Base Setup

## Row-Level HEAL CDE JSON

The current workflow uses a row-level flattened HEAL CDE knowledge base JSON:

`KnowledgeBase/All_HEALPAINCDEsDD_row_level_flattened.json`

This JSON is generated from the Excel knowledge base sheet `ALL`, with:

- **one Excel row = one JSON object**
- a unique `record_id` built from:
  - `CRF Name`
  - `Variable Name`
  - `CRF Question #`

This prevents CRF-specific CDE rows from being collapsed when variable names overlap or appear similar across instruments. This is especially important for cases like GAD2 and GAD7, where the same or related concepts may appear across different forms.

## Knowledge Base Record Content

Each row-level record preserves key official HEAL CDE fields, including:

- CRF Name
- CRF Question #
- CDE Name
- Variable Name
- Domain
- Definition
- Short Description
- Additional Notes / Question Text
- Permissible Values
- PV Description
- Data Type
- Population
- Classification
- Copyright / protected-family flags when applicable

# Step-by-Step Workflow

## 1. Load Submitted Data Dictionary

The workflow reads the submitted study data dictionary into a structured DataFrame using paths and column names defined in the config file.

The original study data dictionary columns are preserved so they can be carried through to the final output.

## 2. CRF Pre-Step Identification

The pre-step uses grouped variable context to infer the most likely HEAL Core CRF match for each study form.

Outputs include:

- HEAL Core CRF Match
- Pre-step confidence
- Rationale
- Full response / parsing support fields

This step provides the form-level anchor used by downstream concept matching and reconciliation.

## 3. Variable-Level Concept and Encoding Matching

The workflow evaluates each variable against the HEAL CDE knowledge base using deterministic matching signals and configured scoring logic.

The matching layer considers:

- Study variable name
- Study form name
- Field label or description
- Normalized text
- Encodings / permissible values
- HEAL Core CRF Match from the pre-step
- Concept retrieval thresholds
- Encoding fidelity thresholds
- Protected-family restrictions

Outputs include:

- Final HEAL CDE Concept Match
- Final Concept Match Status
- Final Concept Match Score
- Final Encoding Fidelity Score
- Best Match candidate
- Potential Match 2
- Potential Match 3
- Candidate CRF names and scores
- Low-confidence analysis outputs when applicable

## 4. Protected-Family Guardrails

The workflow uses `ProtectedPrimaryFamilies` and `SkipVLMDMatchingCRFs` to prevent unsafe cross-family matching for copyright-sensitive or easily confused instruments.

Current protected/copyright-sensitive families include:

- Brief Pain Inventory (BPI)
- BPI Pain Interference
- BPI Pain Severity
- PCS-6
- PCS-13
- PedsQL Inventory

These guardrails help prevent cases where a row anchored to one protected family is incorrectly assigned to another instrument because of similar wording, similar concepts, or similar numeric response scales.

Protected-family logic can:

- identify protected-family rows
- detect off-family candidate packets
- prevent unsafe rows from being sent to LLM recon
- preserve form-level evidence
- assign review outcomes such as:
  - `Protected Family - Form-Level Match Only`
  - `Protected Family - Off-Family Candidates Blocked`
  - `Protected Family - In-Family Candidate Available`

## 5. Recon Candidate Selection

The workflow creates a `recon_candidate_df` from the full matching output.

Rows are eligible for recon when they meet configured criteria such as:

- concept status is `High concept match` or `Possible concept match`
- at least one candidate CDE match is present
- recon is enabled in config

`max_rows` in `[ReconSettings]` can be used as a testing throttle. When blank, all eligible rows are selected.

## 6. Official Candidate Packet Construction

For each recon candidate row, the workflow looks up candidate CDEs in the official row-level HEAL CDE JSON.

It builds official candidate packets containing:

- candidate source rank
- candidate source column
- candidate input value
- candidate CRF from matching
- candidate score from matching
- official CDE name
- official variable name
- official CRF name
- official definition
- official question text
- official permissible values
- official data type
- official population
- official classification

Only official candidate packets are sent to LLM recon. This keeps the model constrained to evidence from the knowledge base.

## 7. Candidate Packet Cleanup

Candidate packets are cleaned into prompt-friendly plain strings.

This removes messy one-item list formatting and converts list-like fields into readable text so the recon payload is easier for both the model and reviewers to interpret.

## 8. Recon Payload Construction

The workflow builds structured row-level recon payloads for rows that are safe to send to the LLM.

Each payload includes:

- study row context
- pre-step CRF context
- matching context
- protected-family context
- candidate lookup context
- official candidate packets

The payload uses config-driven original study columns, so the original form name, variable name, description, and encoding are correctly passed to the model.

## 9. LLM Recon / Adjudication

The recon step uses a bounded LLM instruction from config.

The model must:

- choose only from the provided official candidate list
- avoid inventing CDE names, CRF names, or variable names
- avoid accepting a candidate based only on similar numeric scales
- consider study row concept, form context, question meaning, permissible values, pre-step CRF match, concept score, encoding score, and protected-family guardrails
- return only valid JSON

Recon output schema:

- `best_best_match_cde`
- `best_best_match_crf`
- `best_best_match_variable`
- `recon_decision`
- `recon_confidence`
- `recon_rationale`

Allowed decisions:

- `Accept Candidate`
- `No Match`
- `Needs Human Review`

Allowed confidence values:

- `High`
- `Medium`
- `Low`

## 10. Merge Recon Results

The workflow merges:

1. LLM adjudication results
2. protected-family preassigned results

into a unified recon results table.

Those results are then merged back onto:

- the recon candidate batch
- the full reconciled dataframe

Rows not processed during a limited test run remain blank in recon-specific fields until the full run is executed.

## 11. Final Excel Output

The final reconciled workbook contains three sheets:

### `metadata`

A lightweight summary sheet with:

- Original Variable Name
- Original Form Name
- Best Best Match CRF
- Best Best Match CDE
- Recon Decision

### `final-mapping`

The main user-facing mapping sheet with:

- all original input columns
- `Best Match CDE Name`
- `Best Match CRF Name`
- `Final Decision`
- `recon_confidence`
- `recon_rationale`
- `recon_result_source`

### `all-outputs`

A full audit sheet containing:

- original input columns
- pre-step outputs
- concept and encoding matching outputs
- candidate packet / lookup fields
- protected-family guardrail outputs
- recon outputs
- raw diagnostic fields when retained

# Intermediate Output

The workflow may also produce an intermediate `conceptsplit` workbook before the recon step.

This file represents the pre-recon concept and encoding matching stage. It is useful for debugging, candidate review, and understanding why rows did or did not move into recon.

The final `reconciled` workbook should be treated as the main current output.

# Key Output Goals

- Preserve original study data dictionary context
- Identify likely HEAL Core CRF usage at the form level
- Identify variable-level candidate CDE matches using concept and encoding evidence
- Prevent unsafe cross-family matches for protected/copyright-sensitive instruments
- Use official knowledge base candidate packets for bounded recon adjudication
- Produce structured recon decisions with confidence and rationale
- Support human-in-the-loop review through clean final mapping and full audit outputs
- Improve downstream enrichment of HEAL CDE usage metadata for discovery, reuse, and knowledge graph integration

# Current Design Philosophy

CDE-ID Detective is a specification-driven workflow, not an open-ended prompting workflow.

Python handles:

- data loading
- grouping
- deterministic scoring
- candidate retrieval
- guardrails
- payload construction
- structured parsing
- merging
- output generation

The LLM is used as a bounded interpretation component for specific decisions where semantic judgment is helpful.

The knowledge base, config, response schemas, protected-family rules, and output structure are treated as the source of truth. The model is not allowed to invent unsupported matches.

This design reduces manual first-pass review while preserving auditability, transparency, and human review for final stewardship decisions.
