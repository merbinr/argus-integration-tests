import json
import os
import sys

import requests

HEADERS = {
        "Content-Type" : "application/json",
        "X-Amz-Firehose-Access-Key" : "test",
    }

SAMPLE_DATA =     data = {
        "requestId": "9626f8bb-3247-4c0f-8b9d-54d4a2220ecd",
        "timestamp": 1732010934108,
        "records" : [
            {
            "data": "eyJtZXNzYWdlIjoiMiA3ODMwMjMzNjUzODAgZW5pLTAwZmUyNmMxMDc0MTJlMTcwIDQ0LjIxNy4yNTAuMjIgMTcyLjMxLjMyLjE1MSA0NDMgNTk2MzYgNiA2IDUyNCAxNzMyMDEwNzYwIDE3MzIwMTA3ODggQUNDRVBUIE9LIn0K"
            }
        ]
    }
WEBHOOK_URL = "http://127.0.0.1:8080/aws/logs/vpc/webhook"

def test_webhook_data_with_correct_schema():
    """
    Test the webhook by sending a valid POST request to the catcher service.
    Server should respond with 200 OK.
    """
    expected_status_code = 200
    expected_json_body = {"message": "success"}

    res = requests.post(url=WEBHOOK_URL, headers=HEADERS, json=data)
    assert res.status_code == expected_status_code
    assert res.json() == expected_json_body


def test_webhook_badrequest_when_schema_invalid():
    """
    Test the webhook by sending a POST request to the catcher service with invalid schema.
    Server should respond with 400 bad request.
    """
    expected_status_code = 400
    expected_json_body = {"error": "bad request"}

    data = dict(SAMPLE_DATA)
    del data["records"]
    
    res = requests.post(url=WEBHOOK_URL, headers=HEADERS, json=data)
    assert res.status_code == expected_status_code
    assert res.json() == expected_json_body


def test_webhook_data_with_empty_records():
    """
    Test the webhook by sending a POST request to the catcher service with empty records.
    """
    expected_status_code = 200
    expected_json_body = {"message": "success"}

    data = dict(SAMPLE_DATA)
    data["records"] = []
    
    res = requests.post(url=WEBHOOK_URL, headers=HEADERS, json=data)
    assert res.status_code == expected_status_code
    assert res.json() == expected_json_body


def test_webhook_with_invalid_auth_token():
    """
    Test the webhook by sending a POST request to the catcher service with invalid auth token.
    Server should respond with 401 unauthorized.
    """
    expected_status_code = 401
    expected_json_body = {"error": "unauthorized"}

    headers = dict(HEADERS)
    headers["X-Amz-Firehose-Access-Key"] = "invalid"

    res = requests.post(url=WEBHOOK_URL, headers=headers, json=SAMPLE_DATA)

    assert res.status_code == expected_status_code
    assert res.json() == expected_json_body


def test_webhook_with_invalid_base64_data_as_records():
    """
    Test the webhook by sending a POST request to the catcher service with invalid base64 data.
    Server should respond with 422 unprocessable entity.
    """
    expected_status_code = 422
    expected_json_body = {"error": "unprocessable entity"}

    data = dict(SAMPLE_DATA)
    data["records"][0]["data"] = "invalid_base64_data"
    
    res = requests.post(url=WEBHOOK_URL, headers=HEADERS, json=data)
    assert res.status_code == expected_status_code
    assert res.json() == expected_json_body
