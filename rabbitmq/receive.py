#!/usr/bin/env python2.7

import logging

import pika


AMQP_URL = 'amqp://guest:guest@pe-amqp-sing-01v:5672/%2f'

CONNECTION = None
CHANNEL = None

QUEUE = ''
EXCHANGE = 'my.direct'
ROUTING_KEY = None


def get():
    global CONNECTION, CHANNEL, QUEUE, EXCHANGE, ROUTING_KEY

    open_connection()

    # Create a queue for ourselves, and grab the queue name if necessary.
    reply = CHANNEL.queue_declare(QUEUE)
    if not QUEUE:
        QUEUE = reply.method.queue

    # Create a binding.
    CHANNEL.queue_bind(QUEUE, EXCHANGE, ROUTING_KEY)

    # Create another binding with a common key.
    #CHANNEL.queue_bind(QUEUE, 'my.topic', 'common')

    while True:
        # Pausing so we can publish some messages for our queue.
        raw_input('Press ENTER to get a message')

        # Try and get a message.
        method_frame, properties, body = CHANNEL.basic_get(QUEUE)
        if method_frame:
            print "Method Frame: {0}".format(method_frame)
            print "Properties: {0}".format(properties)
            print "Body: {0}".format(body)

            # Acknowledge the received message.
            CHANNEL.basic_ack(method_frame.delivery_tag)
        else:
            print 'No messages available'
            break

    # Delete the queue once we're done.
    CHANNEL.queue_delete(QUEUE)

    close_connection()


def consume():
    global CONNECTION, CHANNEL, QUEUE, EXCHANGE, ROUTING_KEY

    open_connection()

    # Create a queue for ourselves, and grab the queue name if necessary.
    reply = CHANNEL.queue_declare(QUEUE)
    if not QUEUE:
        QUEUE = reply.method.queue

    # Create a binding.
    CHANNEL.queue_bind(QUEUE, EXCHANGE, ROUTING_KEY)

    # Create another binding with a common key.
    #CHANNEL.queue_bind(QUEUE, 'my.topic', 'common')

    # Receive messages until the sentinel message.
    print 'Ready to receive messages'
    for method_frame, properties, body in CHANNEL.consume(QUEUE):
        print "Method Frame: {0}".format(method_frame)
        print "Properties: {0}".format(properties)
        print "Body: {0}".format(body)
        print '-----'

        # Acknowledge the received message.
        CHANNEL.basic_ack(method_frame.delivery_tag)

        # Sentinel message to break out of the loop.
        if body == 'quit!':
            CHANNEL.cancel()
            break

    # Delete the queue once we're done.
    CHANNEL.queue_delete(QUEUE)

    close_connection()


def open_connection():
    global CONNECTION, CHANNEL
    CONNECTION = pika.BlockingConnection(pika.URLParameters(AMQP_URL))
    CHANNEL = CONNECTION.channel()


def close_connection():
    global CONNECTION, CHANNEL
    CONNECTION.close()
    CHANNEL = None
    CONNECTION = None


def main():
    # Suppress most log messages from other libraries.
    base = logging.getLogger()
    base.setLevel(logging.ERROR)

    # Set up some legible logging.
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname).1s %(asctime)s] %(message)s",
                                  datefmt="%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Action! Pick 1 of either: get() or consume()
    get()


if __name__ == '__main__':
    main()
