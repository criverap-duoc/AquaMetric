# ADR-005: Catálogo sincronizado desde TerraPlan con `sha256`

- **Estado**: aceptado
- **Fecha**: 2026-10-24
- **Contexto**: ver `.clinerules/01-project-context.md` §5 (contrato con TerraPlan)
- **Decisores**: Cristóbal Vera (químico + dev)

## Contexto

Parámetros, unidades y límites normativos son el contrato entre dos proyectos: TerraPlan
(NestJS) los administra y AquaMetric los consume para validar unidades, hacer screening y
calcular capacidad. Si cada repositorio mantuviera su propia copia editable, en tres semanas
habría dos verdades sobre qué es `TURB` o qué unidad canónica tiene `PH`, y el screening
compararía contra límites que ya no existen. Tampoco sirve publicar el catálogo por URL sin
verificación: no habría forma de saber si lo que se cargó es lo que TerraPlan aprobó.

Requisito de portafolio: que un reclutador sin acceso a TerraPlan pueda ver el catálogo, leerlo
y comprobar que no fue editado a mano.

## Decisión

1. **TerraPlan es la fuente de verdad.** AquaMetric mantiene `catalog/` como **copia de solo
   lectura**, sincronizada por `scripts/sync_catalog.py --from-path ../terraplan/catalog`
   (o `--from-url`). Editar `catalog/` a mano está prohibido; un cambio real se hace en
   TerraPlan, se versiona y se sincroniza aquí.
2. **Verificación por `sha256`.** `sync_catalog.py` calcula el hash sobre el **bundle lógico**
   (los archivos versionados, ordenados y sin metadatos de sistema) y lo escribe en
   `catalog.meta.json`. El hash no se incluye a sí mismo ni depende de mtime o del orden del
   directorio: dos sincronizaciones del mismo contenido dan el mismo valor, en cualquier
   máquina, y el CI falla si el archivo no coincide con el contenido.
3. **La versión viaja en el contrato.** Cada lote de ingesta declara `catalogVersion`; si su
   *major* difiere del local, la API responde `409 CATALOG_VERSION_MISMATCH` y no escribe nada
   (ADR-009). Así una deriva entre repositorios se detecta en la puerta, no en un reporte.
4. `GET /api/v1/catalog/meta` publica versión, hash y estado de firma (`status`, `validatedBy`,
   `validatedAt`) para que el cliente sepa contra qué se comparó (ADR-012, ADR-014).

## Consecuencias

**Positivas**
- Una sola fuente de verdad; la copia es verificable por cualquiera con `sha256sum`.
- El CI detecta catálogo editado a mano o desincronizado (`.clinerules/03` §2, health check).
- Los límites `draft-verified` del catálogo actual se muestran como «Pendiente de validación»:
  el sistema no puede inventar una norma que el químico no firmó.

**Negativas / riesgos**
- Sincronizar exige tener TerraPlan disponible (o su URL); en CI se trabaja contra la copia
  commiteada y se verifica el hash, no se re-sincroniza.
- Un cambio de versión *major* obliga a revisar la ingesta y a abrir ADR; es fricción
  intencional, no burocracia.
- El catálogo real manda sobre los ejemplos de las reglas del proyecto: si un código difiere de
  la documentación, se corrige la documentación, nunca el catálogo.

## Referencias

- `.clinerules/01-project-context.md` §5 (contrato, syncing, `catalogVersion`)
- `.clinerules/03-automation-workflows.md` (`sync catalog`, health check)
- `scripts/sync_catalog.py`, `catalog/catalog.meta.json`
- `api/app/catalog/loader.py`, `api/app/routers/catalog.py`
- `docs/adr/014-catalog-metadata-exposure.md`
