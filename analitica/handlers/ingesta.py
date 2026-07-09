import json
import boto3
import os
import csv
import io
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

# CAMBIO CLAVE: Apuntamos directamente a la tabla que tiene la data completa
tabla_pedidos = dynamodb.Table('Burger-Pedidos-dev')
bucket_ingesta = os.environ.get('BUCKET_INGESTA')

def lambda_handler(event, context):
    headers_cors = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
        "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
    }

    auth_context = event.get('requestContext', {}).get('authorizer', {})
    rol = auth_context.get('lambda', {}).get('rol', '').lower()
    
    if rol != 'admin':
        return {
            "statusCode": 403, 
            "headers": headers_cors,
            "body": json.dumps({"error": "Acceso denegado."})
        }
        
    try:
        # Extraemos de la tabla principal
        respuesta = tabla_pedidos.scan()
        registros = respuesta.get('Items', [])

        csv_buffer = io.StringIO()
        escritor_csv = csv.writer(csv_buffer)
        
        # Cabeceras exactas que espera Athena
        escritor_csv.writerow([
            'pedido_id', 'cliente', 'cocinero_id', 'createdAt', 
            'empaquetador_id', 'estado', 'items', 'origen_pedido', 
            'taskToken', 'total'
        ])
        
        for reg in registros:
            items_raw = reg.get('items', [])
            items_str = json.dumps(items_raw) if isinstance(items_raw, (list, dict)) else str(items_raw)

            escritor_csv.writerow([
                reg.get('pedido_id', 'N/A'),
                reg.get('cliente', 'Desconocido'),
                reg.get('cocinero_id', 'Desconocido'),
                reg.get('createdAt', datetime.utcnow().isoformat()),
                reg.get('empaquetador_id', 'Desconocido'),
                reg.get('estado', 'DESCONOCIDO'),
                items_str,
                reg.get('origen_pedido', 'LOCAL'), # Extraerá RAPPI_APP o LOCAL
                reg.get('taskToken', ''),
                str(reg.get('total', 0.0))         # Extraerá el monto real
            ])
            
        nombre_archivo = f"ingesta_pedidos_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Guardamos en S3
        s3.put_object(
            Bucket=bucket_ingesta,
            Key=f"datos_pedidos/{nombre_archivo}", 
            Body=csv_buffer.getvalue()
        )
        
        return {
            "statusCode": 200,
            "headers": headers_cors,
            "body": json.dumps({
                "mensaje": "Ingesta completada",
                "registros_procesados": len(registros)
            })
        }
        
    except Exception as e:
        return {
            "statusCode": 500, 
            "headers": headers_cors,
            "body": json.dumps({"error": str(e)})
        }