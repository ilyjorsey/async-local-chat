import asyncio
import logging

from aioconsole import ainput

from config import ServerSettings

server_settings = ServerSettings()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()


class Client:
    def __init__(
        self, host: str = server_settings.host, port: int = server_settings.port
    ):
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None
        self.connected = True

    async def connect_to_server(self) -> None:
        """
        Establishes a connection with the server 
        """
        try:
            self.reader, self.writer = await asyncio.open_connection(
                self.host, self.port
            )
            logger.info(f"Connected to the server on {self.host}:{self.port}")

            asyncio.create_task(self.read_from_server())

            await self.sending()
        except ConnectionRefusedError:
            logger.error(
                f"Failed to connect to the server at {self.host}:{self.port}")

    async def read_from_server(self) -> None:
        """
        Rreads messages from the server and prints them to the console
        """
        try:
            while True:
                message = await self.reader.read(2048)
                decoded_message = message.decode()

                if not decoded_message:
                    break
                else:
                    if self.connected:
                        logger.info(decoded_message)

        except asyncio.CancelledError:
            logger.error("Connection closed by server")

        except Exception as e:
            logger.error(f"Chat reading error: {e}")

    async def sending(self) -> None:
        """
        Reads messages from the console and sends them to the server
        """
        try:
            while True:
                user_input = await ainput("")
                if user_input.strip() != "":
                    if user_input.strip() == "/disconnect":
                        self.connected = False
                    elif user_input.strip() == "/reconnect":
                        self.connected = True
                    self.writer.write(user_input.encode())
                    await self.writer.drain()
        except Exception as e:
            logger.error(f"Chat sending error: {e}")


if __name__ == "__main__":
    client = Client()
    try:
        asyncio.run(client.connect_to_server())
    except KeyboardInterrupt:
        logger.error("Disconnected from the server")
