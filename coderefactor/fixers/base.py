#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Base fixer interface for CodeRefactor.
Provides common functionality and interfaces for language-specific fixers.
"""

import os
import logging
import difflib
import tempfile
from enum import Enum, auto
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
import uuid

# Try to import rich for better diff display
try:
    from rich.console import Console
    from rich.syntax import Syntax
    from rich import print as rich_print
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


class FixType(Enum):
    """Types of fixes that can be applied."""
    SIMPLE = auto()     # Simple replacements, formatting, style fixes
    COMPLEX = auto()    # More complex refactorings that affect code structure
    LLM = auto()        # Fixes that use LLM assistance
    MANUAL = auto()     # Fixes that require manual intervention


@dataclass
class FixChange:
    """Represents a single change to be applied to code."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    start_line: int = 0
    start_column: int = 0
    end_line: int = 0
    end_column: int = 0
    original_text: str = ""
    replacement_text: str = ""
    fix_type: FixType = FixType.SIMPLE
    confidence: float = 1.0  # 0.0 to 1.0, how confident we are in this fix


@dataclass
class FixResult:
    """Result of applying fixes to a code file."""
    file_path: str
    success: bool = True
    original_code: str = ""
    fixed_code: str = ""
    changes: List[FixChange] = field(default_factory=list)
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


class BaseFixer:
    """Base class for all fixers."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the fixer with configuration options.
        
        Args:
            config: Optional configuration dictionary specific to the fixer.
        """
        self.config = config or {}
        self.logger = logging.getLogger(f"coderefactor.fixer.{self.__class__.__name__}")
    
    async def fix_file(self, file_path: str, issues: Optional[List[Dict[str, Any]]] = None) -> FixResult:
        """
        Fix issues in a file.
        
        Args:
            file_path: Path to the file to fix.
            issues: Optional list of issues to fix. If None, all fixable issues will be addressed.
        
        Returns:
            FixResult containing the original and fixed code, along with details of changes made.
        """
        if not os.path.exists(file_path):
            return FixResult(
                file_path=file_path,
                success=False,
                error=f"File not found: {file_path}"
            )
        
        try:
            # Read the file
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # Fix the code
            return await self.fix_code(code, file_path, issues)
            
        except Exception as e:
            self.logger.error(f"Error fixing file {file_path}: {str(e)}")
            return FixResult(
                file_path=file_path,
                success=False,
                error=str(e)
            )
    
    async def fix_code(self, code: str, file_path: Optional[str] = None, 
                      issues: Optional[List[Dict[str, Any]]] = None) -> FixResult:
        """
        Fix issues in code.
        
        Args:
            code: The code to fix.
            file_path: Optional path to the file (for reference).
            issues: Optional list of issues to fix. If None, all fixable issues will be addressed.
        
        Returns:
            FixResult containing the original and fixed code, along with details of changes made.
        """
        # This should be implemented by subclasses
        return FixResult(
            file_path=file_path or "",
            success=False,
            original_code=code,
            fixed_code=code,
            error="fix_code method must be implemented by subclasses"
        )
    
    async def get_fix_suggestions(self, code: str, issue: Dict[str, Any], 
                                file_path: Optional[str] = None) -> List[FixChange]:
        """
        Get suggestions for fixing a specific issue.
        
        Args:
            code: The code containing the issue.
            issue: The issue to fix.
            file_path: Optional path to the file (for reference).
        
        Returns:
            List of FixChange objects with suggestions.
        """
        # This should be implemented by subclasses
        return []
    
    def apply_changes(self, code: str, changes: List[FixChange]) -> str:
        """
        Apply a list of changes to the code.
        
        Args:
            code: The original code.
            changes: List of changes to apply.
        
        Returns:
            The modified code with all changes applied.
        """
        # Make a copy of the code
        modified_code = code
        
        # Sort changes from last to first to avoid offset issues
        sorted_changes = sorted(
            changes,
            key=lambda x: (x.start_line, x.start_column),
            reverse=True
        )
        
        for change in sorted_changes:
            # Get the line-based view of the code
            lines = modified_code.splitlines(True)  # Keep line endings
            
            # Extract the text to replace
            start_line_idx = change.start_line - 1  # 0-based index
            end_line_idx = change.end_line - 1
            
            # Check if line indices are valid
            if start_line_idx < 0 or start_line_idx >= len(lines) or end_line_idx >= len(lines):
                self.logger.warning(f"Invalid line indices in change: {change.id}")
                continue
            
            # Get the start and end positions within the text
            prefix = ''.join(lines[:start_line_idx])
            suffix = ''.join(lines[end_line_idx + 1:])
            
            # Extract the text to replace
            text_to_replace = ''.join(lines[start_line_idx:end_line_idx + 1])
            
            # For single line changes, consider column positions
            if start_line_idx == end_line_idx:
                line = lines[start_line_idx]
                if change.start_column <= len(line) and change.end_column <= len(line):
                    # Replace only the specified part of the line
                    text_to_replace = line[change.start_column - 1:change.end_column]
                    prefix = prefix + line[:change.start_column - 1]
                    suffix = line[change.end_column:] + suffix
            
            # Apply the replacement
            modified_code = prefix + change.replacement_text + suffix
        
        return modified_code
    
    def generate_diff(self, original: str, modified: str, context_lines: int = 3) -> str:
        """
        Generate a unified diff between original and modified code.
        
        Args:
            original: The original code.
            modified: The modified code.
            context_lines: Number of context lines to include.
        
        Returns:
            Unified diff as a string.
        """
        # Split the code into lines
        original_lines = original.splitlines(True)  # Keep line endings
        modified_lines = modified.splitlines(True)
        
        # Generate the diff
        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile='original',
            tofile='modified',
            n=context_lines
        )
        
        return ''.join(diff)
    
    def preview_changes(self, original: str, modified: str, file_path: Optional[str] = None) -> None:
        """
        Preview changes between original and modified code.
        
        Args:
            original: The original code.
            modified: The modified code.
            file_path: Optional path to the file (for reference).
        """
        diff = self.generate_diff(original, modified)
        
        if file_path:
            print(f"Changes for {file_path}:")
        
        if HAS_RICH:
            # Use rich to display the diff with syntax highlighting
            console = Console()
            syntax = Syntax(diff, "diff", theme="monokai", line_numbers=True)
            console.print(syntax)
        else:
            # Fallback to plain text
            print(diff)
    
    def save_fixed_code(self, file_path: str, fixed_code: str, 
                       create_backup: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Save fixed code to a file.
        
        Args:
            file_path: Path to the file to save.
            fixed_code: The fixed code to save.
            create_backup: Whether to create a backup of the original file.
        
        Returns:
            Tuple of (success, backup_path), where backup_path is the path to the backup file
            if one was created, or None otherwise.
        """
        backup_path = None
        
        try:
            # Create a backup if requested
            if create_backup:
                backup_path = f"{file_path}.bak"
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as src, \
                         open(backup_path, 'w', encoding='utf-8') as dst:
                        dst.write(src.read())
            
            # Write the fixed code
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_code)
            
            return True, backup_path
            
        except Exception as e:
            self.logger.error(f"Error saving fixed code to {file_path}: {str(e)}")
            return False, backup_path


class CompositeFixResult(FixResult):
    """Result of applying multiple fixers to a code file."""
    individual_results: List[FixResult] = field(default_factory=list)


class CompositeFixer(BaseFixer):
    """
    A fixer that combines multiple other fixers.
    Applies each fixer in sequence.
    """
    
    def __init__(self, fixers: List[BaseFixer], config: Optional[Dict[str, Any]] = None):
        """
        Initialize the composite fixer with a list of fixers.
        
        Args:
            fixers: List of fixer instances to apply.
            config: Optional configuration dictionary.
        """
        super().__init__(config)
        self.fixers = fixers
    
    async def fix_code(self, code: str, file_path: Optional[str] = None, 
                      issues: Optional[List[Dict[str, Any]]] = None) -> CompositeFixResult:
        """
        Apply all fixers to the code in sequence.
        
        Args:
            code: The code to fix.
            file_path: Optional path to the file (for reference).
            issues: Optional list of issues to fix. If None, all fixable issues will be addressed.
        
        Returns:
            CompositeFixResult containing results from all fixers.
        """
        # Initialize the result
        result = CompositeFixResult(
            file_path=file_path or "",
            original_code=code,
            fixed_code=code,
            success=True
        )
        
        # Apply each fixer in sequence
        current_code = code
        
        for fixer in self.fixers:
            self.logger.debug(f"Applying fixer: {fixer.__class__.__name__}")
            
            try:
                # Apply the fixer
                fix_result = await fixer.fix_code(current_code, file_path, issues)
                
                # Store the individual result
                result.individual_results.append(fix_result)
                
                # Update the current code if the fix was successful
                if fix_result.success and fix_result.fixed_code != current_code:
                    current_code = fix_result.fixed_code
                    
                    # Add the changes to the composite result
                    result.changes.extend(fix_result.changes)
                
                # Add any warnings
                result.warnings.extend(fix_result.warnings)
                
            except Exception as e:
                self.logger.error(f"Error applying fixer {fixer.__class__.__name__}: {str(e)}")
                result.warnings.append(f"Fixer {fixer.__class__.__name__} failed: {str(e)}")
        
        # Update the final fixed code
        result.fixed_code = current_code
        
        # Set success to False if no changes were made or there was an error
        if result.fixed_code == result.original_code:
            result.success = False
            result.warnings.append("No changes were made to the code")
        
        return result


if __name__ == "__main__":
    # Simple test for the base fixer
    import asyncio
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Create a simple test fixer
    class TestFixer(BaseFixer):
        async def fix_code(self, code: str, file_path: Optional[str] = None, 
                          issues: Optional[List[Dict[str, Any]]] = None) -> FixResult:
            # Just a simple example that replaces "TODO" with "DONE"
            changes = []
            
            # Find all occurrences of "TODO"
            lines = code.splitlines(True)
            for i, line in enumerate(lines):
                if "TODO" in line:
                    # Create a change
                    start_col = line.index("TODO") + 1
                    end_col = start_col + 4
                    
                    change = FixChange(
                        description="Replace TODO with DONE",
                        start_line=i + 1,
                        start_column=start_col,
                        end_line=i + 1,
                        end_column=end_col,
                        original_text="TODO",
                        replacement_text="DONE",
                        fix_type=FixType.SIMPLE
                    )
                    
                    changes.append(change)
            
            # Apply the changes
            fixed_code = self.apply_changes(code, changes)
            
            return FixResult(
                file_path=file_path or "",
                success=len(changes) > 0,
                original_code=code,
                fixed_code=fixed_code,
                changes=changes
            )
    
    async def main():
        # Create a test fixer
        fixer = TestFixer()
        
        # Test code
        test_code = """def example():
    # TODO: Implement this function
    pass

# TODO: Add more examples
"""
        
        # Fix the code
        result = await fixer.fix_code(test_code)
        
        # Display the result
        print("Original code:")
        print(result.original_code)
        print("\nFixed code:")
        print(result.fixed_code)
        print("\nChanges:")
        for change in result.changes:
            print(f"- {change.description}: Line {change.start_line}, Col {change.start_column}")
        
        # Preview the changes
        print("\nDiff:")
        fixer.preview_changes(result.original_code, result.fixed_code)
    
    # Run the test
    asyncio.run(main())