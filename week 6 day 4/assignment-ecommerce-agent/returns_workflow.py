import argparse
import asyncio
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, TextIO

from agent_framework import Agent, Executor, WorkflowBuilder, WorkflowContext, executor, handler, response_handler
from agent_framework.openai import OpenAIChatClient
from dotenv import load_dotenv
from openai import AsyncOpenAI


PROJECT_DIR = Path(__file__).resolve().parent
RETURNS_FILE = PROJECT_DIR / "returns.json"
LOCAL_ENV_FILE = PROJECT_DIR / ".env"
DEMO_CONFIG_FILE = PROJECT_DIR.parent / "WEEK6DAY4-12THNOV MAF DEMO" / "requirements.txt"
AUTO_APPROVAL_LIMIT_INR = 25_000
RETURN_WINDOW_DAYS = 30
HIGH_RETURN_COUNT = 3

ReturnRecord = dict[str, Any]


class ConfigurationError(ValueError):
    """Raised when required model configuration is absent or still a placeholder."""


class AgentResult(Protocol):
    text: str


class TextAgent(Protocol):
    async def run(self, prompt: str) -> AgentResult: ...


@dataclass(frozen=True)
class FoundrySettings:
    api_key: str
    base_url: str
    model: str


@dataclass
class ManagerApprovalRequest:
    request: ReturnRecord
    prompt: str


def required_setting(name: str, environ: Mapping[str, str] | None = None) -> str:
    values = os.environ if environ is None else environ
    value = values.get(name, "").strip()
    if not value or value.lower().startswith(("your-", "paste_", "<your-")):
        raise ConfigurationError(f"Missing or placeholder value for {name}.")
    return value


def load_settings() -> FoundrySettings:
    load_dotenv(LOCAL_ENV_FILE)

    required_names = (
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_BASE_URL",
        "AZURE_OPENAI_MODEL",
    )
    if any(not os.getenv(name, "").strip() for name in required_names) and DEMO_CONFIG_FILE.is_file():
        # The existing demo stores these values in a file named requirements.txt.
        load_dotenv(DEMO_CONFIG_FILE, override=False)

    try:
        return FoundrySettings(
            api_key=required_setting("AZURE_OPENAI_API_KEY"),
            base_url=required_setting("AZURE_OPENAI_BASE_URL"),
            model=required_setting("AZURE_OPENAI_MODEL"),
        )
    except ConfigurationError as exc:
        names = ", ".join(required_names)
        raise ConfigurationError(
            f"{exc} Set {names} in the environment or {LOCAL_ENV_FILE.name}."
        ) from exc


def load_requests(path: Path = RETURNS_FILE) -> list[ReturnRecord]:
    with path.open(encoding="utf-8") as file:
        requests = json.load(file)

    if not isinstance(requests, list) or not requests:
        raise ValueError(f"{path.name} must contain a non-empty JSON list.")

    required_fields = {
        "request_id",
        "order_id",
        "product",
        "request_type",
        "amount_inr",
        "days_since_delivery",
        "item_condition",
        "invoice_available",
        "photo_evidence_available",
        "previous_returns_90_days",
    }
    seen_ids: set[str] = set()
    for index, request in enumerate(requests):
        if not isinstance(request, dict):
            raise ValueError(f"Return record {index + 1} must be a JSON object.")
        missing_fields = required_fields - request.keys()
        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise ValueError(f"Return record {index + 1} is missing: {missing}.")
        request_id = request["request_id"]
        if not isinstance(request_id, str) or not request_id.strip():
            raise ValueError(f"Return record {index + 1} has an invalid request_id.")
        if request_id in seen_ids:
            raise ValueError(f"Duplicate request_id in {path.name}: {request_id}.")
        seen_ids.add(request_id)

    return requests


def evaluate_policy(request: ReturnRecord) -> list[dict[str, Any]]:
    condition = str(request["item_condition"]).strip().upper()
    amount = request["amount_inr"]
    days_since_delivery = request["days_since_delivery"]
    previous_returns = request["previous_returns_90_days"]

    return [
        {
            "rule": f"Product amount is below INR {AUTO_APPROVAL_LIMIT_INR:,}",
            "passed": amount < AUTO_APPROVAL_LIMIT_INR,
            "details": (
                f"Amount INR {amount:,} is below the limit."
                if amount < AUTO_APPROVAL_LIMIT_INR
                else f"Amount INR {amount:,} is not below the limit."
            ),
        },
        {
            "rule": f"Request is within {RETURN_WINDOW_DAYS} days of delivery",
            "passed": 0 <= days_since_delivery <= RETURN_WINDOW_DAYS,
            "details": (
                f"Request received {days_since_delivery} days after delivery."
            ),
        },
        {
            "rule": "Customer invoice is available",
            "passed": request["invoice_available"] is True,
            "details": (
                "Invoice is available."
                if request["invoice_available"] is True
                else "Invoice is not available."
            ),
        },
        {
            "rule": "Item is unopened, or damaged with supporting photographs",
            "passed": condition == "UNOPENED"
            or (
                condition == "DAMAGED"
                and request["photo_evidence_available"] is True
            ),
            "details": (
                "Item condition and evidence meet the policy."
                if condition == "UNOPENED"
                or (
                    condition == "DAMAGED"
                    and request["photo_evidence_available"] is True
                )
                else (
                    "Damaged-item photographs are missing."
                    if condition == "DAMAGED"
                    else f"Item condition {condition!r} does not meet the policy."
                )
            ),
        },
        {
            "rule": f"Fewer than {HIGH_RETURN_COUNT} previous returns in 90 days",
            "passed": previous_returns < HIGH_RETURN_COUNT,
            "details": (
                f"{previous_returns} previous returns in 90 days."
            ),
        },
    ]


def deterministic_risk_flags(request: ReturnRecord) -> list[str]:
    flags: list[str] = []
    if request["amount_inr"] >= AUTO_APPROVAL_LIMIT_INR:
        flags.append("high-value request")
    if request["previous_returns_90_days"] >= HIGH_RETURN_COUNT:
        flags.append("unusually frequent recent returns")
    if request["invoice_available"] is not True:
        flags.append("invoice evidence is missing")
    if (
        str(request["item_condition"]).strip().upper() == "DAMAGED"
        and request["photo_evidence_available"] is not True
    ):
        flags.append("photo evidence for the reported damage is missing")
    return flags


def parse_risk_response(text: str) -> tuple[str, str]:
    first_line = text.strip().splitlines()[0] if text.strip() else ""
    if "|" not in first_line:
        raise ValueError(
            "Risk Agent must start its response with HIGH | or LOW |."
        )
    level, assessment = first_line.split("|", maxsplit=1)
    level = level.strip().upper()
    assessment = assessment.strip()
    if level not in {"HIGH", "LOW"} or not assessment:
        raise ValueError(
            "Risk Agent response must use HIGH | explanation or LOW | explanation."
        )
    return level, assessment


def combine_eligibility_findings(
    policy_checks: list[dict[str, Any]],
    risk_level: str,
    risk_assessment: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    checks = list(policy_checks)
    checks.append(
        {
            "rule": "Risk Agent has not identified a HIGH-risk concern",
            "passed": risk_level == "LOW",
            "details": risk_assessment,
        }
    )
    issues = [check["details"] for check in checks if not check["passed"]]
    return checks, issues


def manager_decision(value: str) -> str:
    decision = value.strip().lower()
    if decision not in {"approve", "reject"}:
        raise ValueError("Manager decision must be 'approve' or 'reject'.")
    return decision


def validate_customer_draft(draft: str, final_decision: str) -> str:
    message = draft.strip()
    if not message:
        raise ValueError("Customer Response Agent returned an empty draft.")
    rejection = re.search(
        r"\b(?:not approved|not eligible|does not qualify|doesn't qualify|"
        r"rejected|declined|could not approve|cannot approve|unable to approve)\b",
        message,
        re.IGNORECASE,
    )
    approval = re.search(
        r"\b(?:approved|eligible|qualifies|qualified|accepted|authorized)\b",
        message,
        re.IGNORECASE,
    )
    if final_decision == "MANAGER_REJECTED":
        if not rejection:
            raise ValueError(
                "Customer Response Agent did not communicate the rejection."
            )
    elif rejection or not approval:
        raise ValueError(
            "Customer Response Agent did not communicate the approval accurately."
        )
    completed_action = re.search(
        r"\b(?:we|i)\s+(?:have\s+)?(?:already\s+)?"
        r"(?:processed|issued|sent|shipped|completed|initiated|refunded|dispatched)\b"
        r"|(?<!no )(?<!not )(?<!never )\b(?:refund|payment|replacement)\b.{0,60}\b"
        r"(?:(?:has|was|is)(?:\s+already)?\s+"
        r"(?:been\s+)?(?:processed|issued|sent|shipped|completed|initiated|"
        r"refunded|dispatched)|(?:is|was)\s+(?:done|complete|completed))\b",
        message,
        re.IGNORECASE | re.DOTALL,
    )
    if completed_action:
        raise ValueError(
            "Customer Response Agent claimed a simulated action was completed."
        )
    return message


class ApprovalGateway(Executor):
    def __init__(self) -> None:
        super().__init__(id="approval_gateway")

    @handler
    async def review(
        self,
        request: ReturnRecord,
        ctx: WorkflowContext[dict[str, Any]],
    ) -> None:
        needs_human_review = any(
            not check["passed"] for check in request["eligibility_checks"]
        )
        if not needs_human_review:
            request["approval_route"] = "Automatic"
            request["final_decision"] = "AUTO_APPROVED"
            await ctx.send_message(request)
            return

        request["approval_route"] = "Human Review"
        issue_lines = "\n".join(
            f"- {issue}" for issue in request["eligibility_issues"]
        )
        await ctx.request_info(
            request_data=ManagerApprovalRequest(
                request=request,
                prompt=(
                    f"Request: {request['request_id']} | "
                    f"Item: {request['product']} | "
                    f"Amount: INR {request['amount_inr']:,}\n"
                    f"Eligibility issues:\n{issue_lines or '- None'}\n"
                    f"Risk assessment: {request['risk_assessment']}\n"
                    "Enter approve or reject:"
                ),
            ),
            response_type=str,
        )

    @response_handler
    async def on_manager_decision(
        self,
        original_request: ManagerApprovalRequest,
        response: str,
        ctx: WorkflowContext[dict[str, Any]],
    ) -> None:
        decision = manager_decision(response)
        request = dict(original_request.request)
        request["final_decision"] = (
            "MANAGER_APPROVED" if decision == "approve" else "MANAGER_REJECTED"
        )
        request["decision_by"] = "Human manager"
        await ctx.send_message(request)


def build_workflow(chat_client: OpenAIChatClient):
    eligibility_agent = Agent(
        client=chat_client,
        name="EligibilityAgent",
        instructions=(
            "Explain the supplied deterministic return-policy checks using only "
            "the supplied request and check results. Do not change any pass/fail "
            "result, invent policy, or make an approval decision. Be concise."
        ),
    )
    risk_agent = Agent(
        client=chat_client,
        name="RiskAgent",
        instructions=(
            "Assess only the supplied return request for high value, unusual "
            "return frequency, missing invoice or damage evidence, and other "
            "clearly evidenced concerns. Use only supplied facts. Return exactly "
            "one first line in this format: HIGH | short explanation or "
            "LOW | short explanation. Do not decide eligibility."
        ),
    )
    customer_response_agent = Agent(
        client=chat_client,
        name="CustomerResponseAgent",
        instructions=(
            "Write a concise customer-facing draft based only on the supplied "
            "request and final decision. If final_decision is AUTO_APPROVED or "
            "MANAGER_APPROVED, explicitly say the request is approved. If it is "
            "MANAGER_REJECTED, explicitly say it was not approved. Use the exact "
            "word approved in the approval message. The first sentence must "
            "clearly communicate that status. This is only a "
            "simulation: do not claim a refund was "
            "processed, a payment was made, or a replacement was shipped or "
            "completed. Do not change or second-guess the final decision."
        ),
    )
    return _build_workflow(
        eligibility_agent,
        risk_agent,
        customer_response_agent,
    )


def _build_workflow(
    eligibility_agent: TextAgent,
    risk_agent: TextAgent,
    customer_response_agent: TextAgent,
):
    @executor(id="eligibility_review")
    async def eligibility_review(
        request: ReturnRecord,
        ctx: WorkflowContext[dict[str, Any]],
    ) -> None:
        policy_checks = evaluate_policy(request)
        result = await eligibility_agent.run(
            json.dumps(
                {"request": request, "policy_checks": policy_checks},
                ensure_ascii=False,
            )
        )
        explanation = result.text.strip()
        if not explanation:
            raise ValueError("Eligibility Agent returned an empty explanation.")
        await ctx.send_message(
            {
                **request,
                "policy_checks": policy_checks,
                "eligibility_explanation": explanation,
            }
        )

    @executor(id="risk_review")
    async def risk_review(
        request: ReturnRecord,
        ctx: WorkflowContext[dict[str, Any]],
    ) -> None:
        result = await risk_agent.run(
            json.dumps(
                {
                    "request": request,
                    "eligibility_issues": [
                        check["details"]
                        for check in request["policy_checks"]
                        if not check["passed"]
                    ],
                },
                ensure_ascii=False,
            )
        )
        model_risk_level, model_assessment = parse_risk_response(result.text)
        deterministic_flags = deterministic_risk_flags(request)
        risk_level = (
            "HIGH" if deterministic_flags else model_risk_level
        )
        risk_assessment = model_assessment
        if deterministic_flags:
            risk_assessment = (
                f"{model_assessment} Deterministic risk flags: "
                f"{'; '.join(deterministic_flags)}."
            )

        eligibility_checks, eligibility_issues = combine_eligibility_findings(
            request["policy_checks"],
            risk_level,
            risk_assessment,
        )
        await ctx.send_message(
            {
                **request,
                "risk_level": risk_level,
                "risk_assessment": risk_assessment,
                "eligibility_checks": eligibility_checks,
                "eligibility_issues": eligibility_issues,
            }
        )

    @executor(id="customer_response")
    async def customer_response(
        request: ReturnRecord,
        ctx: WorkflowContext[dict[str, Any]],
    ) -> None:
        result = await customer_response_agent.run(
            json.dumps(
                {
                    "request_id": request["request_id"],
                    "order_id": request["order_id"],
                    "product": request["product"],
                    "request_type": request["request_type"],
                    "final_decision": request["final_decision"],
                    "approval_route": request["approval_route"],
                    "eligibility_issues": request["eligibility_issues"],
                },
                ensure_ascii=False,
            )
        )
        draft = validate_customer_draft(
            result.text,
            request["final_decision"],
        )
        await ctx.send_message({**request, "customer_communication_draft": draft})

    @executor(id="final_output")
    async def final_output(
        request: ReturnRecord,
        ctx: WorkflowContext[Any, str],
    ) -> None:
        output = {
            "request_id": request["request_id"],
            "order_id": request["order_id"],
            "product": request["product"],
            "requested_amount_inr": request["amount_inr"],
            "eligibility_findings": {
                "checks": request["eligibility_checks"],
                "explanation": request["eligibility_explanation"],
            },
            "risk_assessment": {
                "level": request["risk_level"],
                "summary": request["risk_assessment"],
            },
            "approval_route": request["approval_route"],
            "final_decision": request["final_decision"],
            "customer_communication_draft": request[
                "customer_communication_draft"
            ],
            "simulation_notice": (
                "No payment was processed and no product replacement was initiated."
            ),
        }
        await ctx.yield_output(json.dumps(output, ensure_ascii=False, indent=2))

    gateway = ApprovalGateway()
    return (
        WorkflowBuilder(start_executor=eligibility_review)
        .add_edge(eligibility_review, risk_review)
        .add_edge(risk_review, gateway)
        .add_edge(gateway, customer_response)
        .add_edge(customer_response, final_output)
        .build()
    )


def read_manager_decision(
    prompt: str,
    input_fn: Callable[[str], str] = input,
    output: TextIO | None = None,
) -> str:
    stream = output or sys.stdout
    print(prompt, file=stream)
    while True:
        try:
            response = input_fn("Manager decision (approve/reject): ")
        except EOFError as exc:
            raise RuntimeError(
                "Input ended while waiting for the manager's decision."
            ) from exc
        try:
            return manager_decision(response)
        except ValueError:
            print("Invalid input. Enter approve or reject.", file=stream)


async def run_request(
    workflow: Any,
    request: ReturnRecord,
    input_fn: Callable[[str], str] = input,
    output: TextIO | None = None,
) -> dict[str, Any]:
    stream_out = output or sys.stdout
    responses: dict[str, str] | None = None
    first_run = True

    while True:
        stream = (
            workflow.run(request, stream=True)
            if first_run
            else workflow.run(stream=True, responses=responses)
        )
        first_run = False
        pending: dict[str, ManagerApprovalRequest] = {}
        final_output: dict[str, Any] | None = None

        async for event in stream:
            if event.type == "request_info":
                pending[event.request_id] = event.data
            elif event.type == "output":
                final_output = json.loads(str(event.data))
                print(
                    "\nFINAL RETURN DECISION\n"
                    + json.dumps(final_output, ensure_ascii=False, indent=2),
                    file=stream_out,
                )

        if final_output is not None:
            return final_output
        if not pending:
            raise RuntimeError(
                f"Workflow for {request.get('request_id', '<unknown>')} stopped "
                "without a final output or a human-approval request."
            )

        responses = {}
        for request_id, approval_request in pending.items():
            decision = read_manager_decision(
                approval_request.prompt,
                input_fn=input_fn,
                output=stream_out,
            )
            responses[request_id] = decision


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulate returns and refund decisions using Microsoft Agent Framework."
    )
    parser.add_argument(
        "--check-data",
        action="store_true",
        help="Validate and summarize returns.json without calling Azure AI Foundry.",
    )
    args = parser.parse_args()

    requests = load_requests()
    if args.check_data:
        print(f"Validated {len(requests)} return requests in {RETURNS_FILE.name}.")
        for request in requests:
            checks = evaluate_policy(request)
            print(
                f"{request['request_id']}: "
                f"{sum(check['passed'] for check in checks)}/{len(checks)} "
                "policy checks pass before risk review."
            )
        return

    settings = load_settings()
    print(f"Foundry configuration loaded for model {settings.model}.")

    async with AsyncOpenAI(
        api_key=settings.api_key,
        base_url=settings.base_url,
    ) as sdk_client:
        chat_client = OpenAIChatClient(
            model=settings.model,
            async_client=sdk_client,
        )
        workflow = build_workflow(chat_client)

        for request in requests:
            print(f"\nProcessing {request['request_id']} ({request['product']})")
            await run_request(workflow, request)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except ConfigurationError as exc:
        raise SystemExit(f"Configuration error: {exc}") from exc
