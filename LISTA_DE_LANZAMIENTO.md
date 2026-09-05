# Lista de lanzamiento de HabitaRD

No se debe cambiar `APP_ENV` a `production` hasta completar todos los requisitos obligatorios.

## Completado

- Búsqueda pública sin membresía y cobertura de todas las provincias.
- Cuentas protegidas, recuperación con vencimiento y verificación de correo.
- Límites contra intentos repetidos de acceso y solicitudes duplicadas.
- Reportes, revisión administrativa y suspensión preventiva de anuncios.
- Fuentes externas privadas por defecto, autorización registrada y auditoría.
- Retiro de inventario vencido, revocado, desactualizado o eliminado por el proveedor.
- Páginas públicas de privacidad, términos, datos, aliados y solicitudes de retiro.
- Validación que impide iniciar producción con configuración insegura.
- Documentación técnica de la API desactivada automáticamente en producción.
- `APP_ENV` rechaza valores desconocidos para que un error de escritura no desactive las protecciones de producción.
- Las importaciones conservan el último catálogo válido cuando reciben datos duplicados, antiguos o inesperadamente vacíos.
- Las conexiones PostgreSQL tienen límites de espera, reciclaje y crecimiento configurables para evitar bloqueos prolongados.
- La navegación permite saltar al contenido principal y cada sección presenta un título claro en el navegador.
- Verificación y recuperación usan una conexión SMTP centralizada, cifrada y con tiempo de espera limitado.
- Producción no altera tablas durante el arranque; los cambios se aplican de forma deliberada antes de recibir tráfico.
- Las fotos usan almacenamiento de objetos duradero en producción; el disco local queda limitado al desarrollo.
- Las sesiones tienen identificador único y vencen en un máximo configurable de 60 minutos en producción.
- Cerrar sesión revoca el acceso también en el servidor, incluso si alguien conservó una copia del token.
- El sitio bloquea scripts, formularios, marcos y dispositivos no autorizados mediante una política estricta del navegador.

## Obligatorio antes de inaugurar

1. Registrar el nombre comercial y confirmar la disponibilidad legal de HabitaRD.
2. Comprar el dominio definitivo y configurar HTTPS para el sitio y la API.
3. Contratar PostgreSQL administrado con copias de seguridad.
   Contratar también almacenamiento de objetos compatible con S3 y configurar su dominio público HTTPS.
4. Crear una clave secreta aleatoria de producción y guardarla fuera del código.
5. Configurar los dominios permitidos, hosts confiables, dirección pública y HTTPS obligatorio.
6. Crear la cuenta administrativa inicial.
7. Configurar un remitente verificado de HabitaRD y probar entrega, rebotes y spam.
8. Revisar los términos y la privacidad con un abogado dominicano.
9. Probar la restauración de una copia de seguridad en un entorno separado.
   Antes de iniciar la API, aplicar el esquema con `.venv\\Scripts\\python.exe -m backend.migrate`.
10. Probar registro, acceso, recuperación, búsqueda, publicación, consultas, reportes y retiros
    desde teléfono y computadora.
11. No publicar datos externos hasta recibir autorización escrita para cada fuente.

## Variables requeridas en producción

- `APP_ENV=production`
- `DATABASE_URL` con PostgreSQL, controlador psycopg y `sslmode=require` o una verificación superior
- `DATABASE_POOL_SIZE`, `DATABASE_MAX_OVERFLOW`, `DATABASE_POOL_TIMEOUT_SECONDS`,
  `DATABASE_POOL_RECYCLE_SECONDS` y `DATABASE_CONNECT_TIMEOUT_SECONDS`
- `SECRET_KEY`
- `ACCESS_TOKEN_EXPIRE_MINUTES` entre 5 y 60
- `CORS_ORIGINS` con direcciones HTTPS
- `TRUSTED_HOSTS` sin direcciones locales
- `TRUSTED_PROXY_IPS` con las direcciones o redes oficiales del proveedor, si la API opera detrás de un proxy
- `FORCE_HTTPS=true`
- `ADMIN_USER_IDS`
- `FRONTEND_URL` con HTTPS
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_TIMEOUT_SECONDS`, `SMTP_USERNAME`, `SMTP_PASSWORD`,
  `SMTP_USE_TLS=true` y `SMTP_FROM` verificado
- `PROPERTY_IMAGE_STORAGE=s3`
- `OBJECT_STORAGE_BUCKET`, `OBJECT_STORAGE_ACCESS_KEY_ID`, `OBJECT_STORAGE_SECRET_ACCESS_KEY`
- `OBJECT_STORAGE_PUBLIC_BASE_URL` con HTTPS y, según el proveedor,
  `OBJECT_STORAGE_ENDPOINT_URL` y `OBJECT_STORAGE_REGION`

El servidor se negará a iniciar en producción si falta una de estas protecciones.
