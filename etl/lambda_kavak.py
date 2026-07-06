"""
Handler Lambda para el scraping de Kavak.
Invocado desde GitHub Actions via aws lambda invoke.
"""

import json
import traceback

from etl.scrape_kavak import run


def handler(event, context):
    try:
        run()
        return {"statusCode": 200, "body": json.dumps({"status": "ok"})}
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e), "trace": traceback.format_exc()}),
        }
