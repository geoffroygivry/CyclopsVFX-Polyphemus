

import argparse
import logging

import pika


AMQP_URL = 'amqp://guest:guest@pe-amqp-sing-01v:5672/%2f'


def publish(exchange, routing_key, message):
    logger = logging.getLogger(__name__)

    # Create a connection to RabbitMQ.
    connection = pika.BlockingConnection(pika.URLParameters(AMQP_URL))
    logger.info("Created connection with {0}".format(AMQP_URL))

    # 1 connection can have many channels, eg. 1 for publishing and another for
    # receiving (which is recommended).
    channel = connection.channel()
    logger.info('Opened channel for publishing')

    # Publish the message.
    channel.basic_publish(exchange, routing_key, message)
    logger.info("Published '{message}' to exchange '{exchange}' "
                "with routing key '{routing_key}'".format(
                    exchange=exchange, routing_key=routing_key, message=message))

    # Close the connection.
    connection.close()
    logger.info('Closed connection')


def parse_arguments():
    parser = argparse.ArgumentParser(description='Publish messages to RabbitMQ')
    parser.add_argument('exchange')
    parser.add_argument('routing_key')
    parser.add_argument('message')
    return parser.parse_args()


def main():
    # Suppress most log messages from other libraries.
    base = logging.getLogger()
    base.setLevel(logging.ERROR)

    # Set up some legible logging for ourselves.
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname).1s %(asctime)s] %(message)s",
                                  datefmt="%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    arguments = parse_arguments()
    publish(**(vars(arguments)))


if __name__ == '__main__':
    main()
