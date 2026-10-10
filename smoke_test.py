"""
Smoke tests: render every page headlessly with Streamlit's AppTest and fail on any exception.
Run from the project folder:   python tests/smoke_test.py
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest  # noqa: E402

PAGES = ["overview", "trends", "drivers", "segments", "insights", "model_page", "data_export"]


def _page_script():
    """Executed by AppTest: builds the same context app.py builds, then renders one view."""
    import importlib
    import io
    import os
    import sys

    sys.path.insert(0, os.environ["CHURN_ROOT"])
    from src import analysis as A, config as C, data_loader as D
    from src.synthetic import generate_synthetic_churn
    from src.styles import inject_css

    inject_css()
    mode = os.environ["CHURN_MODE"]
    if mode == "synthetic":
        buf = io.StringIO()
        generate_synthetic_churn().to_csv(buf, index=False)
        buf.seek(0)
        df, rep = D.load_csv(buf, "SYNTHETIC", True)
    else:
        df, rep = D.load_csv(C.TELCO_PATH, "IBM")
    full = A.enrich(df)
    view = full
    if mode == "filtered":
        view = A.apply_filters(full, ["Month-to-month"], None, None, (0, 24), None, None)
    ctx = dict(df=view, df_full=full, data_report=rep, source_kind="real", source_label="test",
               is_synthetic=(mode == "synthetic"), filter_text="test")
    importlib.import_module("views." + os.environ["CHURN_PAGE"]).render(ctx)


def main() -> int:
    failures = 0
    os.environ["CHURN_ROOT"] = str(ROOT)
    for mode in ["real", "filtered", "synthetic"]:
        for page in PAGES:
            os.environ["CHURN_MODE"], os.environ["CHURN_PAGE"] = mode, page
            at = AppTest.from_function(_page_script, default_timeout=240).run()
            if at.exception:
                failures += 1
                print(f"FAIL  [{mode}] {page}")
                for e in at.exception:
                    print("      ", str(e.value)[:400])
            else:
                print(f"ok    [{mode}] {page}")

    # Full app entry point (default page) must also start cleanly.
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=240).run()
    print("ok    [app.py] startup" if not at.exception else f"FAIL  [app.py] {at.exception[0].value}")
    failures += bool(at.exception)
    print("\nAll good." if not failures else f"\n{failures} failure(s).")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
