"""
Pipeline completo: extract → transform → load para cotizaciones del dólar.

Es el punto de entrada que corre el scheduler (GitHub Actions cron).
Si un paso falla, los siguientes no corren — los datos previos quedan intactos.
"""

import sys
from datetime import date

from etl.extract_dolar import run as extract_run
from etl.transform_dolar import run as transform_run
from etl.load_dolar import run as load_run


def run(day: date | None = None) -> None:
    day = day or date.today()
    print(f"=== Pipeline dólar — {day} ===\n")

    try:
        print("[Extract ] iniciando...")
        extract_run()
        print()

        print("[Transform] iniciando...")
        transform_run(day)
        print()

        print("[Load    ] iniciando...")
        load_run(day)
        print()

    except Exception as e:
        print(f"ERROR: {e}")
        print("Pipeline abortado. Los pasos siguientes no corrieron.")
        sys.exit(1)

    print("=== Pipeline completado ===")


if __name__ == "__main__":
    run()
