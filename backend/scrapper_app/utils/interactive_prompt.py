from typing import List
from .logger import logger


def preguntar_usuario(nombre_base: str, candidatos: List[str]) -> List[bool]:
    respuestas: List[bool] = []
    for candidato in candidatos:
        while True:
            try:
                # Mensaje claro para el operador
                respuesta = input(
                    f"¿El producto base '{nombre_base}' es el mismo que el candidato '{candidato}'? (y/n): "
                ).strip().lower()
            except EOFError:
                # Si la entrada no está disponible (por ejemplo, ejecución no interactiva),
                # asumimos una respuesta negativa y registramos la advertencia.
                logger.warning(
                    "Entrada de usuario no disponible; se asume respuesta negativa para el candidato."
                )
                respuesta = "n"

            # Normalizamos respuestas aceptadas
            if respuesta in ("y", "yes", "s", "si", "sí"):
                respuestas.append(True)
                logger.info(f"Usuario respondió 'SI' para candidato: {candidato}")
                break
            elif respuesta in ("n", "no"):
                respuestas.append(False)
                logger.info(f"Usuario respondió 'n' para candidato: {candidato}")
                break
            else:
                # Mensaje de error y repetición del prompt
                logger.warning("Respuesta no válida. Por favor responde 'y' o 'n'.")
                continue
    return respuestas
