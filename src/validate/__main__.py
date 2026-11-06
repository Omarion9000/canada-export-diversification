"""`python -m src.validate`: run V1-V6 on staging tables, write the report, halt on failure."""

import datetime as dt

from src.build import connect
from src.common import PipelineError
from src.validate import report
from src.validate.checks import ALL_CHECKS


class ValidationError(PipelineError):
    """A halting validator failed."""


def main() -> None:
    con = connect()
    results = []
    for check in ALL_CHECKS:
        result = check(con)
        print(f"  {result.check_id}: {result.status} - {result.summary}")
        results.append(result)
    vintage = con.execute("select p('cimt_vintage')").fetchall()[0][0]
    report.write(results, vintage, dt.date.today().isoformat())
    con.close()
    failed = [r.check_id for r in results if r.halting and r.status == "FAIL"]
    if failed:
        raise ValidationError(f"Halting validators failed: {', '.join(failed)}. "
                              "See docs/validation_report.md.")


if __name__ == "__main__":
    main()
