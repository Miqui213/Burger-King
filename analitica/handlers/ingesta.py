import json
import boto3
import os
import csv
import io
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

tabla_historial = dynamodb.Table(os.environ.get('TABLA_HISTORIAL_ESTADOS'))
bucket_ingesta = os.environ.get('BUCKET_INGESTA')

def lambda_handler(event, context):
    auth_context = event.get('requestContext', {}).get('authorizer', {})
    lambda_data = auth_context.get('lambda', {})
    rol = lambda_data.get('rol', '').lower()
    
    if rol != 'admin':
        return {
            "statusCode": 403, 
            "body": json.dumps({"error": "Acceso denegado. Se requieren privilegios de Administrador para el Data Lake."})
        }
        
    try:
        respuesta = tabla_historial.scan()
        registros = respuesta.get('Items', [])

        csv_buffer = io.StringIO()
        escritor_csv = csv.writer(csv_buffer)
        # Cabeceras
        escritor_csv.writerow(['pedido_id', 'estado', 'total', 'origen', 'fecha'])
        
        for reg in registros:
            escritor_csv.writerow([
                reg.get('pedido_id', ''),
                reg.get('estado', ''),
                str(reg.get('total', 0)),
                reg.get('logistica_canal', 'web'),
                reg.get('createdAt', datetime.utcnow().isoformat())
            ])
            
        nombre_archivo = f"ingesta_pedidos_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        
        s3.put_object(
            Bucket=bucket_ingesta,
            Key=f"raw-data/{nombre_archivo}",
            Body=csv_buffer.getvalue()
        )
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "mensaje": "Pipeline de ingesta ejecutado con éxito",
                "registros_procesados": len(registros),
                "archivo_s3": nombre_archivo
            })
        }
        
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}