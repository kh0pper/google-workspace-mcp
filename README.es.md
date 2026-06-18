# Servidor MCP de Google Workspace

[English](./README.md) · **Español**

Brinda a un **asistente de IA local** acceso seguro y estructurado a **tu propio**
Google Workspace — Drive, Documentos, Hojas de cálculo, Presentaciones, Gmail,
Calendar y Apps Script — usando tu propia cuenta de Google, ejecutándose por
completo en tu computadora o servidor. Tus credenciales nunca salen de tu equipo.

Está pensado para combinarse con **[crow](https://maestro.press/software/crow-overview/)** —
un marco agéntico y plataforma MCP autoalojado y de
[código abierto](https://github.com/kh0pper/crow), diseñado explícitamente para
entornos sensibles a FERPA — para que las escuelas y otras organizaciones sensibles
a la privacidad puedan poner la IA a trabajar sobre sus propios datos **sin
enviarlos a terceros** (consulta [Privacidad de datos y FERPA](#privacidad-de-datos-y-ferpa)).
Como utiliza el [Model Context Protocol](https://modelcontextprotocol.io) abierto,
también funciona con cualquier otro cliente MCP (como Claude Code o Claude Desktop),
así que nunca quedas atado a una sola IA.

> _Parte de un esfuerzo por ayudar a administradores escolares a adoptar
> herramientas de IA de código abierto y compatibles con FERPA, en conjunto con crow._

> **Para quién es esta guía.** Está escrita para lectores no técnicos, incluidos
> administradores escolares. **No** necesitas ser programador. Donde tu acceso sea
> limitado (algo común en distritos escolares donde TI gestiona todo), la sección
> [¿Qué acceso tienes?](#qué-acceso-tienes) te ofrece un camino, incluido un correo
> que puedes enviar a tu departamento de TI.

---

## Qué puede hacer

**72 herramientas** en siete servicios de Google:

| Servicio | Qué puedes hacer | Herramientas |
|---|---|---|
| **Documentos** | Leer, buscar y editar de forma segura Google Docs (incl. comentarios) | 14 |
| **Presentaciones** | Leer y crear presentaciones de Google Slides | 17 |
| **Gmail** | Buscar/leer conversaciones, redactar respuestas, gestionar etiquetas y filtros | 11 |
| **Hojas de cálculo** | Leer (incl. fórmulas), escribir y agregar datos; crear/renombrar/eliminar pestañas; formato numérico y visual (colores/bordes/anchos/inmovilizar) | 10 |
| **Drive** | Buscar, listar, organizar, **copiar**, renombrar, enviar a la papelera, transferir propiedad y crear accesos directos a archivos y carpetas | 11 |
| **Calendar** | Listar/leer/crear eventos, responder invitaciones | 5 |
| **Apps Script** | Leer, editar y subir el código de un proyecto de Apps Script; ejecutar funciones | 4 |

**La seguridad viene integrada.** No existe una herramienta para "reemplazar todo
el documento" (en el pasado ha destruido el formato); las ediciones son
quirúrgicas. La única herramienta que realmente *envía* correo está restringida a
una lista de direcciones que está **vacía de forma predeterminada**; todo lo demás
crea **borradores** para que tú los revises y envíes.

---

## Lo que necesitarás

- Una cuenta de Google (una cuenta personal `@gmail.com`, o una cuenta de Google
  Workspace de tu escuela u organización).
- Unos **15 minutos**.
- **Python 3.11 o más reciente** en la computadora que ejecutará el servidor.
  (Para verificar, abre una terminal y ejecuta `python3 --version`.)

---

## ¿Qué acceso tienes?

Configurar esto requiere crear una pequeña "app de OAuth" en la **Consola de Google
Cloud**. En muchos distritos escolares, TI restringe quién puede hacerlo. Tómate 30
segundos para identificar tu nivel y luego sigue el camino correspondiente.

> **Prueba rápida:** Abre [console.cloud.google.com](https://console.cloud.google.com)
> e inicia sesión con la cuenta que quieras usar. ¿Puedes crear un **Nuevo proyecto**
> (*New Project*)? ¿La página está bloqueada o le faltan opciones?

### Nivel A — Acceso completo (puedes crear un proyecto)
Puedes hacer todo tú mismo. Sigue la **[Parte 1](#parte-1--configurar-google-cloud-nivel-ab)**
y elige **Interno** (*Internal*) en la pantalla de consentimiento. Es la mejor
experiencia: tu inicio de sesión **nunca expira** y no aparece la advertencia de
"app no verificada".

### Nivel B — Tienes la Consola, pero "Interno" está deshabilitado o los permisos están bloqueados
Tu proyecto existe, pero tu distrito restringe las apps de terceros. Dos opciones:
- Usa **Externo** (*External*) y agrégate como **usuario de prueba** (*Test user*)
  (la Parte 1 lo cubre). Nota: las apps Externas en modo "Testing" te obligan a
  **volver a autorizar cada ~7 días**, y verás una pantalla de "Google no ha
  verificado esta app" (puedes continuar de forma segura; consulta la Parte 1).
- **Mejor aún:** pide a tu administrador de TI/Workspace que marque la app como
  **De confianza** (*Trusted*) para que desaparezcan las advertencias y los límites.
  Envíale la [plantilla de correo](#correo-para-enviar-a-tu-departamento-de-ti) con
  el ID de cliente de OAuth.
- Verificación de síntomas: un error como *"Acceso bloqueado: esta app está
  bloqueada por tu administrador"* significa que es una política del administrador,
  no algo que puedas arreglar en la pantalla de consentimiento; usa la plantilla de
  correo.

### Nivel C — Sin acceso a la Consola de Google Cloud
No puedes crear la app tú mismo, pero tienes opciones:
1. **Pide a TI que la cree por ti.** Envía la
   [plantilla de correo](#correo-para-enviar-a-tu-departamento-de-ti). Crean un
   cliente de OAuth tipo "Desktop" y te envían el archivo `credentials.json` (es
   seguro enviarlo por correo: no es una contraseña de tu cuenta).
2. **Pruébalo primero en una cuenta personal `@gmail.com`** para aprender cómo
   funciona. Una cuenta personal tiene acceso completo y te permite evaluar la
   herramienta. **No uses una cuenta personal para expedientes de estudiantes ni
   otros datos protegidos**; consulta [Privacidad de datos y FERPA](#privacidad-de-datos-y-ferpa).

### Nivel D — Tu distrito bloquea por completo las apps de terceros
Quizá no sea posible en la cuenta de trabajo sin un cambio de política. Aún puedes
evaluar la herramienta en una cuenta personal `@gmail.com` (solo para aprender, sin
datos protegidos) y compartir esta página con TI para discutir un camino a seguir.

### Correo para enviar a tu departamento de TI

> **Asunto:** Solicitud: cliente de OAuth para una herramienta local de Google Workspace
>
> Hola [equipo de TI]:
>
> Me gustaría usar una herramienta local de código abierto que permite a un
> asistente de IA ayudarme con mi propio Google Workspace (Documentos, Hojas de
> cálculo, Presentaciones, Gmail, Calendar). Se ejecuta en mi propia computadora y
> usa el inicio de sesión estándar de Google; el conector en sí no envía datos a
> ningún servidor de terceros.
>
> ¿Podrían, por favor, hacer una de estas dos cosas?
> 1. Crear un **cliente de OAuth** de tipo **Desktop app** (aplicación de
>    escritorio) en un proyecto de Google Cloud de nuestro dominio y enviarme el
>    `credentials.json` descargado, **o**
> 2. Marcar mi ID de cliente de OAuth como **De confianza** (*Trusted*) en
>    *Consola de administración → Seguridad → Controles de API → Control de acceso
>    a apps* para que pueda usar estas APIs de Google.
>
> Necesita estas APIs habilitadas: **Drive, Documentos, Hojas de cálculo,
> Presentaciones, Gmail, Calendar, Apps Script**, con permisos para leer/editar mi
> propio Drive/Docs/Sheets/Slides, redactar y administrar mi Gmail, administrar mi
> Calendar y administrar mis propios proyectos de Apps Script.
>
> ¡Gracias!

---

## Parte 1 — Configurar Google Cloud (Nivel A/B)

Haz esto en tu navegador, con la sesión iniciada en la cuenta que usarás.

1. Ve a [console.cloud.google.com](https://console.cloud.google.com) y crea un
   **Nuevo proyecto** (cualquier nombre, p. ej. `workspace-mcp`).
2. **Habilita las APIs.** Con la barra de búsqueda de arriba, busca y **Habilita**
   cada una de estas (unos segundos cada una):
   **Google Drive API**, **Google Docs API**, **Google Sheets API**,
   **Google Slides API**, **Gmail API**, **Google Calendar API**,
   **Apps Script API**.
3. **Activa la API de Apps Script para tu usuario** (solo necesario para las
   herramientas de Apps Script). Visita
   [script.google.com/home/usersettings](https://script.google.com/home/usersettings)
   y pon **Google Apps Script API** en **Activado** (*On*). (Es un interruptor por
   usuario, separado de habilitar la API en el proyecto, y se hace una sola vez.)
4. **Configura la pantalla de consentimiento de OAuth** (menú izquierdo →
   *APIs y servicios → Pantalla de consentimiento de OAuth*, o
   *Plataforma de Google Auth*).
   - **Tipo de usuario:** elige **Interno** (*Internal*) si está disponible (lo
     mejor: no expira, sin advertencias). Si solo hay **Externo** (*External*),
     elígelo y agrega tu propio correo como **usuario de prueba** (*Test user*).
   - Completa el nombre de la app y tu correo donde se pida.
5. **Crea las credenciales** (menú izquierdo → *Credenciales* → *Crear
   credenciales* → *ID de cliente de OAuth*).
   - **Tipo de aplicación:** **Desktop app** (aplicación de escritorio). (Esto es
     importante: es lo que hace funcionar el inicio de sesión local. **No** elijas
     "Aplicación web".)
   - Haz clic en **Crear** y luego en **Descargar JSON**.

> **Sobre la pantalla "Google no ha verificado esta app" (solo apps Externas):**
> Como la app es tuya y no está publicada, Google muestra una advertencia. Haz clic
> en **Configuración avanzada → Ir a [nombre de tu app] (no seguro)**: es tu propia
> app, así que es seguro. Las apps Internas no muestran esto. Ten en cuenta también
> que las apps Externas en "Testing" permiten hasta **100 usuarios de prueba** y
> requieren volver a autorizar cada **~7 días**.

---

## Parte 2 — Instalar el servidor

Necesitas los archivos del proyecto en la máquina que ejecutará el servidor, y sus
dependencias instaladas. La forma más sencilla usa
[`uv`](https://docs.astral.sh/uv/) (un instalador rápido de herramientas de Python):

```bash
git clone https://github.com/kh0pper/google-workspace-mcp.git
cd google-workspace-mcp
uv sync
```

¿Prefieres `pip` a secas? Desde dentro de la carpeta clonada:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install .
```

---

## Parte 3 — Iniciar sesión (autorizar) — una sola vez

1. Coloca el `credentials.json` que descargaste (o que te dio TI) aquí:
   - **macOS / Linux:** `~/.config/google-workspace-mcp/credentials.json`
   - (O define la variable de entorno `GOOGLE_CREDENTIALS_FILE` con su ubicación.)
2. Ejecuta el comando de autorización:

   ```bash
   uv run google-workspace-mcp-authorize
   ```

   Se abre tu navegador; inicia sesión y aprueba. Listo: se guarda un token junto a
   tus credenciales y el servidor lo reutilizará automáticamente.

**¿En un servidor remoto sin navegador?** Usa el flujo de copiar y pegar:

```bash
uv run google-workspace-mcp-authorize --manual
```

Imprime un enlace. Ábrelo en cualquier dispositivo, inicia sesión y aprueba. Luego
tu navegador intentará cargar una página `http://localhost/?code=...` que **no
abrirá; eso es lo esperado**. Copia la URL completa de la barra de direcciones y
pégala de vuelta en la terminal.

---

## Parte 4 — Conéctalo a tu IA (crow recomendado)

El servidor habla MCP por stdio, así que funciona con cualquier cliente MCP. Para
una configuración **compatible con FERPA y totalmente local**, combínalo con
**[crow](https://maestro.press/software/crow/)** — un marco agéntico y plataforma
MCP autoalojado. Ejecuta crow con un **modelo local** (Ollama o cualquier endpoint
compatible con OpenAI) y nada sale de tu red. Puedes **instalarlo con un solo clic**
desde el panel de **Extensiones** de Crow (está en el
[registro oficial de add‑ons](https://github.com/kh0pper/crow-addons)), o conectarlo
como un servidor MCP estándar con la configuración de abajo, que también funciona en
otros clientes MCP (como Claude Code o Claude Desktop).

Tienes un punto de partida listo para copiar en
[`.mcp.json.example`](./.mcp.json.example).

**Configuración del servidor MCP:**

```json
{
  "mcpServers": {
    "google-workspace": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/google-workspace-mcp", "google-workspace-mcp"]
    }
  }
}
```

Reemplaza `/absolute/path/to/google-workspace-mcp` con la carpeta que clonaste.
(Si lo instalaste en tu PATH con `pipx install .` o `uv tool install .`, puedes
usar `"command": "google-workspace-mcp"` sin `args`.)

- **crow (recomendado):** abre el panel de **Extensiones** de Crow e instala
  **Google Workspace** con un solo clic (o pídeselo a tu IA: *«Instala el add‑on de
  Google Workspace»*), para que todo permanezca en tu propio hardware.
- **Claude Code:** agrega el bloque anterior a un `.mcp.json` en tu proyecto, o
  ejecuta `claude mcp add`. Reinicia y aprueba el servidor.
- **Otros clientes (Claude Desktop, etc.):** agrega la misma entrada de servidor al
  archivo de configuración MCP de ese cliente.

---

## Privacidad de datos y FERPA

**Esto importa si manejas expedientes de estudiantes u otros datos protegidos.**

Este conector se ejecuta **localmente** y solo se comunica con Google usando **tu
propio** inicio de sesión. Pero el contenido de documentos, correos o calendario
que recupera se entrega luego a **cualquier modelo de IA que use tu cliente**, y
*esa elección* determina si los datos salen de tu control:

- **Modelos de IA en la nube / alojados** (una API alojada) reciben ese contenido
  como parte de su entrada. Para expedientes de estudiantes, trátalo como una
  divulgación a un tercero que debe estar cubierta por las políticas y los acuerdos
  de tratamiento de datos de tu distrito **antes** de usarlo.
- **Modelos de IA locales / autoalojados** mantienen todo en tu propia computadora
  o servidor: **no hay divulgación a terceros**, que es lo que hace **posible una
  implementación compatible con FERPA**. **[crow](https://maestro.press/software/crow/)**
  está hecho precisamente para esto: una plataforma autoalojada que combinas con un
  modelo local ([Ollama](https://ollama.com) o cualquier endpoint compatible con
  OpenAI) para que tus datos permanezcan en una infraestructura que tú controlas.

Mantener los datos en local *facilita* el cumplimiento; no lo *garantiza* por sí
solo (también aplican los controles de acceso y las políticas de tu distrito).
**Sigue la política de tu distrito y consulta a tu oficial de privacidad** antes de
usar esto con datos protegidos.

---

## Referencia de herramientas (72 herramientas)

- **Documentos (14):** `gdocs_read`, `gdocs_read_section`, `gdocs_get_structure`,
  `gdocs_find_replace`, `gdocs_append`, `gdocs_insert_at_heading`,
  `gdocs_replace_section`, `gdocs_create`, `gdocs_rewrite_passages`, más
  herramientas de comentarios (`gdocs_list_comments`, `gdocs_add_comment`,
  `gdocs_reply_comment`, `gdocs_resolve_comment`, `gdocs_apply_comment_edit`).
- **Presentaciones (17):** leer/estructura/notas, crear presentación,
  agregar/duplicar/eliminar/reordenar diapositivas, agregar cuadros de texto e
  imágenes, dar formato a texto/párrafos, buscar y reemplazar, exportar.
- **Gmail (11):** `gmail_search_threads`, `gmail_get_thread`, `gmail_create_draft`,
  `gmail_create_threaded_reply`, `gmail_send_to_self`, `gmail_send_threaded_to_self`,
  `gmail_label_thread`, `gmail_archive`, `gmail_list_labels`, `gmail_create_label`,
  `gmail_create_filter`.
- **Drive (11):** `gdrive_search`, `gdrive_list_folder`, `gdrive_find_folder`,
  `gdrive_get_metadata`, `gdrive_create_folder`, `gdrive_move_file`,
  `gdrive_copy_file`, `gdrive_trash_file`, `gdrive_rename`, `gdrive_transfer_ownership`,
  `gdrive_create_shortcut`.
- **Calendar (5):** `gcal_list_calendars`, `gcal_list_events`, `gcal_get_event`,
  `gcal_create_event`, `gcal_respond_to_event`.
- **Hojas de cálculo (10):** `sheets_list`, `sheets_read` (incl. `value_render_option=FORMULA`),
  `sheets_write`, `sheets_append`, `sheets_add_tab`, `sheets_rename_tab`,
  `sheets_delete_tab`, `sheets_set_number_format`, `sheets_get_tabs`, `sheets_batch_update`.
- **Apps Script (4):** `apps_script_get_content`, `apps_script_update_file`,
  `apps_script_update_content`, `apps_script_run`. Requiere la API de Apps Script
  habilitada + el interruptor por usuario en script.google.com/home/usersettings;
  `apps_script_run` además necesita una implementación tipo «API ejecutable».

---

## Solución de problemas

- **"Acceso bloqueado / app bloqueada por tu administrador":** una política del
  administrador de Workspace está bloqueando la app. Pide a TI que la marque como
  De confianza (consulta la plantilla de correo).
- **"Google no ha verificado esta app":** es lo esperado para tu propia app
  Externa: *Configuración avanzada → Ir a [app] (no seguro)*. Evítalo por completo
  usando una app Interna.
- **El inicio de sesión expiró después de ~una semana:** estás en una app Externa
  en "Testing"; publícala o cambia a una app Interna para detener la expiración de
  7 días.
- **"No autenticado" al ejecutar una herramienta:** ejecuta
  `google-workspace-mcp-authorize` de nuevo, o apunta `GOOGLE_TOKEN_FILE` a tu token.
- **Se denegó un permiso (scope):** si desmarcaste un permiso durante el inicio de
  sesión, vuelve a ejecutar la autorización y aprueba todos los permisos solicitados.

### Configuración (variables de entorno)

| Variable | Predeterminado | Para qué sirve |
|---|---|---|
| `GOOGLE_CREDENTIALS_FILE` | `~/.config/google-workspace-mcp/credentials.json` | Tu cliente de OAuth descargado |
| `GOOGLE_TOKEN_FILE` | `~/.config/google-workspace-mcp/token.json` | Dónde se guarda tu token de inicio de sesión |
| `GOOGLE_OAUTH_LOCAL_PORT` | `8090` | Puerto local usado durante el inicio de sesión en el navegador |
| `GMAIL_SEND_TO_SELF_ALLOWLIST` | *(vacío)* | Direcciones separadas por comas a las que `gmail_send_to_self` puede enviar |

---

## Hoja de ruta

- **Extensión de crow de un clic — ya disponible.** Se instala desde el panel de
  **Extensiones** de Crow a través del
  [registro oficial de add‑ons](https://github.com/kh0pper/crow-addons).
- **Publicar en PyPI** para que `uvx google-workspace-mcp` funcione sin la URL de git.
- **Consultoría:** crow y herramientas como esta se ofrecen para ayudar a distritos
  y administradores a poner en marcha IA de código abierto y compatible con FERPA en
  su propia infraestructura.

## Licencia

[MIT](./LICENSE) © Maestro Press. Libre para usar, modificar y distribuir.
