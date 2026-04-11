import os
import sys
import subprocess
import socket
from importlib.metadata import version, PackageNotFoundError
from services.core.logger_service import setup_logger

logger = setup_logger("EnvService")

class EnvService:
    """Service to handle environment verification and automatic dependency setup."""

    @staticmethod
    def check_and_install_dependencies(requirements_path: str):
        """
        Check if all requirements are installed. If not, attempt to install them.
        """
        if not os.path.exists(requirements_path):
            logger.warning(f"requirements.txt not found at {requirements_path}. Skipping dependency check.")
            return

        try:
            with open(requirements_path, "r", encoding="utf-8") as f:
                requirements = [
                    line.strip().split("==")[0].split(">=")[0].split("<=")[0]
                    for line in f
                    if line.strip() and not line.startswith("#")
                ]
        except Exception as e:
            logger.error(f"Failed to read requirements file: {e}")
            return

        missing = []
        for req in requirements:
            try:
                version(req)
            except PackageNotFoundError:
                missing.append(req)

        if missing:
            logger.info(f"Missing dependencies found: {', '.join(missing)}")
            logger.info("Attempting automatic installation...")
            try:
                # Use sys.executable to ensure we install in the current environment
                # Redirecting stdout/stderr to DEVNULL to prevent MCP protocol pollution
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", requirements_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                if result.returncode == 0:
                    logger.info("Successfully installed missing dependencies.")
                else:
                    logger.error(f"Failed to install dependencies: {result.stderr}")
            except Exception as e:
                logger.error(f"Failed to install dependencies automatically: {e}")
                logger.error("Please run 'pip install -r requirements.txt' manually.")

        else:
            logger.info("All Python dependencies are satisfied.")

    @staticmethod
    def check_ollama_status(host: str = "localhost", port: int = 11434) -> bool:
        """
        Check if Ollama is reachable on the specified host and port.
        """
        # Parse host from URL if provided (e.g. http://localhost:11434)
        clean_host = host.replace("http://", "").replace("https://", "").split(":")[0]
        
        try:
            with socket.create_connection((clean_host, port), timeout=2):
                logger.info(f"Ollama is reachable at {clean_host}:{port}")
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            logger.warning(f"Ollama is NOT reachable at {clean_host}:{port}. AI tools will be disabled.")
            return False
