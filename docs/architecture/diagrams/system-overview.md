# System Overview Diagram

Request flow through the current implementation (M0/M1 + prototype voice cascade). Tables
marked "no endpoints yet" exist in the schema for upcoming milestones but nothing writes to
them yet.

```mermaid
flowchart LR
    subgraph Client
        C[curl / Swagger UI /docs]
    end

    subgraph App["FastAPI app (app/main.py)"]
        R1["routers/jobs.py"]
        R2["routers/candidates.py"]
        S1["services/resume_parser.py"]
        S2["services/llm_client.py"]
        S3["services/stt_client.py"]
        S4["services/tts_client.py"]
        S5["services/interview_pipeline.py"]
        ST["storage/local.py"]
        DB["db.py (SQLAlchemy async)"]
    end

    subgraph Postgres["Postgres + pgvector (Docker, port 5433)"]
        T1[(jobs)]
        T2[(candidates)]
        T3[(resumes)]
        T4[(users)]
        T5[(skills)]
        T6[(resume_skills)]
        T7[(job_skills)]
        T8[(applications)]
        T9[(ai_processing_logs)]
    end

    OR[[OpenRouter API]]

    C --> R1 & R2
    R2 --> S1 --> S2
    R2 --> ST
    S5 --> S3 & S2 & S4
    S2 & S3 & S4 -->|HTTPS| OR
    R1 & R2 --> DB --> T1 & T2 & T3
    DB -.no endpoints yet.-> T4 & T5 & T6 & T7 & T8 & T9
```

`interview_pipeline.py` (the STT→LLM→TTS cascade) is currently only exercised by
`scripts/test_interview_pipeline.py` — it isn't reachable through any HTTP endpoint yet
(that's M4).
