import json
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
RABBITMQ_HOST = "localhost"
QUEUE_NAME = "logs"
RABBITMQ_USERNAME = "rabbit"
RABBITMQ_PASSWORD = "test"
credentials = pika.PlainCredentials(RABBITMQ_USERNAME, RABBITMQ_PASSWORD)


# Flush redis before each test
def flush_redis():
    r = redis.Redis(host='localhost', port=6379, db=0)
    r.flushall()


@pytest.fixture(scope="module")
def rabbitmq_connection():
    """Fixture to set up and tear down RabbitMQ connection."""
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST, 
                                                                   credentials=credentials))
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)

    yield channel  # Provide the channel to tests
    channel.queue_delete(queue=QUEUE_NAME)  # Clean up the queue
    connection.close()

def test_recive_data_from_deduplicator(rabbitmq_connection):
    """
    Send sample valid data to webhook and recieve it from output queue of deduplicator.
    """
    channel : BlockingChannel = rabbitmq_connection
    expected_message = json.loads(str('{"Cloud":"aws","Type":"vpc","Version":2,"AccountID":"783023365380","InterfaceID":"eni-00fe26c107412e170","SourceIP":"67.220.247.194","DestinationIP":"172.31.32.151","DestinationPort":443,"SourcePort":49782,"Protocol":6,"Packets":6,"Bytes":306,"StartTime":1732010760,"EndTime":1732010788,"Action":"ACCEPT","LogStatus":"OK"}'))

    # Purge the queue before sending the data
    channel.queue_purge(queue=QUEUE_NAME)
    # Purge the redis before sending the data
    flush_redis()

    data = dict(SAMPLE_WEBHOOK_DATA)
    data['records'][0]['data'] = "eyJtZXNzYWdlIjoiMiA3ODMwMjMzNjUzODAgZW5pLTAwZmUyNmMxMDc0MTJlMTcwIDY3LjIyMC4yNDcuMTk0IDE3Mi4zMS4zMi4xNTEgNDQzIDQ5NzgyIDYgNiAzMDYgMTczMjAxMDc2MCAxNzMyMDEwNzg4IEFDQ0VQVCBPSyJ9Cg=="


    res = requests.post(url=WEBHOOK_URL, headers=WEBHOOK_HEADERS, json=data)
    assert res.status_code == 200
    assert res.json() == {"message": "success"}

    messages = []

    def callback(ch, method, properties, body):
        messages.append(body)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback, auto_ack=False)
    
    tries = 0

    while not messages:
        tries += 1
        channel.connection.process_data_events(time_limit=1)

        if tries > 10:
            raise Exception("No messages received from deduplicator")
        time.sleep(1) # Wait for the message to be processed
        
        
    
    for message in messages:
        print("Messages starting\n")
        print(message)
        print("Messages Ending\n")

    assert expected_message == json.loads((messages[0].decode()))
    
