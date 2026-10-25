# ADR 015 · `regulation` en las entradas, `regulationCode` en las respuestas

- **Estado:** aceptado
- **Fecha:** 2026-10-24
- **Fase:** B-2 (endpoints de lectura y screening) — hallazgo H2-A5
- **Relacionado:** ADR-005 (catálogo sincronizado), ADR-010 (screening referencial)

## 1. Contexto

El catálogo compartido nombra el campo `regulationCode` (`catalog/limits.v1.json`), y ese es el
nombre que TerraPlan y la UI ya leen. Los endpoints, en cambio, lo reciben como filtro: en el
cuerpo de `POST /screening/evaluate` y en los query params de `GET /screening/limits` y
`GET /catalog/limits`. Mientras se escribían los endpoints convivieron las dos formas
(`regulation` al entrar, `regulationCode` al salir) sin que la documentación dijera cuál era cuál:
un analista que leía `/docs` no sabía si el filtro se llamaba igual que el campo de la respuesta.

## 2. Decisión

**Entradas: `regulation`. Salidas: `regulationCode`.** Sin alias dobles y documentado en OpenAPI.

- En el cuerpo (`ScreeningRequest.regulation`) y en los query params (`?regulation=NCh1333`) el
  nombre es corto porque es un selector: se comparte en una URL, se escribe a mano y no compite
  con ningún otro campo.
- En las respuestas el nombre es `regulationCode`, idéntico al del catálogo, para que la UI y
  TerraPlan tengan un único vocabulario al leer un límite.
- La asimetría se declara donde se ve: `Field(description=…)` en el esquema y
  `Query(description=…)` en cada endpoint, más una frase en la descripción del endpoint.

## 3. Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| `regulationCode` en todo | URLs más largas y un nombre que se repite dentro de las respuestas, sin ganancia de claridad |
| Aceptar los dos alias en el query | Dos formas de acertar y dos de fallar; el cliente no sabe cuál es la canónica |
| Renombrar el campo de salida a `regulation` | Rompe el vocabulario del catálogo compartido y obliga a traducir en la UI |

## 4. Consecuencias

- La UI filtra con `?regulation=` y muestra `limits[].regulationCode`; el mapeo está a la vista en
  `/docs`, no en la cabeza de quien lo escribió.
- Cualquier alias nuevo (o volver a mezclar los nombres) exige otro ADR: son contratos públicos.
- **Pendiente:** ningún test fija todavía el nombre del query param; una regresión se vería solo
  abriendo `/docs`. Cuando la UI consuma el filtro, el test de contrato (e2e) debe cubrirlo.
