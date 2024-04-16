import pika  # type: ignore
#import datetime

try:
    # RabbitMQ setup
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()

    # Declare the queue to consume
    channel.queue_declare(queue='transcript_queue')

    # Define the callback that will be called when a message is delivered
    def callback(ch, method, properties, body):
        body = body.decode('utf-8')
        print(body, end = ' ')
        #print(f"Transcript Received Time: {datetime.datetime.now().strftime('%H:%M:%S')}\n",flush = True)

    # Start consuming from the 'transcript_queue'
    channel.basic_consume(queue='transcript_queue', on_message_callback=callback, auto_ack=True)

    print('\n........Waiting for messages......\n')
    channel.start_consuming()
    
except KeyboardInterrupt:
    print("\n........Program interrupted by user........")

except Exception as e:
    print(f"Error: {e}")

finally:
    # Close the connection in the 'finally' block to ensure it happens even if an exception occurs or the user interrupts
    if connection.is_open:
        connection.close()