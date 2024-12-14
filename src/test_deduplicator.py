import json
import os
import time
import requests
import pytest
import pika
import redis
from pika.channel import Channel as BlockingChannel

# Webhook setup and arguments
WEBHOOK_URL = "http://127.0.0.1:8080/aws/logs/vpc/webhook"
WEBHOOK_HEADERS = {
        "Content-Type" : "application/json",
        "X-Amz-Firehose-Access-Key" : "test",
}
SAMPLE_WEBHOOK_DATA = {
        "requestId": "9626f8bb-3247-4c0f-8b9d-54d4a2220ecd",
        "timestamp": 1732010934108,
        "records" : [
            {
            "data": "eyJtZXNzYWdlIjoiMiA3ODMwMjMzNjUzODAgZW5pLTAwZmUyNmMxMDc0MTJlMTcwIDQ0LjIxNy4yNTAuMjIgMTcyLjMxLjMyLjE1MSA0NDMgNTk2MzYgNiA2IDUyNCAxNzMyMDEwNzYwIDE3MzIwMTA3ODggQUNDRVBUIE9LIn0K"
            }
        ]
    }

# RabbitMQ setup and arguments (Deduplicator output queue)
OUTGOING_RABBITMQ_HOST = "localhost"
QUEUE_NAME = "logs"
RABBITMQ_USERNAME = "rabbit"
RABBITMQ_PASSWORD = "test"
credentials = pika.PlainCredentials(RABBITMQ_USERNAME, RABBITMQ_PASSWORD)

REDIS_HOST = "localhost"


# Flush redis before each test
def flush_redis():
    redis_client = redis.StrictRedis(host=REDIS_HOST, port=6379, db=0)
    redis_client.flushall()


@pytest.fixture(scope="module")
def rabbitmq_connection():
    """Fixture to set up and tear down RabbitMQ connection."""
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=OUTGOING_RABBITMQ_HOST, 
                                                                   credentials=credentials))
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)

    yield channel  # Provide the channel to tests


def test_recive_data_from_deduplicator(rabbitmq_connection):
    """
    Send sample valid data to webhook and recieve it from output queue of deduplicator.
    """
    time.sleep(1)
    channel : BlockingChannel = rabbitmq_connection

    expected_message = json.loads(str('{"Cloud":"aws","Type":"vpc","Version":2,"AccountID":"783023365380","InterfaceID":"eni-00fe26c107412e170","SourceIP":"67.220.247.194","DestinationIP":"172.31.32.151","DestinationPort":443,"SourcePort":49782,"Protocol":6,"Packets":6,"Bytes":306,"StartTime":1732010760,"EndTime":1732010788,"Action":"ACCEPT","LogStatus":"OK"}'))

    # Purge the queue before sending the data
    channel.queue_purge(queue=QUEUE_NAME)
    # Purge the redis before sending the data
    flush_redis()
    time.sleep(1)

    data = dict(SAMPLE_WEBHOOK_DATA)
    data['records'][0]['data'] = "eyJtZXNzYWdlIjoiMiA3ODMwMjMzNjUzODAgZW5pLTAwZmUyNmMxMDc0MTJlMTcwIDY3LjIyMC4yNDcuMTk0IDE3Mi4zMS4zMi4xNTEgNDQzIDQ5NzgyIDYgNiAzMDYgMTczMjAxMDc2MCAxNzMyMDEwNzg4IEFDQ0VQVCBPSyJ9Cg=="


    res = requests.post(url=WEBHOOK_URL, headers=WEBHOOK_HEADERS, json=data)
    assert res.status_code == 200
    assert res.json() == {"message": "success"}

    # For ensure deduplicator has processed the data
    time.sleep(2)
    messages = []

    method_frame, header_frame, body = channel.basic_get(queue=QUEUE_NAME, auto_ack=True)
    if method_frame:
        messages.append(body.decode())
    else:
        Exception("No more messages available in the queue.")


    assert expected_message == json.loads(body.decode())
    assert len(messages) == 1

def test_able_to_remove_duplicate_entries(rabbitmq_connection):
    """
    Send sample valid data to webhook and recieve it from output queue of deduplicator.
    """
    time.sleep(1)
    channel : BlockingChannel = rabbitmq_connection

    # Purge the queue before sending the data
    channel.queue_purge(queue=QUEUE_NAME)
    # Purge the redis before sending the data
    flush_redis()
    time.sleep(1)


    data = dict(SAMPLE_WEBHOOK_DATA)
    records_data = [
        {
            "data" :  "eyJtZXNzYWdlIjoiMiA3ODMwMjMzNjUzODAgZW5pLTAwZmUyNmMxMDc0MTJlMTcwIDY3LjIyMC4yNDcuMTk0IDE3Mi4zMS4zMi4xNTEgNDQzIDQ5NzgyIDYgNiAzMDYgMTczMjAxMDc2MCAxNzMyMDEwNzg4IEFDQ0VQVCBPSyJ9Cg=="
        },
        {
            "data" :  "eyJtZXNzYWdlIjoiMiA3ODMwMjMzNjUzODAgZW5pLTAwZmUyNmMxMDc0MTJlMTcwIDY3LjIyMC4yNDcuMTk0IDE3Mi4zMS4zMi4xNTEgNDQzIDQ5NzgyIDYgNiAzMDYgMTczMjAxMDc2MCAxNzMyMDEwNzg4IEFDQ0VQVCBPSyJ9Cg=="
        }
    ]
    data['records'] = records_data



    res = requests.post(url=WEBHOOK_URL, headers=WEBHOOK_HEADERS, json=data)
    assert res.status_code == 200
    assert res.json() == {"message": "success"}

    messages = []

    # For ensure deduplicator has processed the data
    time.sleep(2)

    for _ in range(2):
        method_frame, header_frame, body = channel.basic_get(queue=QUEUE_NAME, auto_ack=True)
        if method_frame:
            messages.append(body.decode())
        else:
            print("No more messages available in the queue.")
            break
    assert len(messages) == 1


def test_able_to_remove_duplicate_entries_sent_in_different_webhook_calls(rabbitmq_connection):
    """
    Send sample valid data to webhook and recieve it from output queue of deduplicator.
    """
    time.sleep(1)
    channel : BlockingChannel = rabbitmq_connection

    # Purge the queue before sending the data
    channel.queue_purge(queue=QUEUE_NAME)
    # Purge the redis before sending the data
    flush_redis()
    time.sleep(1)


    data = dict(SAMPLE_WEBHOOK_DATA)
    records_data = [
        {
            "data" :  "eyJtZXNzYWdlIjoiMiA3ODMwMjMzNjUzODAgZW5pLTAwZmUyNmMxMDc0MTJlMTcwIDY3LjIyMC4yNDcuMTk0IDE3Mi4zMS4zMi4xNTEgNDQzIDQ5NzgyIDYgNiAzMDYgMTczMjAxMDc2MCAxNzMyMDEwNzg4IEFDQ0VQVCBPSyJ9Cg=="
        }
    ]
    data['records'] = records_data

    # First webhook call
    res = requests.post(url=WEBHOOK_URL, headers=WEBHOOK_HEADERS, json=data)
    assert res.status_code == 200
    assert res.json() == {"message": "success"}

    time.sleep(0.1)
    # Second webhook call
    res = requests.post(url=WEBHOOK_URL, headers=WEBHOOK_HEADERS, json=data)
    assert res.status_code == 200
    assert res.json() == {"message": "success"}

    messages = []

    # For ensure deduplicator has processed the data
    time.sleep(2)

    for _ in range(2):
        method_frame, header_frame, body = channel.basic_get(queue=QUEUE_NAME, auto_ack=True)
        if method_frame:
            messages.append(body.decode())
        else:
            print("No more messages available in the queue.")
            break
    assert len(messages) == 1


def test_not_remove_non_duplicate_entries(rabbitmq_connection):
    """
    Send sample valid data to webhook and recieve it from output queue of deduplicator.
    """
    time.sleep(1)
    channel : BlockingChannel = rabbitmq_connection

    # Purge the queue before sending the data
    channel.queue_purge(queue=QUEUE_NAME)
    # Purge the redis before sending the data
    flush_redis()
    time.sleep(1)

    data = dict(SAMPLE_WEBHOOK_DATA)
    records_data = [
        {
            "data" :  "eyJtZXNzYWdlIjoiMiA3ODMwMjMzNjUzODAgZW5pLTAwZmUyNmMxMDc0MTJlMTcwIDY3LjIyMC4yNDcuMTk0IDE3Mi4zMS4zMi4xNTEgNDQzIDQ5NzgyIDYgNiAzMDYgMTczMjAxMDc2MCAxNzMyMDEwNzg4IEFDQ0VQVCBPSyJ9Cg=="
        }
    ]
    data['records'] = records_data


    # First webhook call
    res = requests.post(url=WEBHOOK_URL, headers=WEBHOOK_HEADERS, json=data)
    assert res.status_code == 200
    assert res.json() == {"message": "success"}


    # Second webhook call
    records_data = [
        {
            "data" :  "eyJtZXNzYWdlIjoiMiA3ODMwMjMzNjUzODAgZW5pLTAwZmUyNmMxMDc0MTJlMTcwIDY4LjIyMC4yNDcuMTk0IDE3My4zMS4zMi4xNTEgNDQ0IDQ5NzgyIDYgNiAzMDYgMTczMjAxMDc2MCAxNzMyMDEwNzg4IEFDQ0VQVCBPSyJ9Cg=="
        }
    ]
    data['records'] = records_data
    res = requests.post(url=WEBHOOK_URL, headers=WEBHOOK_HEADERS, json=data)
    assert res.status_code == 200
    assert res.json() == {"message": "success"}

    messages = []

    # For ensure deduplicator has processed the data
    time.sleep(2)

    for _ in range(2):
        method_frame, header_frame, body = channel.basic_get(queue=QUEUE_NAME, auto_ack=True)
        if method_frame:
            messages.append(body.decode())
        else:
            print("No more messages available in the queue.")
            break
    assert len(messages) == 2
