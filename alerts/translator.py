from deep_translator import GoogleTranslator
from utils.logger import log
from utils.config_loader import load_config

config   = load_config()
LANGUAGE = config["alerts"]["language"]


def translate(text: str) -> str:
    if LANGUAGE == "en":
        return text
    try:
        return GoogleTranslator(source="en", target=LANGUAGE).translate(text)
    except Exception as e:
        log.warning(f"Translation failed: {e}")
        return text