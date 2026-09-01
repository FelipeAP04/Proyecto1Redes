"""Cliente anfitrión para consumir servidores MCP mediante stdio."""

from .cliente import ClienteMCP, ErrorClienteMCP
from .registro import RegistroMCP

__all__ = ["ClienteMCP", "ErrorClienteMCP", "RegistroMCP"]
