import copy

from src.config import APP_CONFIG_FILE, get_default_app_config, load_app_config, save_app_config


class ConfigStore:
    """Reads and writes the user-editable desktop app configuration."""

    def __init__(self):
        self.path = APP_CONFIG_FILE

    def load(self):
        return load_app_config()

    def save(self, config):
        save_app_config(config)

    def reset(self):
        config = get_default_app_config()
        save_app_config(config)
        return config

    def snapshot(self):
        return copy.deepcopy(self.load())
