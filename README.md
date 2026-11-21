# VisionLab — detección de objetos en tiempo real

Aplicación académica en Django para capturar video desde la cámara del navegador, detectar **celulares** con YOLO y OpenCV, dibujar las cajas sobre el fotograma y guardar en PostgreSQL el resumen de cada sesión.

## Funcionalidades

- Captura de cámara desde el navegador con permiso explícito del usuario.
- Envío de fotogramas JPEG de baja resolución al servidor y detección periódica.
- Detección de celulares (clase `cell phone`, ID 67 del conjunto COCO); muestra cajas y conteos por fotograma.
- Umbral de confianza del 65 % por defecto, configurable con `YOLO_PHONE_CONFIDENCE` en `.env` (valor entre 0 y 1). Un umbral más alto descarta detecciones dudosas y puede pasar por alto celulares pequeños o poco visibles.
- Registro en PostgreSQL de duración, fotogramas y conteo acumulado por clase.
- Límites de tamaño y resolución para los fotogramas enviados.

El modelo preentrenado `yolo26n.pt` incluye la clase `cell phone` del conjunto COCO. Para usar pesos de detección personalizados, define `YOLO_MODEL_PATH` con la ruta al archivo `.pt`. VisionLab identifica la clase por nombre y admite `cell phone`, `mobile phone`, `smartphone`, `phone`, `celular`, `telefono` y `teléfono`.

## Requisitos

- Python 3.10 o superior.
- Docker Desktop o Docker Engine para ejecutar PostgreSQL localmente.
- Navegador con acceso a cámara. En localhost se permite cámara sin HTTPS.
- Conexión a Internet la primera vez para descargar los pesos `yolo26n.pt`, salvo que ya tengas el archivo.

## Inicio en Windows

Desde PowerShell, en la carpeta del proyecto:

```powershell
Copy-Item .env.example .env
docker compose up -d db
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
py manage.py migrate
py manage.py runserver
```

Abre `http://127.0.0.1:8000/`, permite el acceso a la cámara y pulsa **Iniciar detección**. La primera inferencia puede tardar mientras el modelo se descarga y carga.

Para detener PostgreSQL al terminar:

```powershell
docker compose down
```

Los datos de PostgreSQL permanecen en el volumen `visionlab_postgres`. Para eliminarlos también, ejecuta `docker compose down -v`.

## Variables de entorno

El archivo `.env.example` contiene los valores locales de PostgreSQL, Django y el modelo. Antes de desplegar, cambia `DJANGO_SECRET_KEY` y `POSTGRES_PASSWORD`, establece `DJANGO_DEBUG=0` y configura `DJANGO_ALLOWED_HOSTS` con el dominio del servidor.

## Estructura

```text
visionlab/                 configuración Django
processor/                 API, detección y registro de sesiones
processor/migrations/      esquema inicial de PostgreSQL
templates/processor/       interfaz de cámara y resultados
static/css/                estilos adaptables
docker-compose.yml         PostgreSQL para desarrollo local
```

## Consideraciones

- La cámara se captura en el navegador y no se guarda como video.
- Los fotogramas se transmiten al servidor para la inferencia; evita usar el sistema con imágenes de personas sin consentimiento.
- Las detecciones de un modelo preentrenado pueden equivocarse y dependen de iluminación, enfoque y ángulo.
- El proyecto no incluye un conjunto de datos ni entrenamiento personalizado para cascos o mascarillas.
- `runserver` sirve solo para desarrollo; para desplegar se debe configurar un servidor WSGI/ASGI, HTTPS, archivos estáticos y credenciales seguras.

## Referencias técnicas

- [Documentación oficial de predicción de Ultralytics YOLO](https://docs.ultralytics.com/modes/predict/)
- [Django: soporte de bases de datos](https://docs.djangoproject.com/en/5.2/ref/databases/)
