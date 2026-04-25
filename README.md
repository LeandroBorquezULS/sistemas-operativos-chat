# Chat Basico con Sockets y Threads

Este proyecto contiene:

- `socket_servidor_3.py`: inicia el servidor del chat.
- `socket_cliente_3.py`: inicia el cliente con interfaz en Tkinter.

## Caracteristicas

- Servidor multiusuario con `socket` + `threading`
- Difusion de mensajes a todos los clientes conectados
- Lista de usuarios conectados
- Historial corto persistido en `server/chat_history.jsonl`
- Login basico con nombre, emoji, color, host y puerto
- Interfaz con panel de usuarios, panel de chat, boton salir y modo oscuro
- Agrupacion visual de mensajes del mismo usuario si llegan con menos de 15 minutos de diferencia
- Limite de 200 caracteres por mensaje
- Validaciones basicas de entrada para nombre, emoji, color y mensaje

## Ejecucion

1. Inicia el servidor:

```bash
python3 socket_servidor_3.py
```

2. Inicia uno o mas clientes:

```bash
python3 socket_cliente_3.py
```

3. En el login del cliente indica:

- Nombre
- Emoji
- Color
- IP o host del servidor
- Puerto

## Nota sobre Tkinter

El cliente usa Tkinter. Si tu sistema no tiene instaladas las librerias graficas de Tk, debes instalarlas antes de ejecutar la interfaz.

## Pruebas fuera de la red local

Si quieres usar un tunel como Cloudflare Tunnel para pruebas externas, no hace falta cambiar el protocolo del chat. Solo necesitas exponer el puerto TCP del servidor y luego usar en el cliente la direccion y puerto publicados por el tunel.
