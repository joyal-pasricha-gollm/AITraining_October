# E-commerce Returns & Refund Processing

This application processes the 10 supplied records in `returns.json` with a
Microsoft Agent Framework graph and Azure AI Foundry. It does not process
payments, send customer messages, or create replacement orders. 
## PLease check the docx file which contains the screenshots of the actual output and testing. 

## Workflow

Each request passes through:

1. **Eligibility Agent** explains deterministic Python policy checks.
2. **Risk Agent** assesses the supplied facts. Python safeguards independently
   flag high-value requests, frequent returns, missing invoices, and damage
   reports without photos.
3. **Approval Gateway** automatically approves only when all six policy
   conditions pass. Otherwise it pauses using the framework's `request_info`
   mechanism and resumes with a validated manager decision.
4. **Customer Response Agent** writes a draft that is included with the final
   structured decision. It cannot change the decision; drafts claiming a
   simulated payment or replacement was completed are rejected.
5. **Final Output** emits JSON with the request/order IDs, product and amount,
   eligibility findings, risk assessment, approval route, final decision,
   customer draft, and simulation notice.

The automatic-approval policy requires an amount below INR 25,000, a request
within 30 days of delivery, an available invoice, an unopened item or a damaged
item with photographs, fewer than three prior returns in 90 days, and no
HIGH-risk finding. A failed condition always requires human review.

## Setup

Use Python 3.11 or newer:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Set `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_BASE_URL`, and
`AZURE_OPENAI_MODEL` in the environment or in a local `.env` copied from
`.env.example`.

## Run and validate

Check all supplied records without making an Azure request:

```powershell
python returns_workflow.py --check-data
```

Run the interactive workflow on all 10 requests:

```powershell
python returns_workflow.py
```

For each exception, review the displayed request, eligibility issues, and risk
assessment, then enter `approve` or `reject`. Invalid input is rejected and
prompted again. The final JSON decision is printed for every request.

Run offline tests of all 10 records, the automatic-approval rules, invalid
manager input, missing API configuration, and actual graph pause/resumption
using fake agents (no model/API calls):

```powershell
python -m unittest -v
```

## Expected demonstration cases

The supplied records include four automatic-approval cases: `RET201`, `RET203`,
`RET208`, and `RET210` (a damaged item with supporting photographs). `RET204`
requires human review because damage photos are missing; approving it produces
`MANAGER_APPROVED`. `RET205` requires human review because it is outside the
30-day window; rejecting it produces `MANAGER_REJECTED`. The offline workflow
test verifies both resumed decisions, re-prompts after invalid manager input,
and checks every record without contacting the model service.
