# TasaJusta — Diario de aprendizaje

> Este archivo documenta cada paso del proyecto: qué hicimos, por qué, y qué preguntaría un
> entrevistador. Es tu guía para poder explicar cualquier decisión en una entrevista.
>
> **Cómo leerlo:** cada sección = una sesión de trabajo. Cada concepto tiene su bloque
> `[ENTREVISTA]` con las preguntas que te van a hacer.

---

## Sesión 1 — Setup del entorno Python (Fase 0 → Fase 1)

**Fecha:** 2026-07-02  
**Qué resolvimos:** preparar el proyecto Python para poder escribir código real en Fase 1.

---

### 1.1 — Estructura de carpetas (monorepo)

```
tasajusta/
├── etl/       → scripts de extracción y transformación de datos
├── ml/        → entrenamiento y evaluación de modelos
├── api/       → FastAPI (endpoint de inferencia)
├── web/       → Next.js (frontend del dashboard)
├── infra/     → Terraform (IaC — provisiona AWS)
├── dags/      → DAGs de Airflow (demo del skill de orquestación)
├── tests/     → tests unitarios y de integración
└── docs/      → documentación y diario de aprendizaje
```

**Por qué esta estructura:**  
Es un **monorepo**: todo el proyecto en un único repositorio. La alternativa es un "polyrepo"
(un repo por servicio). Para un proyecto de portfolio unipersonal, el monorepo es más simple —
todo está en un lugar, los cambios que tocan ETL + API a la vez van en un solo commit.

**Por qué `.gitkeep` en carpetas vacías:**  
Git no versiona carpetas vacías, solo archivos. El `.gitkeep` es un archivo vacío convencional
que fuerza a git a trackear la carpeta. Cuando la carpeta tenga archivos reales, se puede borrar.

**¿Los `.gitkeep` van en el `.gitignore`? No — y es importante entender por qué:**

El propósito de cada uno es opuesto:

```
.gitignore → le dice a git: ignorá este archivo, no lo trackees
.gitkeep   → existe justamente para que git SÍ lo trackee
```

Si pusieras `.gitkeep` en el `.gitignore`, git ignoraría el `.gitkeep`, la carpeta
quedaría sin ningún archivo trackeado, y git ignoraría la carpeta completa.
Exactamente lo contrario de lo que querés.

La lógica completa:

```
git no versiona carpetas, solo archivos
       ↓
carpeta vacía = git la ignora completamente
       ↓
.gitkeep = archivo vacío que "engaña" a git para que trackee la carpeta
       ↓
cuando la carpeta tenga archivos reales → podés borrar el .gitkeep
```

> **[ENTREVISTA]** ¿Por qué git no trackea carpetas vacías? Porque el modelo interno de
> git es un árbol de **contenido** (blobs y trees). Una carpeta sin archivos no tiene
> contenido — literalmente no existe en el modelo de datos de git. El `.gitkeep` es una
> convención de la comunidad, no una feature oficial de git.

> **[ENTREVISTA]** ¿Monorepo vs polyrepo? Tradeoff: monorepo = más simple de coordinar,
> polyrepo = más fácil de deployar por separado y escalar equipos. Para proyectos chicos o
> de una persona, monorepo casi siempre gana.

---

### 1.2 — Package manager: `uv`

**Qué es:** un gestor de dependencias y entornos virtuales para Python, escrito en Rust.
Reemplaza todo esto junto: `pip` + `virtualenv` + `pip-tools`.

**Por qué `uv` y no `poetry`:**

| | `uv` | `poetry` |
|---|---|---|
| Velocidad | Extremadamente rápido (Rust) | Lento en resolución |
| Qué reemplaza | pip + venv + pip-tools | solo pip + venv |
| Soporte CI | Excelente (GitHub Actions oficial) | Requiere plugin |
| Tendencia | Estándar emergente (2024-2026) | Maduro pero menos futuro |

**Cómo se usa (comandos básicos):**
```bash
uv sync                   # instala todas las deps del pyproject.toml
uv sync --group dev       # instala también las deps de desarrollo
uv run pytest             # corre pytest dentro del entorno virtual de uv
uv add httpx              # agrega una dependencia y actualiza pyproject.toml
uv add --dev ruff         # agrega una dependencia de desarrollo
```

> **[ENTREVISTA]** ¿Por qué un entorno virtual? Para aislar las dependencias de este
> proyecto de las del sistema. Sin venv, si dos proyectos necesitan versiones distintas
> de la misma librería, se pisan. Con venv, cada proyecto tiene su propio "Python limpio".

---

### 1.3 — `pyproject.toml` — el archivo de configuración del proyecto

**Qué es:** el archivo estándar moderno de Python (reemplaza `setup.py` + `requirements.txt`).
Define el proyecto, sus dependencias, y la config de las herramientas (ruff, pytest).

**Dependencias de Fase 1 y por qué cada una:**

| Librería | Para qué |
|---|---|
| `httpx` | Cliente HTTP moderno (llamar a `dolarapi.com`). Más moderno que `requests`. |
| `boto3` | SDK oficial de AWS para S3. El mismo código funciona contra MinIO (dev) y S3 real (prod) — solo cambia el endpoint. |
| `polars` | Transformación de datos. Más rápido que Pandas, API moderna, suma puntos en entrevistas. |
| `psycopg2-binary` | Conector a Postgres. El `-binary` incluye las libs C compiladas — evita instalar libpq en el sistema. |
| `python-dotenv` | Leer el `.env` desde Python: `load_dotenv()` carga las variables de entorno al proceso. |

**Dependencias de desarrollo (no van a producción):**

| Librería | Para qué |
|---|---|
| `ruff` | Linter + formatter. Reemplaza `flake8` + `black` + `isort`. Escrito en Rust, muy rápido. |
| `pytest` | Framework de tests. Estándar de la industria en Python. |
| `pytest-cov` | Mide cuánto del código está cubierto por tests. |

> **[ENTREVISTA]** ¿Diferencia entre dependencias de proyecto y de desarrollo? Las de dev
> (`[dependency-groups] dev`) solo se instalan en la máquina del desarrollador — no en
> producción. El servidor no necesita pytest ni ruff para correr la app.

---

### 1.4 — `ruff` — linter y formatter

**Qué es:** una herramienta que analiza tu código en busca de errores de estilo, imports
desordenados, y bugs comunes — y lo corrige automáticamente. Escrito en Rust, es 10-100x
más rápido que las alternativas anteriores (`flake8`, `black`, `isort`).

**Qué detecta (según nuestra config):**
- `E` — errores de estilo PEP8 (líneas muy largas, espacios mal puestos)
- `F` — bugs: variables no usadas, imports no usados
- `I` — imports desordenados (los ordena automáticamente)

**Cómo se usa:**
```bash
uv run ruff check .          # revisa el código
uv run ruff check --fix .    # revisa Y corrige lo que puede
uv run ruff format .         # formatea (como Black)
```

---

### 1.5 — `pre-commit` — automatización de calidad antes de commitear

**Qué es:** un framework que ejecuta hooks antes de cada `git commit`. Si un hook falla,
el commit no se hace — te obliga a tener el código limpio antes de guardarlo en git.

**Nuestra config (`.pre-commit-config.yaml`):**
- Corre `ruff --fix` (linting + auto-fix) antes de cada commit
- Corre `ruff format` (formatting) antes de cada commit

**Cómo instalar los hooks (solo una vez):**
```bash
uv run pre-commit install
```

> **[ENTREVISTA]** ¿Por qué pre-commit en vez de solo correr ruff a mano? Porque a mano
> te olvidás. El hook es automático y crea un estándar compartido: nadie en el equipo puede
> commitear código sin pasar el linter. Es parte de lo que hace que una codebase sea
> mantenible.

---

---

## Sesión 2 — Fase 1: Extractor dolarapi → MinIO bronze

**Fecha:** 2026-07-02  
**Archivo:** `etl/extract_dolar.py`  
**Qué resolvimos:** primer extractor real del ETL — capa bronze del data lake.

---

### 2.1 — El patrón ETL y por qué se separa en tres etapas

**ETL = Extract → Transform → Load**

| Etapa | Qué hace | Principio |
|---|---|---|
| **Extract** | Trae los datos de la fuente externa, los guarda crudos | "Bronze" — sin tocar nada |
| **Transform** | Limpia, normaliza, convierte tipos y monedas | "Silver" — parquet limpio |
| **Load** | Carga los datos transformados al warehouse (Postgres) | "Gold" — listo para la app |

**Por qué separarlas:** si el transform falla, todavía tenés el dato crudo en bronze. Podés
reejecutar solo la transformación sin volver a llamar a la API. Es resiliencia por diseño.

> **[ENTREVISTA]** ¿Por qué guardar el dato crudo antes de transformar? Porque los
> requisitos cambian. Hoy transformás de una manera; en 3 meses quizás necesitás una columna
> que no extrajiste. Si tenés el bronze, podés recomputar. Si no, perdiste esos datos para siempre.

---

### 2.2 — Idempotencia: el concepto más importante del ETL

**Idempotencia** = correr el pipeline N veces produce el mismo resultado que correrlo 1 vez.
Sin duplicados, sin roturas.

**¿Por qué importa?** Los pipelines fallan. La red corta, la API está caída, el servidor
se reinicia. Cuando volvés a correr, necesitás que sea seguro hacerlo sin miedo de
duplicar datos.

**La técnica:** el nombre del archivo en S3/MinIO es **determinístico** — incluye la fecha.

```
# ❌ Mal — no idempotente:
dolar/dolar_a3f9b12c.json  ← UUID distinto cada vez = duplicados infinitos
dolar/dolar_a7c2e91a.json

# ✅ Bien — idempotente:
dolar/2026-07-02.json  ← mismo nombre para el mismo día = overwrite limpio
```

Correrlo dos veces hoy sobreescribe el mismo archivo. Sin duplicados. Sin efectos secundarios.

> **[ENTREVISTA]** ¿Qué hace idempotente a un pipeline? Que el resultado no cambie si
> lo corrés múltiples veces con los mismos inputs. En la práctica: nombres de archivo
> determinísticos, upserts en lugar de inserts, y lógica que detecta si el dato ya existe.

---

### 2.3 — La capa bronze: datos crudos con metadata de ingesta

El extractor guarda el JSON tal cual llega de la API, pero envuelto con metadata:

```json
{
  "fetched_at": "2026-07-02T14:30:00+00:00",
  "source": "https://dolarapi.com/v1/dolares",
  "data": [ ...cotizaciones... ]
}
```

**Por qué agregar `fetched_at`:** la API devuelve cuándo *ella* actualizó el precio, pero
no necesariamente cuándo vos lo descargaste. Si hay un desfase o un retry, sabés exactamente
cuándo fue tu ingesta.

**Por qué `timezone.utc`:** siempre guardar timestamps en UTC. Si en el futuro el servidor
cambia de zona horaria o alguien lo corre desde otro país, los datos son comparables.

> **[ENTREVISTA]** ¿Por qué UTC para los timestamps? Porque UTC no tiene DST (horario de
> verano) y es el estándar en sistemas distribuidos. Si guardás en hora local y alguien
> en otro timezone lee el dato, el timestamp es ambiguo.

---

### 2.4 — Por qué JSON en bronze y Parquet en silver

Una pregunta natural: si Parquet es mejor para analítica, ¿por qué no guardamos Parquet
desde el principio?

**La regla de bronze:** guardás el dato **exactamente como llega de la fuente**. Si la API
manda JSON, guardás JSON. Si alguien te manda CSV, guardás CSV. Bronze no transforma nada.

**¿Por qué?** Bronze es tu seguro de vida. Si en 6 meses el transform tiene un bug, o
necesitás una columna que no extrajiste, volvés al bronze y recomputás desde el crudo
original. Si hubieras transformado en el momento de la ingesta, perdiste el dato original
para siempre.

El flujo completo de formatos:

```
dolarapi.com → JSON crudo       → bronze/dolar/2026-07-02.json
                    ↓ transform (Polars)
              DataFrame limpio  → silver/dolar/2026-07-02.parquet
                    ↓ load
              Tabla en Postgres ← gold, listo para la app
```

**¿Por qué Parquet en silver y no JSON o CSV?**

| | JSON | CSV | Parquet |
|---|---|---|---|
| Formato | Row-oriented | Row-oriented | **Columnar** |
| Compresión | Ninguna nativa | Ninguna nativa | Muy buena (~5-10x menos espacio) |
| Query analítica | Lee todo el archivo | Lee todo el archivo | Lee solo las columnas pedidas |
| Schema | Sin tipos — cualquier campo puede ser cualquier cosa | Sin tipos | **Tipado — el schema está embebido** |
| Para analítica | Lento y pesado | Lento y pesado | **Rápido, diseñado para esto** |

En la práctica: si tenés 1 millón de registros y querés solo la columna `venta`, Parquet
lee solo esa columna del disco. JSON y CSV tienen que leer los 1M registros completos.

> **[ENTREVISTA]** "¿Por qué Parquet en vez de CSV para la capa silver?" — Tres razones:
> (1) **Columnar**: lee solo las columnas que necesitás, no el registro entero. (2)
> **Compresión nativa**: hasta 10x más chico que CSV — menos costo de storage en S3.
> (3) **Schema embebido**: los tipos están guardados en el archivo, no tenés que
> documentar por separado que `precio` es float y `fecha` es date. Para analítica con
> Polars o DuckDB, es la diferencia entre segundos y minutos.

---

### 2.5 — boto3 contra MinIO (y por qué el mismo código funciona en S3 real)


`boto3` es el SDK oficial de AWS para Python. MinIO lo emula completamente — misma API,
mismo protocolo S3. La clave está en el parámetro `endpoint_url`:

```python
# Dev — apunta a MinIO local
boto3.client("s3", endpoint_url="http://localhost:9000", ...)

# Prod — apunta a S3 real (solo borrás endpoint_url y cambiás las credenciales en .env)
boto3.client("s3", ...)
```

El código no cambia. Solo el `.env`. Eso es exactamente lo que buscan cuando hablan de
"portabilidad entre entornos".

> **[ENTREVISTA]** ¿Cómo hacés para que el mismo código funcione en dev y en prod?
> Con variables de entorno para todo lo que cambia entre entornos (endpoint, credenciales,
> nombres de buckets). El código lee del `.env`; el `.env` cambia según el entorno.

---

### 2.6 — Variables de entorno: desacoplando config de código

```python
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
```

El segundo argumento de `os.getenv()` es el **valor por defecto**. Si la variable no está
en el `.env`, usa ese valor. Útil para desarrollo rápido.

**`python-dotenv` y `load_dotenv()`:** carga las variables del archivo `.env` al entorno
del proceso Python. Sin esto, `os.getenv()` solo lee las variables del sistema operativo,
no las del `.env`.

> **[ENTREVISTA]** ¿Por qué no hardcodear las credenciales en el código? Porque el código
> va al repo. Las credenciales en el repo = security incident. Con variables de entorno,
> cada entorno (dev, staging, prod) tiene sus propias credenciales sin tocar el código.

---

### 2.7 — `ensure_bucket_exists`: idempotencia aplicada a la infraestructura

```python
def ensure_bucket_exists(s3_client) -> None:
    try:
        s3_client.head_bucket(Bucket=BRONZE_BUCKET)
    except s3_client.exceptions.ClientError:
        s3_client.create_bucket(Bucket=BRONZE_BUCKET)
```

`head_bucket` hace un request liviano para verificar si el bucket existe (no descarga nada).
Si falla (ClientError), lo crea. Si ya existe, no hace nada. Idempotente.

Este patrón — "verificar primero, crear si no existe" — se repite en toda la infraestructura:
tablas de base de datos, índices, colas, etc.

---

---

### 2.8 — Docker networking: por qué `minio` no resuelve desde el host

Al correr el extractor por primera vez desde el host obtuvimos este error:

```
Failed to resolve 'minio' — Temporary failure in name resolution
```

**Por qué:** el hostname `minio` solo existe dentro de la red interna de Docker.
Docker tiene su propio DNS — cuando el contenedor `app` quiere hablar con MinIO,
resuelve `minio` a la IP interna del contenedor. Desde afuera de Docker, ese hostname
no existe en ningún lado.

```
Host (tu máquina)           Red Docker interna
                            ┌─────────────────────┐
uv run python ... ───✗────► minio:9000            ← no resuelve desde afuera
                            │                     │
localhost:9000    ───✓────► (puerto mapeado        ← sí llega (ports: "9000:9000")
                            │ al host)             │
                            └─────────────────────┘
```

**El fix para correr desde el host:** sobreescribir `MINIO_ENDPOINT` inline,
sin tocar el `.env`:

```bash
MINIO_ENDPOINT=http://localhost:9000 uv run python etl/extract_dolar.py
```

El `MINIO_ENDPOINT=...` antes del comando setea esa variable de entorno solo para
esa ejecución — no modifica el `.env` ni el entorno global.

**Por qué el `.env` tiene `minio:9000` y no `localhost:9000`:**
Porque el `.env` está pensado para cuando el script corra **dentro del contenedor `app`**,
que es como va a correr en producción (el cron lo va a ejecutar ahí adentro). Desde dentro
del contenedor, `minio` resuelve perfecto.

> **[ENTREVISTA]** ¿Cómo se comunican los servicios dentro de Docker Compose?
> Docker Compose crea una red interna automáticamente. Cada servicio es accesible
> por su nombre de servicio (definido en el `docker-compose.yml`) como hostname.
> Ese hostname solo existe dentro de esa red — desde el host tenés que usar `localhost`
> con el puerto mapeado en `ports:`.

---

---

## Sesión 3 — Fase 1: Transform bronze → silver (Parquet)

**Fecha:** 2026-07-02

---

### 3.1 — Polars vs Pandas: por qué elegimos Polars

| | Pandas | Polars |
|---|---|---|
| Velocidad | Un solo hilo — lento en datasets grandes | Paralelo automático en todos los cores |
| Memoria | Copia datos constantemente (~5-10x el tamaño) | Lazy eval + zero-copy — consume mucho menos |
| API | Inconsistente — 4 formas de hacer lo mismo, algunas con bugs silenciosos | Consistente — una sola forma correcta |
| Tipos | Permite mezclar tipos en una columna (bugs silenciosos) | Estricto — si una columna es Float64, siempre es Float64 |
| Año | 2008 — carga con decisiones viejas | 2021 — diseñado sabiendo los errores de Pandas |

**¿Por qué Polars en TasaJusta?**
En este proyecto los datasets no son enormes — con Pandas también andaría. Pero hay dos
razones concretas:
1. **Currículum:** Polars aparece cada vez más en ofertas de 2024-2026. "Conozco Pandas y
   también Polars" suma. "Solo Pandas" es lo básico esperado.
2. **Hábitos correctos desde el principio:** la API de Polars te fuerza a pensar en tipos
   y transformaciones explícitas. Es más difícil hacer algo mal sin darte cuenta.

**¿Cuándo usarías Pandas igualmente?** Cuando heredás un proyecto que ya lo usa, cuando
trabajás con librerías que solo aceptan DataFrames de Pandas (scikit-learn, por ejemplo),
o cuando el equipo ya lo conoce. No es un dogma — es una elección con contexto.

> **[ENTREVISTA]** "¿Por qué Polars sobre Pandas?" — Velocidad (paralelo vs un hilo),
> memoria (lazy eval vs copias), y API más consistente. En datasets medianos/grandes la
> diferencia es real. En datasets chicos es principalmente una decisión de modernidad
> y hábitos correctos.

---

### 3.2 — El transform: bronze → silver

**Archivo:** `etl/transform_dolar.py`

El transform hace exactamente tres cosas:
1. Lee el JSON crudo de bronze desde MinIO
2. Normaliza con Polars — tipos explícitos, solo las columnas que necesitamos
3. Escribe Parquet a `silver/dolar/YYYY-MM-DD.parquet`

**Schema del DataFrame silver:**

| Columna | Tipo | Por qué |
|---|---|---|
| `fecha` | `Date` | El día de la cotización — clave para joins futuros |
| `casa` | `String` | Identificador de la casa (blue, oficial...) |
| `nombre` | `String` | Nombre legible para mostrar en la UI |
| `compra` | `Float64` | Precio de compra explícitamente float |
| `venta` | `Float64` | Precio de venta explícitamente float |
| `fetched_at` | `String` | Timestamp UTC de ingesta — trazabilidad |

**Por qué `io.BytesIO` y no escribir a disco:**
Polars escribe el Parquet a un buffer en memoria y lo subimos directo a MinIO.
No hay archivos temporales en disco — más limpio y más rápido.

```python
buffer = io.BytesIO()
df.write_parquet(buffer)
buffer.seek(0)  # volvemos al inicio del buffer para leerlo
s3_client.put_object(..., Body=buffer.getvalue())
```

**Por qué "carpetas" en S3/MinIO no existen realmente:**
El archivo quedó en `silver/dolar/2026-07-02.parquet` pero en S3/MinIO no hay
carpetas — el `/` es parte del nombre del archivo (la "key"). La UI lo muestra
como si fueran carpetas, pero internamente es un string plano.

> **[ENTREVISTA]** ¿Por qué cast explícito de tipos si Polars ya los infiere?
> Porque la inferencia depende de los datos. Si un día la API devuelve `"1460"`
> (string) en vez de `1460` (número), Polars inferiría String y el pipeline
> rompería más tarde silenciosamente. Con cast explícito, el error aparece
> en el transform — donde pertenece.

**Resultado de correr el transform:**
```
shape: (7, 6)
fecha       casa              compra   venta
2026-07-02  oficial           1460.0   1510.0
2026-07-02  blue              1505.0   1525.0
2026-07-02  bolsa             1517.2   1521.2
...
```

---

### 3.3 — El load: silver → Postgres

**Archivo:** `etl/load_dolar.py`

**Upsert vs Insert — el concepto central:**

Un `INSERT` normal falla si la fila ya existe → no es idempotente.
Un **upsert** inserta si no existe, actualiza si ya existe → idempotente.

```sql
INSERT INTO cotizaciones_dolar (fecha, casa, compra, venta, ...)
VALUES (...)
ON CONFLICT (fecha, casa) DO UPDATE SET
    compra = EXCLUDED.compra,
    venta  = EXCLUDED.venta;
```

- `(fecha, casa)` es la **primary key compuesta** — un par único por día.
- `EXCLUDED` es la tabla virtual con la fila que colisionó — la que intentabas insertar.
- Resultado: correr el pipeline dos veces siempre deja exactamente 7 filas, nunca 14.

**`CREATE TABLE IF NOT EXISTS` — idempotencia en el schema:**
El mismo principio. Si la tabla ya existe, no falla — no hace nada. El pipeline
puede correr en un entorno limpio o en uno ya inicializado sin cambiar el código.

**`executemany` vs loop de `execute()`:**
```python
cur.executemany(UPSERT_SQL, rows)  # ✅ un roundtrip al servidor por batch
# vs
for row in rows:
    cur.execute(UPSERT_SQL, row)   # ❌ un roundtrip por fila
```
Con 7 filas la diferencia es imperceptible. Con 1 millón de filas, la diferencia
es de minutos vs segundos.

**Verificación de idempotencia:**
```bash
# Corrido dos veces → sigue habiendo 7 filas, no 14
SELECT COUNT(*) FROM cotizaciones_dolar;
-- count: 7 ✅
```

> **[ENTREVISTA]** ¿Qué es un upsert y cuándo lo usás? Es una operación atómica
> que hace INSERT si la fila no existe y UPDATE si ya existe. Lo usás en pipelines
> de datos para garantizar idempotencia — podés reejecutar sin duplicar. En Postgres
> se implementa con `ON CONFLICT DO UPDATE`; en otros motores tiene distintos nombres
> (`MERGE` en SQL Server, `REPLACE INTO` en MySQL).

> **[ENTREVISTA]** ¿Qué es `EXCLUDED` en un upsert? Es una tabla virtual especial
> de Postgres que contiene los valores de la fila que intentabas insertar y que
> colisionó con una existente. Te permite decidir exactamente qué actualizar.

---

### 3.4 — El pipeline: orquestador Extract → Transform → Load

**Archivo:** `etl/pipeline.py`

El pipeline encadena los tres pasos en orden y falla rápido si alguno rompe.

**`__init__.py` — por qué lo necesitamos:**
Para importar `from etl.extract_dolar import run`, Python necesita que `etl/`
sea un paquete. Un `__init__.py` vacío es suficiente para marcarlo como tal.

**Fail fast — por qué abortar si un paso falla:**
```
Extract falla → no hay bronze → Transform no tiene qué leer → no corremos
Transform falla → no hay silver limpio → Load cargaría datos corruptos → no corremos
Load falla → los datos están seguros en silver → podemos reintentar solo el Load
```
Cada paso depende del anterior. Correr Transform sobre un bronze incompleto o
Load sobre un silver corrupto es peor que no correr nada.

**Extract no recibe `day`:**
La API de dolarapi siempre devuelve cotizaciones del momento actual — no tiene
endpoint histórico. Extract siempre fetchea "ahora" y nombra el archivo con la
fecha de hoy. Transform y Load sí reciben `day` para saber qué archivo leer.

**Cómo correr el pipeline desde el host:**
```bash
MINIO_ENDPOINT=http://localhost:9000 \
DATABASE_URL=postgresql://tasajusta:tasajusta_dev@localhost:5432/tasajusta \
uv run python -m etl.pipeline
```

La flag `-m etl.pipeline` corre el módulo como paquete (en lugar de `python etl/pipeline.py`),
lo que garantiza que los imports relativos funcionen correctamente.

> **[ENTREVISTA]** ¿Por qué abortar el pipeline en el primer error en vez de
> intentar continuar? Porque en un pipeline de datos, un paso intermedio fallido
> corrompe o deja incompletos todos los pasos siguientes. "Fail fast" es un
> principio de sistemas resilientes: mejor un fallo claro y temprano que datos
> incorrectos que llegan silenciosamente hasta producción.

---

### 3.5 — Falsa abstracción: cuándo NO generalizar

En el pipeline, el primer intento usó una lambda para unificar los tres pasos en un loop:

```python
steps = [
    ("Extract ", lambda _: extract_run()),  # ← hack
    ("Transform", transform_run),
    ("Load    ", load_run),
]
for name, step in steps:
    step(day)
```

El problema: `extract_run()` no acepta argumentos (la API siempre devuelve datos de hoy),
pero `transform_run(day)` y `load_run(day)` sí. La lambda `lambda _: extract_run()` es
una función que acepta un argumento y lo ignora — existe solo para que los tres pasos
"encajen" en el mismo molde.

Eso es **falsa abstracción**: generalizás código que no es realmente uniforme, y el
resultado es más difícil de leer que el problema que resolvés.

```python
# ✅ Versión final — explícita y obvia
extract_run()       # no recibe day: siempre fetchea hoy
transform_run(day)  # recibe day: lee el archivo de esa fecha
load_run(day)       # recibe day: carga los datos de esa fecha
```

> **[ENTREVISTA]** ¿Cuándo no abstraés? Cuando la abstracción requiere más explicación
> que el código que reemplaza. Tres llamadas explícitas son más legibles que un loop
> con una lambda que ignora argumentos. "Prefer duplication over the wrong abstraction"
> — Sandi Metz.

---

### 3.6 — Decisión: GitHub Actions cron se difiere a Fase 2

**Decisión:** no configuramos el cron en Fase 1.

**Por qué:** GitHub Actions no tiene acceso a nuestro MinIO local. La única forma de
tener storage en el workflow sería usar un contenedor de MinIO efímero — que se destruye
al final de cada run. Eso significa que bronze y silver se pierden en cada ejecución.

Eso viola el principio fundamental de la capa bronze: **los datos crudos son permanentes**.
Si los descartamos, perdemos la capacidad de recomputar silver y gold si cambiamos la
lógica de transformación en el futuro.

**La secuencia correcta:**
```
Fase 2 → cuenta AWS → MinIO migra a S3 real (un cambio de endpoint)
       → cron en GitHub Actions persiste bronze/silver en S3
       → gold en Supabase Postgres
```

El código no cambia — solo el endpoint en el `.env`.

> **[ENTREVISTA]** ¿Por qué mantener los datos crudos en bronze si ya los transformaste?
> Porque los requisitos cambian. Si en 6 meses necesitás una columna que no extrajiste,
> o encontrás un bug en el transform, podés recomputar todo desde el crudo original.
> Sin bronze, esos datos históricos se pierden para siempre.

---

---

## Sesión 4 — Tests con pytest y mocks

**Fecha:** 2026-07-02

---

### 4.1 — El gotcha más importante de mocks en Python

`patch()` parchea el nombre **donde se usa**, no donde se define:

```python
# extract_dolar.py hace:
import httpx
httpx.get(...)   ← se usa acá, en el módulo etl.extract_dolar

# Por eso el patch correcto es:
@patch("etl.extract_dolar.httpx.get")   ✅
@patch("httpx.get")                     ❌ no funciona
```

Si lo parcheas donde se define, el módulo que lo usa ya tiene una referencia
al original — tu mock llega tarde.

> **[ENTREVISTA]** ¿Por qué `patch("etl.extract_dolar.httpx.get")` y no `patch("httpx.get")`?
> Porque `patch` reemplaza el nombre en el namespace del módulo que lo usa.
> Para cuando el módulo importó `httpx`, ya tiene su propia referencia al objeto.
> Tenés que reemplazarlo donde está siendo usado, no en su lugar de origen.

---

### 4.2 — Funciones puras vs funciones con efectos

```python
# Función pura — mismo input, mismo output, sin tocar nada externo
def transform(raw: dict, day: date) -> pl.DataFrame:
    ...  # no mocks necesarios

# Función con efectos — toca el mundo exterior
def fetch_dolar_rates():    # llama a una API externa
def save_to_bronze():       # escribe en MinIO
def load_to_postgres():     # escribe en Postgres
```

Las funciones puras son las más fáciles de testear — no necesitan mocks ni servicios.
`transform()` recibe datos y devuelve un DataFrame: siempre el mismo resultado para
el mismo input.

> **[ENTREVISTA]** ¿Qué es una función pura? Una función que (1) siempre devuelve
> el mismo resultado para los mismos inputs y (2) no tiene efectos secundarios
> (no escribe a disco, no llama a red, no modifica estado global). Son trivialmente
> testeables y componibles.

---

### 4.3 — Anatomía de un test con mock

```python
@patch("etl.extract_dolar.httpx.get")   # ← patch donde se USA
def test_returns_list_from_api(self, mock_get):
    # Arrange — configuramos qué devuelve el mock
    mock_get.return_value.json.return_value = FAKE_RATES

    # Act — ejecutamos la función bajo test
    result = fetch_dolar_rates()

    # Assert — verificamos el resultado
    assert result == FAKE_RATES
```

**`MagicMock`** crea un objeto que acepta cualquier atributo o llamada sin romper.
`mock.return_value` define qué devuelve cuando lo llamás. `mock.side_effect`
define qué excepción lanza.

---

### 4.4 — `conftest.py` — datos compartidos entre tests

pytest carga `conftest.py` automáticamente. Tiene dos usos:
1. **Fixtures** (`@pytest.fixture`) — setup/teardown reutilizable entre tests
2. **Constantes** — datos fake compartidos (`FAKE_RATES`, `TEST_DAY`)

```python
@pytest.fixture
def fake_silver_df() -> pl.DataFrame:
    """Disponible en cualquier test que lo declare como parámetro."""
    ...

def test_algo(fake_silver_df):  # pytest inyecta el fixture automáticamente
    ...
```

---

### 4.5 — `pythonpath` en pytest — por qué lo necesitamos

pytest no agrega el root del proyecto a `sys.path` automáticamente.
Sin esta config, `import etl` falla:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]   # ← agrega el root del proyecto a sys.path
```

> **[ENTREVISTA]** ¿Por qué los tests no encuentran los módulos del proyecto?
> pytest ejecuta desde el directorio del proyecto pero no modifica `sys.path`.
> `pythonpath = ["."]` le dice a pytest que agregue el directorio actual al path
> antes de correr los tests, para que `import etl` resuelva correctamente.

---

### 4.6 — Resultado final

```
19 tests en 0.14 segundos — todos en verde
```

| Archivo | Tests | Qué verifica |
|---|---|---|
| `test_extract_dolar.py` | 6 | API call, key idempotente, bucket creation |
| `test_transform_dolar.py` | 5 | Schema, tipos, valores, fecha correcta |
| `test_load_dolar.py` | 5 | Key S3, CREATE TABLE, upsert, commit |
| `test_pipeline.py` | 3 | Happy path, fail-fast en extract, fail-fast en transform |

---

---

## Sesión 5 — Web scraping ético + Transform de autos usados

**Fecha:** 2026-07-02  
**Qué resolvimos:** recolectar el dataset semilla de autos usados desde DeRuedas.com.ar y
transformarlo de JSON bronze a Parquet silver.

---

### 5.1 — Por qué scraping y no un dataset público

Buscamos datasets de autos usados argentinos en Kaggle — no encontramos nada útil: los que
existían eran de autos nuevos del mercado americano o ejercicios de BI con datos sintéticos.

**Mercadolibre** tiene una API pero requiere OAuth y tiene rate limits agresivos.
**DeRuedas.com.ar** es un directorio de usados de Argentina con estructura predecible → ideal
para un dataset semilla.

> Siempre verificá el `robots.txt` antes de scrapear. DeRuedas indica `Crawl-delay: 5`.
> Respetarlo no es solo cortesía — es legal en muchos contextos y protege tu IP.

---

### 5.2 — El problema de las páginas renderizadas con JS

Las páginas de listado (`/precio/Autos/Usados/Argentina`) cargan los resultados con JavaScript.
Un `requests.get()` simple devuelve el HTML vacío; los datos llegan después via XHR.

**Solución:** encontrar el endpoint real que usa el frontend.
Inspeccionando los links del homepage descubrimos `bus.asp` — el endpoint que devuelve el HTML
de resultados directamente, sin necesidad de ejecutar JS.

```
GET https://www.deruedas.com.ar/bus.asp
  ?condicion=Usados
  &tipo=Autos
  &desde=0
  &marca=Toyota
```

Devuelve hasta 60 links del tipo `/vendo/Toyota/Corolla/Usado/Buenos-Aires?cod=12345`.

**`[ENTREVISTA]`** — preguntas clave:
- *¿Por qué no usar Selenium o Playwright?* → innecesario si podés identificar el endpoint real;
  más rápido, más liviano, sin browser overhead.
- *¿Cómo encontrás el endpoint real?* → DevTools → Network → filtrar XHR/Fetch mientras navegás.

---

### 5.3 — Arquitectura del scraper: dos fases

```
Fase 1: bus.asp por marca → set de URLs únicas de listings
Fase 2: por cada URL → detalle con precio/año/km desde inputs ocultos
```

Usamos un `set` para deduplicar URLs antes de la Fase 2 — el mismo auto puede aparecer en
búsquedas de distintas marcas.

Los datos están en **inputs ocultos** del HTML de detalle:
```html
<input type="hidden" name="precio" value="19800000">
<input type="hidden" name="anio" value="2018">
<input type="hidden" name="kilometraje" value="136800">
```

Extraemos con regex en lugar de un parser HTML completo (BeautifulSoup) porque la estructura
es predecible y el regex es suficiente para este caso.

**`[ENTREVISTA]`** — preguntas clave:
- *¿Cuándo usás regex vs BeautifulSoup para parsear HTML?* → regex para estructura predecible
  y acotada; BS4/lxml para HTML anidado complejo o cuando la posición importa.
- *¿Por qué `set` y no `list` para las URLs?* → deduplicación O(1) vs O(n). Si hay 300 URLs
  y el 50% son duplicadas, un set elimina los duplicados automáticamente al hacer `|=`.

---

### 5.4 — Resultados del scraping

```
5 marcas × 60 URLs = 300 URLs únicas
~150 con datos completos (~50% SKIP)
```

El 50% de SKIPs son publicaciones sin precio cargado ("a consultar") — se pueden leer en
el sitio pero los inputs ocultos están vacíos. Los descartamos en bronze; no queremos NaN
en precio en la capa raw.

Respetamos el `Crawl-delay: 5s` → ~25 minutos de ejecución total.

---

### 5.5 — Transform: limpieza antes de silver

El transform aplica reglas de negocio para limpiar datos sospechosos:

| Regla | Qué hace | Por qué |
|---|---|---|
| `precio_ars == 0` → null | Precios nulos en el sitio se guardan como 0 | El 0 no es un precio válido |
| `anio < 1990 or > hoy` → null | Años fuera de rango | Error de carga o dato corrupto |
| `km == 0 and condicion != "Nuevo"` → null | KM 0 en un usado es imposible | Probablemente no completó el campo |
| `.unique(subset=["cod"])` | Deduplicar por código del listing | El mismo auto aparece en múltiples búsquedas |

**Resultado:** 150 registros bronze → 75 silver (la deduplicación eliminó exactamente la mitad,
lo que confirma que el scraper coleccionó cada URL exactamente dos veces).

**`[ENTREVISTA]`** — preguntas clave:
- *¿Por qué null y no eliminar el registro?* → silver puede tener nulls; gold y ML deciden
  qué incluir. Descartar en silver sería pérdida de información irreversible.
- *¿Qué es `keep="first"` en `.unique()`?* → Polars no garantiza orden sin `.sort()` previo.
  En nuestro caso los duplicados son idénticos así que el orden no importa.
- *¿Cómo escalarías el scraper a más marcas?* → async con `httpx.AsyncClient` + semáforo
  para respetar el rate limit, o bien usar un scheduler (Airflow/Prefect) con backoff.

---

---

## Sesión 6 — Fase 2: Deploy en AWS (Lambda + Terraform)

**Fecha:** 2026-07-03
**Qué resolvimos:** pasar de "API que corre local" a "API con URL pública en AWS Lambda",
con infraestructura declarada en Terraform y estado remoto en S3.

---

### 6.1 — La arquitectura de deploy: por qué Lambda y no un servidor

Tenemos dos grandes opciones para servir la API:

| | Servidor (EC2/VPS) | Lambda (serverless) |
|---|---|---|
| Costo | Siempre encendido — pagás 24/7 | Pagás solo cuando hay requests |
| Escalado | Manual o con AutoScaling | Automático hasta millones de requests |
| Ops | Tenés que parchear el SO, monitorear disco, etc. | Cero — AWS gestiona todo |
| Cold start | Ninguno | ~1-3 seg en el primer request (modelo cargándose desde S3) |
| Capa gratuita | Expira en 12 meses o se agotan créditos | **1 millón de requests/mes para siempre** |

Para un proyecto de portfolio con tráfico intermitente y que tiene que sobrevivir meses sin
pagar, Lambda gana claramente. El cold start es el único tradeoff real.

> **[ENTREVISTA]** ¿Cuándo NO usarías Lambda? Cuando el proceso tarda más de 15 minutos
> (el timeout máximo), cuando necesitás estado en memoria entre requests (Lambda puede
> reiniciarse en cualquier momento), o cuando tenés tráfico muy constante y alto (en ese
> caso un servidor puede ser más barato).

---

### 6.2 — `infra/bootstrap/main.tf` — línea por línea

El bootstrap es el único paso que usa **estado local** (no remoto). Existe porque tenemos
un problema del huevo y la gallina: no podemos usar un backend S3 para guardar el estado
del recurso que crea ese bucket S3.

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"   # el provider oficial de AWS
      version = "~> 5.0"          # "compatible con 5.x" — acepta 5.1, 5.2, etc.
    }                             # pero NO 6.0 (podría romper cosas)
  }
}
```

El bloque `terraform {}` define metadatos: qué providers necesita este módulo.
`~> 5.0` es el **pessimistic constraint operator**: acepta parches pero no major versions.

```hcl
provider "aws" {
  region = "us-east-1"
}
```

Le dice a Terraform qué región de AWS usar. No especificamos el profile acá —
viene de la variable de entorno `AWS_PROFILE=personal` que seteamos antes de correr.

```hcl
resource "aws_s3_bucket" "tf_state" {
  bucket = "tasajusta-tf-state-966940665955"
  lifecycle {
    prevent_destroy = true   # Terraform falla si intentás hacer destroy de este bucket
  }                          # Evita borrar accidentalmente el estado de toda la infra
}
```

El nombre incluye el Account ID porque los buckets S3 son **globalmente únicos** en todo AWS.
Dos cuentas distintas no pueden tener el mismo nombre de bucket.

```hcl
resource "aws_s3_bucket_versioning" "tf_state" {
  bucket = aws_s3_bucket.tf_state.id
  versioning_configuration {
    status = "Enabled"
  }
}
```

El versionado guarda todas las versiones anteriores del `terraform.tfstate`.
Si accidentalmente corrés un `destroy` o el estado se corrompe, podés restaurar una versión anterior.

```hcl
resource "aws_dynamodb_table" "tf_lock" {
  name         = "tasajusta-tf-lock"
  billing_mode = "PAY_PER_REQUEST"  # pagás por operación, no por capacidad reservada
  hash_key     = "LockID"           # la primary key que Terraform usa para el locking

  attribute {
    name = "LockID"
    type = "S"   # S = String (DynamoDB distingue String/Number/Binary)
  }
}
```

**¿Para qué sirve el locking?** Si dos personas corren `terraform apply` al mismo tiempo,
podrían pisarse y dejar el estado corrupto. DynamoDB actúa como mutex distribuido:
el primero que llega escribe el lock; el segundo espera o falla.

> **[ENTREVISTA]** ¿Qué es el "state" de Terraform? Es un archivo JSON que mapea
> cada recurso declarado en `.tf` con su equivalente real en AWS (el ID, ARN, etc.).
> Sin state, Terraform no sabe qué recursos ya creó vs cuáles tiene que crear.
> El state remoto en S3 permite que cualquier miembro del equipo (o el CI) corra
> Terraform sin necesitar el archivo local.

---

### 6.3 — `infra/main/provider.tf` — el backend remoto

```hcl
backend "s3" {
  bucket         = "tasajusta-tf-state-966940665955"  # el bucket que creó bootstrap
  key            = "main/terraform.tfstate"            # la "ruta" dentro del bucket
  region         = "us-east-1"
  dynamodb_table = "tasajusta-tf-lock"                 # el lock de bootstrap
}
```

A diferencia del bootstrap, el main module guarda su estado en S3.
`key` es la clave del objeto dentro del bucket — como la ruta de un archivo.
Podés tener múltiples módulos Terraform en el mismo bucket con distintas keys.

> **[ENTREVISTA]** ¿Por qué el backend no puede usar variables de Terraform?
> Porque el backend se inicializa ANTES que las variables. Terraform necesita
> saber dónde está el state antes de poder leer nada más. Por eso el bucket name
> está hardcodeado acá — es el único lugar donde está justificado.

---

### 6.4 — `infra/main/variables.tf` — parametrización

```hcl
variable "database_url" {
  description = "Supabase DATABASE_URL para que Lambda consulte el dólar blue"
  sensitive   = true   # Terraform nunca loguea este valor — no aparece en plan ni apply
}
```

`sensitive = true` es importante para credenciales: Terraform muestra el plan antes de
aplicar y podría mostrar el valor en pantalla. Con `sensitive`, lo reemplaza con `(sensitive value)`.

```hcl
variable "project" {
  default = "tasajusta"
}
```

Variables con `default` son opcionales — si no las pasás, usan ese valor.
Variables sin `default` son obligatorias — Terraform las pide interactivamente o vía `-var`.

---

### 6.5 — `infra/main/s3.tf` — los buckets del data lake

```hcl
resource "aws_s3_bucket" "models" {
  bucket = "${var.project}-models-${var.account_id}"
}
```

`${var.project}` es interpolación de variables en HCL (el lenguaje de Terraform).
El Account ID en el nombre garantiza unicidad global sin depender de la suerte.

```hcl
resource "aws_s3_bucket_versioning" "models" {
  bucket = aws_s3_bucket.models.id
  versioning_configuration {
    status = "Enabled"
  }
}
```

`aws_s3_bucket.models.id` es una **referencia de recursos**: Terraform entiende que
el `aws_s3_bucket_versioning` depende del `aws_s3_bucket.models` y los crea en orden.
No hace falta declararlas explícitamente — Terraform construye el grafo de dependencias solo.

---

### 6.6 — `infra/main/ecr.tf` — el registro de imágenes Docker

ECR (Elastic Container Registry) es el Docker Hub privado de AWS. Lambda necesita
que la imagen esté en ECR — no puede usar Docker Hub directamente.

```hcl
resource "aws_ecr_repository" "api" {
  name                 = "${var.project}-api"
  image_tag_mutability = "MUTABLE"  # permite reescribir el tag :latest
}
```

`MUTABLE` vs `IMMUTABLE`: mutable permite sobreescribir `tasajusta-api:latest` con
una imagen nueva. Immutable garantiza que un tag nunca cambia — útil para auditoría,
pero requiere usar tags únicos (sha del commit) en lugar de `:latest`.

```hcl
resource "aws_ecr_lifecycle_policy" "api" {
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 3
      }
      action = { type = "expire" }
    }]
  })
}
```

ECR cobra por GB almacenado. Esta lifecycle policy borra automáticamente imágenes
viejas cuando hay más de 3, manteniendo siempre las 3 más recientes. Sin esto,
cada deploy acumula una imagen nueva y el storage crece indefinidamente.

> **[ENTREVISTA]** ¿Por qué usar ECR en vez de Docker Hub para Lambda?
> Lambda solo puede usar imágenes de ECR (el registry privado de AWS) — es una
> limitación de diseño. Además, dentro de AWS la transferencia de datos entre ECR
> y Lambda es gratis; descargar desde Docker Hub cobraría egress.

---

### 6.7 — `infra/main/iam.tf` — permisos mínimos (Principle of Least Privilege)

```hcl
resource "aws_iam_role" "lambda" {
  name = "${var.project}-lambda-role"

  assume_role_policy = jsonencode({
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}
```

El `assume_role_policy` define **quién puede usar este rol**. `sts:AssumeRole` es el
permiso que permite a Lambda "ponerse el sombrero" de este rol y actuar con sus permisos.
Sin este bloque, Lambda no podría asumir el rol aunque existiera.

```hcl
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}
```

`AWSLambdaBasicExecutionRole` es una policy managed de AWS que da permiso para
escribir logs en CloudWatch. Sin esto, Lambda corre pero no podés ver nada de lo
que imprime.

```hcl
resource "aws_iam_role_policy" "lambda_s3_models" {
  policy = jsonencode({
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:GetObject", "s3:ListBucket"]
      Resource = [
        aws_s3_bucket.models.arn,
        "${aws_s3_bucket.models.arn}/*",   # necesitás ambos: el bucket y los objetos
      ]
    }]
  })
}
```

Lambda solo necesita leer modelos — no escribir, no borrar. Le damos solo
`GetObject` y `ListBucket`. Si el Lambda se compromete, el atacante no puede
borrar ni sobreescribir los modelos.

Necesitás el ARN del bucket Y el ARN con `/*`: el primero permite `ListBucket`
(ver qué hay), el segundo permite `GetObject` (descargar objetos específicos).

> **[ENTREVISTA]** ¿Qué es el Principle of Least Privilege?
> Dar a cada componente exactamente los permisos que necesita para funcionar,
> ni uno más. Si el Lambda solo lee, no le das write. Si solo necesita un bucket,
> no le das acceso a todos. Reduce el blast radius si algo se compromete.

---

### 6.8 — `infra/main/lambda.tf` — la función y su URL pública

```hcl
resource "aws_lambda_function" "predict" {
  package_type = "Image"
  image_uri    = "${aws_ecr_repository.api.repository_url}:latest"
  memory_size  = 512   # LightGBM + pandas en frío necesitan margen
  timeout      = 30    # cold start: descarga modelo de S3 + inicializa FastAPI
}
```

`package_type = "Image"` le dice a Lambda que use una imagen de contenedor.
La alternativa es `Zip` (un .zip con el código y deps), pero tiene límite de 250MB
descomprimido. LightGBM + pandas solos ya se acercan a ese límite.

```hcl
  environment {
    variables = {
      MODELS_BUCKET = aws_s3_bucket.models.bucket
      DATABASE_URL  = var.database_url
    }
  }
```

Las variables de entorno le llegan al proceso Python dentro del Lambda.
`MINIO_ENDPOINT` no está seteada → `get_s3_client()` detecta que es None y usa
el credential chain de AWS (el IAM role que definimos en `iam.tf`).

```hcl
resource "aws_lambda_function_url" "predict" {
  function_name      = aws_lambda_function.predict.function_name
  authorization_type = "NONE"   # URL pública, sin auth

  cors {
    allow_origins = ["*"]        # el dashboard en Vercel puede llamar a esta URL
    allow_methods = ["GET", "POST"]
    allow_headers = ["Content-Type"]
  }
}
```

`Function URL` es una URL HTTPS pública directa para el Lambda. La alternativa
es API Gateway, pero cuesta dinero. Function URLs son gratis dentro de la
capa gratuita de Lambda.

```hcl
resource "aws_cloudwatch_log_group" "predict" {
  name              = "/aws/lambda/${aws_lambda_function.predict.function_name}"
  retention_in_days = 7
}
```

Sin `retention_in_days`, CloudWatch guarda los logs **para siempre** — cobrando por
cada GB almacenado. 7 días es suficiente para debug y no acumula costo.

> **[ENTREVISTA]** ¿Por qué Function URL y no API Gateway?
> API Gateway agrega features como throttling, auth con API keys, y transformaciones
> de request/response. Para nuestra API pública simple, es overhead innecesario que
> además consume créditos. Function URL da una URL HTTPS directa gratis.

---

### 6.9 — `lambda.Dockerfile` — imagen de inferencia liviana

```dockerfile
FROM public.ecr.aws/lambda/python:3.11
```

La imagen base de AWS para Lambda en Python. Incluye el runtime de Lambda
(el handler que escucha eventos) y las herramientas del sistema necesarias.
**No** es la misma que `python:3.11-slim` del Dockerfile de dev.

```dockerfile
RUN yum install -y libgomp && yum clean all
```

Amazon Linux (la base de la imagen Lambda) usa `yum` en vez de `apt-get`.
`libgomp` es la misma dependencia de OpenMP que LightGBM necesita — igual que
en el Dockerfile de dev, pero instalada con el package manager correcto.
`yum clean all` borra el cache de paquetes para mantener la imagen liviana.

```dockerfile
COPY api/ api/
COPY ml/__init__.py ml/__init__.py
COPY ml/train_lgbm.py ml/train_lgbm.py
COPY etl/__init__.py etl/__init__.py
COPY etl/infra.py etl/infra.py
```

Copiamos solo lo necesario para inferencia. **No** copiamos:
- `ml/train_mlp.py` — PyTorch no está instalado, no se necesita para predicción
- `ml/train_lgbm.py` completo sí, porque `predict.py` importa `CAT_FEATURES` de ahí
- `etl/scrape_deruedas.py`, `etl/transform_autos.py`, etc. — son ETL, no inference

Esto mantiene la imagen chica y reduce la superficie de ataque.

```dockerfile
CMD ["api.lambda_handler.handler"]
```

Le dice al runtime de Lambda qué función ejecutar. El formato es
`módulo.función`. Cuando llega un request HTTP, Lambda llama a
`api.lambda_handler.handler(event, context)`.

---

### 6.10 — `api/lambda_handler.py` — el puente entre Lambda y FastAPI

```python
from mangum import Mangum
from api.main import app

handler = Mangum(app, lifespan="on")
```

**Mangum** es un adaptador ASGI → Lambda. Lambda recibe eventos con este formato:

```json
{
  "requestContext": { "http": { "method": "POST", "path": "/predict" } },
  "body": "{\"marca\": \"Toyota\", ...}",
  "headers": { "content-type": "application/json" }
}
```

FastAPI espera peticiones ASGI (el protocolo de servidores web Python como uvicorn).
Mangum traduce el evento de Lambda al formato que FastAPI entiende — y la respuesta
de FastAPI de vuelta al formato que Lambda espera.

`lifespan="on"` le dice a Mangum que ejecute el `lifespan` de FastAPI (la función
que carga el modelo desde S3) durante el cold start del Lambda.

> **[ENTREVISTA]** ¿Qué es ASGI? Es el protocolo asincrónico de Python para
> comunicación entre servidores web y aplicaciones. FastAPI, Starlette y Django
> son frameworks ASGI. Mangum hace de "adaptador" entre el mundo de AWS Lambda
> (que habla en eventos JSON) y el mundo ASGI.

---

### 6.11 — El cambio clave en `etl/infra.py`

```python
# Antes — siempre usaba MinIO:
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")

# Después — None significa "usá S3 real":
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")  # default None
```

```python
def get_s3_client():
    if MINIO_ENDPOINT:
        # Dev: MinIO con credenciales explícitas
        return boto3.client("s3", endpoint_url=MINIO_ENDPOINT, ...)
    # Prod: S3 real — boto3 usa el credential chain automático:
    # 1. Variables de entorno AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY
    # 2. IAM Role del Lambda (lo que usamos)
    # 3. ~/.aws/credentials (desarrollo local con SSO)
    return boto3.client("s3")
```

**El credential chain de boto3** es el mecanismo por el que boto3 busca credenciales
en orden. En Lambda, el IAM role que definimos en `iam.tf` se inyecta automáticamente
como variables de entorno temporales — boto3 las encuentra sin que hagamos nada.

> **[ENTREVISTA]** ¿Cómo maneja boto3 las credenciales en Lambda?
> AWS inyecta credenciales temporales (via STS) en las variables de entorno del Lambda
> basadas en el IAM role. boto3 las lee automáticamente a través del credential chain.
> No necesitás setear claves de acceso explícitamente — el rol lo hace todo.

---

### 6.12 — Orden de operaciones para el deploy

El deploy tiene un orden estricto porque hay dependencias entre pasos:

```
1. terraform apply (bootstrap)    → crea S3 + DynamoDB para el state
        ↓
2. terraform init (main)          → configura el backend remoto en S3
        ↓
3. terraform apply -target=ecr    → crea el repositorio ECR
        ↓
4. docker build + push a ECR      → sube la imagen Lambda
        ↓
5. terraform apply (main)         → crea Lambda + API Gateway usando la imagen de ECR
        ↓
6. terraform output api_url       → URL pública lista para usar
```

El paso 3 antes del 4 es el chicken-and-egg resuelto: ECR tiene que existir antes de
poder pushear la imagen, y Lambda tiene que poder referenciar una imagen existente.
`-target=aws_ecr_repository.api` le dice a Terraform que solo cree ese recurso por ahora.

---

### 6.13 — Por qué el Dockerfile necesita Python 3.12 (no 3.11)

El build falló tres veces hasta entender la causa raíz. Reconstruyendo el razonamiento:

**El problema:** LightGBM 4.x tiene como dependencia transitiva `scipy 1.17.1`, que al
instalarse necesita compilar con GCC >= 9.3. La imagen Lambda de Python 3.11 usa
**Amazon Linux 2 (AL2)** con GCC 7.3.1 — demasiado viejo.

**La cadena de dependencias:**
```
lightgbm 4.x → scipy 1.17.1 → BUILD requiere numpy >= 2.0
                                → numpy 2.x requiere GCC >= 9.3
                                       → AL2 tiene GCC 7.3.1 ❌
```

**El fix:** cambiar `python:3.11` → `python:3.12`. La imagen Lambda de Python 3.12
usa **Amazon Linux 2023 (AL2023)** con GCC 11 — suficiente para compilar todo.

| Base image | OS | GCC | glibc |
|---|---|---|---|
| `lambda/python:3.11` | Amazon Linux 2 | 7.3.1 | 2.26 |
| `lambda/python:3.12` | Amazon Linux 2023 | 11 | 2.34 |

El cambio del OS no fue explícito — viene implícito con la versión de Python.
Junto con el cambio: `yum` → `dnf` (el package manager de AL2023).

**Multi-stage build — por qué lo usamos:**
```dockerfile
FROM public.ecr.aws/lambda/python:3.12 AS builder
RUN dnf install -y libgomp gcc gcc-c++ make && dnf clean all
RUN pip install -r requirements-lambda.txt --target /build/packages

FROM public.ecr.aws/lambda/python:3.12        # runtime sin compilador
RUN dnf install -y libgomp && dnf clean all   # solo la librería de runtime
COPY --from=builder /build/packages /var/lang/lib/python3.12/site-packages/
```

El compilador (gcc) es necesario para instalar, pero no para correr. Sin multi-stage,
la imagen runtime incluiría ~200MB de herramientas de compilación que nunca se usan.
Con multi-stage: stage builder compila, stage runtime solo copia los resultados.

> **[ENTREVISTA]** ¿Qué es un multi-stage build? Un Dockerfile con múltiples `FROM`.
> Cada stage puede copiar artefactos del anterior con `COPY --from=builder`. El resultado
> final es solo el último stage — los anteriores no van a la imagen publicada. Úsalos
> para separar "entorno de compilación" de "entorno de runtime".

> **[ENTREVISTA]** ¿Por qué la versión de Python en Lambda afecta al compilador?
> Porque cada versión de Python en Lambda usa una imagen base diferente (AL2 vs AL2023).
> AL2023 es más moderno y viene con toolchain más reciente. No es algo que esté
> documentado de forma obvia — hay que saberlo o encontrarlo a golpe de builds fallidos.

---

### 6.14 — Por qué terminamos con API Gateway en vez de Lambda Function URL

**Lambda Function URLs** son URLs HTTPS públicas directas para un Lambda, gratis.
Las configuramos con `authorization_type = "NONE"` (sin auth) y el permiso correcto.
En teoría, deberían funcionar. En la práctica, en cuentas AWS recién creadas devuelven
403 `AccessDeniedException` aunque todo esté bien configurado.

**El diagnóstico — lo que investigamos:**

```bash
# El Lambda directo funciona perfectamente (200 OK):
aws lambda invoke --function-name tasajusta-predict --payload ... response.json
# → {"statusCode": 200, "body": "{\"status\":\"sin modelo\"}"}

# Pero la Function URL siempre da 403, sin llegar al Lambda (vacío en CloudWatch):
curl https://xxx.lambda-url.us-east-1.on.aws/health
# → {"Message":"Forbidden. For troubleshooting Function URL auth..."}
```

Cosas que verificamos y estaban correctas:
- `AuthType: NONE` ✅
- Permiso `lambda:InvokeFunctionUrl` con `Principal: *` y condición correcta ✅
- Lambda `State: Active`, sin VPC ✅
- SCP de la organización: solo `FullAWSAccess` (no bloquea nada) ✅
- No existe `get-public-access-block-config` para Lambda en CLI ni boto3 ✅

**La causa raíz:** cuentas AWS nuevas tienen restricciones temporales para acceso público
a Lambda Function URLs. La cuenta tiene `ConcurrentExecutions: 10` (el default histórico
era 1000) — señal de que AWS aplica límites conservadores a cuentas nuevas.

**La solución: API Gateway HTTP API v2** (`aws_apigatewayv2_api`)

```hcl
resource "aws_apigatewayv2_api" "api" {
  name          = "tasajusta-api"
  protocol_type = "HTTP"            # HTTP API, no REST API (más simple y barato)
  cors_configuration { ... }
}

resource "aws_apigatewayv2_integration" "lambda" {
  integration_type       = "AWS_PROXY"   # pasa el request completo al Lambda
  payload_format_version = "2.0"         # mismo formato que Function URLs
}

resource "aws_lambda_permission" "apigw" {
  action     = "lambda:InvokeFunction"   # distinto a lambda:InvokeFunctionUrl
  principal  = "apigateway.amazonaws.com"
  source_arn = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}
```

**La diferencia clave respecto a Function URL:**
- Function URL: invocación directa, sin infraestructura adicional, pero con restricciones en cuentas nuevas
- API Gateway: una capa intermedia que gestiona HTTP, redirige al Lambda, no tiene esas restricciones

Mangum soporta `payload_format_version = "2.0"` de API Gateway HTTP API — el mismo
formato que usan las Function URLs. El código FastAPI no cambió.

**Resultado:**
```bash
curl https://5yoo5ugs44.execute-api.us-east-1.amazonaws.com/health
# → {"status":"sin modelo","model_key":null,"dolar_blue":null}  HTTP 200 ✅
```

> **[ENTREVISTA]** ¿Cuándo usarías API Gateway sobre Lambda Function URL?
> API Gateway agrega throttling configurable, logging de acceso, custom domains,
> autorización con JWT o Lambda authorizer, y stage management (dev/staging/prod).
> Para producción real, API Gateway es la opción más robusta. Function URL es ideal
> cuando querés simplicidad máxima y el tráfico es confiable.

> **[ENTREVISTA]** ¿Qué es `payload_format_version` en API Gateway?
> Define el esquema del JSON que API Gateway manda al Lambda. v1.0 es el formato legacy
> (REST API). v2.0 es más simple: `requestContext.http.method` en vez de
> `requestContext.httpMethod`. Mangum detecta el formato automáticamente.

---

### 6.15 — Terraform state lock: qué hacer cuando se corrompe

Si interrumpís un `terraform apply` (Ctrl+C), el lock en DynamoDB queda sin liberar.
El próximo apply falla con:

```
Error acquiring the state lock
Lock Info:
  ID:        f3a2b1c9-...
  Operation: OperationTypeApply
```

**Fix:**
```bash
terraform force-unlock f3a2b1c9-...
```

Y si Terraform creó un recurso pero no lo registró en el state (por ejemplo, porque
el apply se interrumpió justo después de crear el recurso en AWS):

```bash
# Importar el recurso al state sin recrearlo
terraform import aws_lambda_permission.public_url tasajusta-predict/FunctionURLAllowPublicAccess
```

`terraform import` toma el recurso existente en AWS y lo agrega al state de Terraform.
A partir de ahí, Terraform sabe que ya existe y no lo va a recrear.

> **[ENTREVISTA]** ¿Qué pasa si corrés `terraform apply` dos veces sobre el mismo recurso?
> Terraform es declarativo e idempotente: compara el state actual con lo declarado en `.tf`
> y solo hace los cambios necesarios. Si el estado coincide, no hace nada.
> `terraform import` es la herramienta para sincronizar el state cuando hay recursos que
> existen en AWS pero Terraform no los conoce (creados manualmente o por un apply parcial).

---

## Sesión 7 — Scraper a escala nacional + GitHub Actions + Frontend completo

**Fecha:** 2026-07-02  
**Qué resolvimos:** el scraper traía solo 30 publicaciones de Mendoza. Lo reescribimos para cubrir
las 3 categorías de DeRuedas y las 24 provincias argentinas. Automatizamos el pipeline completo en
GitHub Actions con OIDC (sin credenciales hardcodeadas). Rediseñamos el frontend con Suspense
streaming y filtros interactivos.

---

### 7.1 — Por qué el scraper traía solo 30 publicaciones de Mendoza

El scraper original usaba `bus.asp?segmento=0` sin ningún parámetro de provincia.
La URL sin provincia en DeRuedas devuelve la **home page** del sitio, que muestra exactamente
30 publicaciones "destacadas" fijas — siempre las mismas, siempre de Mendoza (el datacenter del
sitio). Cada vez que avanzábamos la paginación (`&desde=15`, `&desde=30`...) volvían las mismas
30 URLs. El loop de paginación detectaba que no había URLs nuevas y terminaba inmediatamente.

```
# Lo que hacíamos — devuelve la home con 30 destacados:
GET bus.asp?segmento=0
GET bus.asp?segmento=0&desde=15   ← mismas URLs, loop termina

# Lo correcto — paginación real por provincia:
GET bus.asp?segmento=0&provincia=1&desde=0
GET bus.asp?segmento=0&provincia=1&desde=15   ← URLs nuevas, sigue
GET bus.asp?segmento=0&provincia=1&desde=30   ← hasta que no haya nuevas
GET bus.asp?segmento=0&provincia=2&desde=0    ← siguiente provincia
...
```

**El diagnóstico:** observamos la URL cuando clickeábamos "La Rioja" en el sitio:
`bus.asp?segmento=0&provincia=12`. La Rioja es la 12ava provincia en orden alfabético
— confirmado: hay 24 IDs (1 a 24) en orden alfabético de las 24 jurisdicciones argentinas.

> **[ENTREVISTA]** ¿Cómo descubrís el comportamiento real de una API sin docs?
> Usás DevTools → Network mientras navegás manualmente el sitio. Observás los parámetros
> reales de las URLs, comparás resultados con y sin parámetros, e inferís la lógica.

---

### 7.2 — Arquitectura del scraper reescrito: segmento × provincia

```python
SEGMENTOS = {0: "Autos", 1: "Utilitarios/Camionetas", 2: "Motos"}
PROVINCIA_IDS = range(1, 25)   # 24 jurisdicciones en orden alfabético

def collect_listing_urls(segmento, provincia_id, client):
    all_urls = set()
    desde = 0
    while True:
        r = client.get(f"{BASE_URL}/bus.asp",
            params={"segmento": segmento, "provincia": provincia_id, "desde": desde})
        page_urls = set(re.findall(r"/vendo/[^\s\"<']+", r.text))
        nuevas = page_urls - all_urls
        if not nuevas:
            break          # no hay más páginas para esta provincia
        all_urls |= nuevas
        desde += PAGE_SIZE
        time.sleep(CRAWL_DELAY)
    return all_urls
```

El loop principal es: `for segmento in SEGMENTOS: for provincia_id in PROVINCIA_IDS:`.
URLs que aparecen en múltiples provincias se deduplicaron automáticamente con el `set` global.

**Por qué `set`:** inserción O(1) y la operación `-` (diferencia de conjuntos) hace
deduplicación en O(1) por elemento.

**Bronze key cambió:** `autos_usados/{today}.json` → `vehiculos_usados/{today}.json`
para reflejar que incluimos los 3 segmentos.

**El campo `segmento`** se agregó a cada record y se propagó hasta Postgres:

```sql
ALTER TABLE autos_usados
ADD COLUMN IF NOT EXISTS segmento smallint NOT NULL DEFAULT 0;
```

`smallint` (2 bytes) para un valor 0-2 — no tiene sentido usar `integer` (4 bytes).

> **[ENTREVISTA]** ¿Por qué deduplicás URLs con un `set` global y no por provincia?
> Porque una publicación puede aparecer en búsquedas de distintas provincias. El set global
> garantiza que cada URL se scrapea exactamente una vez sin importar cuántas provincias la tienen.

---

### 7.3 — GitHub Actions + OIDC: credenciales temporales sin secrets

El workflow `etl-vehiculos.yml` corre el pipeline completo cada domingo a las 06:00 UTC
(03:00 ART, antes del horario laboral).

**El problema con credenciales de AWS en CI:** si guardás `AWS_ACCESS_KEY_ID` y
`AWS_SECRET_ACCESS_KEY` como GitHub secrets, son credenciales de larga vida.
Si alguien accede a los secrets, tiene acceso a tu AWS hasta que las rotés manualmente.

**La solución: OIDC (OpenID Connect)**

```yaml
permissions:
  id-token: write   # GitHub genera un token JWT firmado por GitHub
  contents: read

- uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ vars.AWS_ETL_ROLE_ARN }}
    aws-region: us-east-1
```

El flujo:
```
GitHub genera JWT firmado → AWS STS lo verifica → entrega credenciales temporales
(expiran solas al final del run, no hay secret que robar del YAML)
```

En AWS configurás un OIDC Provider que confía en GitHub y un IAM Role que especifica
qué repos pueden asumirlo y con qué permisos.

> **[ENTREVISTA]** ¿Qué es OIDC y por qué es mejor que guardar access keys en CI?
> OIDC es un protocolo de identidad federada. En vez de credenciales de larga vida,
> el CI genera un token firmado que identifica quién es (GitHub, repo X, branch Y).
> AWS confía en GitHub como Identity Provider y entrega credenciales temporales solo
> para ese run. No hay secret que rotar ni blast radius si se filtra el YAML.

---

### 7.4 — Supabase REST API: solución al problema de IPv6 en GitHub Actions

Los runners `ubuntu-latest` de GitHub Actions no pueden conectarse al puerto 5432 de
Supabase directamente (restricción de red IPv6 en el host directo de Supabase).

**El fix:** usar la API REST de Supabase (PostgREST) en lugar de psycopg2.
La REST API escucha en el puerto 443 (HTTPS) — sin restricciones de red.

```python
def load_via_rest(df):
    resp = httpx.post(
        f"{SUPABASE_URL}/rest/v1/autos_usados",
        headers={
            "apikey":        SUPABASE_SVC_KEY,
            "Authorization": f"Bearer {SUPABASE_SVC_KEY}",
            "Content-Type":  "application/json",
            "Prefer":        "resolution=merge-duplicates",   # ← upsert vía REST
        },
        json=df.to_dicts(),
    )
    resp.raise_for_status()

def run():
    if SUPABASE_URL and SUPABASE_SVC_KEY:
        load_via_rest(df)          # GitHub Actions / prod
    else:
        load_to_postgres(df, conn) # dev local con psycopg2
```

El header `Prefer: resolution=merge-duplicates` hace UPSERT — idempotente, sin duplicados.

**Dual-strategy pattern:** el mismo archivo detecta el entorno automáticamente.
El código de negocio no cambia, solo el transporte.

> **[ENTREVISTA]** ¿Por qué Supabase tiene una API REST además del puerto de Postgres?
> Supabase expone PostgREST — convierte tu schema de Postgres en una REST API con auth.
> Útil para clientes que no pueden conectarse directamente a Postgres (browsers, CI con
> restricciones de red). En este caso nos salvó del problema de IPv6 en GitHub Actions.

---

### 7.5 — Next.js Suspense: loading granular sin bloquear la UI

**El problema:** la home carga datos de tres fuentes distintas. Si todo carga junto,
el usuario espera el más lento de los tres antes de ver cualquier cosa.

**React Server Components + Suspense** resuelven esto:

```tsx
// page.tsx — Server Component
export default function HomePage() {
  return (
    <>
      <PredictForm />                          {/* client component — render inmediato */}

      <Suspense fallback={<DolarSkeleton />}>  {/* skeleton hasta que DolarSection resuelva */}
        <DolarSection />                       {/* server component con su propio fetch */}
      </Suspense>

      <Suspense fallback={<TableSkeleton />}>  {/* skeleton hasta que VehiculosSection resuelva */}
        <VehiculosSection />
      </Suspense>
    </>
  );
}
```

**Cómo funciona el streaming:**
1. Next.js empieza a renderizar en el servidor y envía navbar + hero + skeletons al cliente.
2. En paralelo, resuelve `DolarSection` y `VehiculosSection` (cada uno con su fetch).
3. Cuando terminan, envía el HTML final y reemplaza cada skeleton.

```
t=0ms   → navbar + hero + form + skeletons llegan al browser
t=200ms → DolarSection reemplaza el DolarSkeleton (API rápida)
t=800ms → VehiculosSection reemplaza el TableSkeleton (Supabase más lento)
```

**Por qué no `useEffect` + `fetch` en el cliente:**
- El fetch desde el cliente expone el Supabase URL y las keys al browser.
- `useEffect` corre después del render inicial — el usuario ve la página vacía primero.
- Server Components hacen el fetch en el servidor, donde las credenciales son seguras.

> **[ENTREVISTA]** ¿Qué diferencia hay entre un Server Component y un Client Component?
> Un Server Component se ejecuta solo en el servidor — accede a bases de datos, no tiene
> `useState`/`useEffect`. Un Client Component se ejecuta en el browser — puede tener estado
> y reactividad. La convención: `"use client"` al tope del archivo. Sin esa línea, es
> Server Component por default en Next.js 13+.

---

### 7.6 — `useMemo`: filtrado eficiente en el cliente

`AutosTable` recibe 1000 vehículos y filtra en el cliente sin requests extra.

```tsx
const filtered = useMemo(() => {
    return autos.filter((a) => {
        if (marca     && a.marca !== marca)           return false;
        if (provincia && a.provincia !== provincia)   return false;
        if (anioMin   && a.anio < parseInt(anioMin))  return false;
        if (precioMax && a.precio_ars > parseInt(precioMax)) return false;
        // ...
        return true;
    });
}, [autos, marca, provincia, anioMin, anioMax, precioMax, search]);

const sorted = useMemo(() => {
    return [...filtered].sort(/* ... */);
}, [filtered, sortKey, sortDir]);
```

Sin `useMemo`, el filtrado corre en cada render del componente — incluyendo renders
causados por cada tecla que escribís en el search. Con 1000 autos y 6 filtros, eso
es trabajo innecesario en cada keystroke.

**`useMemo` vs `useCallback`:** `useMemo` memoiza el *valor* de retorno.
`useCallback` memoiza la *función* en sí. Aquí queremos el array filtrado (un valor).

> **[ENTREVISTA]** ¿Cuándo usás `useMemo`? Cuando tenés una computación costosa que no
> debería repetirse en cada render. Regla práctica: solo si el profiler muestra que ese
> cálculo es el cuello de botella — tiene su propio overhead de bookkeeping.

---

### 7.7 — Diseño del workflow de GitHub Actions

```yaml
jobs:
  scrape-transform-load:
    timeout-minutes: 360   # scraper puede tardar horas (3 segmentos × 24 provincias × 5s delay)

  retrain:
    needs: scrape-transform-load   # solo corre si el primer job termina OK
    timeout-minutes: 60
```

**`needs:`** crea dependencia entre jobs. Si el scraper falla, el retrain no corre —
no tiene sentido reentrenar con los mismos datos de la semana anterior.

**Cron expression `0 6 * * 0`:**
- `0 6` = 06:00 UTC = 03:00 ART (horario de menor tráfico)
- `* * 0` = cualquier día del mes, cualquier mes, domingo

**`workflow_dispatch:`** permite disparar el workflow manualmente desde la UI de GitHub Actions.
Útil para la primera ejecución tras un cambio o para debugging.

> **[ENTREVISTA]** ¿Por qué separar en dos jobs y no un solo script?
> Timeout distinto (horas vs minutos) y fault isolation: si el scraper falla, el retrain
> no corre. En un solo script, un fallo en el medio deja el estado indefinido. Los jobs
> también podrían correr en runners distintos en paralelo si no hubiera dependencia.

---

### 7.8 — `requirements-train.txt` y el bug de psycopg2 en el retrain

El job de retrain falló con `ModuleNotFoundError: No module named 'psycopg2'`.

**Por qué:** `gold_autos.py` importa desde `etl.infra`, que tiene:
```python
import psycopg2   # ← import a nivel de módulo
```

Aunque el retrain nunca usa psycopg2 directamente, el import a nivel de módulo hace
que Python trate de cargarlo en el momento del import. Si no está instalado, falla
antes de ejecutar una sola línea de código.

**Fix:** agregar `psycopg2-binary>=2.9` a `requirements-train.txt`.

**La alternativa arquitectónica:** lazy import dentro de la función que lo usa:
```python
def get_pg_connection():
    import psycopg2   # ← solo se carga si se llama esta función
```

En este caso la solución simple fue la correcta.

> **[ENTREVISTA]** ¿Cuándo usarías un lazy import?
> Cuando la dependencia es opcional o pesada y no siempre se necesita.
> Por ejemplo, `import torch` demora varios segundos — si solo se usa en el path
> de entrenamiento, un lazy import evita ese overhead en los otros paths.

---

### 7.9 — Las 23 provincias de Argentina en DeRuedas (IDs 1-23)

**Trampita:** el ID 1 es Mendoza (la sede del sitio), no Buenos Aires. El resto siguen
orden alfabético del 2 al 23. DeRuedas tiene un solo "Buenos Aires" — no separa
Provincia y CABA. La Rioja = 12 sigue siendo correcto.

| ID | Provincia | ID | Provincia |
|----|-----------|----|-----------|
| 1  | Mendoza              | 13 | Misiones |
| 2  | Buenos Aires         | 14 | Neuquén |
| 3  | Catamarca            | 15 | Río Negro |
| 4  | Chaco                | 16 | Salta |
| 5  | Chubut               | 17 | San Juan |
| 6  | Córdoba              | 18 | San Luis |
| 7  | Corrientes           | 19 | Santa Cruz |
| 8  | Entre Ríos           | 20 | Santa Fe |
| 9  | Formosa              | 21 | Santiago del Estero |
| 10 | Jujuy                | 22 | Tierra del Fuego |
| 11 | La Pampa             | 23 | Tucumán |
| 12 | La Rioja             | |  |

El scraper usaba `range(1, 25)` (IDs 1-24) — los IDs 24 y 25 no existen y generaban
requests innecesarios. Corregido a `range(1, 24)` (IDs 1-23).

`PredictForm.tsx` tiene "Buenos Aires Ciudad" como entrada separada que no matchea nada
en los datos de DeRuedas — pendiente limpiar ese dropdown.

---

## Sesión 8 — Pipeline de CI/CD completo: scraper + retrain automático

**Fecha:** 2026-07-06  
**Qué resolvimos:** el retrain en GitHub Actions fallaba en cadena: token OIDC vencía, gold_autos
no podía conectarse a Supabase, las dependencias de requirements-train.txt estaban incompletas,
el bucket de modelos tenía nombre hardcodeado y el rol IAM no tenía permisos sobre él. Además
creamos un workflow standalone para reentrenar sin volver a scrapear.

---

### 8.1 — OIDC token expiry: el token vence mientras el scraper sigue corriendo

El error fue `ExpiredTokenException` en el paso de upload a S3 — después de 65+ minutos.

**Por qué:** el token OIDC que GitHub emite tiene un default de **1 hora**. El scraper completo
(3 segmentos × 23 provincias × Crawl-delay 5s) puede tardar hasta 3-4 horas.

**Dos cambios necesarios — si falta uno, sigue rompiendo:**

```yaml
# .github/workflows/etl-vehiculos.yml
- uses: aws-actions/configure-aws-credentials@v4
  with:
    role-duration-seconds: 21600   # ← le pedimos 6 horas al token OIDC
```

```hcl
# infra/main/github_oidc.tf
resource "aws_iam_role" "github_etl" {
  max_session_duration = 21600   # ← AWS tiene que permitir sesiones de hasta 6 horas
}
```

Si pedís 6 horas en el workflow pero el IAM role tiene `max_session_duration = 3600` (default),
AWS rechaza la solicitud. Ambos tienen que coincidir.

> **[ENTREVISTA]** ¿Por qué el token OIDC tiene un límite de tiempo?
> Por diseño de seguridad: las credenciales temporales de STS (que OIDC entrega) siempre
> expiran. Si el token se filtra, tiene una ventana de vida limitada. El límite configurable
> `max_session_duration` en el IAM role define el máximo que podés pedir — AWS nunca entrega
> una sesión más larga que eso.

---

### 8.2 — S3 auto-discovery: no asumir que los datos son de hoy

`gold_autos.py` y `train_lgbm.py` usaban `date.today()` para construir el path del archivo.
Si el scraper corre el domingo y el retrain corre el martes, `date.today()` busca archivos
del martes que no existen → `NoSuchKey`.

**Fix:** listar los objetos del bucket y tomar el más reciente.

```python
def latest_silver_date(s3_client) -> date:
    resp = s3_client.list_objects_v2(Bucket=SILVER_BUCKET, Prefix="silver/autos_usados/")
    keys = [o["Key"] for o in resp.get("Contents", [])]
    if not keys:
        raise FileNotFoundError("No hay archivos silver en S3")
    # el key es "silver/autos_usados/2026-07-06.parquet" → parseamos la fecha del nombre
    dates = [date.fromisoformat(k.split("/")[-1].replace(".parquet", "")) for k in keys]
    return max(dates)
```

`run()` ahora recibe `day: date | None = None` y hace `day = day or latest_silver_date(s3)`.

**Ventaja:** el retrain siempre usa los datos disponibles más recientes, sin importar cuándo corra.
Permite disparar el retrain manualmente días después del scraper sin pasar parámetros.

> **[ENTREVISTA]** ¿Cómo listás los objetos de un bucket de S3 para encontrar el más reciente?
> Con `list_objects_v2()`. Filtrás por prefijo para no listar todo el bucket, extraés las fechas
> de los nombres de archivo (que son determinísticos por diseño), y tomás el `max()`.
> Es barato — una sola llamada de API, no descarga los archivos.

---

### 8.3 — Workflow standalone de retrain

El job de retrain en `etl-vehiculos.yml` depende del scraper (`needs: scrape-transform-load`).
Si querés reentrenar usando datos ya en S3 — sin correr el scraper de 3 horas — necesitás
un workflow separado.

```yaml
# .github/workflows/retrain.yml
on:
  workflow_dispatch:   # solo manual — no tiene cron propio

jobs:
  retrain:
    steps:
      - name: Gold silver → gold
        env:
          MINIO_BUCKET:         tasajusta-datalake-966940665955
          SUPABASE_URL:         https://rcmxwfmemhvjynorrpnd.supabase.co
          SUPABASE_SERVICE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
        run: python -m etl.gold_autos   # usa latest_silver_date() internamente

      - name: Entrenar LightGBM → S3
        env:
          MINIO_BUCKET:  tasajusta-datalake-966940665955
          MODELS_BUCKET: tasajusta-models-966940665955
        run: python -m ml.train_lgbm    # usa latest_gold_date() internamente
```

**Por qué separar en dos archivos y no reusar con `workflow_call`:**
El retrain standalone tiene un timeout distinto (60 min vs 360 min) y no necesita
re-configurar el step de `role-duration-seconds: 21600` del scraper. La duplicación
de configuración YAML es el precio de la independencia — justificado para debugging.

> **[ENTREVISTA]** ¿Cuándo usarías `workflow_call` vs dos archivos separados?
> `workflow_call` es un workflow reutilizable (como una función). Tiene sentido cuando
> la lógica es idéntica y querés un único punto de mantenimiento. Con timeouts y pasos
> distintos, dos archivos son más claros — menos "magia" para alguien que lee el CI.

---

### 8.4 — IAM: extender permisos a un segundo bucket

El rol `github_etl` solo tenía acceso al bucket `datalake`. El retrain necesita también
escribir en el bucket `models`. Sin el permiso, `HeadBucket` devuelve 403/404.

**Patrón correcto en Terraform: múltiples `Statement` en la misma policy**

```hcl
resource "aws_iam_role_policy" "github_etl_s3" {
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["s3:PutObject", "s3:GetObject", "s3:ListBucket"]
        Resource = [aws_s3_bucket.datalake.arn, "${aws_s3_bucket.datalake.arn}/*"]
      },
      {
        Effect = "Allow"
        Action = ["s3:PutObject", "s3:GetObject", "s3:ListBucket"]
        Resource = [aws_s3_bucket.models.arn, "${aws_s3_bucket.models.arn}/*"]   # ← nuevo
      },
    ]
  })
}
```

Necesitás el ARN del bucket (para `ListBucket`) y `${arn}/*` (para `GetObject`/`PutObject`).
Son dos recursos distintos en el modelo de permisos de S3 — uno controla operaciones sobre
el bucket, otro sobre los objetos dentro.

Aplicado con `-target`:
```bash
terraform apply -target=aws_iam_role_policy.github_etl_s3
```

> **[ENTREVISTA]** ¿Por qué necesitás el ARN del bucket Y el ARN con `/*`?
> `ListBucket` opera sobre el bucket como entidad. `GetObject`/`PutObject` operan sobre
> los objetos dentro. Son niveles distintos en el modelo de IAM de S3 — sin `/*`,
> podés listar el bucket pero no descargar nada.

---

### 8.5 — `terraform apply -target` y por qué igual pide todas las variables

```bash
terraform apply -target=aws_iam_role_policy.github_etl_s3
# → var.database_url: Enter a value:
```

Parece raro: solo estamos tocando una IAM policy, ¿para qué necesita `database_url`?

**Por qué:** Terraform evalúa **todas** las variables antes de correr cualquier target.
Lo necesita para construir el grafo completo de dependencias y luego filtrar al recurso
objetivo. La variable `database_url` está declarada sin `default` en `variables.tf` →
Terraform la marca como obligatoria al cargar la configuración, sin importar qué targets uses.

**La solución limpia: `terraform.tfvars`**

```hcl
# infra/main/terraform.tfvars  (en .gitignore — nunca al repo)
database_url = "postgresql://postgres:contraseña@db.xxx.supabase.co:5432/postgres"
```

Terraform lo carga automáticamente si existe. No tenés que pasarlo cada vez con `-var`.
El `.gitignore` ya tiene `*.tfvars` — las credenciales nunca van al repo.

> **[ENTREVISTA]** ¿Por qué Terraform pide variables que no usa el recurso objetivo?
> Terraform es declarativo: antes de ejecutar cualquier cosa, parsea el módulo completo
> y construye el grafo de dependencias. Las variables sin default son parte de la interfaz
> del módulo — Terraform las necesita para saber que la configuración es válida, antes de
> decidir qué subset de recursos crear.

---

### 8.6 — `requirements-train.txt`: las dependencias transitivas que faltaban

El job de retrain fallaba sucesivamente con módulos faltantes. Cada uno tenía una causa:

| Error | Por qué faltaba |
|---|---|
| `ModuleNotFoundError: httpx` | `gold_autos.py` importa `httpx` para la Supabase REST API |
| `ImportError: unable to find a usable engine; tried pyarrow` | `pandas.read_parquet()` necesita `pyarrow` como backend |

**La lección:** `requirements-train.txt` tiene que incluir **todas las dependencias transitivas**
que se usan en el path de ejecución — aunque el módulo principal no las importe directamente.

`gold_autos.py` importa de `etl.gold_autos`, que importa `httpx`. El job de retrain corre
`python -m etl.gold_autos` → Python carga el módulo → falla al importar `httpx` si no está.

```
# requirements-train.txt — versión correcta
httpx>=0.27          # gold_autos.py usa httpx para Supabase REST
pyarrow>=14.0        # pandas.read_parquet necesita pyarrow como engine
lightgbm>=4.0
scikit-learn>=1.5
pandas>=2.0
polars>=0.20
boto3>=1.34
psycopg2-binary>=2.9
python-dotenv>=1.0
```

> **[ENTREVISTA]** ¿Cómo identificás qué dependencias van en qué requirements file?
> Trazás el grafo de imports de cada entry point. Para el retrain: `python -m ml.train_lgbm`
> → imports de `ml/train_lgbm.py` → imports de `etl/gold_autos.py` → imports de `etl/infra.py`.
> Cada `import` a nivel de módulo se carga siempre. Los lazy imports (dentro de funciones)
> solo si se llaman.

---

## Sesión 9 — Scoring pipeline, endpoints de observabilidad y rediseño del frontend

**Fecha:** 2026-07-06  
**Qué resolvimos:** el pipeline de scoring fallaba con 400 Bad Request al hacer upsert en Supabase.
Agregamos endpoints `/health` y `/metrics` a la API Lambda. Rediseñamos el frontend para que sea
coherente con el ícono de la marca y se parezca a los marketplaces reales del mercado argentino.
También integramos TasaJusta al CV personal.

---

### 9.1 — Por qué PostgREST upsert no es un UPDATE puro

El error era:

```
400 Bad Request
null value in column "fecha" of relation "autos_usados" violates not-null constraint
```

El código hacía:

```python
httpx.post(
    f"{SUPABASE_URL}/rest/v1/autos_usados?on_conflict=cod",
    headers={"Prefer": "resolution=merge-duplicates", ...},
    json=records,
)
```

**Por qué fallaba:** `on_conflict=cod` le dice a PostgREST que haga UPSERT — si el `cod` ya existe,
actualiza; si no existe, inserta. Suena bien, pero hay `cod`s de runs anteriores que no están en
el batch actual. Para esos `cod`s desconocidos, PostgREST hace INSERT → la columna `fecha` (NOT NULL)
no viene en el payload → constraint violation.

**La solución: una función SQL que hace UPDATE puro, sin INSERT**

```sql
-- Supabase migration: create_batch_update_scores_function
CREATE OR REPLACE FUNCTION batch_update_scores(records jsonb)
RETURNS void LANGUAGE sql AS $$
  UPDATE autos_usados AS a
  SET precio_estimado = (r->>'precio_estimado')::bigint,
      oportunidad_score = (r->>'oportunidad_score')::real
  FROM jsonb_array_elements(records) AS r
  WHERE a.cod = r->>'cod';
$$;
```

Y el cliente llama al RPC en vez de la tabla directamente:

```python
httpx.post(
    f"{SUPABASE_URL}/rest/v1/rpc/batch_update_scores",
    json={"records": records},
)
```

Las funciones de Supabase viven en `POST /rest/v1/rpc/{nombre}` y bypasean completamente las
restricciones de la tabla — son SQL puro. Si el `cod` no existe, el `UPDATE` simplemente no
toca ninguna fila, sin error.

> **[ENTREVISTA]** ¿Cuándo usarías una función RPC en Supabase en vez del endpoint de tabla REST?
> Cuando necesitás lógica que no encaja en el CRUD estándar: operaciones atómicas sobre múltiples
> tablas, UPDATE sin INSERT (el caso de UPSERT con columnas NOT NULL), o queries que serían
> ineficientes en múltiples llamadas REST. La función corre server-side en Postgres — una sola
> llamada de red para operaciones complejas.

---

### 9.2 — `/health`: HTTP status codes que entienden las herramientas de infraestructura

Antes, `/health` devolvía siempre HTTP 200 aunque el modelo no estuviera cargado:

```json
{"status": "sin modelo"}   // con 200 OK
```

El problema: los load balancers, uptime monitors y orquestadores como ECS Health Checks
interpretan el status code HTTP, no el body JSON. Un 200 con `"sin modelo"` en el body es
invisible para el 99% de las herramientas de infraestructura.

**El fix:**

```python
@router.get("/health")
def health(request: Request):
    state = request.app.state
    ok = state.model is not None
    return JSONResponse(
        status_code=200 if ok else 503,   # 503 = Service Unavailable
        content={
            "status": "ok" if ok else "sin modelo",
            "model_key": state.model_key,
            "dolar_blue": state.dolar_blue,
            "started_at": getattr(state, "started_at", None),
        },
    )
```

**Por qué 503 y no 500:** HTTP 503 significa "el servicio existe pero no está listo para atender
requests". Un 500 implica un error inesperado. Un Lambda que arrancó bien pero todavía no bajó
el modelo es exactamente el caso de 503: la app funciona, pero el servicio no está disponible.

> **[ENTREVISTA]** ¿Por qué importa el status code HTTP en un endpoint de health check?
> Las herramientas de infraestructura leen el código HTTP, no el body. Un load balancer que
> ve 503 saca el nodo del pool. Un uptime monitor que ve 200 no alerta aunque el body diga error.
> La semántica de HTTP es el contrato con tu infraestructura — si la rompés, perdés observabilidad.

---

### 9.3 — `/metrics`: contar filas sin traer los datos

El endpoint de métricas necesitaba contar cuántos autos hay en la tabla y cuántos son
oportunidades — sin descargar las filas completas.

**Solución: HEAD con `Prefer: count=exact`**

```python
def _count(filters: dict | None = None) -> int:
    params = {k: v for k, v in (filters or {}).items()}
    resp = httpx.head(
        f"{SUPABASE_URL}/rest/v1/autos_usados",
        headers={
            ...,
            "Prefer": "count=exact",  # PostgREST devuelve Content-Range: */N
        },
        params=params,
    )
    # Content-Range: 0-0/1234  →  parsear el total después del "/"
    content_range = resp.headers.get("content-range", "*/0")
    return int(content_range.split("/")[-1])
```

**Por qué `HEAD` y no `GET`:** el verbo HTTP HEAD le pide al servidor el header de la respuesta
sin el body. PostgREST devuelve el header `Content-Range: 0-0/1234` donde el número después del
`/` es el total de filas. Nunca se transfieren los datos — solo un número.

**Por qué `app.state` para `predictions_served`:**

```python
# En lifespan (una sola vez al arrancar el Lambda)
app.state.started_at = datetime.now(timezone.utc).isoformat()
app.state.predictions_served = 0

# En cada predict
state.predictions_served += 1
```

`app.state` sobrevive entre requests dentro de la misma instancia Lambda. Un Lambda "tibio"
(warm) reutiliza el proceso Python — el estado en memoria persiste. Pero si AWS escala a
dos instancias, cada una tiene su propio contador. Para conteo global necesitarías Redis o DynamoDB.

> **[ENTREVISTA]** ¿Qué diferencia hay entre guardar estado en `app.state` vs una variable global?
> Funcionalmente, poco. La diferencia es de claridad y lifecycle: `app.state` es el objeto de
> estado oficial de FastAPI/Starlette, accesible desde `request.app.state` en cualquier handler.
> Una variable global funciona igual pero no está atada al ciclo de vida de la app — si en algún
> momento instanciás dos apps en el mismo proceso (tests), comparten el global pero no el state.

---

### 9.4 — Rediseño del frontend: coherencia entre ícono y paleta

El primer rediseño usó una paleta ambar (cálida) que visualmente "peleaba" contra el ícono
de la app, que tiene azul `#2974b4` y verde `#4caf50`.

**Regla:** la paleta siempre tiene que derivar de los colores del ícono o logo de la marca.
Si los dos no se ven bien juntos en pantalla, el problema es la paleta, no el ícono.

**Configuración en `tailwind.config.ts`:**

```ts
colors: {
  brand: {
    50:  "#EEF5FB",
    200: "#A0C4E8",
    300: "#6EA8D9",
    500: "#2974b4",  // ← color exacto del ícono
    700: "#1A4F7E",
    900: "#081C30",
  },
  sage: {
    50:  "#F0FDF4",
    200: "#A7F3D0",
    500: "#4caf50",  // ← verde del ícono
    600: "#3A9440",
    700: "#2D7333",
  },
}
```

**Decisión de diseño: form-in-hero (dos columnas)**

Sites como infoauto.com.ar y deruedas.com.ar no tienen hero decorativo + CTA separado.
El formulario de cotización es el hero. Estructura:

```
┌─────────────────────────────────────────┐
│  Navbar (white, sticky)                  │
├─────────────────────────────────────────┤
│  Hero (bg-slate-50)                      │
│  ┌─────────────────┐ ┌────────────────┐  │
│  │ Texto izquierdo │ │  PredictForm   │  │
│  │ Steps 1-2-3     │ │  (card blanca, │  │
│  │                 │ │  shadow-xl)    │  │
│  └─────────────────┘ └────────────────┘  │
├─────────────────────────────────────────┤
│  Main: Dólar / Oportunidades / Tabla     │
├─────────────────────────────────────────┤
│  Footer (bg-brand-900, dark)             │
└─────────────────────────────────────────┘
```

> **[ENTREVISTA]** ¿Cómo elegís una paleta de colores para un proyecto?
> Partís de los colores de la identidad visual (logo/ícono). Construís una escala de 50 a 900
> por cada color base — herramientas como Tailwind shades o Radix Colors lo automatizan. 
> Verificás que el contraste sea accesible (WCAG AA mínimo) entre texto y fondo. Y en light mode,
> los fondos deben ser claros (slate-50, white) con texto oscuro (slate-900) — no al revés.

---

### 9.5 — Lambda redeploy: no existe un workflow de deploy

Los tres workflows del repo (`etl-dolar.yml`, `etl-vehiculos.yml`, `retrain.yml`) solo corren
código Python en un runner de GitHub Actions. Ninguno toca la Lambda.

**Por qué:** el código de la Lambda vive en una imagen Docker subida a ECR. Para "desplegar
cambios en la API", la secuencia es:

```
1. docker build -t tasajusta-api .   ← construye imagen con el código nuevo
2. docker tag ... → ECR              ← sube la imagen al registry de AWS
3. aws lambda update-function-code   ← apunta la Lambda a la nueva imagen
```

Hoy ese proceso es manual via Terraform:

```bash
cd infra/main
terraform apply -target=aws_lambda_function.api
```

o manual con la CLI:

```bash
aws ecr get-login-password | docker login --username AWS --password-stdin <ecr-uri>
docker build -t tasajusta-api api/
docker tag tasajusta-api:latest <ecr-uri>/tasajusta-api:latest
docker push <ecr-uri>/tasajusta-api:latest
aws lambda update-function-code --function-name tasajusta-api \
  --image-uri <ecr-uri>/tasajusta-api:latest
```

Para automatizarlo haría falta un cuarto workflow `.github/workflows/deploy-lambda.yml` con
trigger `push` en `api/**` — lo natural para Fase 3.

> **[ENTREVISTA]** ¿Por qué Lambda no se actualiza automáticamente cuando pusheas código?
> Porque la Lambda corre una imagen Docker, no el código fuente. El link entre Lambda y código
> es el URI de imagen en ECR. Tenés que reconstruir la imagen, pushearla y actualizar el link.
> Es el mismo modelo que cualquier servicio containerizado: el código cambia, la imagen cambia,
> el deploy apunta a la nueva imagen.

---

## Sesión 10 — Deploy automático de Lambda con GitHub Actions

**Fecha:** 2026-07-06  
**Qué resolvimos:** el deploy de la Lambda era manual (Terraform o CLI). Creamos un workflow
`deploy-lambda.yml` que se dispara automáticamente cada vez que cambia código en `api/**`.

---

### 10.1 — Por qué ETL y Lambda se despliegan de formas completamente distintas

Los tres workflows existentes (ETL, retrain) corren scripts Python en un runner efímero de
GitHub Actions. El runner instala Python, corre el script, el resultado va a S3/Supabase,
y el runner se destruye. No hay "servicio" — solo un proceso que empieza, hace algo y termina.

La Lambda es distinta: es una imagen Docker que está parada en AWS esperando requests.
Cuando cambiás el código, AWS no se entera — sigue sirviendo la imagen vieja. Para actualizar
hay que:

```
1. docker build    → construir nueva imagen con el código nuevo
2. docker push ECR → subir la imagen al registry privado de AWS
3. lambda update   → apuntar la Lambda a la nueva imagen
```

**Por qué la web (Vercel) no necesita esto:** Vercel hace el equivalente automáticamente.
Cada push al repo reconstruye el bundle de Next.js y lo despliega en su CDN. El modelo
"conectar repo → push → deploy" que conocés de Vercel es lo que estamos replicando acá para Lambda.

---

### 10.2 — Rol IAM separado para deploy: Principle of Least Privilege

El rol `github_etl` que ya existía tiene permisos de S3 (leer/escribir datalake y modelos).
**No** tiene permisos de ECR ni de Lambda — y no debería tenerlos.

Si usáramos el mismo rol para ETL y deploy, un script de scraping comprometido podría
reescribir la imagen de producción. Permisos mínimos = superficie de ataque mínima.

Nuevo rol `github_deploy` en Terraform:

```hcl
resource "aws_iam_role" "github_deploy" {
  name = "tasajusta-github-deploy"

  assume_role_policy = jsonencode({
    Condition = {
      StringEquals = {
        # Solo el branch master puede deployar — no feature branches
        "token.actions.githubusercontent.com:sub" =
          "repo:matiasjavierlucero/tasajusta:ref:refs/heads/master"
      }
    }
  })
}

resource "aws_iam_role_policy" "github_deploy" {
  policy = jsonencode({
    Statement = [
      { Action = "ecr:GetAuthorizationToken",   Resource = "*" },
      { Action = ["ecr:BatchCheckLayerAvailability", "ecr:PutImage", ...],
        Resource = aws_ecr_repository.api.arn },
      { Action = "lambda:UpdateFunctionCode",
        Resource = aws_lambda_function.predict.arn },
    ]
  })
}
```

**Por qué `GetAuthorizationToken` necesita `Resource = "*"`:** este permiso no aplica a un
repo de ECR específico — es una operación a nivel de cuenta que obtiene un token de acceso
temporal para Docker. AWS siempre lo exige en `*`.

> **[ENTREVISTA]** ¿Cómo restringís qué branches pueden asumir un rol IAM en GitHub Actions?
> La trust policy del rol usa la condición `StringEquals` sobre el claim `sub` del JWT de GitHub.
> El claim `sub` incluye el ref: `repo:owner/repo:ref:refs/heads/master`. Si usás `StringLike`
> con `*`, cualquier branch puede asumir el rol. Con `StringEquals` y el ref completo, solo
> el branch master puede — un PR o feature branch recibe 403 al intentar asumir el rol.

---

### 10.3 — Estructura del workflow

```yaml
# .github/workflows/deploy-lambda.yml
on:
  push:
    branches: [master]
    paths:
      - "api/**"
      - "requirements/lambda.txt"
      - "lambda.Dockerfile"
```

**Por qué `paths`:** sin el filtro, un push que solo cambia `docs/` o `web/` dispararía
un rebuild de 15+ minutos de la imagen Docker. El filtro limita el trigger a los archivos
que realmente afectan la Lambda.

**Los cuatro pasos del job:**

```
1. configure-aws-credentials  →  OIDC: cambiar JWT de GitHub por credenciales AWS temporales
2. amazon-ecr-login           →  login de Docker al registry privado de ECR
3. docker build + push        →  construir imagen y subir a ECR (2 tags: latest + sha del commit)
4. lambda update-function-code →  apuntar Lambda a la nueva imagen
```

**Por qué taggear con el SHA del commit:**

```bash
docker push $REGISTRY/$ECR_REPOSITORY:latest        # lo que sirve ahora
docker push $REGISTRY/$ECR_REPOSITORY:${{ github.sha }}  # trazabilidad
```

Si en producción hay un bug, podés ver en AWS el SHA del commit que está corriendo y hacer
`git log` para saber exactamente qué código está en producción. Con solo `latest` esa
trazabilidad se pierde.

> **[ENTREVISTA]** ¿Qué es `amazon-ecr-login@v2` y por qué se usa?
> Es una GitHub Action oficial de AWS que ejecuta `aws ecr get-login-password | docker login`.
> Su output `registry` te da la URL completa del registry (`<account>.dkr.ecr.<region>.amazonaws.com`)
> sin hardcodear el account ID en el workflow. Limpio y portable.

---

### 10.4 — `workflow_dispatch`: correr el deploy desde la UI sin pushear

```yaml
on:
  push:
    branches: [master]
    paths: [...]
  workflow_dispatch:   # ← habilita el botón "Run workflow" en GitHub Actions
```

`workflow_dispatch` sin parámetros agrega un botón en `repo → Actions → Deploy Lambda API → Run workflow`.
Elegís el branch y lo disparás manualmente — útil para hacer rollback a una imagen vieja,
para probar sin tocar código, o para el primer deploy después de configurar el rol IAM.

Los dos triggers son independientes: un push a `api/**` lo dispara solo; un deploy manual
corre el mismo job desde el commit que elijas, sin necesidad de cambiar nada.

> **[ENTREVISTA]** ¿Cuándo usarías `workflow_dispatch` vs un trigger automático?
> `workflow_dispatch` es para operaciones que requieren intención explícita: deployar a
> producción en un momento específico, reentrenar con datos nuevos sin esperar el cron,
> o correr un job de mantenimiento. El trigger automático es para el path feliz del día a día.
> Tener ambos es lo más flexible — el auto cubre el 95% de los casos, el manual cubre el resto.

---

### 10.5 — Activar el workflow: pasos necesarios

El workflow usa `vars.AWS_DEPLOY_ROLE_ARN` — una variable de repositorio en GitHub.
Tiene que existir antes de que el workflow corra, de lo contrario el step de OIDC falla.

**Secuencia de activación:**

```bash
# 1. Crear el rol IAM en AWS
cd infra/main
terraform apply   # crea aws_iam_role.github_deploy + policy

# 2. Ver el ARN del rol recién creado
terraform output github_deploy_role_arn
# → arn:aws:iam::966940665955:role/tasajusta-github-deploy

# 3. Agregar la variable en GitHub
#    repo → Settings → Secrets and variables → Actions → Variables → New repository variable
#    Name: AWS_DEPLOY_ROLE_ARN
#    Value: arn:aws:iam::966940665955:role/tasajusta-github-deploy

# 4. Hacer un push a api/** para verificar que el workflow se dispara
```

> **[ENTREVISTA]** ¿Cuál es la diferencia entre GitHub Actions secrets y variables?
> Los **secrets** están encriptados y no aparecen en logs — para credenciales (API keys,
> passwords). Las **variables** son texto plano visible en logs — para configuración no sensible
> como ARNs, nombres de buckets, regiones. Un ARN de IAM no es una credencial — es una
> referencia a un recurso. Si alguien lo ve, no puede hacer nada sin las credenciales.
> Usar secrets para valores no sensibles es over-engineering.

---

## Sesión 11 — Integración MercadoLibre API

**Fecha:** 2026-07-06  
**Qué resolvimos:** incorporamos MercadoLibre como segunda fuente de datos. El scraper de
DeRuedas tarda 3-5 horas y corre solo los domingos — ML tarda 5-10 minutos y corre todos
los días hábiles, resolviendo el overfitting del modelo por falta de datos.

---

### 11.1 — OAuth client_credentials: token sin usuario

La API de ML requiere autenticación. Como no necesitamos actuar en nombre de un usuario
(no compramos ni vendemos — solo leemos listings públicos), usamos el flujo más simple:
`client_credentials`.

```python
resp = httpx.post(
    "https://api.mercadolibre.com/oauth/token",
    data={
        "grant_type":    "client_credentials",
        "client_id":     ML_CLIENT_ID,
        "client_secret": ML_CLIENT_SECRET,
    },
)
token = resp.json()["access_token"]
```

El token se usa como `Authorization: Bearer {token}` en cada request.

**Por qué client_credentials y no Authorization Code:**
- Authorization Code requiere que un usuario haga login en ML y apruebe el acceso
- client_credentials es de máquina a máquina — la app se autentica a sí misma
- Para leer listings públicos no hay nada que "aprobar" — cualquiera puede verlos

> **[ENTREVISTA]** ¿Cuándo usarías Authorization Code vs client_credentials en OAuth 2.0?
> Authorization Code: cuando la app actúa en nombre de un usuario (publicar, comprar, leer
> su historial). client_credentials: cuando la app actúa por sí misma — acceso a datos
> públicos, integraciones server-to-server. La distinción clave es si hay un usuario involucrado.

---

### 11.2 — Descubrir filtros dinámicamente con available_filters

ML limita a 1000 resultados por query. Con `category=MLA1743` sin filtros obtenés los
primeros 1000 listings y punto — no podés ver el resto del mercado.

**Solución: filtrar por marca, una query por marca.**

El truco es que los IDs de filtro no son estáticos — ML los devuelve en `available_filters`
en cada respuesta de búsqueda. Hacés una búsqueda mínima para descubrirlos:

```python
def get_brand_filter_ids(token, client) -> dict[str, str]:
    resp = client.get(
        "https://api.mercadolibre.com/sites/MLA/search",
        params={"category": "MLA1743", "limit": 1},  # limit=1 → barato
        headers={"Authorization": f"Bearer {token}"},
    )
    for f in resp.json().get("available_filters", []):
        if f["id"] == "BRAND":
            return {v["name"]: v["id"] for v in f["values"]
                    if v["name"] in MARCAS_TARGET}
    return {}
```

Retorna `{"Volkswagen": "26450", "Toyota": "5972", ...}`. Después buscás con `BRAND=26450`
como query param y paginás hasta 1000 por marca → ~10 marcas × ~500 = ~5.000 listings.

> **[ENTREVISTA]** ¿Por qué los IDs de filtro no están hardcodeados en el código?
> ML puede cambiar sus IDs internos en cualquier momento. Descubrirlos dinámicamente en cada
> run hace el código resiliente a esos cambios — si ML cambia el ID de Volkswagen, tu código
> sigue funcionando porque siempre lo busca por nombre. Hardcodear un ID es un contrato frágil
> con un sistema externo que no controlás.

---

### 11.3 — Columna `source`: trazabilidad de origen de datos

Con dos fuentes en la misma tabla (`autos_usados`), necesitamos saber de dónde viene cada
fila. Sin eso, no podés debuggear discrepancias entre fuentes ni analizar calidad por origen.

**Migración en Supabase:**
```sql
ALTER TABLE autos_usados
ADD COLUMN IF NOT EXISTS source VARCHAR(20) NOT NULL DEFAULT 'deruedas';
```

`DEFAULT 'deruedas'` asegura que las filas existentes queden correctamente etiquetadas
sin necesidad de un backfill.

**En `load_autos.py`, la fuente se controla con una variable de entorno:**
```python
_SOURCE = os.getenv("SOURCE", "deruedas")
```

El workflow setea `SOURCE=mercadolibre` solo en el step de ML:
```yaml
- name: Load ML silver → Supabase
  env:
    SOURCE: mercadolibre
  run: python -m etl.load_autos
```

**Por qué env var y no parámetro de CLI:**
El script ya existe y funciona. Agregar argparse sería más intrusivo. Las env vars son el
patrón estándar en workflows de CI — cada step puede tener su propio entorno sin tocar
el código del step anterior.

> **[ENTREVISTA]** ¿Cómo agregás una columna NOT NULL a una tabla con datos existentes sin downtime?
> Con `DEFAULT`: la base de datos rellena las filas existentes con ese valor durante el ALTER.
> Sin DEFAULT, Postgres rechaza el ALTER porque las filas existentes tendrían NULL en una
> columna que no lo permite. `ADD COLUMN IF NOT EXISTS` hace la migración idempotente — podés
> correrla dos veces sin error.

---

### 11.4 — Dos cadencias distintas para dos fuentes distintas

DeRuedas usa Crawl-delay 5s sobre 23 provincias × 3 segmentos → 3-5 horas mínimo.
ML API es HTTP puro → ~5-10 minutos para 10 marcas paginadas.

Meter ambas en el mismo workflow desperdicia la ventaja de ML. La solución: workflows separados.

| Workflow | Fuente | Frecuencia | Duración |
|---|---|---|---|
| `etl-vehiculos.yml` | DeRuedas | Domingos 03:00 ART | 3-5h |
| `etl-ml-autos.yml` | MercadoLibre | Lun-Vie 07:00 ART | ~15min |

`etl-ml-autos.yml` incluye su propio job de retrain — cada vez que corre ML con datos frescos,
el modelo se reentrena. El modelo mejora 5 veces por semana en lugar de 1.

**`gold_autos.py` mergea las dos fuentes automáticamente:**
```python
dr = _read(f"silver/autos_usados/{day}.parquet")        # DeRuedas (requerido)
ml = _read(f"silver/ml_autos_usados/{day}.parquet")     # ML (opcional)

if ml is not None:
    return pl.concat([dr, ml], how="diagonal")
return dr
```

`how="diagonal"` en Polars maneja columnas que puedan diferir entre DataFrames — rellena
con null las que faltan en alguno. Es más robusto que `how="vertical"` que requiere schemas idénticos.

> **[ENTREVISTA]** ¿Cómo decidís la frecuencia de un pipeline ETL?
> Depende del costo de correrlo vs el valor de los datos frescos. Un scraper con Crawl-delay
> no puede correr más rápido sin violar el robots.txt — el límite lo pone la fuente. Una API
> sin rate limit agresivo puede correr diario o más frecuente. Siempre modelás: "¿cada cuánto
> cambian los datos que me importan?" Para precios de autos usados, diario es más que suficiente.

---

## Sesión 12 — Segunda fuente de datos: Kavak

**Fecha:** 2026-07-06  
**Qué resolvimos:** incorporamos Kavak como segunda fuente de datos reemplazando
MercadoLibre, que bloqueó su API de búsqueda en abril 2025. El scraper de Kavak
corre lunes a viernes y agrega ~900 listings diarios de autos certificados.

---

### 12.1 — Por qué MercadoLibre falló: PolicyAgent

Después de implementar el extractor de ML, todos los requests al endpoint de búsqueda
devolvían `403`. El mensaje era:

```json
{"code": "PA_UNAUTHORIZED_RESULT_FROM_POLICIES", "blocked_by": "PolicyAgent"}
```

No era Cloudflare bloqueando por IP — era el propio Policy Agent de ML. En abril 2025
MercadoLibre cerró el acceso programático a `/sites/MLA/search` incluso con OAuth token
válido. El flujo `client_credentials` da un token de app, pero ML solo permite búsqueda
a tokens de usuario (Authorization Code flow), y aun así solo sobre los listings de ese
usuario específico.

**Lección:** antes de integrar una API de terceros, verificar en el foro de developers si
hay cambios de política recientes. Los portales de developers suelen tener secciones de
changelog o announcements.

> **[ENTREVISTA]** ¿Cómo manejás la dependencia de tu pipeline en una API de terceros que
> puede cambiar sin aviso? Diversificación de fuentes (no depender de una sola), circuit
> breakers en el código (errores 403 repetidos → alertar, no reintentar indefinidamente),
> y monitoreo. Una API que cambia es riesgo operativo — el diseño debe tolerarlo.

---

### 12.2 — Web scraping con BeautifulSoup vs. API

Kavak no tiene API pública. Su sitio es Next.js con SSR — el HTML viene completo en el
primer request, sin necesidad de ejecutar JavaScript. Eso lo hace scrapeable con httpx +
BeautifulSoup.

**¿Por qué BeautifulSoup y no regex?**

El scraper de DeRuedas usa regex porque su HTML tiene inputs ocultos simples y predecibles.
Kavak tiene estructura anidada con divs y spans — BeautifulSoup permite navegarla semánticamente:

```python
# Con regex — frágil si cambia un atributo
precio = re.search(r'class="price"[^>]*>([^<]+)', html).group(1)

# Con BeautifulSoup — navega la estructura
h3    = card.find("h3")                          # título
p     = card.find("p")                           # subtítulo
span  = card.find("span", class_=re.compile(r"footerInfo"))  # provincia
```

**Selector de precio robusto:**

Kavak tiene dos precios en los cards "Outlet": precio de lista y precio con descuento.
En vez de depender de clases CSS (que cambian con cada deploy), buscamos todos los montos
≥ $1.000.000 en el texto del card y tomamos el último — que siempre es el precio real:

```python
montos = [
    int(m.replace(".", ""))
    for m in re.findall(r"\d{1,3}(?:\.\d{3})+", text)
    if int(m.replace(".", "")) >= 1_000_000
]
precio_ars = montos[-1]
```

> **[ENTREVISTA]** ¿Cuándo usás scraping vs API oficial?
> API cuando existe y es confiable. Scraping cuando la API no existe, está bloqueada, o
> tiene restricciones que impiden el caso de uso. El scraping es más frágil (se rompe si
> cambia el HTML) pero a veces es la única opción. Siempre documentar la fuente y el riesgo.

---

### 12.3 — gold_autos.py: fuentes con cadencias distintas

DeRuedas corre los domingos. Kavak corre de lunes a viernes. Si gold busca los datos de
ambas fuentes para la misma fecha, Kavak no va a tener silver del domingo y viceversa.

**Solución: fallback al silver más reciente por fuente.**

```python
def _read_latest(prefix: str, preferred_day: date) -> pl.DataFrame | None:
    # 1. Intentar el día exacto (el ETL de hoy)
    try:
        return _read(f"{prefix}/{preferred_day}.parquet")
    except:
        pass
    # 2. Fallback al archivo más reciente disponible
    keys = sorted(list_objects(prefix))
    return _read(keys[-1]) if keys else None
```

Así el gold step siempre trabaja con los datos más frescos de cada fuente, sin importar
que no coincidan en fecha:
- Si DeRuedas corrió el domingo y Kavak corre el lunes → gold usa DeRuedas del domingo +
  Kavak del lunes.
- Si solo corrió DeRuedas → gold usa solo DeRuedas (Kavak devuelve None).

> **[ENTREVISTA]** ¿Qué pasa si mergeas dos DataFrames con schemas distintos?
> Polars `concat(..., how="diagonal")` rellena con null las columnas que faltan en alguno
> de los frames. Es más robusto que `how="vertical"` que requiere schemas idénticos. En
> nuestro caso ambas fuentes tienen el mismo schema — pero `diagonal` es defensa en profundidad.

---

### 12.4 — Limpiar código muerto

Cuando la integración con MercadoLibre falló, eliminamos 5 archivos y revertimos los
cambios en otros 6. El código muerto tiene costo real:

- Confunde a quien lee el repo ("¿por qué hay un extractor de ML si no funciona?")
- Los tests pueden seguir pasando sobre código que nadie ejecuta en prod
- El Dockerfile copiaba archivos innecesarios → imagen más pesada

**Regla:** si algo no se usa, se borra. El historial de git preserva la historia — no
hace falta dejar código comentado "por si acaso".

> **[ENTREVISTA]** ¿Cómo decidís qué código eliminar en un refactor?
> Si no hay ningún path de ejecución que llegue a ese código (ni en prod, ni en tests, ni
> en scripts manuales), se puede borrar. `git log --follow -- archivo` te muestra la historia
> completa. Si el código podría ser útil en el futuro, el momento de incorporarlo es cuando
> lo necesitás — no antes (YAGNI: You Aren't Gonna Need It).

---

## Glosario rápido

| Término | Qué es |
|---|---|
| Monorepo | Un único repo que contiene múltiples módulos/servicios del proyecto |
| Entorno virtual (venv) | Aislamiento de dependencias Python por proyecto |
| Linter | Herramienta que analiza el código en busca de errores/estilo sin ejecutarlo |
| Formatter | Herramienta que reformatea el código a un estilo consistente automáticamente |
| Hook (pre-commit) | Script que se ejecuta automáticamente en un evento de git |
| Bronze/Silver/Gold | Las tres capas del data lake: crudo → limpio → agregado |
| Terraform state | Archivo JSON que mapea recursos `.tf` con recursos reales en AWS |
| Remote state | El state guardado en S3 en vez de local — compartible entre devs y CI |
| State locking | Mutex distribuido via DynamoDB — evita dos apply simultáneos |
| Principle of Least Privilege | Dar solo los permisos mínimos necesarios a cada componente |
| Cold start | El tiempo que tarda Lambda en inicializar el contenedor en el primer request |
| ASGI | Protocolo de Python para comunicación servidor web ↔ aplicación (FastAPI lo usa) |
| Mangum | Adaptador que traduce eventos Lambda al formato ASGI que FastAPI entiende |
| ECR | Elastic Container Registry — el Docker Hub privado de AWS |
| Function URL | URL HTTPS pública y gratuita para un Lambda, puede tener restricciones en cuentas nuevas |
| API Gateway HTTP v2 | Capa HTTP gestionada que recibe requests y los delega al Lambda — más robusto que Function URL |
| `payload_format_version` | Versión del esquema JSON que API Gateway manda al Lambda (v2.0 es el moderno) |
| Multi-stage build | Dockerfile con múltiples FROM: stage de compilación + stage de runtime, imagen final más liviana |
| AL2 / AL2023 | Amazon Linux 2 (GCC 7, imagen Lambda Python ≤3.11) vs Amazon Linux 2023 (GCC 11, Python 3.12) |
| `terraform import` | Sincroniza el state de Terraform con un recurso ya existente en AWS sin recrearlo |
| `terraform force-unlock` | Libera manualmente el lock de DynamoDB cuando un apply interrumpido lo dejó bloqueado |
| Credential chain | El orden en que boto3 busca credenciales AWS (env vars → IAM role → ~/.aws) |
| OIDC | OpenID Connect — protocolo de identidad federada que permite a GitHub Actions obtener credenciales AWS temporales sin guardar secrets |
| PostgREST | Servidor que expone un schema de Postgres como REST API — usado por Supabase para acceso HTTPS sin conexión directa al puerto 5432 |
| `Prefer: resolution=merge-duplicates` | Header HTTP que le dice a PostgREST que haga UPSERT en vez de INSERT |
| React Server Components | Componentes que se ejecutan solo en el servidor — pueden hacer fetches sin exponer credenciales al browser |
| Suspense streaming | Patrón de Next.js que envía skeletons al browser mientras los Server Components resuelven sus fetches en paralelo |
| `useMemo` | Hook de React que memoiza el resultado de una computación costosa, recalculando solo cuando cambian las dependencias |
| `useCallback` | Hook de React que memoiza la función en sí (no su resultado), para evitar re-renders en componentes hijos |
| Lazy import | Importar un módulo dentro de una función en lugar del top-level del archivo — evita cargar dependencias opcionales o pesadas siempre |
| `needs:` (GitHub Actions) | Declara dependencia entre jobs — el job hijo solo corre si el padre terminó exitosamente |
| `workflow_dispatch` | Trigger de GitHub Actions que permite disparar un workflow manualmente desde la UI |
| `smallint` | Tipo de dato de 2 bytes en Postgres — suficiente para rangos pequeños (0-32767), más eficiente que `integer` (4 bytes) |
| `max_session_duration` | Máxima duración que puede tener una sesión STS asumiendo un IAM role — tiene que coincidir con `role-duration-seconds` del workflow |
| `role-duration-seconds` | Parámetro de `configure-aws-credentials` que define cuánto dura el token OIDC emitido para el run |
| `list_objects_v2` | API de S3 para listar objetos en un bucket/prefijo — usada para auto-descubrir el archivo más reciente sin hardcodear la fecha |
| `terraform.tfvars` | Archivo local con valores de variables de Terraform — cargado automáticamente, en `.gitignore` para no exponer credenciales |
| `terraform apply -target` | Aplica solo un subconjunto de recursos del módulo, pero sigue evaluando todas las variables para construir el grafo completo |
| Dependencias transitivas | Librerías que no importás directamente pero que sí importan los módulos que usás — tienen que estar en requirements |
| PolicyAgent | Sistema de políticas de MercadoLibre que bloquea requests según reglas de acceso — distinto de Cloudflare, opera a nivel de negocio |
| BeautifulSoup | Librería Python para parsear HTML/XML — permite navegar el DOM con selectores semánticos en lugar de regex |
| SSR (Server-Side Rendering) | El servidor genera el HTML completo antes de enviarlo al browser — scrapeable sin ejecutar JS |
| YAGNI | "You Aren't Gonna Need It" — principio de no agregar código para necesidades futuras hipotéticas |
| `how="diagonal"` | Modo de concat en Polars que permite unir DataFrames con schemas distintos, rellenando con null las columnas faltantes |
