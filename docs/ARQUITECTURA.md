# Gestor Cron & Comandos — Blueprint de arquitectura

> Este documento es solo el plano/diseño. No hay código implementado todavía — es la base para empezar a construir cuando se decida.

## 1. Objetivo

App de escritorio con GUI, para cualquier distribución Linux, que permita sin tocar terminal:

1. **Tareas programadas (cron):** crear/editar/borrar acciones que se ejecutan según un horario (abrir programas, reproducir sonidos, ejecutar comandos, etc.).
2. **Comandos personalizados:** crear una "palabra clave" que al escribirla en la terminal ejecute una acción (ej. `hola` → imprime "hola", `navidad` → suena un villancico), eligiendo para qué shells se instala (bash/zsh/fish).

Debe instalarse con un único script (`install.sh`) que deje todo listo, sin asumir un gestor de paquetes concreto.

## 2. Decisiones de arquitectura ya tomadas

| Decisión | Elección |
|---|---|
| GUI | Python 3 + PySide6 (Qt6) |
| Comandos personalizados | Script fuente de verdad en `~/.local/bin` + alias/función opcional en el rc de la shell elegida |
| Backend de cron | Dual: crontab clásico de usuario **o** systemd user timer, elegible por tarea |

## 3. Stack tecnológico

- **Lenguaje:** Python 3.10+
- **GUI:** PySide6 — se instala vía pip dentro de un venv, no depende de paquetes Qt del sistema
- **Persistencia:** JSON en `~/.config/gestor-cron-comandos/` (migrar a SQLite solo si el volumen de datos lo justifica en el futuro)
- **Cron backend:** `python-crontab` (librería pip) para el crontab del usuario, sin sudo
- **systemd backend:** generación directa de unit files + `subprocess` llamando a `systemctl --user` (sin librería extra)
- **Audio:** detectar en tiempo de ejecución cuál de `paplay` / `aplay` / `ffplay` / `mpg123` está disponible y usar el primero que exista
- **Abrir archivos/imágenes/URLs:** `xdg-open` (estándar freedesktop, presente en cualquier distro de escritorio)
- **Notificaciones:** `notify-send` si existe; si no, se omite sin fallar
- **Tema:** seguir el tema claro/oscuro del sistema vía Qt6, con QSS mínimo para un acabado moderno

## 4. Estructura de directorios (a crear en fases posteriores)

```
gestor-cron-comandos/
├── install.sh
├── uninstall.sh
├── requirements.txt
├── pyproject.toml
├── src/
│   └── gestorcron/
│       ├── __init__.py
│       ├── main.py                 # arranca QApplication
│       ├── gui/
│       │   ├── main_window.py      # ventana principal con pestañas
│       │   ├── tab_cron.py         # pestaña "Tareas programadas"
│       │   ├── tab_comandos.py     # pestaña "Comandos personalizados"
│       │   ├── tab_ajustes.py      # pestaña "Ajustes"
│       │   ├── dialogs/
│       │   │   ├── nueva_tarea.py
│       │   │   └── nuevo_comando.py
│       │   └── widgets/
│       │       └── selector_accion.py   # widget compartido entre tareas y comandos
│       ├── core/
│       │   ├── modelo.py           # dataclasses: Tarea, Comando, Accion
│       │   ├── acciones.py         # registro (plugin-style) de tipos de acción
│       │   ├── cron_backend.py     # interfaz común + implementación crontab
│       │   ├── systemd_backend.py  # implementación systemd user timers
│       │   ├── comandos_backend.py # generación de scripts + alias/funciones de shell
│       │   └── almacen.py          # lectura/escritura del JSON de configuración
│       └── recursos/
│           ├── icono.svg
│           └── sonidos/            # sonidos de ejemplo empaquetados
├── docs/
│   └── ARQUITECTURA.md   (este documento)
└── tests/
```

## 5. Modelo de datos

### Tarea (cron job)
- `id` (uuid)
- `nombre`
- `backend`: `"crontab"` | `"systemd"`
- `horario`:
  - crontab → expresión cron de 5 campos (minuto hora día mes día-semana)
  - systemd → sintaxis `OnCalendar=`
  - en ambos casos la GUI ofrece un **constructor visual** (desplegables/checkboxes) que traduce a la sintaxis real, más una pestaña avanzada para escribirla a mano
- `accion`: referencia a un objeto Acción (ver más abajo)
- `habilitada`: bool
- próxima ejecución / última ejecución: solo lectura, calculado

### Comando personalizado
- `id` (uuid)
- `palabra_clave` (ej. `navidad`)
- `shells_destino`: subconjunto de `["bash", "zsh", "fish"]`
- `accion`: referencia a un objeto Acción
- `crear_alias`: bool — si además del script se añade alias/función en el rc de cada shell elegida

### Acción (unidad reutilizada entre tareas y comandos)
Tipo + parámetros propios. Catálogo inicial:

| Tipo | Parámetros | Uso |
|---|---|---|
| `mostrar_texto` | texto | imprime en terminal / notificación |
| `reproducir_audio` | ruta de archivo | villancico, alarma, etc. |
| `abrir_archivo_o_imagen` | ruta | vía `xdg-open` |
| `abrir_url` | url | vía `xdg-open` |
| `ejecutar_comando` | comando + intérprete | shell arbitrario |
| `ejecutar_script` | ruta a script existente | reutilizar scripts propios |
| `notificacion_escritorio` | título + cuerpo | vía `notify-send` |

Cada Acción sabe **compilarse** a un fragmento de shell portable. Ese mismo compilador es el único punto de verdad reutilizado para generar: la línea de crontab, el `ExecStart=` de systemd, y el script en `~/.local/bin`. Nuevos tipos de acción se añaden registrándolos en `acciones.py` (nombre visible, campos de formulario que necesita, función compiladora) — arquitectura tipo plugin para poder ampliar el catálogo sin tocar el resto de la app.

## 6. Backend de cron (dual)

### 6.1 Interfaz común
Clase base abstracta `TareaBackend` con: `crear(tarea)`, `actualizar(tarea)`, `eliminar(tarea)`, `listar()`, `habilitar/deshabilitar(tarea)`.

Cada entrada gestionada por la app lleva un identificador propio (comentario `# gestorcron:<uuid>` en la línea de crontab, o clave `X-GestorCron-Id=` en el unit file de systemd) para que `listar()` reconstruya solo las tareas creadas por esta app **sin tocar** entradas de cron ajenas que el usuario ya tuviera.

### 6.2 Implementación crontab
- `python-crontab` sobre el crontab del propio usuario (sin sudo, sin `/etc/cron.d`)
- Universal: cron/cronie viene preinstalado o se instala fácilmente en cualquier distro

### 6.3 Implementación systemd user timer
- Genera `~/.config/systemd/user/gestorcron-<id>.service` + `gestorcron-<id>.timer`
- El `.timer` lleva el `OnCalendar=` traducido del constructor visual
- Tras crear/editar: `systemctl --user daemon-reload` y `systemctl --user enable --now gestorcron-<id>.timer`
- La GUI comprueba disponibilidad de systemd (`which systemctl` + `systemctl --user status`) y deshabilita esta opción si no existe, para no romper en distros sin systemd (Alpine, Devuan, etc.)

## 7. Backend de comandos personalizados

- Se genera un script ejecutable en `~/.local/bin/<palabra_clave>` con un único shebang (`#!/usr/bin/env bash` por defecto, o el más específico si el usuario solo marcó una shell). El shebang del script **no** necesita coincidir con la shell interactiva activa del usuario: basta con que el archivo esté en el PATH y sea ejecutable para que funcione al escribir la palabra clave, sin importar qué shell tenga abierta.
- Permisos: `chmod +x` tras generarlo.
- Si `crear_alias` es true, además se añade en el rc de cada shell marcada, dentro de un bloque delimitado (para poder editar/borrar sin tocar el resto del archivo del usuario):
  - bash/zsh → `# >>> gestorcron:<id> >>> ... alias navidad="~/.local/bin/navidad" ... # <<< gestorcron:<id> <<<` en `.bashrc`/`.zshrc`
  - fish → archivo independiente `~/.config/fish/functions/navidad.fish` (fish carga automáticamente cada función de esa carpeta — ni siquiera hace falta tocar `config.fish`)
- Al eliminar un comando: se borra el script y se elimina el bloque delimitado del rc correspondiente, si existe.
- Validación: si la palabra clave coincide con un binario ya existente en el PATH, avisar antes de crear (para no ensombrecer comandos del sistema).

## 8. GUI (PySide6)

**Ventana principal:** pestañas superiores — *Tareas programadas* | *Comandos personalizados* | *Ajustes*. Tema claro/oscuro automático según el sistema.

**Pestaña "Tareas programadas"**
- Tabla: Nombre | Backend | Próxima ejecución | Habilitada | Acciones
- "+ Nueva tarea" → diálogo: nombre → backend (crontab / systemd / automático, con systemd atenuado si no disponible) → constructor visual de horario (rápido + pestaña avanzada de expresión cruda) → selector de acción → Guardar

**Pestaña "Comandos personalizados"**
- Lista: palabra clave | shells | acción resumida | activo
- "+ Nuevo comando" → diálogo: palabra clave (con validación de colisión) → checkboxes de shells detectadas en el sistema → checkbox "crear alias" → selector de acción → botón **Probar** (ejecuta la acción una vez sin guardar, para previsualizar) → Guardar

**Selector de Acción (widget compartido)** entre tareas y comandos: desplegable de tipo → formulario dinámico según el tipo (texto / selector de archivo de audio / selector de archivo o imagen / campo URL / campo comando + intérprete / título+cuerpo de notificación).

**Pestaña "Ajustes"**
- Estado de `~/.local/bin` en el PATH, con botón "Reparar PATH"
- Shells detectadas en el sistema
- Exportar / importar configuración (backup del JSON)
- Enlace a desinstalar (lanza `uninstall.sh` con confirmación)

## 9. `install.sh` — diseño

Objetivo: funcionar en cualquier distro sin asumir `apt`/`pacman`/`dnf`/`zypper`/`apk`, dejando la app lista para usar.

1. Comprobar `python3 >= 3.10`. Si falta, detectar qué gestor de paquetes existe (`command -v apt|dnf|pacman|zypper|apk`) y **sugerir** el comando de instalación — nunca ejecutar instalación de paquetes del sistema sin confirmación explícita del usuario.
2. Comprobar que `python3 -m venv` funciona (en Debian/Ubuntu a veces es un paquete aparte, `python3-venv`) — mismo tratamiento: detectar y sugerir, no forzar.
3. Crear venv dedicado en `~/.local/share/gestor-cron-comandos/venv`.
4. Instalar dependencias del `requirements.txt` (PySide6, python-crontab) dentro del venv.
5. Copiar `src/gestorcron` a `~/.local/share/gestor-cron-comandos/app`.
6. Crear lanzador ejecutable en `~/.local/bin/gestor-cron-comandos` que active el venv y corra `python -m gestorcron.main`.
7. Crear `~/.local/share/applications/gestor-cron-comandos.desktop` (estándar freedesktop: `Name=`, `Exec=`, `Icon=`, `Categories=Utility;`) para que aparezca en el menú de aplicaciones de cualquier entorno de escritorio (GNOME/KDE/XFCE/...).
8. Copiar el icono a `~/.local/share/icons/hicolor/...` (o referenciar ruta absoluta desde el `.desktop`).
9. Comprobar si `~/.local/bin` está en el PATH; si no, añadirlo en un bloque delimitado al rc de cada shell detectada.
10. Comprobar si `cron`/`cronie` está activo (`systemctl status cron`/`crond`, con fallback a `service cron status` en sistemas sin systemd) y avisar si falta — sin instalar un demonio del sistema automáticamente.
11. Resumen final: qué se instaló, dónde, cómo lanzarlo (comando o desde el menú), y qué falta resolver manualmente si algo no estaba disponible.
12. Idempotente: se puede re-ejecutar para actualizar sin duplicar entradas en rc ni `.desktop`.

### `uninstall.sh`
- Elimina venv, código copiado, `.desktop`, icono y lanzador de `~/.local/bin`.
- Pregunta si además se quieren eliminar los comandos personalizados y las tareas de cron/systemd gestionadas (por si el usuario prefiere conservarlas aunque desinstale la GUI).
- Limpia los bloques delimitados añadidos a los rc de shell.

## 10. Principios de portabilidad "cualquier distro"

- Nunca invocar `apt`/`pacman`/`dnf` para instalar dependencias sin consentimiento explícito.
- Toda dependencia Python vive aislada en un venv — cero conflicto con el Python del sistema.
- Usar solo estándares freedesktop.org (`xdg-open`, `.desktop`, `notify-send`) en vez de comandos atados a un entorno de escritorio concreto.
- Comprobar en tiempo de ejecución la existencia de cada herramienta externa opcional (reproductores de audio, `notify-send`) y degradar con gracia si falta, en vez de fallar.
- No asumir systemd: la ruta de crontab clásico debe quedar igual de completa sin él.

## 11. Seguridad

- El comando arbitrario que introduce el usuario en `ejecutar_comando` se escribe tal cual dentro del script generado, con el quoting apropiado — nunca se concatena dentro de un `eval` de forma insegura.
- Todos los scripts generados corren con los permisos propios del usuario, sin sudo ni privilegios elevados.
- Se avisa si la palabra clave de un comando coincide con un binario ya existente en el PATH, antes de crearlo.

## 12. Fases de implementación sugeridas (roadmap)

0. **Esqueleto** — estructura de carpetas, `pyproject.toml`, `requirements.txt`, ventana Qt vacía con las 3 pestañas.
1. **Modelo + almacén** — dataclasses, almacenamiento JSON, CRUD en memoria.
2. **Acciones** — registro de tipos de acción y su compilador a shell.
3. **Backend crontab** — crear/listar/editar/borrar tareas reales.
4. **Backend systemd timer** (opcional, con detección de disponibilidad).
5. **Backend de comandos personalizados** — scripts + alias/funciones fish.
6. **Pulido GUI** — temas, validaciones, botón "Probar".
7. **`install.sh` + `uninstall.sh` + `.desktop` + icono.**
8. **Pruebas manuales** en 2-3 distros distintas (ej. Arch, Debian/Ubuntu, Fedora) para validar la portabilidad real.
