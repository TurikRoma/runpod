import os
import requests
import runpod

LOCAL_URL = "http://127.0.0.1:8000"

def handler(job):
    job_input = job.get('input', {})
    http_method = job_input.get('http_method', 'GET').upper()
    path = job_input.get('path', '/')

    print(f"Received job: Method={http_method}, Path={path}")

    try:
        response = requests.request(
            http_method,
            f"{LOCAL_URL}{path}",
            headers=job_input.get('headers', {}),
            json=job_input.get('body', None),
            timeout=300
        )
        response.raise_for_status()
        print(f"Request to local server successful, status: {response.status_code}")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error requesting local server: {e}")
        return {"error": f"Failed to request local server: {e}"}
    except Exception as e:
        print(f"An unexpected error occurred in handler: {e}")
        return {"error": f"An unexpected error occurred: {e}"}

runpod.serverless.start({"handler": handler})