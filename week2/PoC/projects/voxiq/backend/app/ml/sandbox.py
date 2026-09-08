"""Local code-execution sandbox for the Analytics Agent.

Implements a common "local fallback" sandbox design
(subprocess isolation + OS resource limits + a restricted builtins set) as
the DEFAULT and only validated path in this build. E2B (config field only,
see config.py's `e2b_api_key_file`/`sandbox_provider`) is scaffolded but NOT
validated this round — this project has no E2B API key.

Honesty about what this is NOT, stated plainly (this style of local-fallback
sandbox generally carries the same caveat): this is a *teaching-grade*
isolation boundary, not a production security boundary. A sufficiently
determined attacker can escape a restricted-`__builtins__` sandbox via
introspection tricks (e.g. walking `().__class__.__mro__`). Real isolation
needs a container/VM/gVisor-level boundary — E2B, Docker-in-Docker, or
Firecracker microVMs are the commercial answer; see architecture.md's
production-scaling section.
"""
import json
import os
import subprocess
import sys
import tempfile

from ..config import read_key_file, settings

# Deliberately small: enough for genuine data-analysis snippets (loops,
# arithmetic, string/list/dict work, printing results) without exposing
# filesystem/network/process primitives.
SAFE_BUILTIN_NAMES = [
    "len", "range", "print", "sum", "min", "max", "sorted", "abs", "round",
    "enumerate", "zip", "list", "dict", "set", "tuple", "str", "int", "float",
    "bool", "isinstance", "type", "map", "filter", "any", "all", "reversed",
]

_RUNNER_TEMPLATE = """
import builtins as _builtins_module
import resource

resource.setrlimit(resource.RLIMIT_AS, ({mem_bytes}, {mem_bytes}))
resource.setrlimit(resource.RLIMIT_CPU, ({cpu_seconds}, {cpu_seconds}))

import json
with open({data_path!r}) as f:
    data = json.load(f)

safe_builtins = {{name: getattr(_builtins_module, name) for name in {safe_names!r}}}
sandbox_globals = {{"__builtins__": safe_builtins, "data": data}}

code = {code!r}
exec(code, sandbox_globals)
"""


def run_code(code: str, data: dict | list, timeout_seconds: int | None = None) -> dict:
    """Executes `code` in an isolated subprocess with `data` available as a
    global. Returns {stdout, stderr, exit_code, timed_out}."""
    timeout_seconds = timeout_seconds or settings.sandbox_timeout_seconds
    mem_bytes = settings.sandbox_max_memory_mb * 1024 * 1024

    with tempfile.TemporaryDirectory() as tmp:
        data_path = os.path.join(tmp, "data.json")
        runner_path = os.path.join(tmp, "runner.py")
        with open(data_path, "w") as f:
            json.dump(data, f)

        runner_src = _RUNNER_TEMPLATE.format(
            mem_bytes=mem_bytes,
            cpu_seconds=timeout_seconds,
            data_path=data_path,
            safe_names=SAFE_BUILTIN_NAMES,
            code=code,
        )
        with open(runner_path, "w") as f:
            f.write(runner_src)

        try:
            proc = subprocess.run(
                [sys.executable, runner_path],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                env={"PATH": os.environ.get("PATH", "")},  # no inherited secrets/credentials
            )
            return {
                "stdout": proc.stdout[-8000:],
                "stderr": proc.stderr[-4000:],
                "exit_code": proc.returncode,
                "timed_out": False,
            }
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            return {
                "stdout": stdout[-8000:],
                "stderr": f"Execution exceeded {timeout_seconds}s of wall-clock time and was terminated.",
                "exit_code": -1,
                "timed_out": True,
            }


def e2b_available() -> bool:
    return bool(read_key_file(settings.e2b_api_key_file))


def run_code_e2b(code: str, data: dict | list) -> dict:
    raise NotImplementedError(
        "The E2B sandbox is scaffolded (config.py has e2b_api_key_file / sandbox_provider='e2b') "
        "but not validated in this build — no E2B API key is available this round. "
        "The local sandbox (run_code()) is the default and only validated execution path."
    )
