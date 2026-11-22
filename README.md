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

- Python 3.12 de 64 bits, versión probada con las dependencias del proyecto.
- PostgreSQL. Puedes usar Docker Compose con Docker Desktop o una instalación local de PostgreSQL.
- Navegador con acceso a cámara. En localhost se permite cámara sin HTTPS.
- Conexión a Internet para instalar las dependencias y descargar los pesos `yolo26n.pt` en la primera inferencia. Si ya tienes los pesos, puedes indicar su ubicación con `YOLO_MODEL_PATH`.

## Inicio en Windows

Desde PowerShell, abre la carpeta del proyecto, donde están `manage.py` y `requirements.txt`. Conserva tu archivo `.env` si ya configuraste una base de datos.

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

`requirements.txt` fija las versiones de las dependencias principales y el par compatible PyTorch/torchvision. La instalación de PyTorch puede tardar debido al tamaño de la descarga.

### Configurar PostgreSQL

**Con Docker Compose.** Abre Docker Desktop. Conserva `POSTGRES_HOST=127.0.0.1` en `.env`. Si el puerto `5432` ya está en uso, configura un puerto libre, por ejemplo `POSTGRES_PORT=55432`. Compose usa ese valor para publicar el puerto y Django para conectarse. Inicia el contenedor y espera a que esté listo.

```powershell
docker compose up -d --wait db
```

Si ya existe un volumen de PostgreSQL, usa las credenciales con las que se creó. Editar `.env` por sí solo no cambia las contraseñas de un volumen existente.

**Con PostgreSQL instalado en Windows.** Asegúrate de que el servicio esté iniciado. Desde pgAdmin o `psql`, crea una base para VisionLab y un usuario con permiso de inicio de sesión que sea propietario de esa base. Escribe sus valores reales en `POSTGRES_DB`, `POSTGRES_USER` y `POSTGRES_PASSWORD`. Ajusta `POSTGRES_HOST` y `POSTGRES_PORT` al servidor que estés usando.

### Arrancar y probar VisionLab

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Ejecuta los comandos en orden. Si `migrate` falla por autenticación, comprueba las credenciales en `.env` antes de arrancar el servidor. Si indica que no puede conectarse, verifica que PostgreSQL esté activo y que el puerto sea el correcto.

Abre `http://127.0.0.1:8000/`, pulsa **Iniciar detección** y permite el acceso a la cámara. Muestra un celular para comprobar las cajas y el conteo. Pulsa **Detener** y espera el mensaje de confirmación del guardado. La primera inferencia puede tardar mientras se descargan y cargan los pesos `yolo26n.pt`.

Para cerrar Django, pulsa **Ctrl+C** en PowerShell. Si iniciaste PostgreSQL con Docker Compose, puedes detenerlo con `docker compose down`. Los datos se conservan en el volumen de Compose.

## Pruebas de la práctica 4

Instala las dependencias de Python desde `requirements.txt` siguiendo **Inicio en Windows**. Luego ejecuta las pruebas desde la raíz del repositorio. La suite de Django usa SQLite en memoria y sustituye las predicciones de YOLO por respuestas controladas. Esta configuración solo se aplica a las pruebas. Durante el uso normal, VisionLab guarda los resúmenes en PostgreSQL.

```powershell
.\.venv\Scripts\python.exe manage.py test processor.tests --settings=visionlab.test_settings -v 2
```

La prueba complementaria de interfaz usa Node.js 20 o superior, sin paquetes adicionales. Simula una cámara y comprueba que el JavaScript muestra la imagen con detecciones, el conteo y la confirmación de guardado.

```powershell
node processor/tests/test_interface.cjs
```

Consulta el [reporte de ejecución](docs/practica-4-pruebas.txt) para ver los resultados y el alcance de las pruebas.

| Tipo | Casos | Código |
| --- | ---: | --- |
| Unitarias | 4 | [Procesamiento de imágenes y selección de clases](processor/tests/test_detection.py) |
| Integración | 5 | [Rutas, validación y ciclo de sesiones](processor/tests/test_routes.py) |
| Funcionales | 2 | [Flujo Django de detección y guardado](processor/tests/test_functional.py) y [visualización en JavaScript](processor/tests/test_interface.cjs) |

### Verificación con cámara física

Sigue **Arrancar y probar VisionLab** usando PostgreSQL. Esta comprobación complementa la suite automatizada y sirve para obtener las capturas del informe.

1. Abre VisionLab y pulsa **Iniciar detección**. Concede el permiso y confirma que aparezca **EN VIVO**.
2. Muestra un celular y verifica que el fotograma muestre la caja y que el conteo aumente. Retira el celular y comprueba que el conteo vuelva a cero.
3. Pulsa **Detener** y espera el mensaje de guardado. Comprueba que la sesión quede cerrada en el panel de administración si ya configuraste una cuenta.
4. Prueba con el permiso de cámara denegado y verifica que la interfaz explique el problema.

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
