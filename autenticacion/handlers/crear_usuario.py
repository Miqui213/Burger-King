import json
import os
import boto3
import hashlib
import uuid
from datetime import datetime

dynamodb = boto3.resource('dynamodb')

TABLA_USUARIOS = os.environ.get('TABLA_USUARIOS')
TABLA_EMPLEADOS = os.environ.get('TABLA_EMPLEADOS')

def hash_password(password):
    """
    Crea un hash unidireccional y seguro de la contraseña usando SHA-256.
    """
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def lambda_handler(event, context):
    print(f"CrearUsuario Event INVOKED: {json.dumps(event)}")

    try:
        body = json.loads(event.get('body', '{}'))
    except Exception:
        return {
            "statusCode": 400, 
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "El cuerpo de la petición no es un JSON válido"})
        }
    
    email = body.get('email')
    password = body.get('password')
    nombre = body.get('nombre')
    codigo_secreto = body.get('codigo_secreto', '')
    
    if not email or not password or not nombre:
        return {
            "statusCode": 400, 
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Faltan datos obligatorios (email, password, nombre)"})
        }
        
    hashed_password = hash_password(password)
    timestamp = datetime.utcnow().isoformat()
    
    try:
        if codigo_secreto == "BURGER2026":
            table = dynamodb.Table(TABLA_EMPLEADOS)
            
            empleado_id = f"EMP-{uuid.uuid4().hex[:6].upper()}"
            tipo_empleado = body.get('tipo_empleado', 'COCINA').upper()
            
            item = {
                'empleado_id': empleado_id,
                'email': email,
                'nombre': nombre,
                'password': hashed_password,
                'rol': tipo_empleado,
                'createdAt': timestamp
            }
            
            table.put_item(Item=item)
            id_creado = empleado_id
            rol_final = tipo_empleado
            print(f"Empleado registrado: {email} como {rol_final}")
            
        else:
            table = dynamodb.Table(TABLA_USUARIOS)
            usuario_id = email 

            response = table.get_item(Key={'usuario_id': usuario_id})
            if 'Item' in response:
                return {
                    "statusCode": 400, 
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Este correo ya está registrado en el sistema"})
                }
                
            item = {
                'usuario_id': usuario_id,
                'nombre': nombre,
                'password': hashed_password,
                'rol': 'cliente',
                'createdAt': timestamp
            }
            
            table.put_item(Item=item)
            id_creado = usuario_id
            rol_final = 'cliente'
            print(f"Cliente registrado: {email}")

        return {
            "statusCode": 201,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": True
            },
            "body": json.dumps({
                "message": "Registro completado exitosamente",
                "id": id_creado,
                "rol": rol_final
            })
        }
        
    except Exception as e:
        print(f"Error crítico en DynamoDB: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Error interno del servidor al procesar el registro"})
        }