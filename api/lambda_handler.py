from mangum import Mangum

from api.main import app

# Mangum traduce el evento HTTP de Lambda al formato ASGI que FastAPI entiende.
# lifespan="on" le dice a Mangum que ejecute el lifespan (carga del modelo) en el cold start.
handler = Mangum(app, lifespan="on")
