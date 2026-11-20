# Likely judge questions

**1. Where does the training data come from? Is it real?**
No public Bangladeshi wallet dataset exists, so the production model is trained on 100,000 *simulated* borrowers.
Their behaviour follows Global Findex Bangladesh patterns. We validate the same pipeline on real loans: Home Credit
(307,507 applicants, AUC 0.703 on alternative data; 0.693 vs 0.667 for bureau-only on people without a bureau score) and
LendingClub (AUC 0.737). The first real step is a pilot with a lender's historical micro-loans.

**2. How do you avoid bias against women and rural borrowers?**
Gender, region, division and age are never model inputs (enforced in code and tested). They are used afterwards
to set per-group thresholds. On 20,000 held-out borrowers the approval gap falls from 0.100 to 0.013, and the equalized-odds gap
from 0.097 to 0.034. CI fails if either exceeds 0.05. The Fairness Agent can block any single decision, and a weekly audit runs on live data.

**3. Isn't using group thresholds itself discrimination?**
It is a correction for unequal historical access, applied transparently and audited. Balanced accuracy is
unchanged (0.694 → 0.691). The thresholds are in `models/trustledger_meta.json`, and every decision logs the threshold it used.

**4. What about privacy? You read people's SMS.**
In production SMS are parsed on the phone and only 10 numbers leave it. Consent is per source and can be revoked, and
"delete my data" erases everything, including stored images. Bill photos are encrypted and expire after 30 days. Presidio
redacts phone numbers and IDs before any LLM call, and logs are scrubbed. See `docs/privacy.md`.

**5. How do people without any phone history get a score?**
Bhorsha: a 10–12 question Bangla conversation about planning, saving, risk and emergencies, scored against
rubrics. Paired questions catch inconsistency, and copy-paste, identical or rushed answers are flagged.

**6. Why should a borrower trust the score? Can they understand it?**
Every score shows the two strongest positive and negative SHAP factors in Bangla, plus tips that cite their source.
The LLM summary is rejected if it mentions anything that is not in the SHAP output.

**7. Why DeepSeek?**
DeepSeek's API is low-cost and OpenAI-compatible. DeepSeek-OCR is open-weights, so bills and khata photos can be read on
infrastructure we control. All calls go through one `LLMClient`, so the provider can be swapped, and everything runs offline in mock mode.
The score itself is XGBoost, not an LLM.

**8. What is the business model?**
Lenders (banks' digital nano-loan units, MFIs, NBFIs) pay per decision through the API or MCP. Borrowers never pay.
Value for lenders: about 5× more approvable applicants than a bank-account rule (12% → 59%) at similar repayment.

**9. How does it scale?**
The API is stateless (Heroku dynos / containers), Postgres + pgvector, and scoring takes milliseconds. Temporal holds loan state durably,
and Airflow runs batch audits. Federated learning (Flower, DP-FedAvg) lets several lenders improve the model without pooling
raw data: AUC 0.7555 vs 0.7644 central.

**10. What about Bangladesh Bank regulation?**
The design follows the principles in digital-lending and MFS rules: explicit consent, explainable decline reasons
in Bangla, non-discrimination monitoring and data deletion. The knowledge base holds team summaries of the circulars,
which must be checked against the official PDFs. Production use needs a licensed lending partner.

**11. How accurate is the model, and how do you know it stays accurate?**
AUC 0.764, KS 0.390, Brier 0.168, ECE 0.006 on held-out data. A nightly PSI drift check compares live features with
training distributions. `evals/run_all.py` enforces 8 quality gates in CI.

**12. What if the model is wrong about someone?**
Cases within 0.03 of the threshold go to human review, not auto-decline. Declines come with concrete tips, small first
loans limit risk, and on-time repayment raises the limit by 20% after three installments.

**13. Can people game it?**
Features come from months of transaction history, which is hard to fake cheaply. Bhorsha detects copy-paste, identical and rushed
answers and contradictions between paired questions. Uploads are checked by file signature, and rate limits stop brute force.

**14. How do partners integrate?**
REST with API keys, or MCP (`score_user`, `explain_score`, `fairness_audit`, `get_inclusion_lift`) for AI agents, over stdio
or authenticated streamable HTTP.

**15. What is not finished?**
Being honest: production training data, live DeepSeek keys and real bill-photo accuracy, OTP sign-up, and a regulator-approved
lending partner. Everything else (agents, app, dashboard, workflows, federated learning, evals, privacy controls) runs end to end today.
