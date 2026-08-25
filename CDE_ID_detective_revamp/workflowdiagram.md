CDE-ID Detective v6: High-Level Workflow

This diagram shows the major stages of the workflow for a nontechnical or mixed audience. See pipeline_flow.md for the detailed technical flow.

flowchart TD
    A["Study data dictionary"]
    B["Configuration and HEAL reference knowledge"]
    C["Identify likely HEAL Core CRFs"]
    D["Retrieve variable-level HEAL CDE candidates"]
    E["Evaluate concept similarity and encoding fidelity"]
    F["Apply guardrails and reconcile the final mapping"]
    G["Export the three-sheet reconciled workbook"]
    H["Summarize metrics and conduct human validation"]

    A --> B --> C --> D --> E --> F --> G --> H

    style A fill:#f4f8fa,stroke:#25788e,stroke-width:2px
    style B fill:#e8f4f8,stroke:#25788e,stroke-width:2px
    style C fill:#e8f4f8,stroke:#25788e,stroke-width:2px
    style D fill:#e8f4f8,stroke:#25788e,stroke-width:2px
    style E fill:#fff7e6,stroke:#982568,stroke-width:2px
    style F fill:#fff7e6,stroke:#982568,stroke-width:2px
    style G fill:#edf7ed,stroke:#25788e,stroke-width:2px
    style H fill:#d9f2e6,stroke:#532565,stroke-width:2px

What the workflow produces

For each successfully processed data dictionary, CDE-ID Detective produces:

potential HEAL Core CRF identifications

reconciled variable-level HEAL CDE mappings

concept-similarity and encoding-fidelity evidence

final reconciliation decisions, confidence, and rationale

a clean mapping view and a full audit trail

file-level and variable-level reporting metrics for stewardship and validation

Automated outputs remain candidate metadata mappings until they are validated through human review.