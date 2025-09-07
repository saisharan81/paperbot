#!/usr/bin/env python3
"""
Verify that every dashboard JSON in config/grafana/provisioning/dashboards
has a non-empty top-level "title".

Usage:
  python3 scripts/verify_dashboards.py [dashboards_dir]

Exit codes:
  0 = OK
  1 = Failure (prints JSON report with offending files)
"""

import json
import os
import sys
from typing import List, Dict, Any


def find_dashboard_jsons(root: str) -> List[str]:
    files: List[str] = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            if name.lower().endswith('.json'):
                files.append(os.path.join(dirpath, name))
    return sorted(files)


def check_titles(paths: List[str]) -> Dict[str, Any]:
    offenders: List[str] = []
    parse_errors: Dict[str, str] = {}
    for p in paths:
        try:
            with open(p, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:  # JSON parse error
            parse_errors[p] = str(e)
            offenders.append(p)
            continue

        title = data.get('title')
        if not isinstance(title, str) or not title.strip():
            offenders.append(p)

    status = 'ok' if not offenders else 'failed'
    return {
        'status': status,
        'checked': len(paths),
        'offenders': offenders,
        'parse_errors': parse_errors,
    }


def main() -> int:
    dashboards_dir = (
        sys.argv[1]
        if len(sys.argv) > 1
        else os.path.join('config', 'grafana', 'provisioning', 'dashboards')
    )

    files = find_dashboard_jsons(dashboards_dir)
    report = check_titles(files)
    print(json.dumps(report, indent=2))

    return 0 if report['status'] == 'ok' else 1


if __name__ == '__main__':
    raise SystemExit(main())

