# Modo aprendizaje — cómo construir TasaJusta SIN quedar sin saber qué hiciste

> El objetivo no es tener el proyecto terminado. Es poder **explicar cada decisión** en una entrevista.
> Un proyecto que no podés defender vale menos que uno más chico que entendés de punta a punta.

---

## Las 6 reglas del modo aprendizaje

1. **Concepto antes que código.** No generamos nada que no puedas explicar en una frase. Primero el
   *qué* y el *por qué*, después el código.
2. **Vos decidís.** Claude Code te da 2-3 opciones con trade-offs; elegís vos y anotás por qué. Ese
   "por qué" es lo que te preguntan en la entrevista.
3. **Test de "explicámelo de vuelta".** Después de cada bloque, explicalo en voz alta (o escribilo en
   el `DECISIONS.md`). Si no te sale, no avanzamos: volvemos sobre eso.
4. **Núcleo a mano, boilerplate acelerado.** La lógica que importa (transforms del ETL, loop de
   entrenamiento, scoring de anomalías) la escribís vos. El boilerplate (Terraform, Dockerfile,
   configs) lo acelera la IA, pero lo leés y lo entendés.
5. **Diario de decisiones.** Un `DECISIONS.md` vivo: qué elegimos, por qué, qué descartamos. Es a la
   vez documentación e insumo de preparación para entrevistas.
6. **Checkpoints de entrevista.** Cada fase termina con "¿podés dibujar esto en un pizarrón?" y una
   lista de preguntas para autoevaluarte (más abajo).

**Regla de pacing:** que el código nunca se adelante a tu comprensión. Si Claude Code generó tres
cosas y entendiste una, parás y entendés las otras dos antes de seguir.

---

## Parte A — Pegar esto en el `CLAUDE.md` (configura a Claude Code para que ENSEÑE)

```markdown
## Modo de trabajo: enseñar mientras construimos

Estoy usando este proyecto para APRENDER, no solo para tener un resultado. Seguí estas reglas:

1. Antes de escribir código, explicá el enfoque en 3-5 líneas: qué vas a hacer y por qué.
   Esperá a que confirme antes de implementar cambios grandes.
2. Cuando haya una decisión de diseño (librería, patrón, estructura), NO la tomes en silencio:
   presentá 2-3 opciones con sus trade-offs y pedime que elija.
3. Escribí diffs chicos, una cosa a la vez. Nada de generar 8 archivos de una.
4. Comentá el código no obvio explicando el PORQUÉ, no el qué.
5. Después de implementar algo, cerrá con 3 bullets: "qué hace esto / por qué así / qué preguntaría
   un entrevistador sobre esto".
6. Si algo que estamos construyendo es un concepto que debería poder explicar en una entrevista,
   marcalo con `// [ENTREVISTA]` y una nota corta.
7. Si te pido "dejame intentar primero", NO escribas el código: esperá mi intento y después
   revisámelo señalando qué mejorarías y por qué.
8. Nunca uses una librería o patrón que no hayas explicado antes en esta sesión.
```

**Prompts útiles para el día a día con Claude Code:**
- "Explicame el enfoque antes de escribir código."
- "Dame las opciones con trade-offs, elijo yo."
- "Dejame intentar esta función primero, después revisás la mía."
- "¿Qué me preguntaría un entrevistador sobre lo que acabamos de hacer?"
- "Quizeame sobre esto: hacé 5 preguntas y corregí mis respuestas."

---

## Parte B — Guía de estudio por fase

Para cada fase: **conceptos que TENÉS que poder explicar** + **preguntas de entrevista** para
autoevaluarte. Si no podés responder una pregunta sin mirar, ese concepto todavía no está.

### Fase 1 — ETL / Data engineering
**Conceptos a dominar:**
- Extract / Transform / Load: qué pasa en cada etapa y por qué se separan.
- **Idempotencia**: por qué correr el pipeline dos veces no debe duplicar ni romper datos.
- **Arquitectura medallion** (bronze → silver → gold): qué vive en cada capa y por qué.
- **Parquet vs CSV/JSON**: columnar, compresión, esquema. Por qué parquet para analítica.
- Data lake vs warehouse: para qué sirve cada uno y por qué usás los dos.
- Carga full vs incremental.
- Chequeos de calidad de datos (nulls, rangos, dedup).

**Preguntas de entrevista:**
- ¿Por qué parquet en vez de CSV para la capa silver?
- ¿Qué hace idempotente a un pipeline y por qué importa?
- ¿Diferencia entre un data lake y un data warehouse?
- Si una fuente falla a mitad de la corrida, ¿qué pasa? ¿Cómo lo diseñaste?
- ¿Cuándo harías carga incremental en vez de full refresh?

### Fase 2 — ML + API en producción
**Conceptos a dominar:**
- Train/test split y **data leakage** (qué es y cómo lo evitás).
- Métricas de regresión: MAE, MAPE, RMSE — qué te dice cada una y cuándo usás cuál.
- Overfitting y regularización (a alto nivel).
- Por qué el boosting (LightGBM) suele ganarle a una red en datos tabulares.
- **El loop de entrenamiento de PyTorch**: Dataset, DataLoader, forward, loss, backward,
  `optimizer.step()`, `zero_grad()`. Poder recitarlo.
- Serialización del modelo (guardar/cargar el artefacto).
- Diferencia entre entrenar y servir; API stateless.
- **Cold start** en Lambda: qué es y cómo lo mitigaste.

**Preguntas de entrevista:**
- ¿Por qué elegiste LightGBM sobre una red neuronal para este problema?
- ¿Qué es data leakage y cómo lo evitaste?
- Explicame tu loop de entrenamiento de PyTorch paso a paso.
- ¿Qué te dice el MAPE que no te dice el MAE?
- ¿Cómo se sirve un modelo en producción? ¿Qué es un cold start?

### Fase 3 — NLP + detector de oportunidades
**Conceptos a dominar:**
- **Embeddings**: qué es representar texto como un vector; similitud semántica; distancia coseno.
- Transformers a alto nivel (no hace falta la matemática fina, sí la intuición).
- Por qué precomputás los embeddings en batch y no en cada request.
- **Scoring de anomalías por residuo**: `(precio_real - precio_estimado) / precio_estimado`.
- Trade-off precisión/recall al fijar el umbral de "oportunidad".

**Preguntas de entrevista:**
- ¿Qué es un embedding? Explicámelo como si no supiera de ML.
- ¿Por qué precomputar embeddings en vez de calcularlos en inferencia?
- ¿Cómo elegís el umbral para flaggear una oportunidad?
- Sin etiquetas de "es o no una ganga", ¿cómo evaluás el detector?

### Fase 4 — Producción de verdad (IaC, CI/CD, observabilidad)
**Conceptos a dominar:**
- Infrastructure as Code: por qué (reproducibilidad, evitar "drift" de clicks manuales).
- `terraform plan` vs `apply`.
- **OIDC** vs claves de larga vida para que el CI acceda a AWS sin secretos hardcodeados.
- Etapas de un pipeline de CI/CD.
- Retención de logs y su impacto en costos.
- Observabilidad: logs vs métricas vs health checks.

**Preguntas de entrevista:**
- ¿Por qué Terraform en vez de configurar por consola?
- ¿Diferencia entre `plan` y `apply`?
- ¿Cómo se autentica tu CI contra AWS sin guardar credenciales?
- Si el pipeline se rompe a las 3 de la mañana, ¿cómo te enterás?

---

## Parte C — Template del `DECISIONS.md` (tu diario de decisiones)

Una entrada por decisión relevante. Es tu mejor prep de entrevista y a la vez documenta el proyecto.

```markdown
## [Fecha] — <Título de la decisión>

**Contexto:** qué problema estábamos resolviendo.

**Opciones consideradas:**
- Opción A — pros / contras
- Opción B — pros / contras

**Decisión:** elegí ___ porque ___.

**Trade-off que acepté:** ___ (qué resignás con esta elección).

**Cómo lo explicaría en 30 segundos:** ___
```

---

## Parte D — Auto-chequeo antes de cada entrevista

Elegí 3 partes random del proyecto e intentá explicarlas en voz alta, de memoria, en 2 minutos cada
una. Si en alguna te trabás, ese es tu tema de estudio de esa semana. La meta no es memorizar: es que
las decisiones te salgan naturales porque las tomaste vos.
```
