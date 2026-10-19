# Estrategia de despacho

## Objetivo

Optimizar el despacho de tarjetas para completar todos los escenarios sin
errores, sin envíos `UNRESOLVED`, sin infracciones de retención voluntaria y
con un incumplimiento de SLA igual o inferior al 6 %.

## Qué cambié

- Reemplacé el despacho round-robin de una tarjeta por lote por agrupación de
  envíos compatibles por `delivery_cluster_id`, zona y número de intento.
- Respeto la capacidad efectiva del carrier y sus capacidades requeridas.
- Ordeno los grupos por el `sla_deadline` más próximo.
- Refresco el snapshot del servicio después de cada aceptación para no usar
  información obsoleta sobre unidades disponibles.
- La selección considera operación actual, zona, capacidades, velocidad,
  capacidad del lote y, como desempate, el carrier del intento anterior.
- Eliminé el histórico completo de envíos, que no era necesario para decidir y
  aumentaba el consumo de memoria.
- Los callbacks de entregas terminales limpian el estado interno; los fallos
  reintentables vuelven a la cola con el `Shipment` actualizado por el motor.

## Corrección de envíos no resueltos

La estrategia conserva en `pending` únicamente los envíos que todavía no son
despachables en el instante actual. En cada tick procesa los que ya están
listos, forma lotes válidos y utiliza el snapshot actualizado tras cada
despacho. Si no hay una unidad compatible, el envío permanece en cola hasta el
siguiente tick; no se descarta ni se fija permanentemente a un carrier que ya
no sea válido.

Además, los reintentos usan el número de intento y las capacidades recibidas
en el callback de fallo. Los fallos terminales no se vuelven a encolar. Esto
evita que la estrategia pierda referencias a envíos o mantenga en cola estados
que el motor ya cerró.

## Eliminación de infracciones de retención

Los envíos listos se intentan en el primer tick disponible. La estrategia no
aplica esperas voluntarias artificiales: solo conserva un envío cuando todavía
no está listo o cuando ningún carrier compatible tiene una unidad libre.

El batching reduce la cantidad de llamadas y libera capacidad de forma más
eficiente. Como resultado, los envíos que tienen un carrier factible no quedan
pendientes durante el periodo de auditoría de 45 minutos.

## Resultados medidos

Se ejecutaron las pruebas unitarias, `run.py` y `run_150k.py` con la estrategia
actualizada. Los reportes fueron generados por el motor local y los cambios
fueron revisados después de cada ejecución.

### `run.py`

- Estado: `COMPLETED`
- Envíos admitidos: `5.000`
- Entregados: `5.000`
- `unresolved`: `0`
- `voluntary_hold_breaches`: `0`
- `SLA breach_rate`: `0.0026`
- Rechazos de despacho: `0`
- Archivos protegidos: intactos

### `run_150k.py`

- Estado: `COMPLETED`
- Envíos admitidos: `150.000`
- Entregados: `149.982`
- Devueltos a custodia tras fallos terminales: `18`
- `unresolved`: `0`
- `voluntary_hold_breaches`: `0`
- `SLA breach_rate`: `0.00424`
- Rechazos de despacho: `0`
- Archivos protegidos: intactos

Los 18 envíos devueltos a custodia no son `UNRESOLVED`: alcanzaron el máximo
de intentos definido por el motor y terminaron en un estado terminal esperado.

## Uso de IA y revisión

Usé ChatGPT como apoyo para comprender el contrato público, revisar las
interfaces, analizar el flujo de callbacks y proponer mejoras de batching,
selección de carriers y reintentos. Revisé manualmente los cambios, ejecuté
las pruebas unitarias y verifiqué los resultados de `run.py` y `run_150k.py`.
La estrategia entregada fue comprobada contra los requisitos de estado,
retención, SLA e integridad de archivos protegidos.

## Limitaciones

Los resultados documentados corresponden a los escenarios públicos incluidos
en el repositorio. Las realizaciones privadas de fallos y la disponibilidad de
carriers pueden variar; por eso la estrategia evita depender de nombres,
órdenes fijos o capacidades concretas del catálogo.
