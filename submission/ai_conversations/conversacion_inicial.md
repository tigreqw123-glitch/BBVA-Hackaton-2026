# Registro de conversación técnica con IA

## Información general

- Fecha aproximada: 16–19 de octubre de 2026.
- Herramienta utilizada: ChatGPT.
- Modelo: GPT-5.
- Objetivo: preparar, desarrollar, probar y documentar una estrategia para el reto de mejora de entrega de tarjetas.
- Repositorio: `BBVA-Hackaton-2026`.

## 1. Configuración inicial del repositorio

Se revisaron las instrucciones del reto y se identificaron los pasos obligatorios:

- Crear un repositorio privado y vacío.
- Clonar el repositorio oficial.
- Cambiar el origen remoto hacia el repositorio personal.
- Subir la rama `main`.
- Agregar la cuenta `bbvaHackaton2026` como colaborador.
- Ejecutar los escenarios públicos y las pruebas unitarias.

El repositorio fue clonado correctamente y se configuró el origen remoto con el repositorio personal:

```text
https://github.com/tigreqw123-glitch/BBVA-Hackaton-2026.git
```

También se verificó que el código inicial se subiera correctamente a GitHub.

## 2. Preparación del entorno

Inicialmente, al ejecutar los comandos del reto, Windows no encontraba Python. Se comprobó que la extensión de Python de Visual Studio Code estaba instalada, pero que el intérprete de Python no estaba disponible en la terminal.

Se instaló Python y se verificó la versión disponible:

```text
Python 3.14.8
```

Posteriormente se ejecutaron correctamente:

```powershell
python run.py
python run_150k.py
python -m unittest discover -s tests -v
```

Las pruebas iniciales terminaron correctamente:

```text
Ran 2 tests
OK
```

## 3. Revisión de la documentación del reto

Se revisaron los siguientes documentos:

- `README.md`
- `PRUEBA_TECNICA.md`
- `REGLAS_PUBLICAS.md`
- `EVALUACION.md`
- `interfaces.py`

Se identificaron como requisitos críticos:

- No dejar envíos en estado `UNRESOLVED`.
- Mantener el incumplimiento de SLA en un máximo del 6 %.
- Evitar infracciones de retención superiores a 45 minutos.
- Finalizar todos los escenarios sin errores.
- Entregar la versión final en `submission/candidate_strategy.py`.
- Documentar el uso de IA y conservar las conversaciones técnicas.
- No modificar el motor, las interfaces ni los datos del simulador.

También se revisaron los campos disponibles en `Shipment`, `CarrierSnapshot`, `DispatchContext` y `DeliveryAttemptResult`.

## 4. Preparación de la entrega

Se creó la estructura requerida:

```text
submission/
├── candidate_strategy.py
├── STRATEGY.md
├── submission_manifest.json
├── ai_conversations/
│   └── conversacion_inicial.md
└── generated_artifacts/
    └── .gitkeep
```

Se completó `submission_manifest.json` con:

- Nombre completo del candidato.
- Correo de inscripción.
- Herramienta y modelo utilizados.
- Archivo evaluado.
- Archivos de conversación.
- Declaración de autoría y revisión.

El archivo `generated_artifacts/.gitkeep` se dejó vacío porque su función es conservar la carpeta en Git aunque no contenga otros artefactos.

## 5. Línea base de la estrategia inicial

La estrategia inicial utilizaba despacho round-robin y enviaba una tarjeta por lote. Su resultado en el escenario público de 5.000 envíos fue:

```text
Entregados: 4.983 de 5.000
SLA: 0,66 %
RCP: 9,869
Tiempo medio: 230,555 minutos
Coste: 4.443.213 céntimos
Envíos no resueltos: 16
Infracciones de retención: 42
Tamaño medio de lote: 1,0
```

El informe mostró que la estrategia inicial tenía varios problemas:

- Cada lote contenía una sola tarjeta.
- Existían envíos no resueltos.
- Se registraban infracciones de retención.
- Se generaban numerosos intentos de despacho innecesarios.
- La selección de transportistas no validaba correctamente todas las capacidades.

## 6. Correcciones de gestión de fallos

Se revisó `on_delivery_failed`. El comportamiento inicial volvía a introducir en la cola incluso los envíos con fallos terminales.

Esto provocaba intentos posteriores de despachar tarjetas que ya no podían volver a procesarse y generaba rechazos `TERMINAL_SHIPMENT`.

Se corrigió la función para distinguir entre:

- Fallos terminales: se eliminan de las estructuras pendientes.
- Fallos reintentables: se vuelven a colocar en la cola.

Durante este cambio se produjo un error de edición: se eliminó accidentalmente la implementación de `on_monthly_planning`. Esto provocó:

```text
TypeError:
Can't instantiate abstract class CandidateStrategy
without an implementation for abstract method 'on_monthly_planning'
```

Se restauró la copia de respaldo de `candidate_strategy.py`, se reaplicó el cambio de forma controlada y se verificó que las pruebas volvieran a pasar.

Después de la corrección, los rechazos `TERMINAL_SHIPMENT` se redujeron a cero.

## 7. Validación de zonas y capacidades

Se detectó que la selección inicial utilizaba una comprobación incorrecta:

```python
shipment.zone in allowed_zone
```

donde `allowed_zone` era una cadena creada al unir las zonas con `"|"`.

Se sustituyó por una comprobación directa contra la colección de zonas del transportista:

```python
shipment.zone in carrier.allowed_zones
```

También se añadió la validación de capacidades requeridas:

```python
all(
    capability in carrier.capabilities
    for capability in shipment.required_capabilities
)
```

La misma validación se aplicó al transportista preferido en los reintentos, evitando reutilizar un transportista que ya no cumpliera los requisitos del envío.

Como resultado, los rechazos por `ZONE_UNSUPPORTED` se redujeron a cero.

## 8. Evaluación de un cambio que fue descartado

Se probó eliminar temporalmente la espera aplicada después de algunos rechazos del transportista. La intención era permitir que la estrategia intentara rápidamente otras alternativas.

Sin embargo, ese cambio provocó una cantidad excesiva de intentos repetidos:

```text
Despachos rechazados: 67.873
```

Además, no redujo los envíos no resueltos ni las infracciones de retención.

El cambio fue descartado porque aumentaba el coste computacional y la cantidad de rechazos sin mejorar los resultados funcionales. Se restauró la gestión de espera anterior y se conservó únicamente la lógica validada.

Este experimento se documenta porque forma parte del proceso real de desarrollo y permitió comprobar que intentar despachos repetidamente en cada tick no era una mejora segura.

## 9. Resultado final del escenario público de 5.000 envíos

Después de las correcciones, el escenario público terminó con:

```text
Estado: COMPLETED
Envíos admitidos: 5.000
Entregados: 5.000
SLA: 0,26 %
RCP: 9,959
Tiempo medio: 196,571 minutos
Envíos no resueltos: 0
Devueltos a custodia: 0
Infracciones de retención: 0
Despachos rechazados: 0
```

El informe también mostró:

```text
Intentos aceptados: 5.457
Lotes aceptados: 5.079
```

La diferencia entre intentos y lotes confirma que se formaron lotes con más de una tarjeta en ciertos casos.

## 10. Resultado final del escenario público de 150.000 envíos

La ejecución del escenario grande terminó correctamente:

```text
Estado: COMPLETED
Envíos admitidos: 150.000
Entregados: 149.982
SLA: 0,424 %
RCP: 9,928
Tiempo medio: 187,022 minutos
Memoria máxima: 27.312.128 bytes
```

El escenario grande no presentó errores de ejecución y las pruebas unitarias continuaron pasando.

## 11. Pruebas ejecutadas

Se ejecutaron repetidamente las pruebas públicas:

```powershell
python -m unittest discover -s tests -v
```

Resultado final:

```text
Ran 2 tests
OK
```

También se ejecutaron:

```powershell
python run.py
python run_150k.py
```

Ambos escenarios finalizaron con estado `COMPLETED`.

## 12. Revisión y responsabilidad sobre la solución

La IA se utilizó como apoyo para:

- Interpretar la documentación.
- Comprender las interfaces.
- Analizar los informes generados.
- Identificar errores de lógica.
- Proponer cambios concretos.
- Revisar los resultados de las ejecuciones.

Los cambios fueron aplicados y ejecutados localmente. También se revisaron los errores producidos durante el desarrollo, se restauraron versiones funcionales cuando fue necesario y se verificó que la estrategia final conservara las funciones requeridas por `BaseDispatcherStrategy`.

La solución final fue revisada antes de copiarla a:

```text
submission/candidate_strategy.py
```

y subirla a la rama `main`.