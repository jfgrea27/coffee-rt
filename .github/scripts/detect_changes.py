#!/usr/bin/env python3
"""Detect which services need rebuilding based on changed files and pyproject.toml dependencies."""

import json
import os
import sys

# Use tomllib (Python 3.11+) or fall back to toml package
try:
    import tomllib
except ImportError:
    try:
        import toml as tomllib  # type: ignore[import-not-found]
    except ImportError:
        print("Error: Python 3.11+ required, or install toml package", file=sys.stderr)
        sys.exit(1)

# Define services with their Dockerfiles
# Only services that have Dockerfiles are buildable
SERVICES = {
    "cafe-order-api": {
        "path": "backend/cafe_order_api",
        "dockerfile": "backend/cafe_order_api/Dockerfile",
        "context": ".",
    },
    "cafe-order-aggregator": {
        "path": "backend/cafe_order_aggregator",
        "dockerfile": "backend/cafe_order_aggregator/Dockerfile",
        "context": ".",
    },
    "stream-worker": {
        "path": "backend/stream_worker",
        "dockerfile": "backend/stream_worker/Dockerfile",
        "context": ".",
    },
    "load-tester": {
        "path": "backend/coffee_consumer_simulator",
        "dockerfile": "backend/coffee_consumer_simulator/Dockerfile",
        "context": ".",
    },
}

# Non-Python services
OTHER_SERVICES = {
    "cafe-dashboard": {
        "path": "frontend",
        "dockerfile": "frontend/Dockerfile",
        "context": "frontend",
        "deps": [],
    },
    "flink-job": {
        "path": "flink/coffee-rt-flink",
        "dockerfile": "flink/coffee-rt-flink/Dockerfile",
        "context": "flink/coffee-rt-flink",
        "deps": [],
    },
}


def get_local_deps(pyproject_path: str) -> list[str]:
    """Extract local dependencies from [tool.uv.sources]."""
    if not os.path.exists(pyproject_path):
        return []
    try:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
        sources = data.get("tool", {}).get("uv", {}).get("sources", {})
        local_deps = []
        for config in sources.values():
            if isinstance(config, dict) and "path" in config:
                # Resolve relative path
                base_dir = os.path.dirname(pyproject_path)
                dep_path = os.path.normpath(os.path.join(base_dir, config["path"]))
                local_deps.append(dep_path)
        return local_deps
    except Exception as e:
        print(f"Error parsing {pyproject_path}: {e}", file=sys.stderr)
        return []


def path_matches(changed_file: str, service_path: str) -> bool:
    """Check if changed file is under service path."""
    return changed_file.startswith(service_path + "/") or changed_file == service_path


def detect_changes(changed_files: list[str]) -> dict:
    """Determine which services need rebuilding based on changed files."""
    # Build deps for each Python service
    for name, config in SERVICES.items():
        pyproject = os.path.join(config["path"], "pyproject.toml")
        config["deps"] = get_local_deps(pyproject)
        print(f"{name} depends on: {config['deps']}")

    # Determine which services need rebuilding
    matrix = {"include": []}
    all_services = {**SERVICES, **OTHER_SERVICES}

    for name, config in all_services.items():
        needs_rebuild = False
        reason = ""

        # Check if service's own files changed
        if any(path_matches(f, config["path"]) for f in changed_files):
            needs_rebuild = True
            reason = "direct change"

        # Check if any dependency changed
        for dep_path in config.get("deps", []):
            if any(path_matches(f, dep_path) for f in changed_files):
                needs_rebuild = True
                reason = f"dependency {dep_path} changed"
                break

        # Check if root pyproject.toml or uv.lock changed (affects all Python services)
        if name in SERVICES:  # Python service
            if any(f in ["pyproject.toml", "uv.lock"] for f in changed_files):
                needs_rebuild = True
                reason = "root deps changed"

        if needs_rebuild:
            print(f"✓ {name}: REBUILD ({reason})")
            matrix["include"].append(
                {
                    "name": name,
                    "context": config["context"],
                    "dockerfile": config["dockerfile"],
                }
            )
        else:
            print(f"✗ {name}: skip")

    return matrix


def check_helm_changed(changed_files: list[str]) -> bool:
    """Check if helm chart files changed."""
    return any(f.startswith("helm/") for f in changed_files)


def main():
    # Get changed files from environment or stdin
    changed_files_str = os.environ.get("CHANGED_FILES", "")
    if not changed_files_str and not sys.stdin.isatty():
        changed_files_str = sys.stdin.read()

    changed_files = [f for f in changed_files_str.strip().split("\n") if f]

    print("Changed files:")
    for f in changed_files:
        print(f"  {f}")
    print()

    # Detect changes
    matrix = detect_changes(changed_files)
    helm_changed = check_helm_changed(changed_files)

    # Output results
    print(f"\nMatrix: {json.dumps(matrix)}")
    print(f"Helm changed: {helm_changed}")

    # Write to GitHub Actions output if available
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"matrix={json.dumps(matrix)}\n")
            f.write(f"has_changes={'true' if matrix['include'] else 'false'}\n")
            f.write(f"helm={str(helm_changed).lower()}\n")
    else:
        # Print for local testing
        print("\n--- Output ---")
        print(f"matrix={json.dumps(matrix)}")
        print(f"has_changes={'true' if matrix['include'] else 'false'}")
        print(f"helm={str(helm_changed).lower()}")


if __name__ == "__main__":
    main()
