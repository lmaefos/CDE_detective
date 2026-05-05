flowchart TD


    A[Start: Run CDE_ID_revamp_v5.ipynb] --> B[Load config.ini settings]
    B --> B1[Read file paths, model settings, prompt text, thresholds, and column mappings]
    B1 --> C[Load study data dictionary into DataFrame]


    C --> C1[Resolve original input columns from config<br/>variable_column, crf_column, description_column, encoding_column]
    C1 --> D[Pre-step CRF-level matching]


    D --> D1[Group rows by original form / CRF]
    D1 --> D2[Build CRF context from grouped variables]
    D2 --> D3[Send grouped CRF context to LLM]
    D3 --> D4[Return HEAL Core CRF Match, rationale, confidence]
    D4 --> E[Merge pre-step outputs back onto row-level dataframe]


    E --> F[Variable-level matching and scoring]
    F --> F1[Normalize study text and encoding]
    F1 --> F2[Run fuzzy / rule-based candidate retrieval]
    F2 --> F3[Respect SkipVLMDMatchingCRFs rules]
    F3 --> F4[Apply protected primary family logic]
    F4 --> F5[Compute concept match + encoding fidelity]
    F5 --> F6[Assign Final HEAL CDE Concept Match, status, scores, and candidate columns]


    F6 --> G[Optional intermediate output:<br/>conceptsplit workbook]
    F6 --> H[Recon enabled?]


    H -->|No| Z1[Stop after concept matching outputs]


    H -->|Yes| I[Step 4: Build recon_candidate_df]
    I --> I1[Filter to eligible concept statuses<br/>High concept match / Possible concept match]
    I1 --> I2[Apply max_rows setting if present]
    I2 --> J[Step 5: Load official HEAL KB JSON]
    
    J --> J1[Use row-level flattened JSON<br/>one Excel row = one JSON object]
    J1 --> J2[record_id = CRF Name + Variable Name + CRF Question #]
    J2 --> J3[Build official lookup map]


    J3 --> K[Build official candidate packets]
    K --> K1[Use Final Concept Match, Potential Match 2, Potential Match 3]
    K1 --> K2[Retrieve official KB entries for candidate names]
    K2 --> K3[Store recon_official_candidates + lookup notes]


    K3 --> L[Clean candidate packets]
    L --> L1[Convert list-like fields to plain strings]
    L1 --> M[Optional inspect missing official candidates]


    M --> N[Apply protected-family recon guardrails]
    N --> N1[Read ProtectedPrimaryFamilies aliases from config]
    N1 --> N2[Detect protected-family rows using pre-step CRF match]
    N2 --> N3[Compare official candidates against family aliases]
    N3 --> N4[If protected + no in-family candidate:<br/>skip LLM and preassign review outcome]
    N4 --> N5[If protected + in-family candidate:<br/>allow recon but keep protected-family context]


    N5 --> O[Step 6: Build recon payloads]
    O --> O1[Use config-driven study columns directly<br/>study_variable_name, study_form_name, study_question_text, study_encoding]
    O1 --> O2[Attach pre-step context, matching context,<br/>protected-family context, and official candidates]
    O2 --> O3[Keep only rows not skipped by guardrail<br/>and with official candidate packets]


    O3 --> P[Step 7: Run recon/adjudication LLM]
    P --> P1[Send recon_adjudication_instruction + row payload]
    P1 --> P2[Require structured JSON output]
    P2 --> P3[Return best_best_match_cde, best_best_match_crf,<br/>best_best_match_variable, recon_decision,<br/>recon_confidence, recon_rationale]


    P3 --> Q[Step 8a: Build unified recon results]
    Q --> Q1[Combine LLM recon rows]
    Q1 --> Q2[Add preassigned protected-family skipped rows]
    Q2 --> Q3[Create unified_recon_results_df]


    Q3 --> R[Step 8b: Merge unified results back onto recon_candidate_df]
    R --> S[Step 9a: Merge recon results onto full dataframe]
    S --> S1[Create final_reconciled_df]
    S1 --> S2[Rows outside recon scope remain blank for recon fields]


    S2 --> T[Step 9b: Build final Excel sheet dataframes]
    T --> T1[metadata sheet]
    T --> T2[final-mapping sheet]
    T --> T3[all-outputs sheet]


    T1 --> T1a[Original Variable Name<br/>Original Form Name<br/>Best Best Match CRF<br/>Best Best Match CDE<br/>Recon Decision]
    T2 --> T2a[All original input columns<br/>+ Best Match CDE Name<br/>+ Best Match CRF Name<br/>+ Final Decision<br/>+ recon_confidence<br/>+ recon_rationale<br/>+ recon_result_source]
    T3 --> T3a[Full audit trail:<br/>original columns + pre-step + VLMD + recon outputs]


    T1a --> U[Step 9c: Export reconciled Excel workbook]
    T2a --> U
    T3a --> U


    U --> V[Final outputs]
    V --> V1[Intermediate conceptsplit workbook]
    V --> V2[Final reconciled workbook with 3 sheets]
    V --> V3[Structured audit-ready mapping results]
