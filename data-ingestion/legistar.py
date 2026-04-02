import os
from dotenv import load_dotenv

import requests
import json

load_dotenv()

legistar_api_key = os.getenv("LEGISTAR_API_KEY")

def legistar_fetch(endpoint: str, page_size: int = 500):
    url = f'https://webapi.legistar.com/v1/nyc/{endpoint}'
    output_dir = os.path.join(os.path.dirname(__file__), 'json-data')
    os.makedirs(output_dir, exist_ok=True)

    output_file = os.path.join(output_dir, f'{endpoint}.json')
    checkpoint_file = os.path.join(output_dir, f'{endpoint}.checkpoint.json')

    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
            if not isinstance(existing_data, list):
                raise ValueError(f"Expected list in {output_file}, found {type(existing_data).__name__}")
    else:
        existing_data = []

    if os.path.exists(checkpoint_file):
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            checkpoint = json.load(f)
        skip = int(checkpoint.get('next_skip', 0))
    else:
        checkpoint = {'next_skip': 0, 'page_size': page_size, 'complete': False}
        skip = 0

    if checkpoint.get('complete'):
        print(f"{endpoint}: fetch already marked complete.")
        return

    while True:
        try:
            response = requests.get(
                url,
                params={
                    'token': legistar_api_key,
                    '$top': page_size,
                    '$skip': skip
                },
                timeout=30,
            )
        except requests.RequestException as exc:
            checkpoint['last_error'] = str(exc)
            checkpoint['last_attempted_skip'] = skip
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint, f, indent=2)
            print(f"Request failed at skip={skip}: {exc}")
            break

        if response.status_code == 200:
            data = response.json()

            if not data:
                checkpoint['complete'] = True
                checkpoint['last_error'] = None
                checkpoint['last_attempted_skip'] = skip
                with open(checkpoint_file, 'w', encoding='utf-8') as f:
                    json.dump(checkpoint, f, indent=2)
                break

            existing_data.extend(data)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, indent=2)

            skip += len(data)
            checkpoint['next_skip'] = skip
            checkpoint['page_size'] = page_size
            checkpoint['complete'] = False
            checkpoint['last_error'] = None
            checkpoint['last_attempted_skip'] = skip
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint, f, indent=2)
        else:
            checkpoint['last_error'] = f"{response.status_code}: {response.text}"
            checkpoint['last_attempted_skip'] = skip
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint, f, indent=2)
            print(f"Error: {response.status_code}, {response.text}")
            break

legistar_fetch("persons")

