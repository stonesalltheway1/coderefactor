#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CLI Commands: Command-line interface for the CodeRefactor tool.
Provides commands for analyzing code, getting fix suggestions, and running the web interface.
"""

import os
import sys
import time
import argparse
import logging
import asyncio
import json
import tempfile
import webbrowser
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
import importlib
import shutil

# Import our modules
from .. import CodeRefactorApp
from ..utils.config import get_config
from ..utils.output import format_output
from ..utils.logging import get_logger

# Setup logging
logger = get_logger("coderefactor.cli")


def analyze_command(args: argparse.Namespace) -> int:
    """Handle the 'analyze' command."""
    logger.info(f"Analyzing {args.path}")
    
    # Create the app with configuration
    app = CodeRefactorApp(args.config)
    
    # Override tools if specified
    if args.tools:
        tool_list = [t.strip() for t in args.tools.split(",")]
        app.config["python"]["tools"] = tool_list
    
    # Start measuring time
    start_time = time.time()
    
    # Perform analysis
    try:
        if os.path.isfile(args.path):
            # Analyze a single file
            result = app.analyze_file(args.path)
        else:
            # Analyze a directory
            result = app.analyze_directory(args.path, args.recursive, args.pattern)
        
        # Add execution time
        end_time = time.time()
        if isinstance(result, dict):
            result["execution_time"] = end_time - start_time
        else:
            result.execution_time = end_time - start_time
        
        # Output the results
        app.output_results(result, args.format, args.output)
        
        # Return appropriate exit code
        if has_critical_issues(result):
            logger.warning("Analysis found critical issues")
            return 2
        if has_error_issues(result):
            logger.warning("Analysis found error issues")
            return 1
        
        logger.info("Analysis completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        return 1


def fix_command(args: argparse.Namespace) -> int:
    """Handle the 'fix' command."""
    logger.info(f"Getting fix suggestion for {args.issue_id} in {args.file}")
    
    try:
        # Check if file exists
        if not os.path.isfile(args.file):
            logger.error(f"File not found: {args.file}")
            return 1
        
        # Create the app with configuration
        app = CodeRefactorApp(args.config)
        
        # Get fix suggestion
        result = asyncio.run(app.get_fix_suggestion(args.file, args.issue_id))
        
        # Handle fix application if requested
        if args.apply:
            if "error" in result:
                logger.error(f"Cannot apply fix: {result['error']}")
                return 1
            
            if "refactored_code" not in result:
                logger.error("Fix suggestion does not contain refactored code")
                return 1
            
            # Create backup if needed
            if not args.no_backup:
                backup_path = f"{args.file}.bak"
                logger.info(f"Creating backup at {backup_path}")
                shutil.copy2(args.file, backup_path)
            
            # Apply the fix
            logger.info(f"Applying fix to {args.file}")
            with open(args.file, 'w', encoding='utf-8') as f:
                f.write(result["refactored_code"])
            
            print(f"Fix applied to {args.file}")
            if not args.no_backup:
                print(f"Backup saved to {backup_path}")
            
            return 0
        else:
            # Just output the suggestion
            app.output_results(result, "json" if args.output else "text", args.output)
            
            return 0 if "error" not in result else 1
    
    except Exception as e:
        logger.error(f"Failed to get fix suggestion: {str(e)}")
        return 1


def web_command(args: argparse.Namespace) -> int:
    """Handle the 'web' command."""
    logger.info(f"Starting web interface on {args.host}:{args.port}")
    
    # Create the app with configuration
    app = CodeRefactorApp(args.config)
    
    # Open browser if requested
    if not args.no_open:
        url = f"http://{args.host}:{args.port}"
        logger.info(f"Opening web interface in browser: {url}")
        webbrowser.open(url)
    
    # Start the web interface
    try:
        app.start_web_interface(args.host, args.port)
        return 0
    except Exception as e:
        logger.error(f"Failed to start web interface: {str(e)}")
        return 1


def version_command(args: argparse.Namespace) -> int:
    """Handle the 'version' command."""
    # Get version information
    try:
        from .. import __version__
        print(f"CodeRefactor version: {__version__}")
        
        if args.verbose:
            # Get Python version
            py_version = ".".join(map(str, sys.version_info[:3]))
            print(f"Python version: {py_version}")
            
            # Get OS info
            import platform
            print(f"Platform: {platform.platform()}")
            
            # Get installed packages
            packages = get_installed_packages()
            print("\nInstalled packages:")
            for pkg, version in packages:
                print(f"  {pkg}: {version}")
        
        return 0
    except ImportError:
        print("CodeRefactor version: unknown")
        return 1


def get_installed_packages() -> List[Tuple[str, str]]:
    """Get a list of installed packages and versions relevant to CodeRefactor."""
    relevant_packages = [
        "pylint", "mypy", "flake8", "bandit", "flask", "httpx",
        "anthropic", "pyyaml"
    ]
    
    packages = []
    
    for pkg in relevant_packages:
        try:
            module = importlib.import_module(pkg)
            version = getattr(module, "__version__", "unknown")
            packages.append((pkg, version))
        except ImportError:
            pass
    
    return packages


def has_critical_issues(result: Union[Dict[str, Any], Any]) -> bool:
    """Check if an analysis result contains critical issues."""
    if isinstance(result, dict):
        # Directory result
        for file_result in result.get("files", []):
            for issue in file_result.get("issues", []):
                if issue.get("severity") == "critical":
                    return True
    else:
        # Single file result
        for issue in getattr(result, "issues", []):
            if hasattr(issue, "severity") and getattr(issue, "severity").name == "CRITICAL":
                return True
            if isinstance(issue, dict) and issue.get("severity") == "critical":
                return True
    
    return False


def has_error_issues(result: Union[Dict[str, Any], Any]) -> bool:
    """Check if an analysis result contains error issues."""
    if isinstance(result, dict):
        # Directory result
        for file_result in result.get("files", []):
            for issue in file_result.get("issues", []):
                if issue.get("severity") == "error":
                    return True
    else:
        # Single file result
        for issue in getattr(result, "issues", []):
            if hasattr(issue, "severity") and getattr(issue, "severity").name == "ERROR":
                return True
            if isinstance(issue, dict) and issue.get("severity") == "error":
                return True
    
    return False


def main() -> int:
    """Main entry point for the CLI."""
    # Create the argument parser
    parser = argparse.ArgumentParser(
        description="CodeRefactor: Advanced Code Analysis & Refactoring Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a Python file
  coderefactor analyze path/to/file.py
  
  # Analyze a directory recursively with HTML files only
  coderefactor analyze path/to/directory --recursive --pattern "*.html"
  
  # Get a fix suggestion for an issue
  coderefactor fix path/to/file.py issue-id-12345
  
  # Start the web interface on a specific port
  coderefactor web --port 8080
  
  # Display verbose logging output
  coderefactor analyze path/to/file.py --log-level debug
"""
    )
    
    # Common parent parser for shared options
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
        "-c", "--config", 
        help="Path to configuration file"
    )
    parent_parser.add_argument(
        "--log-level", 
        choices=["debug", "info", "warning", "error", "critical"],
        default="info",
        help="Set logging level"
    )
    
    # Create subparsers for commands
    subparsers = parser.add_subparsers(
        dest="command",
        title="Commands",
        help="Command to execute"
    )
    
    # Analyze command
    analyze_parser = subparsers.add_parser(
        "analyze", 
        help="Analyze code files or directories",
        parents=[parent_parser]
    )
    analyze_parser.add_argument(
        "path", 
        help="File or directory path to analyze"
    )
    analyze_parser.add_argument(
        "-r", "--recursive", 
        action="store_true", 
        help="Recursively analyze directories"
    )
    analyze_parser.add_argument(
        "-p", "--pattern", 
        help="File pattern to match (e.g. *.py)"
    )
    analyze_parser.add_argument(
        "-o", "--output", 
        help="Output file path"
    )
    analyze_parser.add_argument(
        "-f", "--format", 
        choices=["text", "json", "html", "markdown"],
        default="text", 
        help="Output format"
    )
    analyze_parser.add_argument(
        "--open-browser", 
        action="store_true",
        help="Open HTML output in browser"
    )
    analyze_parser.add_argument(
        "--no-color", 
        action="store_true",
        help="Disable colored output"
    )
    analyze_parser.add_argument(
        "--tools",
        help="Comma-separated list of tools to use for analysis"
    )
    analyze_parser.set_defaults(func=analyze_command)
    
    # Fix command
    fix_parser = subparsers.add_parser(
        "fix", 
        help="Get fix suggestions for an issue",
        parents=[parent_parser]
    )
    fix_parser.add_argument(
        "file", 
        help="File path"
    )
    fix_parser.add_argument(
        "issue_id", 
        help="Issue ID to fix"
    )
    fix_parser.add_argument(
        "-o", "--output", 
        help="Output file path"
    )
    fix_parser.add_argument(
        "-a", "--apply", 
        action="store_true",
        help="Apply the fix to the file instead of just showing it"
    )
    fix_parser.add_argument(
        "--no-backup", 
        action="store_true",
        help="Don't create backup when applying fixes"
    )
    fix_parser.set_defaults(func=fix_command)
    
    # Web interface command
    web_parser = subparsers.add_parser(
        "web", 
        help="Start the web interface",
        parents=[parent_parser]
    )
    web_parser.add_argument(
        "-H", "--host", 
        default="127.0.0.1", 
        help="Host to bind to"
    )
    web_parser.add_argument(
        "-p", "--port", 
        type=int, 
        default=5000, 
        help="Port to listen on"
    )
    web_parser.add_argument(
        "--no-open", 
        action="store_true",
        help="Don't open the web interface in a browser"
    )
    web_parser.add_argument(
        "--debug", 
        action="store_true",
        help="Run the web server in debug mode"
    )
    web_parser.set_defaults(func=web_command)
    
    # Version command
    version_parser = subparsers.add_parser(
        "version", 
        help="Show version information",
        parents=[parent_parser]
    )
    version_parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Show detailed version information"
    )
    version_parser.set_defaults(func=version_command)
    
    # Parse arguments
    args = parser.parse_args()
    
    # Setup logging based on args
    logging_config = {
        "log_level": args.log_level.upper() if hasattr(args, "log_level") else "INFO"
    }
    from ..utils.logging import setup_logging
    setup_logging(logging_config)
    
    # If no command is specified, show help
    if not hasattr(args, 'func'):
        parser.print_help()
        return 0
    
    try:
        # Execute the command function
        return args.func(args)
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 130  # Standard exit code for SIGINT
    except Exception as e:
        logger.error(f"Command failed: {str(e)}")
        if logging_config["log_level"] == "DEBUG":
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())