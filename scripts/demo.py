"""Exercise both public endpoints, assert the supplied outcomes, and save real responses."""
import argparse
import json
import uuid
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]


def send(base_url, path, body, content_type):
    request = Request(base_url.rstrip("/") + path, data=body, method="POST", headers={
        "Content-Type": content_type, "X-Caller-Id": "atlas-employee-01"})
    try:
        with urlopen(request, timeout=120) as response:
            return json.load(response)
    except HTTPError as error:
        raise SystemExit(f"HTTP {error.code}: {error.read().decode()}") from None


def batch_body(manifest):
    boundary = "desk-" + uuid.uuid4().hex
    parts = []
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="metadata"\r\nContent-Type: application/json\r\n\r\n'.encode()
                 + json.dumps(manifest).encode() + b"\r\n")
    for entry in manifest["documents"]:
        name = entry["filename"]
        kind = "application/pdf" if name.endswith(".pdf") else "text/plain"
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="files"; filename="{name}"\r\nContent-Type: {kind}\r\n\r\n'.encode()
                     + (ROOT / "examples" / "requests" / name).read_bytes() + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def run(base_url, output):
    request = (ROOT / "examples" / "answer-request.json").read_bytes()
    answer = send(base_url, "/answer", request, "application/json")
    assert answer["status"] == "ANSWERED"
    assert answer["citations"][0]["chunk_id"] == "atlas-cert-current"
    manifest = json.loads((ROOT / "examples" / "batch-metadata.json").read_text())
    body, content_type = batch_body(manifest)
    batch = send(base_url, "/batches", body, content_type)
    assert batch["summary"] == {"total": 8, "completed": 7, "failed": 1}, batch
    results = batch["results"]
    assert [r["document_id"] for r in results] == [e["document_id"] for e in manifest["documents"]]
    assert all(r["review_required"] is True for r in results)
    assert results[0]["extracted"]["amount"] == "18000"
    assert results[1]["policy"]["status"] == "CONFLICT"
    assert results[2]["extracted"]["amount"] is None
    assert results[2]["policy"]["status"] == "ANSWERED"
    assert results[3]["policy"]["status"] == "INSUFFICIENT_EVIDENCE"
    assert results[4]["policy"]["citations"][0]["chunk_id"] == "atlas-cert-current"
    assert results[5]["duplicate_of"] == "request-01"
    assert results[6]["extracted"]["amount"] is None
    assert results[7]["error"]["code"] == "EMPTY_FILE"
    output.mkdir(parents=True, exist_ok=True)
    for name, value in (("answer-response", answer), ("batch-response", batch)):
        (output / f"{name}.json").write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: /answer and /batches; 8 items, 7 completed, 1 failed. Responses saved to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8080")
    parser.add_argument("--output", type=Path, default=ROOT / "examples" / "responses")
    args = parser.parse_args()
    run(args.base_url, args.output)
