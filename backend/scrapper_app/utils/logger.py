import logging, sys, os

def setup_logger():
    # 1. Crear el logger principal de la aplicación
    logger = logging.getLogger('UltraPresetGaming')
    logger.setLevel(logging.INFO)

    # 2. Evitar que se añadan múltiples handlers si se importa varias veces
    if not logger.handlers:
        # Formato profesional: Fecha | Nivel | Archivo | Mensaje
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | [%(module)s] | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 3. Handler para guardar en el archivo (se guarda en la raíz de scrapper_app)
        ruta_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_file = os.path.join(ruta_base, 'scraper.log')
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)

        # 4. Handler para seguir viendo los mensajes por la terminal (Sys.stdout)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        # Añadir ambos handlers
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger

# Instancia global lista para ser importada
logger = setup_logger()