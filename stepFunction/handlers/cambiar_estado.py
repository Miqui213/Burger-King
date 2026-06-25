import json
import os
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
stepfunctions = boto3.client('stepfunctions')
TABLE_HISTORIAL_ESTADOS = os.environ['TABLE_HISTORIAL_ESTADOS']

def decimal_to_number(obj):
    """Convert Decimal objects to int or float for JSON serialization"""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_number(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_number(i) for i in obj]
    return obj

def handler(event, context):
    print("=" * 60)
    print("🔔 CambiarEstado Lambda INVOKED")
    print("=" * 60)
    print(f"Full Event: {json.dumps(event, indent=2)}")
    
    detail = event.get('detail', {})
    detail_type = event.get('detail-type')
    source = event.get('source')
    order_id = detail.get('order_id')
    
    print(f"Source: {source}")
    print(f"Detail-Type: {detail_type}")
    print(f"Order ID: {order_id}")
    
    if not order_id:
        print("ERROR: No order_id in event")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'No order_id in event'})
        }
    
    table = dynamodb.Table(TABLE_HISTORIAL_ESTADOS)
    
    response = table.query(
        KeyConditionExpression=Key('pedido_id').eq(order_id),
        ScanIndexForward=False,
        Limit=1
    )
    
    items = response.get('Items', [])
    if not items:
        print(f"No history found for order {order_id}")
        return
    
    latest_item = items[0]
    task_token = latest_item.get('taskToken')
    current_estado = latest_item.get('estado')
    
    if not task_token:
        print(f"No task token found in latest state ({current_estado}) for order {order_id}")
        return
    
    print(f"Found token for order {order_id} in estado {current_estado}. Triggering SF...")

    stored_data = latest_item.get('details') or {}
    retry_count = stored_data.get('retry_count', 0) if isinstance(stored_data, dict) else 0
    local_id = stored_data.get('local_id') if isinstance(stored_data, dict) else None
    
    output_payload = {
        "order_id": order_id,
        "event": detail_type,
        "status": detail.get('status', 'ACEPTADO'),
        "retry_count": decimal_to_number(retry_count),
        "empleado_id": detail.get('empleado_id', 'UNKNOWN'),
        "details": decimal_to_number(detail)
    }
    
    if local_id:
        output_payload['local_id'] = local_id
        print(f"📍 Passing local_id: {local_id}")
    
    try:
        print(f"Sending task success with payload: {json.dumps(output_payload, indent=2)}")
        stepfunctions.send_task_success(
            taskToken=task_token,
            output=json.dumps(output_payload)
        )
        print("Successfully sent task success to Step Function")
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Task success sent', 'order_id': order_id})
        }
    except Exception as e:
        print(f"Error sending task success: {e}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e), 'order_id': order_id})
        }