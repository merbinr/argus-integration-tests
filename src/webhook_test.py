import json
import os
import sys

import requests

def test_webhook():
    """
    Test the webhook by sending a POST request to the catcher service.
    """
    
    headers = {
        "Content-Type" : "application/json",
        "X-Amz-Firehose-Access-Key" : os.getenv('CATCHER_HTTP_WEBHOOK_TOKEN'),
    }
    data = None
    with open("webhook_data.json", "r") as f:
        data = json.load(f)

    url = "http://catcher:8080/aws/logs/vpc/webhook"
    res = requests.post(url=url, headers=headers, json=data)
    if res.status_code == 200:
        print(f"Successfully sent the webhook! status_code: 200, response: {res.text}")
    else:
        print(f"Error on sending the webhook! status_code: {res.status_code}, response: {res.text}")
        sys.exit(1)
