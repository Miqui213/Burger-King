import json
import os
import boto3
import hashlib
import jwt
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb')

TABLA_USUARIOS = os.environ.get('TABLA_USUARIOS')
TABLA_EMPLEADOS = os.environ.get('TABLA_EMPLEADOS')
TABLA_TOKENS = os.environ.get('TABLA_TOKENS')

JWT_SECRET = os.environ.get('JWT_SECRET', 'burger-king-secret-2026')

def hash_password(password):
    """Aplica el mismo hash SHA-256 usado en el registro para comparar"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def lambda_handler(event, context):
    print(f"LoginUsuario Event INVOKED: {json.dumps(event)}")
    
    try:
        body = json.loads(event.get('body', '{}'))
    except Exception:
        return {
            "statusCode": 400, 
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "JSON inválido"})
        }
        
    username = body.get('username') or body.get('email')
    password = body.get('password')
    
    if not username or not password:
        return {
            "statusCode": 400, 
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Faltan credenciales (email/username o password)"})
        }
        
    hashed_password = hash_password(password)

    user_data = None
    es_empleado = username.upper().startswith('EMP-')
    
    try:
        if es_empleado:
            table = dynamodb.Table(TABLA_EMPLEADOS)
            response = table.get_item(Key={'empleado_id': username.upper()})
            user_data = response.get('Item')
        else:
            table = dynamodb.Table(TABLA_USUARIOS)
            response = table.get_item(Key={'usuario_id': username})
            user_data = response.get('Item')
            
        if not user_data:
            return {
                "statusCode": 401, 
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Usuario no encontrado"})
            }
            
        if user_data.get('password') != hashed_password:
            return {
                "statusCode": 401, 
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Contraseña incorrecta"})
            }
            
        rol_usuario = user_data.get('rol', 'cliente')
        payload = {
            'sub': username,
            'rol': rol_usuario,
            'nombre': user_data.get('nombre'),
            # El token expira en 8 horas
            'exp': datetime.utcnow() + timedelta(hours=8)
        }
        
        token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')
        
        tokens_table = dynamodb.Table(TABLA_TOKENS)
        tokens_table.put_item(Item={
            'token_id': token,
            'usuario_id': username,
            'rol': rol_usuario,
            'createdAt': datetime.utcnow().isoformat()
        })
        
        print(f"Login exitoso: {username} ({rol_usuario})")
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": True
            },
            "body": json.dumps({
                "message": "Login exitoso",
                "token": token,
                "user": {
                    "id": username,
                    "nombre": user_data.get('nombre'),
                    "rol": rol_usuario
                }
            })
        }
        
    except Exception as e:
        print(f"Error interno en el proceso de login: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Error interno del servidor al procesar el login"})
        }