import json
import os
import boto3
from datetime import datetime

events = boto3.client('events')
EVENT_BUS_NAME = os.environ.get('EVENT_BUS_NAME', 'default')

def handler(event, context):
    print(f"TriggerEvent INVOKED: {json.dumps(event)}")
    
    try:
        body = json.loads(event.get('body', '{}'))
    except:
        body = {}
        
    event_type = body.get('type')
    source = body.get('source', 'burgerking.api')
    detail = body.get('detail', {})
    
    if not event_type:
        print("Error: Falta el campo 'type' en el body")
        return {
            "statusCode": 400, 
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Missing 'type'"})
        }
        
    detail['at'] = datetime.utcnow().isoformat()
    
    try:
        response = events.put_events(
            Entries=[
                {
                    'Source': source,
                    'DetailType': event_type,
                    'Detail': json.dumps(detail),
                    'EventBusName': EVENT_BUS_NAME
                }
            ]
        )
        print(f"Evento publicado exitosamente: {event_type} desde {source}")
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "message": "Event published",
                "response": response
            })
        }
    except Exception as e:
        print(f"Error al publicar evento en EventBridge: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }