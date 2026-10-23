import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile

repo = Path.cwd()
evidence = Path(__file__).parent
suites = sys.argv[1:] or [
    "fm-dispatch-resolve", "fm-quota-choose", "fm-bootstrap",
    "fm-procevent-quota", "fm-startup-memory-budget", "fm-secondmate-sync",
    "fm-secondmate-harness", "fm-secondmate-liveness", "fm-shared-captain-inheritance",
]
results = []
suffix = "-indexed" if os.environ.get("FM_TEST_PRODUCT_INDEX") else "-isolated" if os.environ.get("FM_TEST_PRODUCT_COPY") else "-retest" if sys.argv[1:] else ""
for suite in suites:
    with tempfile.TemporaryDirectory(prefix=".test-phase-", dir=repo) as temporary:
        root = Path(temporary)
        for child in ("tmp", "home", "config", "cache"):
            (root / child).mkdir()
        product = repo
        if os.environ.get("FM_TEST_PRODUCT_COPY"):
            product = root / "product"
            files = subprocess.check_output(["git", "ls-files", "-z"], text=True).split("\0")
            for name in filter(None, files):
                source = repo / name
                destination = product / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination, follow_symlinks=False)
                if source.is_file():
                    assert source.read_bytes() == destination.read_bytes()
            if os.environ.get("FM_TEST_PRODUCT_INDEX"):
                git_env = {"PATH": os.environ["PATH"], "HOME": str(root / "home"),
                           "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null"}
                subprocess.run(["git", "init", "-q", "-b", "main", str(product)], env=git_env, check=True)
                subprocess.run(["git", "-C", str(product), "add", "--all"], env=git_env, check=True)
        env = {
            "PATH": os.environ["PATH"], "HOME": str(root / "home"),
            "TMPDIR": str(root / "tmp"), "XDG_CONFIG_HOME": str(root / "config"),
            "XDG_CACHE_HOME": str(root / "cache"), "LANG": "en_US.UTF-8",
            "USER": os.environ.get("USER", "tester"),
            "NO_MISTAKES_GATE": os.environ.get("NO_MISTAKES_GATE", "1"),
        }
        command = ["bash", f"tests/{suite}.test.sh"]
        print("RUN " + " ".join(command), flush=True)
        result = subprocess.run(command, cwd=product, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (evidence / f"{suite}{suffix}.log").write_text(result.stdout)
        record = {"command": " ".join(command), "exit_code": result.returncode,
                  "passed": sum(line.startswith("ok -") for line in result.stdout.splitlines()),
                  "failed": sum(line.startswith("not ok -") for line in result.stdout.splitlines())}
        results.append(record)
        print(json.dumps(record), flush=True)
        if result.returncode:
            print("\n".join(result.stdout.splitlines()[-15:]), flush=True)
        (evidence / f"targeted-tests{suffix}.json").write_text(json.dumps(results, indent=2) + "\n")
raise SystemExit(any(result["exit_code"] for result in results))
