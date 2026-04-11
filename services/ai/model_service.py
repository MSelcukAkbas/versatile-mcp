import os
import requests
from tqdm import tqdm
from pathlib import Path
from services.core.logger_service import setup_logger

logger = setup_logger("ModelService")

class ModelService:
    """Service to handle model presence and downloading from remote sources."""

    DEFAULT_MODEL_URL = "https://huggingface.co/mradermacher/paraphrase-multilingual-MiniLM-L12-v2-GGUF/resolve/main/paraphrase-multilingual-MiniLM-L12-v2.I1-Q8_0.gguf"
    DEFAULT_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-118M-v2-Q8_0.gguf"

    def __init__(self, models_dir: str = "models"):
        self.project_root = Path(__file__).parent.parent.parent
        self.models_dir = self.project_root / models_dir
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def ensure_model(self, model_name: str = None, url: str = None) -> str:
        """
        Ensures the model exists locally. Downloads it if missing.
        Returns the absolute path to the model.
        """
        name = model_name or self.DEFAULT_MODEL_NAME
        download_url = url or self.DEFAULT_MODEL_URL
        model_path = self.models_dir / name

        if model_path.exists():
            logger.info(f"ModelService | Model already exists: {name}")
            return str(model_path)

        logger.info(f"ModelService | Model missing: {name}. Starting download...")
        try:
            self._download_file(download_url, model_path)
            logger.info(f"ModelService | Download complete: {name}")
            return str(model_path)
        except Exception as e:
            logger.error(f"ModelService | Failed to download model: {e}")
            raise

    def _download_file(self, url: str, dest_path: Path):
        """Downloads a file with a progress bar."""
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024 * 1024 # 1MB

        with open(dest_path, 'wb') as f:
            with tqdm(total=total_size, unit='iB', unit_scale=True, desc=dest_path.name) as pbar:
                for data in response.iter_content(block_size):
                    f.write(data)
                    pbar.update(len(data))
