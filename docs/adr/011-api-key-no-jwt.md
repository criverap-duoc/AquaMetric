# ADR-011: API key para escribir, lectura pública; sin JWT ni usuarios

- **Estado**: aceptado
- **Fecha**: 2026-10-24
- **Contexto**: ver `.clinerules/01-project-context.md` §2 y `.clinerules/02-coding-standards.md` §5, §10
- **Decisores**: Cristóbal Vera (químico + dev)

## Contexto

AquaMetric es un servicio de portafolio con datos demo: un dashboard científico público que
cualquiera pueda abrir y evaluar. La tentación de copiar el esquema de autenticación de TerraPlan
(login, JWT, roles) agregaría pantallas de registro, recuperación de contraseña, verificación de
correo y gestión de sesiones — una semana de trabajo que no aporta nada a lo que el proyecto
quiere demostrar (SPC correcto, ingesta sólida, UI clara) y que además expone superficie de
ataque que nadie auditaría.

Lo que sí hay que proteger es la **escritura**: nadie desde internet debe poder inyectar
observaciones, porque una serie contaminada invalida cualquier carta de control. La lectura, en
cambio, es el producto: hacerla privada sería contradecir el objetivo.

## Decisión

**Sin JWT, sin usuarios, sin roles.** Dos reglas de acceso, explícitas y verificables:

1. **Escritura ⇒ `X-API-Key`.** Todo endpoint que modifica datos (`POST /api/v1/ingest/observations`
   y la carga del simulador) exige la cabecera, validada con `hmac.compare_digest` contra
   `INGEST_API_KEY` (comparación en tiempo constante). Falta o no coincide ⇒ `401 UNAUTHORIZED`
   en `application/problem+json`. La clave no tiene valor por defecto: la app **falla al
   arrancar** si no está configurada.
2. **Lectura ⇒ pública.** `GET` (catálogo, screening, series) y `POST /api/v1/screening/evaluate`
   (es una consulta, no una escritura) no piden credenciales. La UI es de solo lectura y no tiene
   login.

La regla se aplica por dependencia (`IngestKeyDep`) en el router, no por middleware global: un
endpoint nuevo que escriba sin `IngestKeyDep` es un bug, y el `health check` del proyecto lo
revisa explícitamente. CORS por allowlist (nunca `*`) y tope de 5 000 observaciones por lote.

## Consecuencias

**Positivas**
- Ningún campo de contraseña, ningún hash, ningún flujo de recuperación: menos código y menos
  cosas que pueden fallar en la demo.
- La UI pública puede enlazarse desde un CV o un correo sin pedir credenciales.
- Coherente con la arquitectura real: **TerraPlan** (donde el operador hace login) es quien
  escribe; AquaMetric recibe y analiza.

**Negativas / riesgos**
- No hay cuentas de usuario: si en el futuro se quiere auth de usuarios finales (perfiles,
  guardados, roles), hace falta un **ADR nuevo**, no un parche sobre este.
- La clave es compartida: rotar `INGEST_API_KEY` exige actualizar TerraPlan **y** las Lambdas y
  redeployar. Se documenta como procedimiento, no se automatiza en el MVP.
- Sin usuarios no hay auditoría de «quién escribió»: la trazabilidad llega por la
  `Idempotency-Key` y el `requestId`, no por identidad.
- La lectura pública implica que todo dato cargado es público; por eso el MVP solo publica datos
  demo y de laboratorio ya publicados, nunca secretos ni configuración.

## Referencias

- `.clinerules/01-project-context.md` §2 (auth) y §4 (ADR-011)
- `.clinerules/02-coding-standards.md` §5 (routers y `IngestKeyDep`), §10 (seguridad)
- `api/app/core/security.py`, `api/app/core/dependencies.py`
- `api/app/routers/ingest.py`, `api/app/routers/screening.py`
- `docs/adr/009-atomic-ingest.md`
