"""
Handler Lambda para el ETL de MercadoLibre.

Invocado desde GitHub Actions via `aws lambda invoke`.
Corre extract_ml_autos.run() y devuelve statusCode 200/500.
"""

import json
import traceback

from etl.extract_ml_autos import run


def handler(event, context):
    try:
        run()
        return {"statusCode": 200, "body": json.dumps({"status": "ok"})}
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e), "trace": traceback.format_exc()}),
        }
