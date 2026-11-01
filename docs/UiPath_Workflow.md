# UiPath invoice workflow diagram

Follow [the step-by-step walkthrough](UiPath_Walkthrough.md). This diagram is the
workflow to build, not a claim that Main.xaml already implements it.

Edit in **Studio Web** and debug **On local machine** through the installed
UiPath Assistant/Robot. Studio Desktop is optional. Cloud execution cannot use
this computer's localhost API and file paths directly.

```mermaid
flowchart TD
    A[Manual Trigger] --> B[Configure paths and create unique run folder]
    B --> C[GET /health]
    C --> D{HTTP 200?}
    D -- No or connection error --> STOP[Log startup failure and stop]
    D -- Yes --> E[Enumerate input/invoices PDFs]
    E --> F{Any PDFs?}
    F -- No --> EMPTY[Log no work and finish]
    F -- Yes --> G[For each PDF: reset per-file variables]
    G --> H[POST /extract: multipart field file]
    H --> I{Response outcome}
    I -- 200 --> J[Deserialize invoice JSON]
    J --> K[Add fields, status, reasons to results table]
    I -- Document error --> L[Add Failed row: eligible for failed folder]
    I -- Server error or exception --> M[Add Failed row: leave input for retry]
    K --> N{More PDFs?}
    L --> N
    M --> N
    N -- Yes --> G
    N -- No --> O[Flag every batch duplicate as NeedsReview]
    O --> P[Write runFolder/results.csv with headers]
    P -- Save failed --> SAVEFAIL[Stop: do not move inputs]
    P -- Saved --> Q[For each recorded row]
    Q --> R{Retryable?}
    R -- Yes --> KEEP[Leave in input and log retry required]
    R -- No --> S{Validation status}
    S -- ReadyForReview --> READY[Move to runFolder/ready_for_review]
    S -- NeedsReview --> REVIEW[Move to runFolder/needs_review]
    S -- Failed --> FAILED[Move to runFolder/failed]
    READY --> LOG[Append routing outcome to routing.log]
    REVIEW --> LOG
    FAILED --> LOG
    KEEP --> LOG
    LOG --> T{More rows?}
    T -- Yes --> Q
    T -- No --> END[Log batch summary and finish]
```

Move exceptions leave the source available and are logged as routing failures.
The first version does not guarantee crash-safe exactly-once processing; add a
durable identity/result ledger before completing the repeat-run milestone.

## What happens inside the API

```mermaid
sequenceDiagram
    participant U as UiPath local robot
    participant F as FastAPI
    participant P as pypdf
    participant O as Ollama / qwen3:8b
    participant V as Pydantic and validation rules
    U->>F: POST /extract (PDF multipart upload)
    F->>P: Extract text
    P-->>F: Document text
    F->>O: Text, extraction instructions, JSON schema
    O-->>F: Structured field values
    F->>V: Check structure, required fields, dates, money
    V-->>F: Reasons and validation outcome
    F-->>U: HTTP 200 invoice JSON or clear HTTP error
    Note over U: Batch duplicate checks, CSV, routing, and audit log
```

## If Mermaid does not render

In VS Code, open this file and use **Open Preview** (Ctrl+Shift+V on Windows).
If your Markdown preview does not support Mermaid, use this plain-text outline:

```text
Manual trigger
  Configure paths
  Health check -> stop if unavailable
  Enumerate PDFs -> finish if empty
  For each PDF
    Try: upload -> read response -> add result row
    Catch: add failure row and leave for retry
  Flag batch duplicates
  Save CSV -> stop before moves if save fails
  For each result
    Retryable -> leave in input
    Otherwise -> move to ready / review / failed
    Log routing outcome
  Finish
```
