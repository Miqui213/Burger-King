import boto3
import requests
import uuid
import os
import time
from decimal import Decimal

REGION = 'us-east-1'
BUCKET_NAME = 'burger-king-catalogo-imagenes' 
TABLE_NAME = 'Burger-Productos-dev'

s3 = boto3.client('s3', region_name=REGION)
dynamodb = boto3.resource('dynamodb', region_name=REGION)
table = dynamodb.Table(TABLE_NAME)

menu = [
    {
        "nombre": "WHOPPER Grande",
        "precio": "16.90",
        "categoria": "Whopper",
        "img_url": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=500&q=80"
    },
    {
        "nombre": "WHOPPER Cheese Grande",
        "precio": "20.90",
        "categoria": "Whopper",
        "img_url": "https://images.unsplash.com/photo-1586816001966-79b736744398?w=500&q=80"
    },
    {
        "nombre": "WHOPPER Crispy Grande",
        "precio": "21.90",
        "categoria": "Whopper",
        "img_url": "https://images.unsplash.com/photo-1594221708779-94832f4320d1?w=500&q=80"
    },
    {
        "nombre": "WHOPPER Junior",
        "precio": "14.90",
        "categoria": "Whopper",
        "img_url": "https://images.unsplash.com/photo-1605901309584-818e25960b8f?w=500&q=80"
    },

    {
        "nombre": "10 Nuggets",
        "precio": "15.90",
        "categoria": "Pollo",
        "img_url": "https://images.unsplash.com/photo-1562967914-608f82629710?w=500&q=80"
    },
    {
        "nombre": "KING DE POLLO",
        "precio": "16.90",
        "categoria": "Pollo",
        "img_url": "https://images.unsplash.com/photo-1615444812328-87979685ceea?w=500&q=80"
    },
    {
        "nombre": "Doble Chicken BBQ",
        "precio": "16.90",
        "categoria": "Pollo",
        "img_url": "https://images.unsplash.com/photo-1625869016774-3a92be237599?w=500&q=80"
    },

    {
        "nombre": "Papa Familiar",
        "precio": "9.50",
        "categoria": "Complementos",
        "img_url": "https://images.unsplash.com/photo-1576107232684-1279f390859f?w=500&q=80"
    },
    {
        "nombre": "Papa Tumbay Mediana",
        "precio": "7.90",
        "categoria": "Complementos",
        "img_url": "https://images.unsplash.com/photo-1630497370208-411ea21b8f52?w=500&q=80"
    },
    {
        "nombre": "Camote Familiar",
        "precio": "10.90",
        "categoria": "Complementos",
        "img_url": "https://images.unsplash.com/photo-1604908176997-125f25cc6f3d?w=500&q=80"
    },
    {
        "nombre": "Inca Kola Sin Azucar 500 ml",
        "precio": "4.90",
        "categoria": "Complementos",
        "img_url": "https://images.unsplash.com/photo-1622483767028-3f66f32aef97?w=500&q=80" 
    },
    {
        "nombre": "Coca-Cola Sin Azucar 500 ml",
        "precio": "4.90",
        "categoria": "Complementos",
        "img_url": "https://images.unsplash.com/photo-1554866585-cd94860874b7?w=500&q=80"
    },

    {
        "nombre": "Pie de Manzana",
        "precio": "5.50",
        "categoria": "Postres",
        "img_url": "https://images.unsplash.com/photo-1621236378699-8597faf6a176?w=500&q=80"
    },
    {
        "nombre": "Shake OREO de Chocolate",
        "precio": "14.90",
        "categoria": "Postres",
        "img_url": "https://images.unsplash.com/photo-1572490122747-3968b75cc699?w=500&q=80"
    },
    {
        "nombre": "King Fusion OREO",
        "precio": "8.50",
        "categoria": "Postres",
        "img_url": "https://images.unsplash.com/photo-1563805042-7684c8a9e9ce?w=500&q=80"
    },
    {
        "nombre": "4 Churros",
        "precio": "6.90",
        "categoria": "Postres",
        "img_url": "https://images.unsplash.com/photo-1624371414325-e2244f8fcc9c?w=500&q=80"
    },
    {
        "nombre": "Mega STACKER",
        "precio": "27.90",
        "categoria": "Contundentes",
        "img_url": "https://images.unsplash.com/photo-1594221708779-94832f4320d1?w=500&q=80"
    },
    {
        "nombre": "Bacon King",
        "precio": "30.90",
        "categoria": "Contundentes",
        "img_url": "https://images.unsplash.com/photo-1553979459-d2229ba7433b?w=500&q=80"
    },
    {
        "nombre": "Parrillera XL",
        "precio": "21.90",
        "categoria": "Contundentes",
        "img_url": "https://images.unsplash.com/photo-1605901309584-818e25960b8f?w=500&q=80"
    },
    {
        "nombre": "Philly Cheese",
        "precio": "27.90",
        "categoria": "Contundentes",
        "img_url": "https://images.unsplash.com/photo-1586816001966-79b736744398?w=500&q=80"
    },

    {
        "nombre": "XT Clásica",
        "precio": "22.90",
        "categoria": "XT Premium",
        "img_url": "https://images.unsplash.com/photo-1550547660-d9450f859349?w=500&q=80"
    },
    {
        "nombre": "XT Steakhouse",
        "precio": "27.90",
        "categoria": "XT Premium",
        "img_url": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=500&q=80"
    },

    {
        "nombre": "WHOPPER Vegetal",
        "precio": "18.90",
        "categoria": "Whopper Vegetal",
        "img_url": "https://images.unsplash.com/photo-1520072959219-c595dc870360?w=500&q=80"
    },
    {
        "nombre": "WHOPPER Vegetal con Queso",
        "precio": "21.90",
        "categoria": "Whopper Vegetal",
        "img_url": "https://images.unsplash.com/photo-1586190848861-99aa4a171e90?w=500&q=80"
    }
]

print("Iniciando extracción y carga del catálogo...")

cabeceras_navegador = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
}

for item in menu:
    producto_id = f"PROD-{str(uuid.uuid4())[:8].upper()}"
    nombre_archivo = f"{producto_id}.jpg"
    
    print(f"Descargando imagen para: {item['nombre']}...")
    
    try:
        respuesta_img = requests.get(item['img_url'], stream=True, headers=cabeceras_navegador)
        
        if respuesta_img.status_code == 200:
            s3.upload_fileobj(
                respuesta_img.raw, 
                BUCKET_NAME, 
                nombre_archivo,
                ExtraArgs={'ContentType': 'image/jpeg'}
            )
            
            s3_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{nombre_archivo}"
            
            producto_db = {
                'local_id': 'STORE-001',
                'producto_id': producto_id,
                'nombre': item['nombre'],
                'precio': Decimal(item['precio']),
                'categoria': item['categoria'],
                'imagen_url': s3_url
            }
            
            table.put_item(Item=producto_db)
            print(f"Éxito: {item['nombre']} inyectado (DynamoDB + S3)")
        else:
            print(f"Fallo de red. El servidor devolvió error HTTP: {respuesta_img.status_code}")
            
    except Exception as e:
        print(f"Error interno con {item['nombre']}: {str(e)}")

    time.sleep(1)

print("¡Proceso finalizado!")