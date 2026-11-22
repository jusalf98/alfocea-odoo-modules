# Alfocea Odoo Modules · Suite de suscripciones para Odoo 18

Proyecto Final (TFM) del **Máster en Desarrollo con Inteligencia Artificial** (BIG school).

- **Autor:** Justo Alfocea Frutos
- **Repositorio (entregable del proyecto):** [github.com/jusalf98/alfocea-odoo-modules](https://github.com/jusalf98/alfocea-odoo-modules)


---

## 1. Descripción general

Odoo es un ERP de código abierto muy extendido entre pymes, pero su edición Community (gratuita) **no incluye gestión de suscripciones**: el módulo `sale_subscription` solo existe en la edición Enterprise, de pago.

Este proyecto es una **suite de módulos para Odoo 18 Community** que cubre ese hueco. Permite gestionar los dos lados de una suscripción:

- **Las que vende la empresa** a sus clientes: cajas mensuales, cuotas, licencias, servicios… Al confirmar un pedido de venta se crea la suscripción automáticamente, y cada periodo se genera solo el pedido de renovación o la factura.
- **Las que la empresa contrata** a sus proveedores: software, alojamiento, mantenimientos… Al confirmar un pedido de compra se crea la suscripción de proveedor, y cada periodo se genera solo el pedido de compra o la factura de proveedor. Así sus costes y renovaciones quedan controlados en el mismo sitio.

Además, el cliente gestiona sus suscripciones desde su **portal** (consultar, descargar, pausar o cancelar), recibe **avisos por correo** antes de cada renovación, y la empresa analiza su **ingreso recurrente mensual (MRR)** y sus **bajas**.

La suite se ha diseñado por capas: un **núcleo** independiente, tres módulos de integración (Ventas, Compras y Facturación) y dos módulos de servicio (Portal y Análisis) que se instalan según lo que necesite cada empresa. Cada suscripción indica con qué documento se renueva, así que, aunque estén todos instalados, **nunca se renueva dos veces**. Sigue las guías de desarrollo de la [Odoo Community Association (OCA)](https://github.com/OCA) y de Odoo SA, e incluye pruebas automáticas, control de calidad con pre-commit y traducción completa al español.

## 2. Stack tecnológico

| Área | Tecnología |
|---|---|
| ERP / framework | [Odoo 18.0](https://www.odoo.com) Community (ORM, vistas XML, QWeb, acciones planificadas, plantillas de correo, portal y controladores HTTP) |
| Lenguaje backend | Python 3.12 |
| Vistas | XML de Odoo 18 (`list`, `form`, `kanban`, `search`, `chatter`) |
| Base de datos | PostgreSQL 16 |
| Contenedores | Docker y Docker Compose |
| Pruebas | Framework de tests de Odoo (`TransactionCase` / `BaseCommon`, `HttpCase` para el portal) |
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
   - **Datos de demostración:** márcalo para tener contactos, productos y el usuario portal de prueba (`portal` / `portal`).

5. **Instala los módulos.** En *Aplicaciones*, busca e instala **Subscription Core** y los módulos de integración que necesites:
   - **Subscription Sale**, que instala también *Ventas*.
   - **Subscription Purchase**, que instala también *Compras*.
   - **Subscription Account**, que instala también *Facturación*.
   - **Subscription Portal**, para que los clientes vean y gestionen sus suscripciones en *Mi cuenta*.
   - **Subscription Dashboard**, para el análisis de MRR, altas y bajas.

   Si no aparecen, activa el modo desarrollador y pulsa *Actualizar lista de aplicaciones*.

### Instalación en un Odoo 18 existente (sin Docker)

1. Clona el repositorio en cualquier carpeta del servidor.
2. Añade esa carpeta al parámetro `addons_path` del `odoo.conf`.
3. Reinicia Odoo, actualiza la lista de aplicaciones e instala los módulos.

### Ejecutar las pruebas automáticas

Con los contenedores levantados, crea una base de datos desechable, instala los módulos y ejecuta sus tests:

```bash
docker compose run --rm odoo odoo -d test_suscripciones \
  -i alfo_subscription_core,alfo_subscription_sale,alfo_subscription_purchase,alfo_subscription_account,alfo_subscription_portal,alfo_subscription_dashboard \
  --test-enable --test-tags /alfo_subscription_core,/alfo_subscription_sale,/alfo_subscription_purchase,/alfo_subscription_account,/alfo_subscription_portal,/alfo_subscription_dashboard \
  --addons-path=/mnt/custom-addons/alfocea-odoo-modules \
  --stop-after-init --without-demo=all
```

El resultado esperado es `0 failed, 0 error(s) of 153 tests`.

## 4. Estructura del proyecto

Cada carpeta del repositorio es un módulo de Odoo independiente, con la estructura recomendada por OCA. Todos los módulos llevan el prefijo `alfo_`.

```
alfocea-odoo-modules/
├── README.md                          Documentación del proyecto (este fichero)
├── alfo_subscription_core/            Núcleo: planes, contratos y ciclo de vida
│   ├── __manifest__.py                Metadatos, dependencias (base, mail, product) y ficheros de datos
│   ├── models/                        Una clase por fichero
│   │   ├── subscription_plan.py           Plan: periodicidad, intervalo, días de prueba
│   │   ├── subscription_contract.py       Contrato: tipo, estados, fechas, documento de renovación,
│   │   │                                  acciones, cron y motor común de renovaciones
│   │   ├── subscription_contract_line.py  Líneas: producto, cantidad, precio de venta o compra
│   │   ├── subscription_contract_order_change.py  Registro de lo que cada pedido cambió
│   │   ├── subscription_close_reason.py   Motivos de baja
│   │   └── product_template.py            Plan de suscripción por defecto en el producto
│   ├── views/                         Formularios, listas, kanban, búsquedas y menús
│   ├── security/                      Grupos (Usuario / Administrador), permisos y reglas multicompañía
│   ├── data/                          Secuencias (SUB/, PSUB/), acciones planificadas, plantillas de
│   │                                  correo de aviso y motivos de baja
│   ├── i18n/es.po                     Traducción al español
│   ├── wizard/                        Asistentes: confirmación de cambios desde pedidos, cancelar o
│   │                                  pausar con motivo y cambio de plan
│   ├── report/                        Informes PDF (QWeb) de suscripciones y de planes
│   ├── tests/                         68 tests (common.py con los datos compartidos)
│   ├── readme/                        Fragmentos de documentación del módulo (formato OCA)
│   └── static/description/            Icono y página de descripción del módulo
├── alfo_subscription_sale/            Integración con Ventas (depende del núcleo y de sale)
│   ├── models/
│   │   ├── sale_order.py                  Crea y activa suscripciones al confirmar pedidos
│   │   ├── sale_order_line.py             Prepara las líneas de contrato desde el pedido
│   │   ├── subscription_contract.py       Renovación con pedido de venta
│   │   ├── subscription_contract_line.py  Líneas del pedido de renovación
│   │   └── subscription_plan.py           Confirmar automáticamente las renovaciones
│   ├── hooks.py                       Asigna el documento a las suscripciones previas
│   ├── views/ data/ i18n/ readme/     Smart buttons, acción planificada, traducción y documentación
│   └── tests/                         45 tests
├── alfo_subscription_purchase/        Integración con Compras (depende del núcleo y de purchase)
│   ├── models/
│   │   ├── purchase_order.py              Crea y activa suscripciones de proveedor al confirmar
│   │   ├── purchase_order_line.py         Prepara las líneas de contrato desde el pedido
│   │   ├── subscription_contract.py       Renovación con pedido de compra
│   │   ├── subscription_contract_line.py  Líneas del pedido de compra de renovación
│   │   ├── subscription_plan.py           Confirmar automáticamente las renovaciones
│   │   └── product_template.py            Plan de suscripción de proveedor en el producto
│   ├── hooks.py                       Asigna el documento a las suscripciones previas
│   ├── views/ data/ i18n/ readme/     Smart buttons, acción planificada, traducción y documentación
│   └── tests/                         20 tests
├── alfo_subscription_account/         Integración con Facturación (depende del núcleo y de account)
│   ├── models/
│   │   ├── account_move.py                Enlace factura → suscripción
│   │   ├── subscription_contract.py       Renovación con factura de cliente o de proveedor
│   │   ├── subscription_contract_line.py  Líneas de la factura de renovación
│   │   └── subscription_plan.py           Publicar automáticamente las facturas
│   ├── hooks.py                       Asigna el documento a las suscripciones previas
│   ├── views/ data/ i18n/ readme/     Smart buttons, acción planificada, traducción y documentación
│   └── tests/                         10 tests (incluida la integración con todos los módulos)
├── alfo_subscription_portal/          Portal del cliente (depende del núcleo y de portal)
│   ├── controllers/portal.py          Rutas /my/subscriptions: lista, detalle, PDF y acciones
│   ├── models/                        Acceso por portal y permisos del plan (pausar, cancelar)
│   ├── security/                      Acceso de lectura y reglas: cada cliente solo ve lo suyo
│   ├── views/portal_templates.xml     Plantillas QWeb del portal
│   └── tests/                         6 tests HTTP con un usuario portal
└── alfo_subscription_dashboard/       Análisis (depende del núcleo)
    ├── models/                        MRR y ARR almacenados en cada suscripción
    ├── views/                         Pivote, gráficos y menú Informes
    └── tests/                         4 tests
```

**Arquitectura por capas.** El núcleo no depende de Ventas, Compras ni Contabilidad. Cada integración es un módulo aparte que depende del núcleo, nunca al revés, lo que evita dependencias circulares. Así una empresa instala solo lo que necesita.

**Motor común de renovaciones.** El núcleo contiene la lógica que comparten las tres integraciones: qué suscripciones tocan, qué periodos (con recuperación de atrasos y respeto a la fecha de fin), el texto del periodo en el idioma del contacto y el aislamiento de errores por suscripción. Cada integración solo aporta cómo se crea su documento.

**Documento de renovación.** Cada suscripción indica con qué se renueva: *Nada*, *Pedido de venta*, *Pedido de compra* o *Factura*. Cada integración añade su opción a la lista, y cada acción planificada solo procesa la suya, así que una suscripción nunca se renueva dos veces. El valor por defecto prefiere los pedidos cuando su módulo está instalado (venta → pedido de venta; compra → pedido de compra) y, si no, la factura.

## 5. Funcionalidades principales

### Subscription Core (`alfo_subscription_core`)

- **Planes de suscripción:**
  - "Una suscripción por contacto": decide si los productos nuevos de un contacto van a su suscripción existente o a una nueva.
  - Periodicidad en días, semanas, meses o años, con intervalo configurable, mostrada en lenguaje natural ("cada mes", "cada 3 semanas").
  - Días de aviso por correo y renovación automática de la fecha de fin con días de preaviso.
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
- **Documento de renovación** por suscripción (ver sección 4), con seguimiento en el chatter.
- **Terminar prueba** (solo administradores): termina hoy la prueba gratuita, pasa la suscripción a activa y adelanta la próxima factura. En el chatter queda quién la terminó y el fin previsto.
- **Acción planificada diaria:** reanuda las pausas que llegan a su fecha, pasa a *Activo* las pruebas terminadas, renueva la fecha de fin de los planes con renovación automática y pasa a *Vencido* el resto de contratos que superan su fecha de fin.
- **Avisos por correo al cliente** (plantillas traducibles, en su idioma): X días antes de cada renovación, del fin de la prueba y del vencimiento. Cada aviso se envía una sola vez y queda en el chatter.
- **Renovación automática con preaviso:** botón **No renovar** (solo antes del fin del preaviso) y **Volver a renovar**.
- **Pausa con fecha de reanudación:** al reanudar, las fechas (próxima factura, fin de la prueba, fin) se desplazan los días que estuvo en pausa, así el cliente no paga el tiempo pausado.
- **Cancelar o pausar con motivo** (catálogo configurable de motivos de baja) y fecha de baja guardada, para el análisis de bajas.
- **Cambio de plan** con un asistente: se mantiene el periodo actual y las siguientes renovaciones usan el plan nuevo.
- **Responsable** de cada suscripción (el comercial del pedido): si una renovación falla, recibe una actividad.
- **Plan por defecto en el producto:** solo lo ve y edita el administrador de suscripciones.
- **Informe PDF del contrato** (QWeb), en el idioma del contacto: datos del cliente o proveedor, plan, periodicidad, estado, fechas, líneas, total por periodo y términos y condiciones. Se imprime desde el menú *Imprimir* del formulario o de la lista (varias a la vez, una página por suscripción).
- **Informe PDF del plan** (QWeb): facturación, prueba gratuita, compañía, estado, descripción, suscripciones abiertas que lo usan y total por periodo de las que están en curso, separado en clientes (ingresos) y proveedores (gastos). También se imprimen varios a la vez desde la lista.
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
  - Si el cliente ya tiene una suscripción abierta con ese plan **y ese producto**, se suma la cantidad.
  - Un producto que el cliente aún no tiene crea una suscripción nueva o, si el plan tiene activado **"Una suscripción por contacto"**, se añade como línea a la existente.
  - El pedido solo se enlaza con las suscripciones que contienen sus productos.
  - **Cancelar el pedido deshace lo que hizo:** resta las cantidades que sumó, quita las líneas que añadió y cancela la suscripción que creó si se queda sin líneas. Lo ya facturado no se toca, cada cambio queda registrado (pestaña *Cambios desde pedidos*) y el chatter explica qué se ha deshecho.
  - **Asistente de confirmación:** si al confirmar desde el formulario el pedido va a modificar suscripciones existentes, primero muestra lo que ya tienen y, en verde, lo que se añade (también en compras). Tres opciones: **Confirmar y añadir**, **Confirmar sin añadir** (no toca las suscripciones existentes; esos productos se venden una sola vez, las suscripciones nuevas sí se crean y queda anotado en el pedido) y **Cancelar**.
  - Funciona aunque el comercial no tenga permisos de suscripciones (se ejecuta con `sudo`).
- **Pedidos de renovación automáticos:**
  - Una acción planificada diaria genera el pedido de venta de cada suscripción cuando le toca el periodo.
  - Incluye las líneas y precios del contrato, y el periodo en la descripción, en el idioma del cliente.
  - Recupera los periodos atrasados, respeta la fecha de fin y mantiene el comercial del pedido original.
  - Si un contrato da error, se registra y no bloquea al resto.
- **Sin cobro doble:** el pedido que crea la suscripción cubre el primer periodo, así que la primera renovación se programa un periodo después.
- **Prueba gratuita real:** las líneas en prueba se ven en verde. Si el producto inicia una suscripción con un plan con prueba, la línea del presupuesto sale con un 100 % de descuento y la nota "Prueba gratuita: 7 días. Después se factura cada mes.". El cliente no paga nada al contratar; la suscripción conserva el precio real y el primer cobro llega al terminar la prueba. Recomprar el producto o añadirlo a una suscripción existente nunca es prueba, y los pedidos ya confirmados no se tocan.
- **Confirmación configurable por plan:** los pedidos de renovación se confirman solos o se quedan como presupuesto para revisarlos.
- **Smart buttons en los dos sentidos:** del pedido a sus suscripciones y de la suscripción a sus pedidos.

### Subscription Purchase (`alfo_subscription_purchase`)

- **Suscripción de proveedor automática al comprar:**
  - Al confirmar un pedido de compra (directamente o tras su aprobación), cada producto con **Plan de suscripción de proveedor** crea e inicia la suscripción del proveedor.
  - Es un campo distinto del plan de venta, para que un producto pueda venderse con plan y comprarse sin él, o al revés.
  - Mismas reglas que en ventas: se suma la cantidad si el producto ya está, y si no, suscripción nueva o línea nueva según "Una suscripción por contacto". Funciona aunque el comprador no tenga permisos de suscripciones.
- **Pedidos de compra de renovación automáticos:** una acción planificada diaria genera el pedido de compra de cada periodo, con el precio del contrato y el periodo en la descripción. Recupera los periodos atrasados y mantiene el comprador del pedido original.
- **Confirmación configurable por plan:** los pedidos de compra de renovación se confirman solos o se quedan como solicitud de presupuesto.
- **Smart buttons en los dos sentidos:** del pedido de compra a sus suscripciones y al revés.

### Subscription Account (`alfo_subscription_account`)

- **Facturación directa:** para las suscripciones que se renuevan con *Factura*, una acción planificada diaria genera cada periodo una **factura de cliente** (suscripciones de venta) o una **factura de proveedor** (suscripciones de compra).
  - La factura lleva fecha del primer día del periodo, las líneas y precios del contrato y el periodo en la etiqueta.
  - Recupera los periodos atrasados y respeta la fecha de fin.
- **Publicación configurable por plan:** las facturas se publican solas o se quedan en borrador para revisarlas (por defecto, en borrador).
- **Smart buttons en los dos sentidos:** de la suscripción a sus facturas y de la factura a su suscripción.
- **Compatible con Ventas y Compras:** con todo instalado, cada suscripción se renueva solo con su documento (lo verifica un test de integración).

### Subscription Portal (`alfo_subscription_portal`)

- **Mi cuenta → Suscripciones:** el cliente ve sus suscripciones de cliente con plan, facturación, próxima factura, total por periodo y estado.
- **Detalle** con fechas, líneas, total por periodo, historial de mensajes y **descarga del PDF**.
- **Autoservicio**, si el plan lo permite (*Los clientes pueden pausar* / *pueden cancelar*): **pausar**, **reanudar**, **cancelar** o, en planes con renovación automática, **no renovar** (antes del fin del preaviso). Cada acción queda en el chatter con el cliente como autor.
- **Seguridad:** reglas de registro para que un usuario portal solo vea las suscripciones de su empresa; también se pueden compartir con enlace (token de acceso), como los demás documentos de Odoo.

### Subscription Dashboard (`alfo_subscription_dashboard`)

- **MRR y ARR** almacenados en cada suscripción: el total por periodo llevado a un mes (un plan anual de 1.200 € cuenta 100 €/mes) y a un año.
- **Suscripciones → Informes**, con gráfico, pivote y lista:
  - **Ingresos recurrentes (MRR)** de las suscripciones activas, por plan.
  - **Altas de suscripciones** por mes.
  - **Bajas** por mes y motivo, con el MRR perdido.
  - **Gastos recurrentes** de las suscripciones de proveedores, por proveedor.

## 6. Usuario y contraseña de prueba

Se recomienda probar la suite en un Odoo 18 base, con **datos de demostración** y los módulos instalados (sección 3), entrando con estos dos usuarios. Cada uno representa un tipo de usuario de Odoo:

- **Usuario interno** (`admin`): trabaja dentro del ERP, en el *backend*, y ve los menús y aplicaciones que le permiten sus grupos.
- **Usuario portal** (`portal`): es un usuario externo, normalmente un **cliente o un proveedor**. **No tiene acceso al ERP**: solo entra en el portal web (*Mi cuenta*) y ve los documentos que cada módulo le deja ver, como sus pedidos o sus facturas. No ocupa licencia de usuario.

Lo que ve un usuario portal lo decide la seguridad de cada módulo: permisos de acceso por modelo (`ir.model.access.csv`) y reglas de registro (`ir.rule`) que filtran los registros. En esta suite, `alfo_subscription_portal` le da permiso de lectura sobre las suscripciones, y sus reglas de registro dejan ver a cada cliente **solo las suscripciones de su empresa**. Las acciones (pausar, cancelar…) pasan por el controlador del portal, que comprueba antes si el plan las permite. Documentación oficial de Odoo:

- [Acceso al portal (usuarios portal)](https://www.odoo.com/documentation/18.0/applications/general/users/portal.html)
- [Seguridad en Odoo: grupos, permisos de acceso y reglas de registro](https://www.odoo.com/documentation/18.0/developer/reference/backend/security.html)

| Rol | Usuario | Contraseña | Para qué sirve |
|---|---|---|---|
| Administrador | `admin` | `admin` | Gestión completa: planes, suscripciones de clientes y de proveedores, pedidos, facturas, renovaciones e informes |
| Portal (cliente externo) | `portal` | `portal` | Ver el lado del cliente en *Mi cuenta → Suscripciones*: consultar, descargar el PDF, pausar, reanudar, cancelar o pedir que no se renueve |

- **Administrador:** es el usuario y la contraseña que se introducen al crear la base de datos (paso 4 de la instalación). Si se usan `admin` / `admin`, coinciden con la tabla. Tiene acceso completo a la app *Suscripciones* desde la instalación.
- **Portal:** Odoo crea el usuario `portal` al marcar **Datos de demostración** al crear la base de datos. Sirve igual cualquier otro usuario portal: basta con dar acceso a un contacto en *Contactos → (el contacto) → Acción → Conceder acceso al portal* y ponerle una contraseña desde *Ajustes → Usuarios*.
- **Clientes y proveedores:** para probar el lado cliente, crea una suscripción de venta (un pedido de venta confirmado) a nombre del contacto del usuario portal que uses y entra con ese usuario en otra ventana o en modo incógnito. El portal muestra solo las suscripciones de cliente; las de proveedor (`PSUB/…`) se prueban con el administrador, desde los pedidos de compra y el menú *Suscripciones*.

### Guion de prueba rápido

1. **Crea los planes:** en *Suscripciones → Configuración → Planes*, crea "Mensual" (cada 1 mes) y "Mensual con prueba" (14 días de prueba).
2. **Asigna un plan a un producto:** abre un producto y pon "Mensual" en **Plan de suscripción**, junto a la categoría.
3. **Vende el producto:** crea y confirma un presupuesto con él. En el pedido aparece el botón **Suscripciones**, con la suscripción ya **Activa**.
4. **Genera una renovación:**
   1. En la suscripción, pon la **Fecha de la próxima factura** a hoy.
   2. Ve a *Ajustes → Técnico → Acciones planificadas → "Suscripciones: crear pedidos de venta de renovación"* y pulsa **Ejecutar manualmente**.
   3. Se crea el pedido del periodo y la fecha avanza un mes.
5. **Compra con suscripción:** en un producto comprable, pon un plan en **Plan de suscripción de proveedor** y confirma un pedido de compra con él. En el pedido aparece el botón **Suscripciones**, con la suscripción de proveedor (`PSUB/…`) ya activa. Sus renovaciones se generan con *"Suscripciones: crear pedidos de compra de renovación"*.
6. **Factura directamente:**
   1. En una suscripción activa, cambia el **Documento de renovación** a *Factura* y pon la próxima fecha a hoy.
   2. Ejecuta *"Suscripciones: crear facturas de renovación"*.
   3. Se crea la factura del periodo: de cliente o de proveedor, según el tipo de suscripción.
7. **Portal del cliente:**
   1. En el plan, activa *Los clientes pueden pausar* y *pueden cancelar*.
   2. Crea y confirma un presupuesto con un producto de suscripción para el contacto de un usuario portal (por ejemplo, el del usuario `portal` de los datos de demostración).
   3. Entra con ese usuario portal en una ventana de incógnito y abre *Mi cuenta → Suscripciones*: verás su suscripción, podrás descargar el PDF y pausarla o cancelarla.
   4. De vuelta como administrador, el chatter de la suscripción muestra la acción con el cliente como autor.
8. **Análisis:** cancela una suscripción eligiendo un motivo y abre *Suscripciones → Informes → Bajas* y *Ingresos recurrentes (MRR)*.

## 7. Calidad y pruebas

- **153 tests automáticos:** 68 en el núcleo, 45 en Ventas, 20 en Compras, 10 en Facturación, 6 en el Portal (peticiones HTTP reales con un usuario portal) y 4 en el Análisis.
  - Cubren cálculos, validaciones, transiciones de estado, acciones planificadas, permisos y renovaciones (incluidos periodos atrasados y aislamiento de errores).
  - También la creación desde pedidos por usuarios sin permisos de suscripciones.
  - Un test de integración verifica que, con todos los módulos instalados, ninguna suscripción se renueva dos veces.
- **Instalación independiente:** cada módulo de integración se ha probado también instalado solo con el núcleo.
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

- Prorrateo al añadir productos o cambiar de plan a mitad de periodo.
- Cobro automático con tarjeta guardada (tokens de pago) en las facturas de renovación.
- Facturación por consumo (horas, GB…) con mínimo incluido y exceso facturado aparte.
- Entregas periódicas con control de stock para suscripciones de productos físicos.

## Licencia

LGPL-3. La licencia de cada módulo figura en su `__manifest__.py`.

## Autor

**Justo Alfocea Frutos**. Proyecto Final del Máster en Desarrollo con Inteligencia Artificial.
