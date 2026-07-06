# TasaJusta — Guion para NotebookLM

Este documento explica con palabras simples todo lo que construimos en el proyecto TasaJusta.
Está pensado para que puedas estudiarlo, escucharlo o hacerle preguntas a una IA.

---

## ¿Qué es TasaJusta?

TasaJusta es una plataforma que predice el precio justo de un auto usado en Argentina.
Si alguien publica un auto a $15 millones y el modelo dice que debería valer $22 millones,
eso es una oportunidad. Si lo publica a $25 millones, está caro.

El proyecto también muestra cómo el precio de los autos se mueve junto al dólar,
algo muy importante en la economía argentina.

---

## Las tres grandes partes del proyecto

El proyecto tiene tres partes que trabajan juntas:

1. **El pipeline de datos** — busca y limpia la información
2. **El modelo de machine learning** — aprende los precios y hace predicciones
3. **El dashboard y la API** — muestra los resultados al usuario

---

## Parte 1: El pipeline de datos

### ¿Qué es un pipeline?

Un pipeline es una cadena de pasos donde la salida de uno es la entrada del siguiente.
Como una línea de producción en una fábrica.

### Los tres pasos del pipeline (arquitectura medallion)

Usamos una arquitectura llamada **medallion** con tres capas: bronze, silver y gold.

**Bronze (datos crudos):**
El primer paso es obtener los datos. Tenemos dos fuentes:
- El precio del dólar: lo bajamos de una API pública (dolarapi.com). Nos da el precio del dólar blue, oficial, MEP, y otros.
- Autos usados: tenemos un scraper que entra al sitio DeRuedas.com.ar y extrae información de cada publicación (marca, modelo, año, kilómetros, precio, provincia).

Todo esto se guarda tal cual, sin tocar, en archivos JSON. Eso es el bronze: los datos crudos originales. Si algo falla más adelante, podemos volver al original y empezar de nuevo.

**Silver (datos limpios):**
El segundo paso es limpiar los datos. Los datos del mundo real tienen errores:
- Autos con precio $0 (la publicación no tiene precio cargado)
- Autos con años imposibles (1800, o el año que viene)
- Autos "usados" con 0 kilómetros (sospechoso)
- Registros duplicados del mismo auto

Limpiamos todo eso y lo guardamos en formato Parquet. Parquet es un formato de archivo pensado para datos: ocupa menos espacio que un CSV y se lee mucho más rápido.

**Gold (datos listos para el modelo):**
El tercer paso es preparar los datos para que el modelo pueda aprender. Aquí calculamos features nuevas:

- **Antigüedad**: cuántos años tiene el auto (año actual menos año del auto)
- **km_valido**: si el kilometraje que figura es real o es un placeholder (muchos autos dicen "1 km" cuando no informaron los km)
- **km_por_año**: los kilómetros divididos la antigüedad — mide el desgaste relativo del auto
- **dolar_blue_venta**: el precio del dólar blue del mismo día que se scrapeo el auto, para dar contexto económico

---

## Parte 2: El modelo de machine learning

### ¿Qué es un modelo de machine learning?

Un modelo de machine learning aprende patrones a partir de ejemplos.
En nuestro caso: le mostramos 121 autos con sus características y su precio,
y el modelo aprende la relación entre las características y el precio.
Después, cuando le mostramos un auto nuevo que nunca vio, puede predecir su precio.

### Las variables que usa el modelo

El modelo recibe estas variables (llamadas "features") para hacer la predicción:

- Marca del auto (Toyota, Ford, Volkswagen, etc.)
- Modelo del auto (Corolla, Ka, Gol, etc.)
- Provincia donde está publicado
- Año del auto
- Antigüedad (calculada)
- Kilómetros
- Si los kilómetros son reales o un estimado
- Kilómetros por año (calculado)
- Precio del dólar blue ese día

Y lo que predice (llamado "target") es: el precio en pesos argentinos.

### ¿Qué es overfitting?

Cuando el modelo memoriza los ejemplos en lugar de aprender el patrón general.
Como un estudiante que copia las respuestas exactas de los ejercicios del libro:
si el examen trae preguntas ligeramente distintas, no sabe qué hacer.

Con 152 autos, el modelo tiene suficiente capacidad para memorizar todos los ejemplos.
Por eso las métricas en los datos de entrenamiento son mejores que en los datos de prueba.
Con 1000+ autos, esto mejora mucho porque memorizar se vuelve imposible.

### ¿Cómo evaluamos si el modelo es bueno?

Usamos estas métricas:

- **MAE (Mean Absolute Error)**: el error promedio en pesos. Si el MAE es $4 millones, en promedio el modelo se equivoca $4 millones por auto.
- **RMSE**: similar al MAE pero penaliza más los errores grandes.
- **R²**: qué tan bien explica el modelo la variación de precios. R²=1 es perfecto, R²=0 es tan malo como adivinar el promedio.
- **MAPE**: el error en porcentaje. 20% significa que en promedio el modelo se equivoca un 20% del precio real.

### Los dos modelos que entrenamos

Entrenamos y comparamos dos modelos distintos:

**LightGBM:**
Un modelo basado en árboles de decisión. Funciona muy bien con datos tabulares (como una planilla de Excel). Sus ventajas: maneja variables categóricas de forma nativa (marca, provincia), es rápido de entrenar, y con pocos datos tiende a generalizar mejor que las redes neuronales.

Resultados en datos que nunca vio (test set):
- MAE: $4.058.279
- R²: 0.556
- Error porcentual: 21%

**MLP (Red Neuronal):**
Una red neuronal artificial con 3 capas. Inspirada en cómo funciona el cerebro, aunque de forma muy simplificada. Necesita más datos para brillar — con 152 filas, el LightGBM le gana.

Resultados en datos que nunca vio (test set):
- MAE: $3.985.379
- R²: 0.473
- Error porcentual: 20%

**Resultado: empate técnico.** Con más datos, el LightGBM seguirá siendo competitivo y será más fácil de poner en producción.

---

## Parte 3: La API y el Dashboard

### La API (FastAPI)

Una API es una puerta de entrada para que otros programas usen nuestro modelo.
Construimos un endpoint en FastAPI:

```
POST /predict
{
  "marca": "Toyota",
  "modelo": "Corolla",
  "anio": 2018,
  "km": 80000,
  "provincia": "Mendoza"
}

→ Respuesta:
{
  "precio_estimado_ars": 18516281
}
```

Cualquier aplicación (una app mobile, el dashboard web, otro servicio) puede llamar a esta URL y obtener una predicción de precio.

### El Dashboard (Next.js en Vercel)

El dashboard es el sitio web que muestra los datos al usuario. Tiene dos secciones:

**Cotizaciones del dólar:**
Muestra el precio actual del dólar en todas sus variantes (blue, oficial, MEP, tarjeta, etc.). El dólar blue y el oficial están destacados con una barra visual que muestra el spread (la diferencia entre compra y venta).

**Tabla de autos usados:**
Muestra todos los autos scrapeados con su precio, año, kilómetros y provincia. Se puede ordenar por cualquier columna haciendo clic en el encabezado. Cada marca tiene un color distinto. Hay una barra visual que muestra el precio relativo de cada auto respecto al más caro.

---

## Las herramientas que usamos y por qué

**Python:** el lenguaje principal para todo el pipeline y el modelo. Es el estándar de la industria para data engineering y machine learning porque tiene el ecosistema de librerías más completo del mundo en esas áreas.

---

### Polars — la librería de datos que reemplaza a Pandas

Polars es una librería para manipular datos en Python, similar a Pandas, pero construida desde cero en Rust. Rust es un lenguaje de programación de sistemas, extremadamente rápido y eficiente en memoria.

**¿Por qué no usamos Pandas directamente?**

Pandas fue creado en 2008 y tiene algunas limitaciones de diseño que se vuelven problemáticas con datasets grandes:
- Usa un solo núcleo del procesador por defecto (aunque tu computadora tenga 8 o 16)
- Copia los datos en memoria constantemente, lo que consume mucha RAM
- Tiene un sistema de tipos inconsistente heredado de NumPy

Polars resuelve estos problemas desde el diseño:
- **Paralelo por defecto**: usa todos los núcleos del procesador automáticamente
- **Lazy evaluation**: puede analizar toda la cadena de operaciones antes de ejecutar y optimizarla, como un compilador optimizando código
- **Apache Arrow por dentro**: usa un formato de memoria columnar llamado Apache Arrow, el mismo estándar que usan herramientas como Spark, DuckDB y BigQuery

**¿Qué es columnar?** Imaginá una planilla de Excel con 1 millón de filas y 10 columnas. Si querés calcular el promedio de la columna "precio", Pandas tiene que pasar por toda la fila (los 10 campos) para encontrar el precio de cada fila. Polars guarda todos los precios juntos en memoria, así los lee de corrido sin saltar — lo que se llama acceso secuencial y es mucho más rápido para el procesador.

**¿Por qué usamos Pandas en el modelo entonces?** LightGBM, la librería de machine learning, espera un DataFrame de Pandas para activar su soporte nativo de variables categóricas. Es una limitación de esa librería, no una preferencia nuestra. En el futuro esto puede cambiar.

**Ejemplo concreto en el proyecto:** cuando limpiamos 304 registros crudos de autos, Polars aplica todas las transformaciones (filtrar precios nulos, corregir años fuera de rango, eliminar duplicados) en una sola pasada optimizada. Con Pandas habría que hacerlo paso a paso.

---

### LightGBM — el modelo de machine learning principal

LightGBM fue creado por Microsoft y publicado en 2017. El nombre significa "Light Gradient Boosting Machine". Es uno de los modelos más usados en competencias de machine learning y en producción en empresas de datos.

**¿Qué es Gradient Boosting?**

Gradient Boosting es una técnica que construye muchos árboles de decisión pequeños, uno a la vez, donde cada árbol nuevo aprende a corregir los errores del árbol anterior.

Imaginá que querés predecir el precio de un auto:
- El primer árbol hace una predicción básica: "todos los autos valen $18 millones"
- Calcula los errores: algunos autos tienen un error de +$5M, otros de -$3M
- El segundo árbol aprende específicamente esos errores: "si es Toyota, el error tiende a ser positivo"
- El tercer árbol aprende los errores que todavía quedan
- Y así hasta tener 300 árboles, cada uno corrigiendo al anterior

La predicción final es la suma de las predicciones de todos los árboles.

**¿Por qué "Light"?** LightGBM tiene dos innovaciones que lo hacen más rápido que sus predecesores (como XGBoost):
- **Histogramas**: en lugar de probar cada valor posible para dividir un árbol, agrupa los valores en 255 "buckets", lo que reduce dramáticamente el tiempo de cómputo
- **Leaf-wise growth**: crece el árbol siguiendo la hoja con mayor ganancia de información, en lugar de crecer nivel por nivel. Esto produce árboles más precisos con menos nodos

**¿Por qué es mejor que una red neuronal para nuestro caso?**

Con datos tabulares estructurados (como una planilla) y pocos ejemplos (152 filas), LightGBM casi siempre gana porque:
- Los árboles tienen "memoria corta": si no hay suficientes datos para aprender algo, simplemente no aprenden esa rama. Las redes neuronales, en cambio, empiezan a inventar patrones que no existen
- Maneja variables categóricas de forma nativa: sabe automáticamente que "Toyota" y "Ford" son categorías distintas sin necesidad de convertirlas en números
- Es muy rápido de entrenar: nuestros 300 árboles se entranan en milisegundos

En el proyecto: LightGBM logró un error promedio de $4 millones en autos que nunca había visto, con solo 152 ejemplos de entrenamiento.

---

### PyTorch — redes neuronales para la comparación

PyTorch es la librería de redes neuronales creada por Meta (Facebook). Junto con TensorFlow (de Google), es el estándar de la industria para deep learning.

**¿Qué es una red neuronal?**

Una red neuronal es una serie de capas matemáticas encadenadas. Cada capa recibe números, los multiplica por unos pesos (que el modelo aprende), les aplica una función matemática simple, y pasa el resultado a la siguiente capa. Al final, la última capa produce un número: la predicción del precio.

Nuestra red tiene esta estructura:
```
Entrada (8 números) → 64 neuronas → 32 neuronas → 16 neuronas → Salida (1 número: precio)
```

**¿Cómo aprende?** A través de un proceso llamado backpropagation. Funciona así:
1. La red hace una predicción
2. Calculamos cuánto se equivocó (la "pérdida" o loss)
3. Propagamos ese error hacia atrás por toda la red, calculando cuánto contribuyó cada peso al error
4. Ajustamos cada peso un poquito en la dirección que reduce el error
5. Repetimos esto 500 veces (epochs)

PyTorch hace el paso 3 automáticamente con algo llamado autograd (diferenciación automática). Vos solo defines el modelo y la pérdida; PyTorch calcula los gradientes solo.

**¿Por qué usamos la versión CPU-only?** PyTorch tiene una versión con soporte para GPUs (tarjetas gráficas) que es mucho más rápida para entrenar. Pero nuestra imagen Docker pesa ~200MB con la versión CPU vs ~2GB con CUDA. Para 152 filas, el entrenamiento dura 2 segundos en CPU de todas formas — no necesitamos la GPU.

En el proyecto: el MLP logró resultados muy similares al LightGBM en el test set ($3.9M de error promedio), pero con más complejidad de código y más tiempo de entrenamiento. Esto confirma que para datos tabulares con pocos ejemplos, LightGBM es la elección correcta.

---

### MinIO — el almacenamiento de archivos

MinIO es un servidor de almacenamiento de objetos que funciona igual que Amazon S3, el servicio de almacenamiento de Amazon Web Services. La diferencia es que MinIO corre en tu propia computadora, gratis, dentro de Docker.

**¿Qué es almacenamiento de objetos?**

Es una forma de guardar archivos donde cada archivo es un "objeto" identificado por una clave (como una URL). A diferencia de un sistema de archivos (carpetas y subcarpetas) o una base de datos (filas y columnas), el almacenamiento de objetos está pensado para guardar archivos grandes en cantidad masiva sin preocuparse por la estructura.

Ejemplos de objetos en nuestro proyecto:
- `autos_usados/2026-07-02.json` — los datos crudos del scraping
- `silver/autos_usados/2026-07-02.parquet` — los datos limpios
- `gold/autos_usados/2026-07-02.parquet` — las features para el modelo
- `lgbm/model_lgbm_2026-07-02.pkl` — el modelo entrenado

**¿Por qué MinIO y no simplemente guardar archivos en disco?**

Tres razones:
1. **Portabilidad**: cuando pasemos a producción con AWS S3, no cambiamos ni una línea de código. La librería boto3 funciona igual con MinIO en dev que con S3 en prod.
2. **Separación de almacenamiento y cómputo**: el container que procesa datos y el container que guarda datos son independientes. Si reiniciamos el container de la app, los datos siguen en MinIO.
3. **Realismo**: en proyectos de data engineering reales, el data lake siempre vive en S3 o equivalente. Usar MinIO en dev nos hace pensar desde el principio en la arquitectura correcta.

---

### Las otras herramientas

**Pandas:** librería de datos clásica de Python, creada en 2008. La usamos específicamente para LightGBM porque esa librería la requiere para su soporte de variables categóricas nativas.

**PostgreSQL:** base de datos relacional (tablas, filas, columnas, SQL). Guardamos ahí los precios del dólar y los autos usados para que el dashboard los pueda consultar rápido.

**Supabase:** PostgreSQL en la nube con una API REST incluida. El dashboard web (Next.js) consulta Supabase directamente desde el navegador, sin necesidad de un servidor propio.

**FastAPI:** framework para construir APIs en Python. Es el más moderno y rápido del ecosistema. Tiene documentación automática (si vas a /docs en la API, ves todos los endpoints con ejemplos).

**Next.js:** framework de React para el dashboard web. Tiene "Server Components" que hacen que la página se construya en el servidor antes de enviarse al navegador, lo que la hace más rápida y segura (las claves de la base de datos nunca llegan al navegador).

**Docker:** permite empaquetar una aplicación junto con todas sus dependencias en un "contenedor". Así el pipeline funciona igual en tu computadora, en la de un colega, y en un servidor en la nube.

---

## La arquitectura del proyecto: medallion, separación de capas, reproducibilidad

Estos tres conceptos son los pilares de cómo está diseñado el proyecto. No son decorativos — cada uno resuelve un problema real que aparece en proyectos de datos a medida que crecen.

### Arquitectura Medallion: bronze, silver, gold

La arquitectura medallion divide el almacenamiento de datos en tres capas con responsabilidades distintas. El nombre viene de las medallas: bronce, plata, oro — indicando niveles crecientes de calidad y refinamiento.

**Bronze — los datos tal cual llegaron:**

Esta capa guarda los datos originales sin tocarlos. Cada archivo JSON que baja el scraper de DeRuedas va directo al bronze, sin limpiar ni transformar. Lo mismo con las cotizaciones del dólar.

¿Por qué es importante guardar los datos sucios? Porque la limpieza puede tener bugs. Si mañana descubrimos que estamos filtrando autos válidos por error, podemos volver al bronze y re-procesar todo desde el principio. Sin el bronze, esos datos están perdidos para siempre.

El bronze es inmutable: nunca se modifica un archivo que ya está ahí. Solo se agregan archivos nuevos.

**Silver — los datos limpios y confiables:**

Esta capa tiene los mismos datos que el bronze, pero limpios y en un formato eficiente (Parquet en lugar de JSON). Aquí se aplicaron todas las reglas de negocio: precios inválidos eliminados, años fuera de rango corregidos, duplicados removidos.

El silver es la fuente de verdad para cualquier análisis. Un analista que quiera explorar los datos con DuckDB o Jupyter, los lee del silver. No necesita saber cómo funciona el scraper ni entender el formato crudo del bronze.

**Gold — los datos listos para el modelo:**

Esta capa tiene las features calculadas: antigüedad del auto, kilómetros por año, flag de km válido, cotización del dólar del día. No son datos crudos ni datos limpios — son datos enriquecidos específicamente para el problema que queremos resolver (predecir precios).

El modelo de machine learning solo toca el gold. Si mañana queremos agregar una nueva feature, solo modificamos el script que produce el gold — el bronze y el silver no se tocan.

**¿Por qué tres capas y no una sola?**

Imaginá que tenemos una sola capa y algo falla. ¿Dónde falló? ¿En el scraping? ¿En la limpieza? ¿En el cálculo de features? No sabés. Con tres capas, podés mirar cada etapa por separado y encontrar el problema exacto.

Además, cada capa puede tener múltiples consumidores independientes. El silver lo pueden leer analistas, el modelo, y reportes. El gold es específico para el modelo pero podría alimentar varios modelos distintos.

---

### Separación de capas: cada cosa en su lugar

Este principio dice que los distintos componentes del sistema deben ser independientes entre sí. En TasaJusta hay cuatro capas completamente separadas:

**1. La capa de ingesta (ETL):**
`etl/scrape_deruedas.py`, `etl/extract_dolar.py`
Su única responsabilidad: traer datos de afuera y guardarlos en bronze.
No sabe nada del modelo, no sabe nada del dashboard.

**2. La capa de transformación:**
`etl/transform_autos.py`, `etl/gold_autos.py`
Su única responsabilidad: limpiar y enriquecer los datos.
No sabe de dónde vienen los datos crudos ni quién los va a usar.

**3. La capa de machine learning:**
`ml/train_lgbm.py`, `ml/train_mlp.py`
Su única responsabilidad: aprender patrones y hacer predicciones.
Solo toca el gold Parquet. No sabe cómo se obtuvieron esos datos.

**4. La capa de presentación:**
`api/main.py`, `web/`
Su única responsabilidad: mostrar resultados al usuario.
No sabe cómo funciona el modelo ni cómo se limpian los datos.

¿Por qué importa esto? Porque cuando algo necesita cambiar, el cambio está contenido. Si el sitio DeRuedas cambia su estructura HTML y tenemos que actualizar el scraper, no tocamos nada del modelo ni del dashboard. Si encontramos un modelo mejor que LightGBM, cambiamos el training sin tocar el pipeline de datos.

En proyectos grandes con equipos de 5, 10 o 20 personas, esta separación es lo que permite que distintos equipos trabajen en paralelo sin pisarse.

---

### Reproducibilidad: los mismos inputs siempre dan los mismos outputs

Este concepto tiene dos dimensiones en el proyecto:

**Idempotencia del pipeline:**
Cada paso del pipeline puede correrse dos veces y el resultado es el mismo. Si el scraper de hoy se corre dos veces, el bronze tiene un solo archivo `2026-07-02.json` (se sobreescribe, no se duplica). Si el transform se corre dos veces, el silver tiene un solo Parquet. Si el load se corre dos veces, el upsert en Postgres actualiza los registros existentes en lugar de duplicarlos.

Esto es crucial porque en producción los pipelines pueden fallar a mitad de camino y necesitan poder reiniciarse desde el principio sin corromper los datos.

**Reproducibilidad del modelo:**
El modelo se entrenó con `random_state=42` en el split de datos. Eso significa que el 80% de entrenamiento y el 20% de prueba siempre serán los mismos autos. Si alguien vuelve a entrenar el modelo mañana con los mismos datos, obtiene exactamente los mismos resultados. Esto es fundamental para comparar modelos de forma justa: LightGBM y MLP fueron evaluados en exactamente el mismo conjunto de prueba, no en conjuntos distintos que podrían ser más fáciles o difíciles por azar.

---

## ¿Qué viene después?

1. **Más datos:** con 1000+ autos, el overfitting se reduce y las predicciones mejoran.
2. **Más provincias:** hoy el 70% de los datos son de Mendoza. Expandir a Buenos Aires, Santa Fe, Córdoba.
3. **Detector de oportunidades:** marcar automáticamente los autos que están publicados muy por debajo del precio estimado.
4. **GitHub Actions:** automatizar el pipeline para que corra solo todos los días.
5. **NLP en descripciones:** usar procesamiento de lenguaje natural para extraer features del texto de la publicación (tiene GNC, techo solar, cuero, etc.).


