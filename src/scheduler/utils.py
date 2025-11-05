from textwrap import indent
import json


def print_json(data, title="JSON"):
    """Pretty print JSON data"""
    print(f"\n{'='*50}")
    print(f"{title}:")
    print('='*50)
    print(json.dumps(data, indent=2, default=str))
    print('='*50 + "\n")
