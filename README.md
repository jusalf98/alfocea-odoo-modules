# Alfocea Odoo Modules · Suite de suscripciones para Odoo 18

Proyecto Final (TFM) del **Máster en Desarrollo con Inteligencia Artificial** (BIG school).

- **Autor:** Justo Alfocea Frutos
- **Repositorio (entregable del proyecto):** [github.com/jusalf98/alfocea-odoo-modules](https://github.com/jusalf98/alfocea-odoo-modules)

| Recurso | Enlace |
|---|---|
| Código fuente | https://github.com/jusalf98/alfocea-odoo-modules |
| Despliegue | _Pendiente de publicar_ |
| Presentación (slides) | _Pendiente de publicar_ |
| Vídeo explicativo | _Pendiente de publicar_ |

---

## 1. Descripción general

Odoo es un ERP de código abierto muy extendido entre pymes, pero su edición Community (gratuita) **no incluye gestión de suscripciones**: el módulo `sale_subscription` solo existe en la edición Enterprise, de pago.

Este proyecto es una **suite de módulos para Odoo 18 Community** que cubre ese hueco. Permite gestionar los dos lados de una suscripción:

- **Las que vende la empresa** a sus clientes: cajas mensuales, cuotas, licencias, servicios… Al confirmar un pedido de venta se crea la suscripción automáticamente, y cada periodo se genera solo el pedido de renovación.
- **Las que la empresa contrata** a sus proveedores: software, alojamiento, mantenimientos… Así sus costes y renovaciones quedan controlados en el mismo sitio.

La suite se ha diseñado por capas: un **núcleo** independiente y módulos de integración que se instalan según lo que necesite cada empresa. Sigue las guías de desarrollo de la [Odoo Community Association (OCA)](https://github.com/OCA) y de Odoo SA, e incluye pruebas automáticas, control de calidad con pre-commit y traducción completa al español.

## 2. Stack tecnológico

| Área | Tecnología |
|---|---|
| ERP / framework | [Odoo 18.0](https://www.odoo.com) Community (ORM, vistas XML, QWeb, acciones planificadas) |
| Lenguaje backend | Python 3.12 |
| Vistas | XML de Odoo 18 (`list`, `form`, `kanban`, `search`, `chatter`) |
| Base de datos | PostgreSQL 16 |
| Contenedores | Docker y Docker Compose |
| Pruebas | Framework de tests de Odoo (`TransactionCase` / `BaseCommon`) |
| Calidad de código | pre-commit con la configuración de OCA 18.0: ruff, ruff-format, pylint-odoo, prettier (XML), oca-checks-odoo-module, oca-checks-po |
| Utilidades | click-odoo-contrib (`click-odoo-update`) |
| Traducciones | gettext (`.po`), español completo |
| Desarrollo asistido por IA | Claude Code (Anthropic), con skills y agentes propios (ver sección 8) |
| Control de versiones | Git y GitHub |

## 3. Instalación y ejecución

### Requisitos

- Docker Desktop (o Docker Engine) con Docker Compose v2.
- Git.

### Puesta en marcha con Docker

1. **Crea una carpeta de trabajo y clona el repositorio dentro:**

   ```bash
   mkdir odoo18 && cd odoo18
   git clone https://github.com/jusalf98/alfocea-odoo-modules.git custom_addons/alfocea-odoo-modules
   ```

2. **Crea `docker-compose.yml` en `odoo18/`:**

   ```yaml
   services:
     db:
       image: postgres:16
       environment:
         POSTGRES_DB: postgres
         POSTGRES_USER: odoo
         POSTGRES_PASSWORD: odoo
       volumes:
         - odoo-db-data:/var/lib/postgresql/data

     odoo:
       image: odoo:18.0
       depends_on:
         - db
       ports:
         - "8069:8069"
       environment:
         HOST: db
         USER: odoo
         PASSWORD: odoo
       volumes:
         - odoo-web-data:/var/lib/odoo
         - ./custom_addons/alfocea-odoo-modules:/mnt/custom-addons/alfocea-odoo-modules
       command: odoo --addons-path=/mnt/custom-addons/alfocea-odoo-modules

   volumes:
     odoo-db-data:
     odoo-web-data:
   ```

3. **Arranca los contenedores:**

   ```bash
   docker compose up -d
   ```

4. **Crea la base de datos.** Abre http://localhost:8069 y rellena el formulario:
   - **Master Password:** la imagen no trae ninguna configurada, así que Odoo propone una. Guárdala: se pide para crear, copiar o borrar bases de datos.
   - **Email y Password:** son el usuario y la contraseña con los que entrarás en Odoo. Usa los de la sección 6 si quieres que coincidan con los de prueba.

5. **Instala los módulos.** En *Aplicaciones*, busca e instala **Subscription Core** y **Subscription Sale**. Este último instala también *Ventas* si no lo estaba. Si no aparecen, activa el modo desarrollador y pulsa *Actualizar lista de aplicaciones*.

### Instalación en un Odoo 18 existente (sin Docker)

1. Clona el repositorio en cualquier carpeta del servidor.
2. Añade esa carpeta al parámetro `addons_path` del `odoo.conf`.
3. Reinicia Odoo, actualiza la lista de aplicaciones e instala los módulos.

### Ejecutar las pruebas automáticas

Con los contenedores levantados, crea una base de datos desechable, instala los módulos y ejecuta sus tests:

```bash
docker compose run --rm odoo odoo -d test_suscripciones \
  -i alfo_subscription_core,alfo_subscription_sale \
  --test-enable --test-tags /alfo_subscription_core,/alfo_subscription_sale \
  --addons-path=/mnt/custom-addons/alfocea-odoo-modules \
  --stop-after-init --without-demo=all
```

El resultado esperado es `0 failed, 0 error(s) of 54 tests`.

## 4. Estructura del proyecto

Cada carpeta del repositorio es un módulo de Odoo independiente, con la estructura recomendada por OCA. Todos los módulos llevan el prefijo `alfo_`.

```
alfocea-odoo-modules/
├── README.md                          Documentación del proyecto (este fichero)
├── alfo_subscription_core/            Núcleo: planes, contratos y ciclo de vida
│   ├── __manifest__.py                Metadatos, dependencias (base, mail, product) y ficheros de datos
│   ├── models/                        Una clase por fichero
│   │   ├── subscription_plan.py           Plan: periodicidad, intervalo, días de prueba
│   │   ├── subscription_contract.py       Contrato: tipo, estados, fechas, acciones y cron
│   │   ├── subscription_contract_line.py  Líneas: producto, cantidad, precio de venta o compra
│   │   └── product_template.py            Plan de suscripción por defecto en el producto
│   ├── views/                         Formularios, listas, kanban, búsquedas y menús
│   ├── security/                      Grupos (Usuario / Administrador), permisos y reglas multicompañía
│   ├── data/                          Secuencias (SUB/, PSUB/) y acción planificada diaria
│   ├── i18n/es.po                     Traducción al español
│   ├── tests/                         32 tests (common.py con los datos compartidos)
│   ├── readme/                        Fragmentos de documentación del módulo (formato OCA)
│   └── static/description/            Icono y página de descripción del módulo
└── alfo_subscription_sale/            Integración con Ventas
    ├── __manifest__.py                Depende de alfo_subscription_core y sale
    ├── models/
    │   ├── sale_order.py                  Crea y activa suscripciones al confirmar pedidos
    │   ├── sale_order_line.py             Prepara las líneas de contrato desde el pedido
    │   ├── subscription_contract.py       Cron de renovación: genera los pedidos de cada periodo
    │   ├── subscription_contract_line.py  Prepara las líneas del pedido de renovación
    │   └── subscription_plan.py           Opción de confirmar automáticamente las renovaciones
    ├── views/                         Smart buttons pedido ⇄ suscripción y opciones del plan
    ├── data/                          Acción planificada de renovación
    ├── i18n/es.po                     Traducción al español
    └── tests/                         22 tests
```

**Arquitectura por capas.** El núcleo no depende de Ventas, Compras ni Contabilidad. Cada integración es un módulo aparte que depende del núcleo, nunca al revés, lo que evita dependencias circulares. Así una empresa instala solo lo que necesita, y la suite puede crecer con nuevos módulos (por ejemplo, Compras o Facturación) sin tocar el núcleo.

## 5. Funcionalidades principales

### Subscription Core (`alfo_subscription_core`)

- **Planes de suscripción:**
  - Periodicidad en días, semanas, meses o años, con intervalo configurable ("cada 3 meses").
  - Días de prueba gratuita.
  - Archivado.
  - Seguimiento de cambios en el chatter.
- **Suscripciones de dos tipos:**
  - **De clientes (venta)**, con referencia `SUB/00001`. El precio de las líneas sale del precio de venta del producto.
  - **De proveedores (compra)**, con referencia `PSUB/00001`. El precio sale de la tarifa del proveedor para ese producto o, si no la hay, del coste.
- **Ciclo de vida con estados:**
  - Borrador → En prueba → Activo → Pausado → Cancelado / Vencido.
  - Botones Iniciar, Pausar, Reanudar, Cancelar y Restablecer a borrador. Solo se permiten las transiciones válidas.
- **Cálculo automático** de la fecha de fin de la prueba, de la primera factura y del total del contrato.
- **Acción planificada diaria:** pasa a *Activo* las pruebas terminadas y a *Vencido* los contratos que superan su fecha de fin.
- **Plan por defecto en el producto:** solo lo ve y edita el administrador de suscripciones.
- **Vistas de lista, formulario y kanban:**
  - Columnas por estado en el kanban.
  - Filtros por tipo, estado y "a facturar".
  - Chatter y actividades en los contratos.
- **Seguridad:**
  - Grupos *Suscripciones / Usuario* y *Suscripciones / Administrador*.
  - Reglas multicompañía.
  - El administrador de Odoo recibe acceso completo al instalar.

### Subscription Sale (`alfo_subscription_sale`)

- **Suscripción automática al vender:**
  - Al confirmar un presupuesto, cada producto con plan crea e **inicia** la suscripción del cliente (una por plan).
  - Si el cliente ya tiene una suscripción abierta con ese plan, se reutiliza y no se duplica.
  - Funciona aunque el comercial no tenga permisos de suscripciones (se ejecuta con `sudo`).
- **Pedidos de renovación automáticos:**
  - Una acción planificada diaria genera el pedido de venta de cada suscripción cuando le toca el periodo.
  - Incluye las líneas y precios del contrato, y el periodo en la descripción, en el idioma del cliente.
  - Recupera los periodos atrasados, respeta la fecha de fin y mantiene el comercial del pedido original.
  - Si un contrato da error, se registra y no bloquea al resto.
- **Sin cobro doble:** el pedido que crea la suscripción cubre el primer periodo, así que la primera renovación se programa un periodo después.
- **Confirmación configurable por plan:** los pedidos de renovación se confirman solos o se quedan como presupuesto para revisarlos.
- **Smart buttons en los dos sentidos:** del pedido a sus suscripciones y de la suscripción a sus pedidos.

## 6. Usuario y contraseña de prueba

Odoo tiene login. Para la base de datos de prueba se usan estas credenciales:

| Entorno | URL | Usuario | Contraseña |
|---|---|---|---|
| Local (Docker) | http://localhost:8069 | `admin` | `admin` |
| Despliegue | _Pendiente de publicar_ | _Pendiente_ | _Pendiente_ |

En local, el usuario y la contraseña son los que se introducen al crear la base de datos (paso 4 de la instalación). Si se usan `admin` / `admin`, coinciden con la tabla. El usuario administrador tiene acceso completo a la app *Suscripciones* desde la instalación.

### Guion de prueba rápido

1. **Crea los planes:** en *Suscripciones → Configuración → Planes*, crea "Mensual" (cada 1 mes) y "Mensual con prueba" (14 días de prueba).
2. **Asigna un plan a un producto:** abre un producto y pon "Mensual" en **Plan de suscripción**, junto a la categoría.
3. **Vende el producto:** crea y confirma un presupuesto con él. En el pedido aparece el botón **Suscripciones**, con la suscripción ya **Activa**.
4. **Genera una renovación:**
   1. En la suscripción, pon la **Fecha de la próxima factura** a hoy.
   2. Ve a *Ajustes → Técnico → Acciones planificadas → "Suscripciones: crear pedidos de venta de renovación"* y pulsa **Ejecutar manualmente**.
   3. Se crea el pedido del periodo y la fecha avanza un mes.
5. **Registra una suscripción de proveedor:** en *Suscripciones de proveedores*, crea una para un servicio que contratas y comprueba que el precio sale de la tarifa del proveedor.

## 7. Calidad y pruebas

- **54 tests automáticos:** 32 en el núcleo y 22 en la integración de ventas. Cubren cálculos, validaciones, transiciones de estado, acciones planificadas, permisos, renovaciones (incluidos periodos atrasados y aislamiento de errores) y la creación desde pedidos con un comercial sin permisos.
- **pre-commit** con la configuración oficial de OCA para Odoo 18: formato (ruff, prettier), análisis estático (pylint-odoo) y validación de manifests y traducciones.
- **Comprobación de dependencias** entre módulos para garantizar que no hay ciclos.
- **Traducción al español** del 100 % de los textos.
- **Convenciones propias, aplicadas en todos los módulos:**
  - Prefijo `alfo_`.
  - Una clase por fichero.
  - Wizards en `wizard/`.
  - Sin etiquetas `string` redundantes.
  - Sin `self.env[...]` evitables dentro de bucles.
  - Operaciones en bloque en lugar de llamadas dentro de bucles.

## 8. Desarrollo con Inteligencia Artificial

El proyecto se ha desarrollado con **Claude Code** como asistente de programación, aplicando el flujo de trabajo del máster: la IA propone e implementa, y el autor define los requisitos, revisa, decide y hace los commits. Para que la IA trabajase siempre con los mismos criterios se crearon:

- **Una skill de desarrollo de módulos Odoo.** Recoge las convenciones de OCA y Odoo SA y las reglas propias del autor: prefijo, autoría, estructura, seguridad, tests, traducciones y rendimiento.
- **Agentes especializados:**
  - Uno que pasa el pre-commit y los tests de los módulos indicados.
  - Uno que detecta dependencias circulares entre módulos.
  - Uno que actualiza los módulos en una base de datos.
- **Scripts de apoyo:**
  - Análisis del grafo de dependencias.
  - Fusión de traducciones `.po`.
  - Generación de los iconos de la suite con el estilo de Odoo 18.

Todo el código se ha verificado ejecutando sus tests en contenedores Docker, con bases de datos desechables, antes de darlo por bueno.

## 9. Hoja de ruta

- `alfo_subscription_purchase`: generación automática de pedidos de compra para las suscripciones de proveedores.
- `alfo_subscription_account`: facturación directa de suscripciones, sin pasar por pedidos.
- Portal del cliente para consultar y gestionar sus suscripciones.

## Licencia

LGPL-3. La licencia de cada módulo figura en su `__manifest__.py`.

## Autor

**Justo Alfocea Frutos**. Proyecto Final del Máster en Desarrollo con Inteligencia Artificial.
