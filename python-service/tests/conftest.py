"""Keep tests independent of developer live-provider credentials and call budgets.

Set these before test modules import app.main (which loads the local .env).
Live-provider tests explicitly construct mocked HTTP clients instead.
"""
import os


os.environ["AI_PROVIDER"] = "offline"
os.environ["MODEL_TIMEOUT_SECONDS"] = "1"
os.environ["INTERNAL_SERVICE_TOKEN"] = ""
