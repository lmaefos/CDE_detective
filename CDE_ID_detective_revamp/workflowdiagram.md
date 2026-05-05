flowchart TD

    A[Study Data Dictionary] --> B[Config + HEAL CDE Knowledge Base]
    B --> C[CRF-Level Matching]
    C --> D[Variable-Level Concept Matching]
    D --> E[Scoring + Guardrails]
    E --> F[Recon Adjudication]
    F --> G[Final 3-Sheet Excel Output]

    style A fill:#f4f8fa,stroke:#25788e,stroke-width:2px
    style B fill:#e8f4f8,stroke:#25788e,stroke-width:2px
    style C fill:#e8f4f8,stroke:#25788e,stroke-width:2px
    style D fill:#e8f4f8,stroke:#25788e,stroke-width:2px
    style E fill:#fff7e6,stroke:#25788e,stroke-width:2px
    style F fill:#edf7ed,stroke:#25788e,stroke-width:2px
    style G fill:#d9f2e6,stroke:#25788e,stroke-width:2px
