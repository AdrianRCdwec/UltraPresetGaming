import threading

# Evento global para el apagado seguro (Graceful Shutdown)
shutdown_event = threading.Event()