import base64
import binascii
import logging
import re
from decimal import Decimal
from io import BytesIO
from pathlib import PurePath

from pypdf import PdfReader

from app.evidence import BENEFIT_TERMS, MONEY, benefits, matches
from app.models import DocumentResult, ExtractedFields, FieldEvidence, InternalDocumentRequest, ItemError
from app.policy_service import PolicyService
from app.provider import ProviderFailure

logger = logging.getLogger(__name__)
REVIEW = "Human review is required; this report does not approve a claim or authorize payment."


class DocumentFailure(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def read_document(filename: str, content: bytes) -> str:
    if not content:
        raise DocumentFailure("EMPTY_FILE", "The submitted file is empty")
    if len(content) > 5 * 1024 * 1024:
        raise DocumentFailure("FILE_TOO_LARGE", "Files must be at most 5 MiB")
    extension = PurePath(filename).suffix.casefold()
    try:
        if extension == ".txt":
            text = content.decode("utf-8-sig")
            if "\x00" in text:
                raise ValueError("Binary text")
        elif extension == ".pdf":
            if not content.startswith(b"%PDF-"):
                raise ValueError("Not a PDF")
            reader = PdfReader(BytesIO(content), strict=True)
            if reader.is_encrypted:
                raise ValueError("Encrypted PDF")
            if len(reader.pages) > 50:
                raise DocumentFailure("DOCUMENT_TOO_LARGE", "PDFs must contain at most 50 pages")
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        else:
            raise DocumentFailure("UNSUPPORTED_FILE_TYPE", "Only UTF-8 TXT and text-based PDF files are supported")
    except DocumentFailure:
        raise
    except Exception:
        raise DocumentFailure("UNREADABLE_FILE", "The file could not be read as supported text") from None
    if not text.strip():
        raise DocumentFailure("NO_EXTRACTABLE_TEXT", "The file contains no readable text; OCR is not supported")
    if len(text) > 100_000:
        raise DocumentFailure("DOCUMENT_TOO_LARGE", "Extracted text exceeds 100000 characters")
    return text


def extract_fields(text: str) -> tuple[ExtractedFields, FieldEvidence, list[str]]:
    fields = ExtractedFields()
    evidence = FieldEvidence()
    issues = [REVIEW]
    # Keep quotations verbatim from the extracted text. Do not execute embedded instructions.
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]
    detected = benefits(text)
    if len(detected) == 1:
        fields.benefit = detected[0]
        evidence.benefit = [s for s in sentences if any(matches(s, t) for t in BENEFIT_TERMS[detected[0]])]
    else:
        issues.append("Benefit is missing or ambiguous; policy selection requires clarification.")

    money = list(MONEY.finditer(text))
    amounts = {Decimal(m[2].replace(",", "")) for m in money}
    currencies = {m[1].upper() for m in money}
    if len(amounts) == 1 and len(currencies) == 1:
        fields.amount = next(iter(amounts))
        evidence.amount = list(dict.fromkeys(m[0] for m in money))
    elif money:
        issues.append("Amount is ambiguous; candidate quotations: " + " | ".join(dict.fromkeys(m[0] for m in money)))
    else:
        issues.append("Amount is missing or unsupported; no unambiguous currency-qualified amount was found.")
    if len(currencies) == 1:
        fields.currency = next(iter(currencies))
        evidence.currency = list(dict.fromkeys(m[0] for m in money))
    else:
        issues.append("Currency is missing or ambiguous.")

    refs = list(re.finditer(r"\bReference\s*:\s*([A-Za-z0-9][A-Za-z0-9_-]*)", text, re.I))
    values = {m[1] for m in refs}
    if len(values) == 1:
        fields.reference = next(iter(values))
        evidence.reference = list(dict.fromkeys(m[0] for m in refs))
    else:
        issues.append("Reference is missing or ambiguous.")
    if re.search(r"system message|ignore.{0,30}(header|rules)|mark.{0,30}approved", text, re.I):
        issues.append("Instruction-like document text was treated as untrusted data; caller identity and review requirements were not changed.")
    return fields, evidence, issues


class DocumentService:
    def __init__(self, policies: PolicyService):
        self.policies = policies

    def process(self, request: InternalDocumentRequest) -> DocumentResult:
        try:
            try:
                content = base64.b64decode(request.content_base64, validate=True)
            except (ValueError, binascii.Error):
                raise DocumentFailure("UNREADABLE_FILE", "File encoding is invalid") from None
            text = read_document(request.filename, content)
            fields, evidence, issues = extract_fields(text)
            policy = None
            if fields.benefit:
                policy = self.policies.answer(request.tenant, request.role, request.as_of, fields.benefit)
                if policy.status == "CONFLICT":
                    issues.append("Applicable policies disagree; a reviewer must resolve the policy conflict.")
                elif policy.status == "INSUFFICIENT_EVIDENCE":
                    issues.append("No supported applicable policy terms were found for this benefit.")
                else:
                    issues.append("Policy terms do not establish remaining balance, individual expense eligibility, or a payable amount; no claims history is supplied.")
                    if any("approval" in c.quote.casefold() for c in policy.citations):
                        issues.append("A reviewer must verify the policy's approval requirement, including whether approval preceded booking.")
            result = DocumentResult(document_id=request.document_id, processing_status="COMPLETED",
                                    extracted=fields, field_evidence=evidence, policy=policy, issues=issues)
        except (DocumentFailure, ProviderFailure) as exc:
            result = self.failed(request.document_id, exc.code, str(exc))
        except Exception:
            # Keep independent items processing; never disclose parser/provider internals.
            result = self.failed(request.document_id, "PROCESSING_FAILURE", "Document processing failed")
        logger.info("batch=%r document=%r status=%s error=%s", request.batch_id, request.document_id,
                    result.processing_status, result.error.code if result.error else "none")
        return result

    @staticmethod
    def failed(document_id: str, code: str, message: str) -> DocumentResult:
        return DocumentResult(document_id=document_id, processing_status="FAILED", issues=[REVIEW],
                              error=ItemError(code=code, message=message))
