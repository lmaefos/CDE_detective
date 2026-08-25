# CDE-ID Detective

CDE-ID Detective is a specification-driven, AI-assisted workflow for identifying potential HEAL Common Data Element (CDE) use in heterogeneous study data dictionaries.

For each data dictionary, the workflow has two primary goals:

1. Identify HEAL Core case report forms (CRFs) that appear to be used by the study.
2. Identify variable-level HEAL Core CDE matches, including cases where local variable names, descriptions, or response encodings differ from the official CDE specification.

The workflow combines deterministic Python processing, curated HEAL CDE knowledge base records, bounded large language model interpretation, form-level context, protected-family guardrails, reconciliation, and human review. The final outputs are intended to be auditable candidate mappings that support stewardship, metadata enrichment, discovery, and data reuse.

> **Important:** Automated match scores are similarity and confidence signals. They are not validated accuracy percentages. True mapping performance must be calculated from human-reviewed validation outcomes.

## Documentation map

This README is the main entry point and current source of truth for the project goal, output interpretation, and reporting metrics.

| Document | Purpose | Intended audience |
|---|---|---|
| [`README.md`](README.md) | Project overview, key outputs, metric definitions, and validation framework | All users |
| [`workflowdiagram.md`](workflowdiagram.md) | High-level workflow with minimal technical detail | Stewards, collaborators, presentations |
| [`pipeline_flow.md`](pipeline_flow.md) | Detailed technical workflow, data lineage, scoring, reconciliation, and exports | Developers, maintainers, technical reviewers |
| `config_prestep.ini` | Configurable paths, column aliases, thresholds, rules, models, and prompts | Pipeline operators and developers |
| `CDE_ID_revamp_v6.ipynb` | Current notebook implementation | Developers and technical reviewers |
| `run_cde_id_batch.py` | Batch execution and operational run reporting | Pipeline operators |
| `build_cde_mapping_report.py` | File-level and variable-level reporting across reconciled workbooks | Stewards and analysts |

The former `Goal_updated_2026-05-05.md` is retained as a historical design record. Its current project-goal content is incorporated into this README, so it should be archived instead of maintained as a second source of truth.

## Workflow overview

The workflow moves from a submitted data dictionary through CRF identification, variable-level CDE matching, reconciliation, and structured reporting.

See:

- [`workflowdiagram.md`](workflowdiagram.md) for the high-level view.
- [`pipeline_flow.md`](pipeline_flow.md) for the detailed technical view.

## Main inputs

The workflow uses:

- A study data dictionary, typically provided as a CSV for batch processing.
- `config_prestep.ini` for paths, input-column aliases, scoring thresholds, guardrails, models, and prompts.
- An environment file containing the configured API connection values.
- A HEAL Core CRF reference file.
- The compiled HEAL CDE knowledge base.
- A row-level HEAL CDE JSON used to construct official candidate packets during reconciliation.

The workflow resolves common input-column aliases rather than requiring every data dictionary to use identical headers. Original input columns are preserved in the final output.

## Final reconciled workbook

Each completed data dictionary produces a reconciled Excel workbook with three sheets.

### `metadata`

A filtered stewardship view containing rows with either:

- `Accept Candidate`
- `Needs Human Review`

Rows with `No Match` or blank reconciliation decisions are excluded.

Typical columns include:

- Original Variable Name
- Original Form Name
- HEAL Core CRF Match
- Best Match CDE Name
- Best Match CDE Var
- `recon_decision`

### `final-mapping`

The main clean mapping output. It preserves the original data dictionary columns and adds selected CRF, CDE, encoding-fidelity, and reconciliation fields.

This sheet is designed for downstream use and stewardship review. It intentionally excludes many intermediate and diagnostic columns.

### `all-outputs`

The full audit trail. It contains the original data dictionary, CRF-identification outputs, concept-matching scores, encoding-fidelity scores, form-level consensus, protected-family guardrails, reconciliation fields, model responses, and operational flags.

Use `all-outputs` as the source sheet for quantitative reporting because several important reporting fields, including `recon_confidence` and `Final Concept Match Score`, are not retained in `final-mapping`.

## Best columns to use

No single column fully describes mapping correctness and combinability. The following columns answer different questions.

| Reporting question | Best column or columns | Interpretation |
|---|---|---|
| Was a final CDE mapping accepted? | `recon_decision` + `best_best_match_variable` | Treat a row as an accepted mapping when `recon_decision = Accept Candidate` and a final CDE variable is present. |
| Which CRF was selected after reconciliation? | `best_best_match_crf` | Final reconciled HEAL Core CRF associated with the selected CDE. |
| Which official CDE was selected? | `best_best_match_cde` + `best_best_match_variable` | Final official CDE name and variable identifier. |
| How confident was reconciliation? | `recon_confidence` | Model-reported confidence of `High`, `Medium`, or `Low`. This is not validated accuracy. |
| Why was the final decision made? | `recon_rationale` | Row-level explanation from reconciliation or an applied guardrail. |
| Where did the reconciliation result originate? | `recon_result_source` | Distinguishes LLM reconciliation from protected-family or content-filter guardrails. |
| How strong was the conceptual candidate match? | `Final Concept Match Score` | Numeric 0-100 concept-similarity score from candidate retrieval. Higher indicates stronger similarity. |
| How closely did the response encodings align? | `Final Encoding Fidelity Score` | Numeric 0-100 similarity between the study encoding and the official CDE response encoding. |
| Was encoding alignment high, moderate, or low? | `Final Encoding Fidelity Status` | Review-friendly classification derived from the fidelity score. |
| Does the original score belong to the final reconciled CDE? | Compare `Final HEAL CDE Concept Match` with `best_best_match_variable` | If reconciliation changes the candidate, the original concept and fidelity scores should not be treated as final without recomputation. |

### Interpreting the two numeric scores

`Final Concept Match Score` and `Final Encoding Fidelity Score` measure different aspects of a proposed mapping.

- **Concept similarity** asks whether the study variable appears to represent the same underlying concept as the HEAL CDE.
- **Encoding fidelity** asks whether the study implemented that concept using similar response values or permissible-value labels.

A variable can represent the correct CDE concept while using different encodings. This can support a valid mapping while still requiring recoding or harmonization before datasets can be combined.

### Important scoring limitations

1. **Scores are not accuracy percentages.** They are algorithmic similarity signals.
2. **Reconciliation can change the selected CDE.** Existing concept and encoding scores were calculated before the final reconciliation decision. Reporting should recompute scores against the final selected CDE or flag rows where the candidate changed.
3. **An encoding score of zero can be ambiguous.** The current scoring function returns zero when one or both encoding strings are empty. This can mean missing or unscorable encoding information rather than confirmed incompatibility.
4. **Confidence is not validation.** `recon_confidence` is useful for prioritization, but human review is required to estimate scientific performance.

## Report metrics

The reporting layer should preserve separate denominators for processing completeness, CDE coverage, confidence, and combinability.

### 1. Accepted CDE mapping rate

The share of all variable rows that received an accepted final CDE mapping.

```text
Accepted CDE mapping rate =
    accepted CDE mappings / total variable rows
```

An accepted mapping requires:

- `recon_decision = Accept Candidate`
- a nonblank `best_best_match_variable`

This measures mapping coverage, not accuracy.

### 2. High-confidence share of accepted mappings

The share of accepted mappings assigned high reconciliation confidence.

```text
High-confidence share of accepted mappings =
    accepted mappings with recon_confidence = High / accepted CDE mappings
```

This is useful for prioritizing downstream review or metadata enrichment. It should still be described as model confidence rather than observed accuracy.

### 3. Mean post-reconciliation concept similarity

The average concept-similarity score after recalculating the score against the final reconciled CDE.

```text
Mean post-reconciliation concept similarity =
    sum of recomputed final concept scores / mappings with a recomputable score
```

Report the number of scorable mappings with the average. Do not report the average without its denominator.

### 4. Encoding-scorable mapping count

The number of accepted, high-confidence mappings where both the study variable and official CDE contain response-encoding information that can be compared.

```text
Encoding-scorable mapping count =
    accepted + high-confidence mappings with both encoding inputs available
```

This denominator prevents missing encodings from being silently interpreted as poor fidelity.

### 5. Ready-to-combine rate

A conservative indicator of variables that appear conceptually aligned and closely implemented.

A variable is provisionally classified as **Ready to combine** when it has:

- `recon_decision = Accept Candidate`
- `recon_confidence = High`
- post-reconciliation concept similarity at or above the configured high threshold, currently 75
- encoding fidelity at or above the configured high threshold, currently 80

```text
Ready-to-combine rate among scorable mappings =
    ready-to-combine mappings /
    accepted, high-confidence, encoding-scorable mappings
```

Also report the stricter total-variable coverage measure when useful:

```text
Ready-to-combine coverage =
    ready-to-combine mappings / total variable rows
```

These values are readiness indicators, not evidence that datasets can be combined without further scientific, unit, timing, population, or analytic review.

### Processing completeness

Batch-processing outcomes should be reported separately from mapping quality.

Recommended operational fields include:

- Total input files
- Successfully processed files
- Skipped files
- Errored files
- Total variable rows processed
- Processing time

A skipped or errored file is part of the operational denominator but does not have a scientific mapping-quality score.

## Human validation outcomes

Human validation is required before reporting the workflow's observed mapping performance as accuracy or precision.

### Validation record

| Field | Value |
|---|---|
| Validation workflow or UI version | `<TBD>` |
| CDE-ID workflow version | `v6` |
| Validation dataset or sample | `<TBD>` |
| Sampling method | `<TBD>` |
| Reviewer or reviewers | `Urja / <additional reviewers>` |
| Validation start date | `<TBD>` |
| Validation completion date | `<TBD>` |
| Total mappings selected for review | `<TBD>` |

### Outcome counts

| Human-review outcome | Definition | Count |
|---|---|---:|
| Confirmed | Proposed final CDE mapping was accepted without revision | `<TBD>` |
| Revised | A CDE mapping was appropriate, but the proposed CDE or variable required correction | `<TBD>` |
| Rejected | Proposed mapping was not supported | `<TBD>` |
| Unresolved | Reviewer could not make a final determination with the available evidence | `<TBD>` |
| Total reviewed | All rows that received a recorded human-review outcome | `<TBD>` |

### Validation calculations

Observed precision among resolved reviews:

```text
Observed mapping precision =
    confirmed /
    (confirmed + revised + rejected)
```

Conservative precision, treating unresolved reviews as not confirmed:

```text
Conservative mapping precision =
    confirmed / total reviewed
```

Review-resolution rate:

```text
Review-resolution rate =
    (confirmed + revised + rejected) / total reviewed
```

Revision rate:

```text
Revision rate =
    revised / (confirmed + revised + rejected)
```

Keep `Revised` separate from `Confirmed` so the report does not hide mappings that required human correction.

Validation results should also be stratified when the sample size permits, for example by:

- concept-match category
- encoding-fidelity category
- reconciliation confidence
- HEAL Core CRF
- protected-family or guardrail status
- original candidate retained versus candidate changed during reconciliation

## HSS and Monday board eligibility

CDE-ID outputs do not establish that a mapping is already available in the HEAL Semantic Search (HSS) system. HSS availability must be joined from a separate authoritative HSS source.

A conservative data-package board rule is:

```text
Board eligible =
    available in HSS
    AND recon_decision = Accept Candidate
    AND recon_confidence = High
```

If the board is specifically intended to surface readily combinable variables, add the `Ready to combine` classification as an additional requirement or a separate status field.

## Interpretation boundaries

CDE-ID Detective identifies and prioritizes candidate metadata mappings. A high-confidence or high-fidelity result does not independently establish:

- scientific equivalence across studies
- equivalent units or time windows
- equivalent populations or sampling designs
- identical data-collection procedures
- freedom from licensing or copyright restrictions
- readiness for pooled statistical analysis

The workflow supports stewardship and harmonization decisions. It does not replace human validation or study-specific scientific review.

## Versioning and reproducibility

Every formal run should retain or record:

- notebook or pipeline version
- config version
- knowledge base version
- model names
- thresholds and weights
- input-file identifier
- output-file identifier
- run timestamp
- processing status
- validation version, when available

This information allows reported mapping and validation metrics to be traced to the exact workflow configuration that produced them.
