"""Configuration file handler for ES-CLI."""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """Handles loading and accessing configuration."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize config from file.
        
        Args:
            config_path: Path to config file. If None, looks for config.yaml in current dir or home.
        """
        if config_path is None:
            # Try current directory first, then home directory
            current_dir = Path.cwd() / "config.yaml"
            home_dir = Path.home() / ".es-cli" / "config.yaml"
            
            if current_dir.exists():
                config_path = str(current_dir)
            elif home_dir.exists():
                config_path = str(home_dir)
            else:
                raise FileNotFoundError(
                    f"Config file not found. Please create config.yaml in current directory "
                    f"or ~/.es-cli/config.yaml. See config.yaml.example for template."
                )
        
        self.config_path = config_path
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Ensure config is a dictionary
        if config is None:
            config = {}
        if not isinstance(config, dict):
            raise ValueError(
                f"Config file must contain a YAML dictionary/mapping. "
                f"Got {type(config)} instead."
            )
        
        # Set defaults
        defaults = {
            'default_index': '*',
            'query': {
                'default_size': 100,
                'max_size': 10000
            }
        }
        
        # Merge with defaults
        for key, value in defaults.items():
            if key not in config:
                config[key] = value
            elif isinstance(value, dict):
                existing_value = config.get(key)
                if isinstance(existing_value, dict):
                    config[key] = {**value, **existing_value}
                else:
                    # Keep existing value if it's not a dict
                    pass
        
        return config
    
    @property
    def elasticsearch_config(self) -> Dict[str, Any]:
        """Get Elasticsearch connection configuration."""
        es_config = self._config.get('elasticsearch', {})
        
        # Ensure it's a dictionary
        if not isinstance(es_config, dict):
            raise ValueError(f"elasticsearch config must be a dictionary, got {type(es_config)}")
        
        # Filter out any None values, invalid keys, and comments
        # Keys to ignore (not valid for Elasticsearch client)
        ignored_keys = {'Optional', 'optional'}  # Common mistake: uncommented "Optional:" line
        
        clean_config = {}
        for key, value in es_config.items():
            # Skip None values, invalid keys, and ensure key is a string
            if value is None or not isinstance(key, str):
                continue
            
            # Skip ignored keys (like "Optional" from comments)
            if key in ignored_keys:
                continue
            
            # Skip keys that start with comment-like patterns
            if key.strip().startswith('#'):
                continue
            
            clean_config[key] = value
        
        return clean_config
    
    @property
    def default_index(self) -> str:
        """Get default index pattern."""
        return self._config.get('default_index', '*')
    
    @property
    def default_size(self) -> int:
        """Get default query result size."""
        return self._config.get('query', {}).get('default_size', 100)
    
    @property
    def max_size(self) -> int:
        """Get maximum query result size."""
        return self._config.get('query', {}).get('max_size', 10000)
