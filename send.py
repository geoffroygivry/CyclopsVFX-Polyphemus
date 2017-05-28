import pika
from cyc_config import cyc_config as cfg
pika_connection = cfg.RABBITMQ_URI

url = pika_connection
params = pika.URLParameters(url)
params.socket_timeout = 5
connection = pika.BlockingConnection(params)  # Connect to CloudAMQP

channel = connection.channel()
channel.queue_declare(queue='info')

channel.basic_publish(exchange='',
                      routing_key='info',
                      body='Hello World!')
print(" [x] Sent 'Hello World!'")

connection.close()
