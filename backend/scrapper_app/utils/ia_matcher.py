import json, requests, time
from scrapper_app.utils.logger import logger
from .interactive_prompt import preguntar_usuario

# --- CONFIGURACIÓN DEL AGENTE OLLAMA (LOCAL) ---
OLLAMA_URL = 'http://localhost:11434/api/generate'
MODELO_RAPIDO = "phi3"
MODELO_PESADO = "llama3"

def consultar_ollama_sync(modelo, system_prompt, user_prompt, reintentos=3):
    prompt_completo = f"{system_prompt}\n\n{user_prompt}"
    payload = {"model": modelo, "prompt": prompt_completo, "stream": False, "format": "json"}
    
    for intento in range(reintentos):
        try:
            respuesta = requests.post(OLLAMA_URL, json=payload, timeout=120)
            respuesta.raise_for_status()
            return respuesta.json().get('response', '{}')
        except requests.exceptions.Timeout:
            logger.warning(f"⚠️ [IA {modelo}] Timeout (Intento {intento+1}/{reintentos}). Esperando 8s...")
            time.sleep(8)
        except requests.exceptions.RequestException as e:
            logger.warning(f"⚠️ Error Ollama ({modelo}): {e}")
            break
    return "{}"

# COMPARACIÓN DE PRODUCTOS
def es_mismo_producto_ia_batch(nombre_base, lista_candidatos):
    if not lista_candidatos:
        return []

    prompt_sistema = """
    Eres un sistema estricto de validación de productos de hardware de PC.
    Tu única tarea es decidir si dos nombres de producto describen EXACTAMENTE el mismo producto base.

    IMPORTANTE:
    - Si tienes cualquier duda, responde "duda".
    - Si falta información crítica en uno de los textos, responde "duda".
    - No intentes adivinar.
    - No uses sentido comercial general ni aproximaciones.
    - Solo responde true si los atributos esenciales coinciden de forma exacta.

    DEFINICIÓN DE "MISMO PRODUCTO":
    Dos textos representan el mismo producto SOLO si describen el mismo modelo base real.
    Si cambia un atributo técnico esencial, NO es el mismo producto.

    ORDEN OBLIGATORIO DE ANÁLISIS:
    1. Detecta la categoría.
    2. Extrae los atributos técnicos esenciales.
    3. Compara los atributos esenciales.
    4. Ignora solo palabras decorativas o comerciales.
    5. Responde con JSON.

    SI NO PUEDES IDENTIFICAR CON CLARIDAD LA CATEGORÍA O EL MODELO:
    {"mismo_producto": "duda"}

    ==================================================
    1) REGLA GENERAL DE SEGURIDAD
    ==================================================

    Responde "duda" (en lugar de false automático) si ocurre cualquiera de estas situaciones y no estás 100% seguro:
    - Las categorías parecen distintas.
    - El modelo exacto no coincide.
    - El sufijo no coincide.
    - La capacidad no coincide.
    - La versión no coincide.
    - El formato no coincide.
    - La interfaz no coincide.
    - El chipset no coincide.
    - La serie o familia no coincide.
    - Hay ambigüedad.
    - Un texto parece incompleto y no permite confirmar igualdad exacta.

    Nunca respondas true por parecido general del texto.

    ==================================================
    2) PALABRAS QUE NORMALMENTE DEBES IGNORAR
    ==================================================

    Ignora solo palabras no esenciales como:
    - box
    - tray
    - oferta
    - reacondicionado
    - refurbished
    - nuevo
    - gaming
    - overclocking
    - ai
    - ia
    - frecuencia
    - base
    - turbo
    - núcleos
    - hilos
    - cache
    - caché
    - graphics
    - gráficos integrados
    - sin ventilador
    - con ventilador
    - wof
    - processor
    - procesador
    - cpu
    - gpu
    - retail

    Estas palabras NO cambian el modelo base por sí solas.

    ==================================================
    3) REGLAS POR CATEGORÍA
    ==================================================

    -------------------------
    A. PROCESADORES (CPU)
    -------------------------
    Atributos esenciales:
    - Marca: Intel o AMD
    - Familia: Core i3/i5/i7/i9, Core Ultra 5/7/9, Ryzen 3/5/7/9, Xeon, Threadripper
    - Modelo numérico: 12400, 14700, 265, 7800, 7600, etc.
    - Sufijo exacto: K, KF, F, X, X3D, G, GT, etc.

    Regla:
    Dos CPUs solo son el mismo producto si marca + familia + número de modelo + sufijo coinciden exactamente.

    Ejemplos:
    - i7-14700K != i7-14700KF
    - i7-14700 != i7-14700K
    - Ryzen 5 7600 != Ryzen 5 7600X
    - Ryzen 7 7800X3D != Ryzen 7 7700X
    - Core Ultra 7 265K != Core Ultra 7 265KF
    - Xeon E-2414 != Xeon E-2478

    Notas:
    - La velocidad en GHz no define el producto si el modelo exacto ya está claro.
    - “Box” y “Tray” se pueden ignorar.
    - Si el modelo exacto no aparece claro en ambos textos, responde false.

    -------------------------
    B. TARJETAS GRÁFICAS (GPU)
    -------------------------
    Atributos esenciales:
    - Fabricante del chip: NVIDIA / AMD / Intel
    - Serie exacta del chip: RTX 4060, RTX 4060 Ti, RTX 4070 Super, RX 7800 XT, RX 7600, Arc A770, etc.
    - Sufijo del chip: Ti, Super, XT, XTX, etc.
    - Memoria VRAM si forma parte del modelo comercial diferenciador.

    Regla:
    Dos GPUs solo son el mismo producto si el chip exacto coincide.
    Si cambia 4060 por 4060 Ti, o 7800 XT por 7800 XTX, responde false.

    Importante:
    - La ensambladora puede variar si tu sistema quiere agrupar por chip base: MSI, ASUS, Gigabyte, Zotac, Sapphire pueden considerarse equivalentes.
    - Pero si cambia la VRAM y eso define el modelo comercial, responde false.
    - Si un texto tiene 8GB y otro 16GB, por defecto responde false.

    Ejemplos:
    - RTX 4060 != RTX 4060 Ti
    - RTX 4070 != RTX 4070 Super
    - RX 7800 XT != RX 7800 XTX
    - RTX 3060 8GB != RTX 3060 12GB

    -------------------------
    C. PLACAS BASE
    -------------------------
    Atributos esenciales:
    - Socket: AM4, AM5, LGA1700, etc.
    - Chipset: B650, X670, Z790, B760, H610, etc.
    - Formato si aparece en el nombre del modelo: B650M, B650I, etc.

    Regla:
    Dos placas base solo son el mismo producto si socket + chipset + formato/modelo coinciden.
    Si cambia B650 por B650M, responde false.
    Si cambia B760 por Z790, responde false.

    -------------------------
    D. MEMORIA RAM
    -------------------------
    Atributos esenciales:
    - Capacidad total: 16GB, 32GB, 64GB
    - Configuración del kit: 1x16, 2x8, 2x16, etc.
    - Tipo: DDR4 o DDR5
    - Frecuencia: 3200, 3600, 5600, 6000, etc.
    - Latencia si aparece y diferencia el modelo: CL16, CL30, CL36, etc.

    Regla:
    Dos kits de RAM solo son el mismo producto si coinciden capacidad total + distribución del kit + tipo + frecuencia.
    Si cambia DDR4 por DDR5, responde false.

    -------------------------
    E. SSD / ALMACENAMIENTO
    -------------------------
    Atributos esenciales:
    - Tipo: SSD / HDD
    - Formato: M.2, 2.5", PCIe card, etc.
    - Interfaz/generación: SATA, NVMe, PCIe 3.0, PCIe 4.0, PCIe 5.0
    - Capacidad: 500GB, 1TB, 2TB, etc.

    Regla:
    Dos unidades de almacenamiento solo son el mismo producto si coinciden tipo + formato + interfaz + capacidad.
    Si cambia 1TB por 2TB, responde false.

    -------------------------
    F. FUENTES DE ALIMENTACIÓN (PSU)
    -------------------------
    Atributos esenciales:
    - Potencia: 650W, 750W, 850W, etc.
    - Certificación: Bronze, Gold, Platinum, etc.
    - Formato si aparece: ATX, SFX, etc.

    Regla:
    Dos PSUs solo son el mismo producto si coinciden potencia + certificación + formato/modelo.

    -------------------------
    G. REFRIGERACIÓN
    -------------------------
    Atributos esenciales:
    - Tipo: aire o líquida
    - Tamaño del radiador si es líquida: 120, 240, 280, 360, 420

    Regla:
    Dos sistemas de refrigeración NO son iguales si cambia el tipo o el tamaño del radiador.

    -------------------------
    H. MONITORES
    -------------------------
    Atributos esenciales:
    - Tamaño: 24, 27, 32 pulgadas
    - Resolución: 1080p, 1440p, 4K
    - Frecuencia: 60Hz, 144Hz, 165Hz, 240Hz

    Regla:
    Dos monitores solo son el mismo producto si coinciden tamaño + resolución + refresco + modelo.

    ==================================================
    4) MARCAS Y FABRICANTES
    ==================================================
    Si la marca comercial cambia y no puedes confirmar con seguridad el mismo modelo exacto, responde false.

    ==================================================
    5) REGLAS DE DESEMPATE
    ==================================================
    - Si un atributo crítico entra en conflicto, responde false.
    - Si ves dos capacidades distintas, responde false.

    ==================================================
    6) EJEMPLOS
    ==================================================
    Texto A: "Intel Core i5-12400 2.5 GHz"
    Texto B: "Intel Core Ultra 9 285K IA Integrada 3.2/5.7GHz Box"
    {"mismo_producto": false}

    Texto A: "AMD Ryzen 5 3400G 4 Núcleos 3.7 GHz"
    Texto B: "AMD Ryzen 5 3400G 3.7GHz Box"
    {"mismo_producto": true}

    ==================================================
    7) FORMATO DE SALIDA (BATCH)
    ==================================================
    Vas a recibir un "Producto Base" y una lista numerada de "Candidatos".
    Debes evaluar el Producto Base contra CADA UNO de los candidatos.
    Devuelve ÚNICAMENTE un JSON válido donde las claves sean el ID numérico del candidato y el valor sea true, false o "duda" (como cadena de texto).
    Ejemplo de salida:
    {
        "0": false,
        "1": true,
        "2": "duda"
    }"""

    candidatos_str = "\n".join([f"[{i}] {nombre}" for i, nombre in enumerate(lista_candidatos)])
    prompt_usuario = f"Producto Base: '{nombre_base}'\na evaluar:\n{candidatos_str}"

    try:
        # --- INTENTO 1: Modelo rápido ---
        contenido_rapido = consultar_ollama_sync(MODELO_RAPIDO, prompt_sistema, prompt_usuario)
        try:
            datos_json_rapido = json.loads(contenido_rapido)
        except json.JSONDecodeError:
            # Si el modelo pequeño falla al dar un JSON válido, marcamos todo como duda
            datos_json_rapido = {str(i): "duda" for i in range(len(lista_candidatos))}

        resultados = [False] * len(lista_candidatos)
        candidatos_duda = []
        indices_duda = []

        for i in range(len(lista_candidatos)):
            es_match = datos_json_rapido.get(str(i), False)
            if es_match == "duda":
                candidatos_duda.append(lista_candidatos[i])
                indices_duda.append(i)
            else:
                resultados[i] = True if str(es_match).lower() == 'true' else False

        # --- INTERACCIÓN CON EL USUARIO (Fallback para dudas) ---
        if candidatos_duda:
            try:
                # Preguntamos al operador por cada candidato que la IA marcó como "duda".
                respuestas_usuario = preguntar_usuario(nombre_base, candidatos_duda)
                # Asignamos las respuestas a los índices correspondientes en la lista de resultados.
                for idx_relativo, idx_real in enumerate(indices_duda):
                    resultados[idx_real] = respuestas_usuario[idx_relativo]
            except Exception as e:
                # En caso de cualquier error inesperado, registramos la advertencia y marcamos los
                # candidatos dudosos como "False" (no coinciden).
                logger.warning(f"⚠️ Error en la interacción con el usuario: {e}. Marcando dudas como False.")
                for idx_real in indices_duda:
                    resultados[idx_real] = False

        return resultados

    except Exception as e:
        # Si ocurre cualquier error inesperado al intentar usar la IA (por ejemplo, timeout,
        # error de red o respuesta no parseable), delegamos la decisión al operador mediante
        # la interacción terminal. De esta forma el proceso no se bloquea y el usuario puede
        # proporcionar manualmente la respuesta para cada candidato.
        logger.warning(
            f"⚠️ Aviso: Error en el flujo de Ollama: {e}. Se solicita interacción al usuario."
        )
        try:
            # Preguntamos al usuario por todos los candidatos originales.
            respuestas_usuario = preguntar_usuario(nombre_base, lista_candidatos)
            return respuestas_usuario
        except Exception as e_interactivo:
            # Si la interacción también falla (por ejemplo, entorno no interactivo),
            # registramos la advertencia y devolvemos un fallback conservador (False).
            logger.warning(
                f"⚠️ Error en la interacción con el usuario tras fallo de IA: {e_interactivo}. "
                "Marcando todos los candidatos como False."
            )
            return [False] * len(lista_candidatos)

# EVALUAR PRODUCTOS DE FORMA SÍNCRONA
def evaluar_productos_ia_sync(nombre_base, lista_candidatos):
    return es_mismo_producto_ia_batch(nombre_base, lista_candidatos)