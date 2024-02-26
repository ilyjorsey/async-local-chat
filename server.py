import asyncio
import csv
import logging
from collections import deque
from asyncio import StreamReader, StreamWriter

import aiofiles

from config import ServerSettings

server_settings = ServerSettings()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()


class Server:
    def __init__(
        self, host: str = server_settings.host, port: int = server_settings.port
    ):
        self.host = host
        self.port = port
        self.clients = set()
        self.clients_online = set()

    async def run_server(self) -> None:
        """
        Starts the server and processes connections from clients
        """
        logger.info(
            f"Starting the server on host {self.host} and port {self.port}")
        server = await asyncio.start_server(self.client_handler, self.host, self.port)
        try:
            async with server:
                await server.serve_forever()
        except asyncio.CancelledError:
            logger.info("The server has shutdown")

    async def transfer(
        self, message: str, sender_name: str, writer: StreamWriter
    ) -> None:
        """
        Processes the message from the sender and sends it to all connected clients
        """
        if message.startswith("/private"):
            _, recipient_name, private_message = message.split(" ", 2)
            recipient_writer = next(
                (
                    client_writer
                    for client_writer, name in self.clients
                    if name == recipient_name
                ),
                None,
            )

            if recipient_writer:
                formatted_private_message = (
                    f"Private message from {sender_name}: {private_message}"
                )
                try:
                    recipient_writer.write(
                        formatted_private_message.encode() + b"\n")
                    await recipient_writer.drain()
                    await self.history_file(
                        private_message, sender_name, recipient_name
                    )
                except asyncio.CancelledError:
                    logger.error("Error sending private message")
            else:
                sender_writer = next(
                    (
                        client_writer
                        for client_writer, name in self.clients
                        if name == sender_name
                    ),
                    None,
                )
                if sender_writer:
                    try:
                        sender_writer.write("Recipient not found.\n".encode())
                        await sender_writer.drain()
                    except asyncio.CancelledError:
                        logger.error("Error sending notification to sender")

        elif message.startswith("/disconnect"):
            self.clients_online.remove(sender_name)
            await self.broadcast("/disconnect", sender_name)
            await self.history_file(message, sender_name, None)
            logger.info(f"{sender_name} has disconnected")

        elif message.startswith("/reconnect"):
            if sender_name not in self.clients_online:
                self.clients_online.add(sender_name)
                await self.broadcast("/reconnect", sender_name)
                logger.info(f"{sender_name} has reconnected")
                await self.restore_for_reconnect(writer, sender_name)
            else:
                logger.debug("0_о")

        else:
            if sender_name in self.clients_online:
                await self.broadcast(f"{sender_name}: {message}", sender_name)
                await self.history_file(message, sender_name, None)
            else:
                logger.info(f"The client {sender_name} must reconnect")

    async def broadcast(self, message: str, sender_name) -> None:
        """
        Sends a message to all connected clients
        """
        for client_writer, _ in self.clients:
            if client_writer.is_closing():
                continue
            try:
                client_writer.write(message.encode() + b"\n")
                await client_writer.drain()
            except asyncio.CancelledError:
                logger.error("Error broadcasting message")

    async def client_handler(self, reader: StreamReader, writer: StreamWriter) -> None:
        """
        Processes the connection of a new client and its messages
        """
        try:
            writer.write("Enter your name: ".encode())
            await writer.drain()
            name = (await reader.read(100)).decode().strip()
            logger.info(f"Client connected: {name}")

            self.clients.add((writer, name))
            self.clients_online.add(name)
            await self.restore_for_new(writer)
            writer.write(f"Welcome to the chat, {name}!\n".encode())
            await writer.drain()

            while True:
                message = (await reader.read(2048)).decode().strip()
                if not message:
                    break
                else:
                    await self.transfer(message, name, writer)

        except ConnectionResetError:
            logger.info(f"Client {name} disconnected unexpectedly.")
            self.clients_online.remove(name)

        finally:
            writer.close()

    async def history_file(
        self, message: str, sender_name: str, recipient: None
    ) -> None:
        """
        Writes a message to the history.csv
        """
        async with aiofiles.open(
            server_settings.history_file, mode="a", newline="", encoding="utf-8"
        ) as file:
            file_writer = csv.writer(file)
            await file_writer.writerow([sender_name, message, recipient])

    async def restore_for_new(self, writer: StreamWriter) -> None:
        """
        Restores the latest messages for a new connected client
        """
        try:
            async with aiofiles.open(
                server_settings.history_file, mode="r", newline="", encoding="utf-8"
            ) as file:
                messages = deque()
                file_reader = await file.readlines()
                file_reader.reverse()
                for line in file_reader:
                    sender_name, message, recipient = line.strip().split(",", 2)
                    if not recipient:
                        messages.appendleft((sender_name, message))
                    if len(messages) >= server_settings.restore_last_messages:
                        break

                for sender_name, message in messages:
                    writer.write(f"{sender_name}: {message}\n".encode())
                await writer.drain()
        except Exception as e:
            logger.error(f"File reading error: {e}")

    async def restore_for_reconnect(
        self, writer: StreamWriter, sender_name: str
    ) -> None:
        """
        Recovers messages for a reconnected client
        """
        try:
            async with aiofiles.open(
                server_settings.history_file, mode="r", newline="", encoding="utf-8"
            ) as file:
                file_reader = await file.readlines()
                disconnect_index = None
                for i, line in enumerate(reversed(file_reader)):
                    line_sender, message, _ = line.strip().split(",", 2)
                    if line_sender == sender_name and message.startswith("/disconnect"):
                        disconnect_index = len(file_reader) - i - 1
                        break

                if disconnect_index is not None:
                    messages = file_reader[disconnect_index + 1:]
                    for line in messages:
                        line_sender, message, _ = line.strip().split(",", 2)
                        writer.write(f"{line_sender}: {message}\n".encode())
                    await writer.drain()
        except Exception as e:
            logger.error(f"File reading error: {e}")


if __name__ == "__main__":
    serv = Server()
    asyncio.run(serv.run_server())
