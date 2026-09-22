# Employee Support Desk Assessment

This repository is being built in small milestones so every part is easy to understand and explain.

## Implemented so far

The project currently provides the public Spring Boot `/answer` flow backed by a deterministic Python policy engine. It:

- loads the 12 supplied policies without changing their data;
- filters by trusted tenant, role, approval state, and effective date;
- finds policies relevant to a requested benefit;
- returns `ANSWERED`, `INSUFFICIENT_EVIDENCE`, or `CONFLICT`;
- includes exact policy quotations as citations;
- does not require an API key or paid AI service.
- validates the public caller and request in Spring Boot;
- derives trusted tenant and role from `X-Caller-Id`;
- calls Python with bounded connection and read timeouts;
- converts dependency failures into safe public errors.

The multipart `/batches` document-processing flow will be added in the next milestone.

## Requirements

- Python 3.13 (Python 3.11+ also works)
- Java JDK 21
- VS Code with the Python and Pylance extensions
- VS Code Extension Pack for Java and Spring Boot Extension Pack

## Run on Windows

Open the project folder in VS Code, then open a terminal:

```powershell
cd python-service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest
python -m uvicorn app.main:app --reload --port 8000
```

If PowerShell prevents virtual-environment activation, allow scripts only for the current terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Test the internal API

Open `http://localhost:8000/docs`, or run:

```powershell
curl.exe -X POST "http://localhost:8000/internal/answer" `
  -H "Content-Type: application/json" `
  -d '{"tenant":"Atlas","role":"employee","as_of":"2026-09-21","question":"What is my annual certification reimbursement limit?"}'
```

Expected business result: `ANSWERED`, with the current Atlas employee certification policy and its exact quotation.

> `/internal/answer` is not intended for end users. Callers use Spring Boot `/answer`, and Spring Boot supplies trusted tenant and role values to Python.

## Run the Spring Boot public API

Keep Python running on port 8000. In a second VS Code terminal:

```powershell
cd spring-api
.\mvnw.cmd test
.\mvnw.cmd spring-boot:run
```

The public API runs on port 8080. Test it with:

```powershell
curl.exe -X POST "http://localhost:8080/answer" `
  -H "Content-Type: application/json" `
  -H "X-Caller-Id: atlas-employee-01" `
  -d '{"question":"What is my annual certification reimbursement limit?","as_of":"2026-09-21"}'
```

Spring Boot derives `Atlas` and `employee` from the caller ID. It never accepts tenant or role from the public request body.
