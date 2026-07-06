# Setup inicial — Entorno (Docker/WSL2) y cuentas (AWS/Terraform)

> Hacé esto ANTES de la Fase 0 del proyecto. En modo aprendizaje: entendé el *por qué* de cada paso,
> no lo ejecutes en piloto automático.

---

## Orden recomendado (qué hacés ahora y qué diferís)

| Ahora (Fase 0-1) | Diferido (Fase 2, cuando toque Lambda) |
|---|---|
| WSL2 + Docker Desktop | Crear cuenta AWS personal |
| Entorno Docker (Python + Postgres + MinIO) | IAM user + Budget USD 1 |
| Terraform CLI instalado | Backend de estado en S3 + DynamoDB |
| — | HCP Terraform (opcional, probablemente ni lo necesites) |

**Idea clave:** la Fase 1 corre 100% local en Docker. No creás la cuenta AWS hasta la Fase 2, así no
arrancás el reloj de 6 meses antes de tiempo.

---

## Parte 1 — Entorno de desarrollo

### Concepto primero: ¿qué resuelve Docker acá?

Docker empaqueta tu app **con su propio "userland" de Linux y todas sus dependencias** dentro de una
imagen. Un contenedor que arranca de esa imagen corre igual en Windows, en tu futura Linux, o en un
servidor. Eso mata el clásico "en mi máquina anda" y hace que **cambiar de SO no rompa nada**: el
contenedor lleva su entorno adentro.

Dos ideas que conviene tener claras:
- **Imagen** = plantilla inmutable (la receta). **Contenedor** = instancia corriendo de esa imagen.
- **Dockerfile** = cómo se construye UNA imagen. **docker-compose** = cómo orquestás VARIOS
  contenedores juntos para desarrollo (tu app + una base de datos + almacenamiento).

Y una distinción importante para más adelante: el contenedor de **desarrollo** (para portabilidad de
tu laburo) es distinto de la imagen de **producción** (por ejemplo, la imagen que después va a Lambda
para servir el modelo). Son dos cosas separadas y está bien que lo sean.

### Windows: WSL2 + Docker Desktop (y por qué desarrollar DENTRO de WSL2)

En Windows, Docker corre sobre **WSL2** (una VM de Linux liviana e integrada). Recomendación fuerte:

1. Instalá **WSL2** y una distro (Ubuntu está bien).
2. Instalá **Docker Desktop** y activá el **backend WSL2** en sus settings.
3. **Cloná y trabajá el repo DENTRO del filesystem de WSL2** (ej. `~/proyectos/tasajusta`),
   **no** en `C:\Users\...`.

¿Por qué dentro de WSL2? Dos razones:
- **Performance:** los volúmenes de Docker con archivos que viven en WSL2 vuelan. Si los archivos
  están del lado de Windows y el contenedor los lee cruzando el límite Windows↔WSL, es lentísimo.
- **Migración futura gratis:** WSL2 *es* Linux. Cuando pases a una PC con Linux, ya venías trabajando
  en Linux; casi no cambia nada.

Editás con VS Code + la extensión **WSL** (o el editor que uses conectado a WSL). Se siente igual que
siempre, pero por debajo todo es Linux.

### El stack de contenedores para dev

`docker-compose.yml` con tres servicios (lo vamos a escribir juntos en la Fase 0, línea por línea):

- **`app`** — Python 3.11 con tus dependencias (ETL/ML/API). Acá vivís vos.
- **`postgres`** — Postgres local para desarrollo. En prod usás Supabase; en dev, este contenedor.
- **`minio`** — almacenamiento **S3-compatible** local. Desarrollás todo el data lake (bronze/silver/
  gold) con el mismo `boto3` que usarías contra S3 real; después solo cambiás el *endpoint*.

Boceto (referencia — lo construimos y explicamos juntos, no lo pegues a ciegas):

```yaml
services:
  app:
    build: .                      # usa tu Dockerfile
    volumes:
      - .:/workspace              # tu código, editable en caliente
    depends_on: [postgres, minio]
    env_file: [.env]

  postgres:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: dev
    volumes:
      - pgdata:/var/lib/postgresql/data   # persiste la data entre reinicios
    ports: ["5432:5432"]

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minio
      MINIO_ROOT_PASSWORD: minio123
    volumes:
      - miniodata:/data
    ports: ["9000:9000", "9001:9001"]     # 9000 API S3, 9001 consola web

volumes:
  pgdata:
  miniodata:
```

> Los **volumes** (`pgdata`, `miniodata`) son clave: sin ellos, cuando parás los contenedores perdés
> la base y los objetos. Con ellos, la data sobrevive.

---

## Parte 2 — Cuentas

### AWS

- **Necesitás una cuenta personal nueva.** NO uses la del trabajo: seguridad, riesgo de perder acceso,
  y prolijidad (no mezcles proyectos personales con infra del empleador).
- **Creala en la Fase 2, no ahora.** La cuenta nueva arranca el "plan gratuito" de 6 meses que después
  cierra la cuenta. No lo gastes en fases que no usan AWS.
- **Ojo con la elegibilidad de créditos:** los USD 200 en créditos son solo para clientes *nuevos*. Si
  alguna vez tuviste una cuenta AWS personal propia, podrías no calificar. Usar un IAM user dentro de
  la cuenta del trabajo **no** cuenta como haber tenido cuenta propia, así que en principio deberías
  calificar — pero tenelo presente por si el signup no te ofrece los créditos.
- Cuando la crees:
  - No trabajes con el usuario **root**. Creá un **IAM user** (o IAM Identity Center) con permisos
    acotados para el proyecto, y activá MFA en el root.
  - Configurá `aws configure` con las access keys de ese IAM user. Las keys van en
    `~/.aws/credentials` o en variables de entorno — **NUNCA en el repo**.
  - Creá el **Budget de USD 1** con alerta y **Cost Anomaly Detection** el día uno.

### Terraform (aclaración importante)

- **Terraform NO tiene "cuenta".** Es un CLI gratuito y open source. Lo instalás (en WSL2/Linux) y ya.
- Lo que sí tiene cuenta es **HCP Terraform (antes Terraform Cloud)** — un servicio de HashiCorp para
  estado remoto y ejecuciones. Si en el trabajo usaban eso, era una cuenta aparte. **Para este
  proyecto solo, probablemente no lo necesites.**

**¿Dónde vive el "estado" de Terraform?** El estado es el archivo donde Terraform recuerda qué recursos
creó. Opciones (decisión tuya):

| Opción | Pros | Contras | Cuándo |
|---|---|---|---|
| **Local** (`terraform.tfstate` en disco) | Simple, cero setup | No compartible, se puede perder | Para arrancar/aprender |
| **S3 + DynamoDB** (en tu cuenta AWS) | Estándar profesional; lock de estado; always-free | Requiere la cuenta AWS | Cuando armemos infra real (Fase 2) |
| **HCP Terraform** (free tier) | UI linda, estado hosteado | Otra cuenta más | Opcional, no lo veo necesario |

**Recomendación:** local para empezar, y **migrar a backend S3 + DynamoDB** en la Fase 2. Esa migración
es en sí una buena lección (y un buen tema de entrevista).

### Qué NUNCA va al repo (`.gitignore`)

```
*.tfstate
*.tfstate.*
.terraform/
.env
*.pem
credentials
```

Secretos y estado fuera de git, siempre. Esto es lo primero que mira alguien con criterio de seguridad.

---

## Conceptos que tenés que poder explicar (auto-chequeo)

**Docker:**
- ¿Cuál es la diferencia entre una imagen y un contenedor?
- ¿Para qué sirve `docker-compose` frente a un `Dockerfile` solo?
- ¿Qué es un volumen y por qué sin él perdés la data de Postgres al reiniciar?
- ¿Por qué Docker hace que tu proyecto sea portable entre Windows y Linux?
- ¿Por qué conviene desarrollar dentro de WSL2 y no en el filesystem de Windows?

**Cuentas / IaC:**
- ¿Por qué no usás credenciales del trabajo para un proyecto personal?
- ¿Qué es el "estado" de Terraform y por qué querés un backend remoto con lock?
- ¿Por qué MinIO te deja desarrollar el flujo de S3 sin una cuenta AWS?

---

## Checklist final antes de la Fase 0

- [ ] WSL2 instalado + Docker Desktop con backend WSL2.
- [ ] Repo clonado dentro del filesystem de WSL2.
- [ ] `docker compose up` levanta `app`, `postgres` y `minio` sin errores.
- [ ] Entrás a la consola de MinIO en `http://localhost:9001` y creás un bucket de prueba.
- [ ] Terraform CLI instalado (`terraform version`).
- [ ] `.gitignore` con secretos y estado excluidos.
- [ ] (Diferido) Cuenta AWS: la creás recién en la Fase 2.
