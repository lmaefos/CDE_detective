# Goal

To create the **CDE-ID Detective** workflow: a specification-driven, AI-assisted workflow that identifies, harmonizes, and reconciles potential HEAL Common Data Element (CDE) usage in study data dictionaries submitted under NIH DMSP compliance.

Because study teams often use local variable names, abbreviated form names, incomplete descriptions, or inconsistent encodings, CDE usage is not always obvious from the submitted data dictionary alone. The workflow combines deterministic Python logic, curated HEAL CDE knowledge base records, bounded LLM interpretation, form-level context, protected-family guardrails, and human-in-the-loop review to produce structured, auditable candidate CDE mappings.

The current v5 workflow combines the pre-step CRF identification, variable-level concept and encoding matching, form-level consensus review, protected-family guardrails, and final reconciliation/adjudication into one notebook-driven pipeline.

# Current Workflow Overview

## 1. Configuration-Driven Setup

The workflow is controlled through `config_prestep.ini`, including:

- Input file and worksheet paths
- Output file paths
- Environment file path
- CRF description JSON path
- HEAL CDE knowledge base JSON path
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

The setup cell now keeps only the config path directly in the notebook. Other modifiable paths, such as `.env` and the CRF descriptions JSON, are read from the config file so the notebook logic does not need to be edited for routine path changes.

# Knowledge Base Setup

## CRF Description JSON

The workflow loads a local CRF description JSON, such as:

`KnowledgeBase/CRF_descriptions.json`

This file supports the CRF pre-step by providing official CRF names, abbreviations, and descriptions that can be converted into prompt-ready reference text.

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
- Match rationale
- Canonical CRF Name
- Full response / parsing support fields

This step provides an initial form-level anchor used by downstream concept matching and reconciliation.

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
- Final Concept Match CRF
- Final Encoding Fidelity Score
- Final Encoding Fidelity Status
- Best Match candidate
- Potential Match 2
- Potential Match 3
- Candidate CRF names and scores
- Low-confidence analysis outputs when applicable

## 4. Form-Level Consensus Summary

After recon candidates are selected, the workflow builds a form-level consensus summary using the original form column from config, such as:

`crf_column = section`

This step looks across all rows that belong to the same original form and summarizes the strongest CRF-level pattern based on variable-level evidence.

The form-level consensus summary includes:

- `form_row_count`
- `form_consensus_high_possible_count`
- `form_consensus_crf`
- `form_consensus_crf_count`
- `form_consensus_crf_share`
- `form_consensus_crf_distribution`
- `form_consensus_encoding_pattern`
- `form_consensus_avg_encoding_score`
- `form_consensus_encoding_status`
- `form_consensus_note`

This layer helps the workflow recognize that forms usually contain multiple related variables. Instead of evaluating every row as an isolated island, the recon step can now use the broader form context.

For example, if several rows in the same form point to GAD7, that form-level signal can help ambiguous rows such as “Trouble Relaxing,” “Feeling Afraid,” or “Being Restless” avoid being incorrectly blocked by a mistaken row-level pre-step result.

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

## 8. Protected-Family Guardrails with Form-Consensus Rescue

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
  - `Protected Family - No Official Candidate Packet`
  - `Protected Family - Off-Family Candidates Blocked`
  - `Protected Family - In-Family Candidate Available`

The latest workflow also includes a **form-consensus rescue** rule.

If a row is flagged for protected-family auto-skip because the pre-step produced a protected-family CRF, but the broader form-level evidence strongly points to another CRF and the row-level final concept CRF agrees with that form consensus, the row can be rescued and sent to LLM recon instead of being automatically skipped.

A conservative rescue requires signals such as:

- form consensus CRF exists
- final concept CRF matches the form consensus CRF
- form consensus count meets a minimum threshold
- form consensus share meets a minimum threshold
- encoding fidelity score is strong when available

Rescued rows are flagged as:

`Protected Family - Rescued by Form Consensus`

This keeps the protected-family guardrails in place while preventing a mistaken pre-step result from blocking rows that have strong form-level and variable-level evidence.

## 9. Recon Payload Construction

The workflow builds structured row-level recon payloads for rows that are safe to send to the LLM.

Each payload includes:

- study row context
- pre-step CRF context
- variable-level matching context
- form-level consensus context
- protected-family context
- candidate lookup context
- official candidate packets

The payload uses config-driven original study columns, so the original form name, variable name, description, and encoding are correctly passed to the model.

The form-level consensus context helps the model interpret each row within its broader form. For example, a row may be individually ambiguous, but if multiple rows in the same form point to GAD7 and share the same GAD7-style encoding pattern, the recon model can use that context when adjudicating the final match.

## 10. LLM Recon / Adjudication

The recon step uses a bounded LLM instruction from config.

The model must:

- choose only from the provided official candidate list
- avoid inventing CDE names, CRF names, or variable names
- avoid accepting a candidate based only on similar numeric scales
- consider study row concept, form context, form-level consensus, question meaning, permissible values, pre-step CRF match, concept score, encoding score, and protected-family guardrails
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

## 11. Merge Recon Results

The workflow merges:

1. LLM adjudication results
2. protected-family preassigned results

into a unified recon results table.

Those results are then merged back onto:

- the recon candidate batch
- the full reconciled dataframe

Rows not processed during a limited test run remain blank in recon-specific fields until the full run is executed.

## 12. Final Excel Output

The final reconciled workbook contains three sheets:

### `metadata`

A filtered summary sheet containing only rows where `recon_decision` is:

- `Accept Candidate`
- `Needs Human Review`

Rows with blank recon decisions or `No Match` are excluded from this sheet.

The metadata sheet includes:

- Original Variable Name
- Original Form Name
- HEAL Core CRF Match
- Best Match CDE Name
- Best Match CDE Var
- recon_decision

### `final-mapping`

The main user-facing mapping sheet.

It includes:

- all original study data dictionary columns
- Canonical CRF Name
- Match Rationale
- Final Encoding Fidelity Score
- Final Encoding Fidelity Status
- HEAL Core CRF Match
- Best Match CDE Name
- Best Match CDE Var
- recon_decision

Intermediate/debug fields are removed from this sheet, including parsing outputs, raw model responses, normalized helper columns, intermediate concept modes, protected-family diagnostic columns, and blocked candidate diagnostics.

### `all-outputs`

A full audit sheet containing:

- original input columns
- pre-step outputs
- concept and encoding matching outputs
- form-level consensus outputs
- candidate packet / lookup fields
- protected-family guardrail outputs
- form-consensus rescue outputs
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
- Add form-level consensus so row-level decisions consider neighboring variables in the same original form
- Prevent unsafe cross-family matches for protected/copyright-sensitive instruments
- Rescue rows from protected-family auto-skip when strong form-level and variable-level evidence contradicts a mistaken pre-step result
- Use official knowledge base candidate packets for bounded recon adjudication
- Produce structured recon decisions with confidence and rationale
- Support human-in-the-loop review through clean final mapping and full audit outputs
- Improve downstream enrichment of HEAL CDE usage metadata for discovery, reuse, and knowledge graph integration

# Current Design Philosophy

CDE-ID Detective is a specification-driven workflow, not an open-ended prompting workflow.

Python handles:

- data loading
- config-driven setup
- grouping
- deterministic scoring
- candidate retrieval
- form-level consensus summaries
- protected-family guardrails
- form-consensus rescue logic
- payload construction
- structured parsing
- merging
- output generation

The LLM is used as a bounded interpretation component for specific decisions where semantic judgment is helpful.

The knowledge base, config, response schemas, protected-family rules, form-level consensus criteria, and output structure are treated as the source of truth. The model is not allowed to invent unsupported matches.

This design reduces manual first-pass review while preserving auditability, transparency, and human review for final stewardship decisions.