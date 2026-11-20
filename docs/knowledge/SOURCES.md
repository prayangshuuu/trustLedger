# Knowledge base sources

Documents in this folder are ingested by `uv run python -m app.rag.ingest` into `knowledge_chunks`
(pgvector). Each file declares its source with a `**Source URL:**` line; the retriever returns it with every chunk.

> **Verification status.** The three Bangladesh Bank files below are **team-written English summaries**,
> not the original circular text. Figures in them (limits, caps, circular numbers) must be checked
> against the official PDFs on bb.org.bd before the final. To replace a summary with the real
> circular, drop the PDF in this folder (`.pdf`, `.html`, `.md` and `.txt` are supported) and re-run
> ingestion; it is idempotent.

| File | Title | Author | Type | Source URL | Verified |
|---|---|---|---|---|---|
| `bb_digital_lending_guidelines.md` | Digital nano lending guidelines (summary) | Bangladesh Bank, summarised by the team | Regulation summary | https://www.bb.org.bd/en/index.php/mediaroom/circular | No - check against circular |
| `bb_mfs_regulations_2022.md` | MFS regulations (summary) | Bangladesh Bank, summarised by the team | Regulation summary | https://www.bb.org.bd/mediaroom/circulars/psd/apr182022psd04.pdf | No - check against circular |
| `financial_literacy_bangla_guide.md` | পারিবারিক বাজেট ও সঞ্চয় নির্দেশিকা | Team Minus One | Team note (Bangla) | repo file | Team-authored |
| `credit_repayment_discipline.md` | ঋণ পরিশোধের শৃঙ্খলা নির্দেশিকা | Team Minus One | Team note (Bangla) | repo file | Team-authored |
| `trustledger_score_guide_bn.md` | ট্রাস্টলেজার স্কোর নির্দেশিকা | Team Minus One | Product guide (Bangla) | repo file | Team-authored |
| `data_rights_and_safety_bn.md` | তথ্য অধিকার ও ডিজিটাল নিরাপত্তা | Team Minus One | Product guide (Bangla) | repo file | Team-authored |
