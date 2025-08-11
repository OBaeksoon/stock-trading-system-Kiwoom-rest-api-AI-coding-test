"""
Settings and configuration for Kiwoom MCP Server
"""

import os
import configparser
from dataclasses import dataclass
from typing import Optional


@dataclass
class KiwoomConfig:
    """Kiwoom API configuration"""
    appkey: Optional[str] = None
    secretkey: Optional[str] = None
    is_mock: bool = True
    access_token: Optional[str] = None
    token_expires_dt: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> "KiwoomConfig":
        """Create config from environment variables or config.ini file"""
        
        # First, try to load from environment variables
        appkey = os.getenv("KIWOOM_APPKEY")
        secretkey = os.getenv("KIWOOM_SECRETKEY")
        is_mock = os.getenv("KIWOOM_IS_MOCK", "false").lower() == "true"

        # If not found in env, try to load from config.ini
        if not appkey or not secretkey:
            try:
                # Path to config.ini in the parent directory
                config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config.ini')
                if os.path.exists(config_path):
                    config = configparser.ConfigParser()
                    config.read(config_path)
                    
                    if 'API' in config:
                        appkey = appkey or config['API'].get('APP_KEY')
                        secretkey = secretkey or config['API'].get('APP_SECRET')
                    
                    if 'SETTINGS' in config:
                        is_mock_str = config['SETTINGS'].get('IS_MOCK', 'false')
                        is_mock = is_mock_str.lower() == 'true'

            except Exception:
                # Ignore errors if config.ini is not found or invalid
                pass

        return cls(
            appkey=appkey,
            secretkey=secretkey,
            is_mock=is_mock,
            access_token=os.getenv("KIWOOM_ACCESS_TOKEN"),
            token_expires_dt=os.getenv("KIWOOM_TOKEN_EXPIRES_DT")
        )


@dataclass
class ServerConfig:
    """MCP Server configuration"""
    name: str = "kiwoom-stock-mcp"
    version: str = "1.0.0"
    log_level: str = "INFO"
    
    @classmethod
    def from_env(cls) -> "ServerConfig":
        """Create config from environment variables"""
        return cls(
            name=os.getenv("MCP_SERVER_NAME", "kiwoom-stock-mcp"),
            version=os.getenv("MCP_SERVER_VERSION", "1.0.0"),
            log_level=os.getenv("LOG_LEVEL", "INFO")
        ) 