#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuration handling for CodeRefactor.
Provides functionality to load, validate, and access configuration settings.
"""

import os
import sys
import yaml
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

# Default configuration paths
DEFAULT_CONFIG_PATHS = [
    "./coderefactor.yaml",
    "./coderefactor.yml",
    "~/.config/coderefactor/config.yaml",
    "~/.coderefactor.yaml",
]

# Default configuration settings
DEFAULT_CONFIG = {
    "python": {
        "enabled": True,
        "tools": ["pylint", "mypy", "flake8", "bandit", "ast"],
        "pylint_args": [],
        "mypy_args": [],
        "flake8_args": [],
        "bandit_args": []
    },
    "javascript": {
        "enabled": True,
        "eslint_config": None
    },
    "typescript": {
        "enabled": True,
        "eslint_config": None
    },
    "html": {
        "enabled": True,
        "htmlhint_config": None
    },
    "css": {
        "enabled": True,
        "stylelint_config": None
    },
    "csharp": {
        "enabled": True,
        "tools": ["Roslyn", "Roslynator"],
        "disabled_rules": []
    },
    "llm": {
        "enabled": False,
        "model": "claude-3-7-sonnet-20250219",
        "use_extended_thinking": True,
        "temperature": 0.3
    },
    "output": {
        "format": "terminal",
        "colored": True,
        "details": True
    },
    "web": {
        "host": "0.0.0.0",
        "port": 5000,
        "debug": False
    }
}


class ConfigManager:
    """Manages configuration for the CodeRefactor application."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.logger = logging.getLogger("coderefactor.config")
        self.config: Dict[str, Any] = {}
        self.config_path: Optional[str] = None
        
        # Load configuration
        self.load_config(config_path)
    
    def load_config(self, config_path: Optional[str] = None) -> None:
        """
        Load configuration from file or use defaults.
        
        Args:
            config_path: Optional path to a configuration file.
                        If None, will search in default locations.
        """
        # Start with default configuration
        self.config = DEFAULT_CONFIG.copy()
        
        # If a specific config path is provided, try to load it
        if config_path:
            if self._load_from_file(config_path):
                self.config_path = config_path
                return
            else:
                self.logger.warning(f"Could not load configuration from {config_path}")
                self.logger.warning("Using default configuration")
                return
        
        # Try loading from default paths
        for path in DEFAULT_CONFIG_PATHS:
            expanded_path = os.path.expanduser(path)
            if os.path.exists(expanded_path):
                if self._load_from_file(expanded_path):
                    self.config_path = expanded_path
                    return
        
        # If we get here, no config file was found or loaded
        self.logger.info("No configuration file found, using default configuration")
    
    def _load_from_file(self, file_path: str) -> bool:
        """
        Load configuration from a file.
        
        Args:
            file_path: Path to the configuration file.
        
        Returns:
            bool: True if the file was loaded successfully, False otherwise.
        """
        try:
            with open(file_path, 'r') as f:
                file_ext = os.path.splitext(file_path)[1].lower()
                
                if file_ext in ['.yaml', '.yml']:
                    file_config = yaml.safe_load(f)
                elif file_ext == '.json':
                    file_config = json.load(f)
                else:
                    self.logger.error(f"Unsupported configuration file format: {file_ext}")
                    return False
                
                # Merge configurations
                self._deep_merge(self.config, file_config)
                
                self.logger.info(f"Loaded configuration from {file_path}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error loading configuration from {file_path}: {str(e)}")
            return False
    
    def _deep_merge(self, base: Dict, update: Dict) -> None:
        """
        Deep merge two dictionaries.
        
        Args:
            base: Base dictionary to merge into.
            update: Dictionary with updates to apply.
        """
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: The dot-separated path to the configuration value.
            default: The default value to return if the key is not found.
        
        Returns:
            The configuration value, or the default if not found.
        """
        parts = key.split('.')
        current = self.config
        
        try:
            for part in parts:
                current = current[part]
            return current
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.
        
        Args:
            key: The dot-separated path to the configuration value.
            value: The value to set.
        """
        parts = key.split('.')
        current = self.config
        
        # Navigate to the right location
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # Set the value
        current[parts[-1]] = value
    
    def save(self, file_path: Optional[str] = None) -> bool:
        """
        Save the current configuration to a file.
        
        Args:
            file_path: Optional path to save the file.
                      If None, will use the path the config was loaded from.
        
        Returns:
            bool: True if the file was saved successfully, False otherwise.
        """
        save_path = file_path or self.config_path
        
        if not save_path:
            self.logger.error("No save path specified and no config was loaded from a file")
            return False
        
        try:
            # Create parent directories if they don't exist
            os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
            
            with open(save_path, 'w') as f:
                file_ext = os.path.splitext(save_path)[1].lower()
                
                if file_ext in ['.yaml', '.yml']:
                    yaml.dump(self.config, f, default_flow_style=False)
                elif file_ext == '.json':
                    json.dump(self.config, f, indent=2)
                else:
                    self.logger.error(f"Unsupported configuration file format: {file_ext}")
                    return False
                
            self.logger.info(f"Saved configuration to {save_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving configuration to {save_path}: {str(e)}")
            return False
    
    def validate(self) -> List[str]:
        """
        Validate the current configuration.
        
        Returns:
            List of validation errors, empty if the configuration is valid.
        """
        errors = []
        
        # Validate Python config
        if self.config.get('python', {}).get('enabled', False):
            tools = self.config.get('python', {}).get('tools', [])
            if not tools:
                errors.append("Python tools list is empty")
        
        # Validate LLM config
        if self.config.get('llm', {}).get('enabled', False):
            if not os.environ.get("ANTHROPIC_API_KEY"):
                errors.append("LLM is enabled but ANTHROPIC_API_KEY environment variable is not set")
            
            model = self.config.get('llm', {}).get('model', '')
            if not model:
                errors.append("LLM is enabled but no model is specified")
        
        # Validate web config
        web_config = self.config.get('web', {})
        if 'port' in web_config and (not isinstance(web_config['port'], int) or 
                                    web_config['port'] < 1 or 
                                    web_config['port'] > 65535):
            errors.append("Web port must be an integer between 1 and 65535")
        
        return errors


# Singleton instance for global access
_config_instance = None

def get_config(config_path: Optional[str] = None) -> ConfigManager:
    """
    Get the global configuration instance.
    
    Args:
        config_path: Optional path to a configuration file.
                    Only used if this is the first call.
    
    Returns:
        The global ConfigManager instance.
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigManager(config_path)
    return _config_instance


if __name__ == "__main__":
    # Simple CLI for configuration management
    import argparse
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    parser = argparse.ArgumentParser(description="CodeRefactor Configuration Manager")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--get", help="Get a configuration value")
    parser.add_argument("--set", help="Set a configuration value")
    parser.add_argument("--value", help="Value to set (used with --set)")
    parser.add_argument("--validate", action="store_true", help="Validate the configuration")
    parser.add_argument("--save", help="Save the configuration to a file")
    parser.add_argument("--show", action="store_true", help="Show the entire configuration")
    
    args = parser.parse_args()
    
    # Initialize configuration
    config = get_config(args.config)
    
    # Process commands
    if args.get:
        value = config.get(args.get)
        print(f"{args.get}: {value}")
    
    if args.set and args.value:
        # Convert value to appropriate type
        value = args.value
        if value.lower() == "true":
            value = True
        elif value.lower() == "false":
            value = False
        elif value.isdigit():
            value = int(value)
        elif value.replace(".", "", 1).isdigit() and value.count(".") == 1:
            value = float(value)
        
        config.set(args.set, value)
        print(f"Set {args.set} to {value}")
    
    if args.validate:
        errors = config.validate()
        if errors:
            print("Configuration validation errors:")
            for error in errors:
                print(f"- {error}")
        else:
            print("Configuration is valid")
    
    if args.save:
        success = config.save(args.save)
        if success:
            print(f"Configuration saved to {args.save}")
        else:
            print(f"Failed to save configuration to {args.save}")
    
    if args.show:
        print(json.dumps(config.config, indent=2))