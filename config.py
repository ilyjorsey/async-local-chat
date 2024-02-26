from pydantic_settings import BaseSettings

class ServerSettings(BaseSettings):
    host: str = '127.0.0.1'
    port: int = 8000
    history_file: str = 'history.csv' # History file name
    
    restore_last_messages: int = 20 # The number of messages to restore for a new client
