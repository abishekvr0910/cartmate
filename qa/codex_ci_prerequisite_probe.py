"""Independent, offline check of the RT-17 dependency ordering in hosted CI.

Runs only the existing RT-17 function, without importing the backend or opening
any database. A temporary checkout-shaped directory demonstrates the missing
frontend dependency when CI orders pytest before npm ci. No packages installed.
Exit 0: dependency order and local positive control pass; 1: finding; 2: incomplete.
"""

import ast
import json
import subprocess
import tempfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
TEST_FILE = REPO / "backend" / "test_private_pilot_review.py"
TEST_NAME = "test_rt17_native_destination_policy_and_trust_boundary"


def run_regression(repo: Path, scratch: Path) -> None:
    tree = ast.parse(TEST_FILE.read_text(encoding="utf-8"), filename=str(TEST_FILE))
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == TEST_NAME)
    standalone = ast.Module(body=[function], type_ignores=[])
    namespace = {"Path": Path, "subprocess": subprocess, "REPO_ROOT": repo}
    exec(compile(standalone, str(TEST_FILE), "exec"), namespace)
    namespace[TEST_NAME](scratch)


def main() -> int:
    workflow = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    install_index = workflow.index("- name: Install frontend dependencies")
    test_index = workflow.index("- name: Compile and test backend with isolated SQLite database")
    prerequisite_precedes_tests = install_index < test_index
    result = {"frontend_install_precedes_backend_tests": prerequisite_precedes_tests}

    with tempfile.TemporaryDirectory(prefix="cartmate-ci-prerequisite-") as scratch:
        scratch = Path(scratch)
        positive = scratch / "positive"
        positive.mkdir()
        run_regression(REPO, positive)
        result["local_rt17_positive_control"] = "passed"
        if not prerequisite_precedes_tests:
            empty_checkout = scratch / "checkout"
            (empty_checkout / "qa").mkdir(parents=True)
            (empty_checkout / "frontend").mkdir()
            negative = scratch / "negative"
            negative.mkdir()
            try:
                run_regression(empty_checkout, negative)
            except AssertionError as error:
                missing = "MODULE_NOT_FOUND" in str(error) and "typescript" in str(error)
                if not missing:
                    raise
                result["fresh_dependency_state_rt17"] = "fails: Cannot find module frontend/node_modules/typescript"
            else:
                raise RuntimeError("Expected clean-dependency-state failure did not occur")

    print(json.dumps(result, indent=2))
    return 0 if prerequisite_precedes_tests else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(json.dumps({"probe_incomplete": str(error)}))
        raise SystemExit(2)
