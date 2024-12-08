import time
from src.webhook_test import test_webhook


def main():
    sleep_time = 10
    print(f"Starting, and sleeping for {sleep_time} seconds to make sure all services are up!")
    time.sleep(sleep_time)

    # Test the webhook
    test_webhook()



if __name__ == '__main__':
    main()
