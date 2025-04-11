#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
C# code fixer for CodeRefactor.
Implements interop with .NET Roslyn-based fixers.
"""

import os
import re
import sys
import json
import tempfile
import subprocess
import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple

# Import the base fixer
from fixers.base import BaseFixer, FixResult, FixChange, FixType

# Import claude_api for LLM-assisted fixes if available
try:
    from claude_api import ClaudeAPI, RefactorSuggestion
    HAS_LLM = True
except ImportError:
    HAS_LLM = False

# Check if Python for .NET is available for interop
try:
    import clr
    from System import Environment, AppDomain
    HAS_PYTHONNET = True
except ImportError:
    HAS_PYTHONNET = False


class CSharpFixer(BaseFixer):
    """
    Fixer for C# code.
    Uses Roslyn analyzers and code fixers when available,
    and falls back to regex-based fixes and LLM fixes.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the C# fixer.
        
        Args:
            config: Optional configuration dictionary with the following keys:
                - autoformat: Whether to automatically format code (default: True)
                - use_roslyn: Whether to use Roslyn analyzers (default: True)
                - use_regex_fixes: Whether to use regex-based fixes (default: True)
                - fix_style: Whether to fix style issues (default: True)
                - fix_bugs: Whether to fix bug issues (default: True)
                - use_llm: Whether to use LLM for complex fixes (default: True if available)
                - llm_config: Configuration for LLM integration
                - dotnet_path: Path to .NET SDK (optional)
        """
        super().__init__(config)
        
        # Extract config options
        self.autoformat = self.config.get('autoformat', True)
        self.use_roslyn = self.config.get('use_roslyn', True)
        self.use_regex_fixes = self.config.get('use_regex_fixes', True)
        self.fix_style = self.config.get('fix_style', True)
        self.fix_bugs = self.config.get('fix_bugs', True)
        self.use_llm = self.config.get('use_llm', HAS_LLM)
        self.dotnet_path = self.config.get('dotnet_path')
        
        # Initialize .NET interop if available
        self.roslyn_fixer = None
        if HAS_PYTHONNET and self.use_roslyn:
            try:
                self._init_roslyn_fixer()
            except Exception as e:
                self.logger.error(f"Failed to initialize Roslyn fixer: {str(e)}")
        
        # Initialize LLM if configured
        self.llm = None
        if self.use_llm and HAS_LLM:
            llm_config = self.config.get('llm_config', {})
            try:
                from claude_api import ClaudeAPI, LLMConfig
                api_key = llm_config.get('api_key') or os.environ.get("ANTHROPIC_API_KEY")
                
                if api_key:
                    config = LLMConfig(
                        api_key=api_key,
                        model=llm_config.get('model', "claude-3-7-sonnet-20250219"),
                        temperature=llm_config.get('temperature', 0.3)
                    )
                    self.llm = ClaudeAPI(config)
                    self.logger.info("Initialized LLM integration for complex fixes")
                else:
                    self.logger.warning("LLM integration enabled but no API key provided")
            except Exception as e:
                self.logger.error(f"Failed to initialize LLM integration: {str(e)}")
    
    def _init_roslyn_fixer(self):
        """Initialize the Roslyn fixer through .NET interop."""
        if not HAS_PYTHONNET:
            self.logger.warning("Python.NET not available, Roslyn fixer will not be used")
            return
        
        try:
            # Find the fixer assembly
            assembly_dir = os.path.join(os.path.dirname(__file__), "dotnet")
            assembly_path = os.path.join(assembly_dir, "CodeRefactor.CSharp.Fixer.dll")
            
            if not os.path.exists(assembly_path):
                # Try to build the assembly if not found
                self._build_roslyn_fixer(assembly_dir)
                
                if not os.path.exists(assembly_path):
                    self.logger.error(f"Roslyn fixer assembly not found: {assembly_path}")
                    return
            
            # Add assembly reference
            clr.AddReference(assembly_path)
            
            # Import .NET types
            from CodeRefactor.CSharp.Fixer import RoslynCodeFixer
            
            # Create fixer instance
            self.roslyn_fixer = RoslynCodeFixer()
            self.logger.info("Initialized Roslyn fixer")
            
        except Exception as e:
            self.logger.error(f"Error initializing Roslyn fixer: {str(e)}")
            self.roslyn_fixer = None
    
    def _build_roslyn_fixer(self, output_dir: str):
        """
        Build the Roslyn fixer .NET assembly.
        
        Args:
            output_dir: Output directory for the assembly.
        """
        try:
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Create a temporary project directory
            with tempfile.TemporaryDirectory() as temp_dir:
                # Project file content
                project_content = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net6.0</TargetFramework>
    <OutputType>Library</OutputType>
    <RootNamespace>CodeRefactor.CSharp.Fixer</RootNamespace>
    <AssemblyName>CodeRefactor.CSharp.Fixer</AssemblyName>
  </PropertyGroup>
  
  <ItemGroup>
    <PackageReference Include="Microsoft.CodeAnalysis.CSharp" Version="4.0.1" />
    <PackageReference Include="Microsoft.CodeAnalysis.CSharp.Workspaces" Version="4.0.1" />
  </ItemGroup>
</Project>
"""
                
                # C# class file content
                class_content = """using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Formatting;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using Microsoft.CodeAnalysis.Formatting;
using Microsoft.CodeAnalysis.Text;

namespace CodeRefactor.CSharp.Fixer
{
    /// <summary>
    /// Fix information for a code issue
    /// </summary>
    public class FixInfo
    {
        public string Id { get; set; } = Guid.NewGuid().ToString();
        public string Description { get; set; }
        public int StartLine { get; set; }
        public int StartColumn { get; set; }
        public int EndLine { get; set; }
        public int EndColumn { get; set; }
        public string OriginalText { get; set; }
        public string ReplacementText { get; set; }
        public string FixType { get; set; } = "Simple";
        public double Confidence { get; set; } = 1.0;
    }

    /// <summary>
    /// Result of fixing code issues
    /// </summary>
    public class FixResult
    {
        public string FilePath { get; set; }
        public bool Success { get; set; } = true;
        public string OriginalCode { get; set; }
        public string FixedCode { get; set; }
        public List<FixInfo> Changes { get; set; } = new List<FixInfo>();
        public string Error { get; set; }
        public List<string> Warnings { get; set; } = new List<string>();
    }

    /// <summary>
    /// Uses Roslyn to fix C# code issues
    /// </summary>
    public class RoslynCodeFixer
    {
        /// <summary>
        /// Fix issues in C# code
        /// </summary>
        public FixResult FixCode(string code, string filePath = null)
        {
            var result = new FixResult
            {
                FilePath = filePath ?? "",
                OriginalCode = code,
                FixedCode = code
            };

            try
            {
                // Parse the code
                var tree = CSharpSyntaxTree.ParseText(code);
                var root = tree.GetRoot();
                
                // Apply various fixes
                root = FixUnusedUsings(root, result);
                root = FixMissingBraces(root, result);
                root = FixInconsistentIndentation(root, result);
                
                // Format the code
                var workspace = new AdhocWorkspace();
                var formattedRoot = Formatter.Format(root, workspace);
                
                result.FixedCode = formattedRoot.ToFullString();
                result.Success = result.FixedCode != code || result.Changes.Count > 0;
            }
            catch (Exception ex)
            {
                result.Success = false;
                result.Error = ex.Message;
            }
            
            return result;
        }
        
        /// <summary>
        /// Fix unused using directives
        /// </summary>
        private SyntaxNode FixUnusedUsings(SyntaxNode root, FixResult result)
        {
            var usings = root.DescendantNodes().OfType<UsingDirectiveSyntax>().ToList();
            var referencedNamespaces = new HashSet<string>();
            
            // Collect all referenced namespaces
            foreach (var node in root.DescendantNodes())
            {
                if (node is IdentifierNameSyntax identifier)
                {
                    var name = identifier.Identifier.Text;
                    
                    // This is a simplistic approach - a more complete solution would
                    // need semantic analysis to determine actual namespace usage
                    foreach (var usingDirective in usings)
                    {
                        var ns = usingDirective.Name.ToString();
                        if (ns.EndsWith("." + name) || ns == name)
                        {
                            referencedNamespaces.Add(ns);
                        }
                    }
                }
            }
            
            // Remove unused usings
            var newRoot = root;
            foreach (var usingDirective in usings)
            {
                var ns = usingDirective.Name.ToString();
                if (!referencedNamespaces.Contains(ns))
                {
                    // Create a fix for this issue
                    var lineSpan = usingDirective.GetLocation().GetLineSpan();
                    var fix = new FixInfo
                    {
                        Description = $"Remove unused using directive: {ns}",
                        StartLine = lineSpan.StartLinePosition.Line + 1,
                        StartColumn = lineSpan.StartLinePosition.Character + 1,
                        EndLine = lineSpan.EndLinePosition.Line + 1,
                        EndColumn = lineSpan.EndLinePosition.Character + 1,
                        OriginalText = usingDirective.ToFullString(),
                        ReplacementText = "",
                        FixType = "Simple"
                    };
                    
                    result.Changes.Add(fix);
                    
                    // Remove the using directive
                    newRoot = newRoot.RemoveNode(usingDirective, SyntaxRemoveOptions.KeepNoTrivia);
                }
            }
            
            return newRoot;
        }
        
        /// <summary>
        /// Fix missing braces in control statements
        /// </summary>
        private SyntaxNode FixMissingBraces(SyntaxNode root, FixResult result)
        {
            var newRoot = root;
            
            // Find if statements without braces
            foreach (var ifStatement in root.DescendantNodes().OfType<IfStatementSyntax>())
            {
                if (!(ifStatement.Statement is BlockSyntax))
                {
                    // Create a fix for this issue
                    var statement = ifStatement.Statement;
                    var lineSpan = statement.GetLocation().GetLineSpan();
                    
                    var fix = new FixInfo
                    {
                        Description = "Add braces to if statement",
                        StartLine = lineSpan.StartLinePosition.Line + 1,
                        StartColumn = lineSpan.StartLinePosition.Character + 1,
                        EndLine = lineSpan.EndLinePosition.Line + 1,
                        EndColumn = lineSpan.EndLinePosition.Character + 1,
                        OriginalText = statement.ToFullString(),
                        ReplacementText = $"{{{Environment.NewLine}{statement.ToFullString()}}}{Environment.NewLine}",
                        FixType = "Simple"
                    };
                    
                    result.Changes.Add(fix);
                    
                    // Replace with block
                    var newStatement = SyntaxFactory.Block(statement);
                    newRoot = newRoot.ReplaceNode(statement, newStatement);
                }
            }
            
            // Find for statements without braces
            foreach (var forStatement in root.DescendantNodes().OfType<ForStatementSyntax>())
            {
                if (!(forStatement.Statement is BlockSyntax))
                {
                    // Create a fix for this issue
                    var statement = forStatement.Statement;
                    var lineSpan = statement.GetLocation().GetLineSpan();
                    
                    var fix = new FixInfo
                    {
                        Description = "Add braces to for statement",
                        StartLine = lineSpan.StartLinePosition.Line + 1,
                        StartColumn = lineSpan.StartLinePosition.Character + 1,
                        EndLine = lineSpan.EndLinePosition.Line + 1,
                        EndColumn = lineSpan.EndLinePosition.Character + 1,
                        OriginalText = statement.ToFullString(),
                        ReplacementText = $"{{{Environment.NewLine}{statement.ToFullString()}}}{Environment.NewLine}",
                        FixType = "Simple"
                    };
                    
                    result.Changes.Add(fix);
                    
                    // Replace with block
                    var newStatement = SyntaxFactory.Block(statement);
                    newRoot = newRoot.ReplaceNode(statement, newStatement);
                }
            }
            
            // Handle while, foreach, etc. similarly
            
            return newRoot;
        }
        
        /// <summary>
        /// Fix inconsistent indentation
        /// </summary>
        private SyntaxNode FixInconsistentIndentation(SyntaxNode root, FixResult result)
        {
            // This is harder to do with the Roslyn API directly
            // The Formatter.Format call in the main method will handle this
            return root;
        }
    }
}
"""
                
                # Write files
                project_file = os.path.join(temp_dir, "CodeRefactor.CSharp.Fixer.csproj")
                with open(project_file, "w", encoding="utf-8") as f:
                    f.write(project_content)
                
                src_dir = os.path.join(temp_dir, "src")
                os.makedirs(src_dir, exist_ok=True)
                
                class_file = os.path.join(src_dir, "RoslynCodeFixer.cs")
                with open(class_file, "w", encoding="utf-8") as f:
                    f.write(class_content)
                
                # Build the project
                dotnet_cmd = "dotnet"
                if self.dotnet_path:
                    dotnet_cmd = os.path.join(self.dotnet_path, "dotnet")
                
                self.logger.info(f"Building Roslyn fixer assembly...")
                
                # Check if dotnet is available
                try:
                    subprocess.run([dotnet_cmd, "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                except (subprocess.SubprocessError, FileNotFoundError):
                    self.logger.error("dotnet command not found. Please install .NET SDK or set dotnet_path in the configuration.")
                    return
                
                # Build the project
                build_cmd = [dotnet_cmd, "build", "-c", "Release", "-o", output_dir]
                build_result = subprocess.run(
                    build_cmd, 
                    cwd=temp_dir,
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False
                )
                
                if build_result.returncode != 0:
                    self.logger.error(f"Failed to build Roslyn fixer: {build_result.stderr}")
                else:
                    self.logger.info(f"Successfully built Roslyn fixer")
                
        except Exception as e:
            self.logger.error(f"Error building Roslyn fixer: {str(e)}")
    
    async def fix_code(self, code: str, file_path: Optional[str] = None, 
                      issues: Optional[List[Dict[str, Any]]] = None) -> FixResult:
        """
        Fix issues in C# code.
        
        Args:
            code: The C# code to fix.
            file_path: Optional path to the file (for reference).
            issues: Optional list of issues to fix. If None, all fixable issues will be addressed.
        
        Returns:
            FixResult containing the original and fixed code, along with details of changes made.
        """
        # Initialize the result
        result = FixResult(
            file_path=file_path or "",
            original_code=code,
            fixed_code=code,
            success=False
        )
        
        # Skip if the code is empty
        if not code.strip():
            result.warnings.append("Empty code provided, nothing to fix")
            return result
        
        # 1. Try Roslyn fixer first if available
        roslyn_changes = []
        roslyn_fixed_code = code
        
        if self.roslyn_fixer:
            try:
                # Call the Roslyn fixer
                roslyn_result = self.roslyn_fixer.FixCode(code, file_path)
                
                # Extract results
                if roslyn_result.Success:
                    roslyn_fixed_code = roslyn_result.FixedCode
                    
                    # Convert .NET FixInfo objects to our FixChange objects
                    for fix_info in roslyn_result.Changes:
                        change = FixChange(
                            id=fix_info.Id,
                            description=fix_info.Description,
                            start_line=fix_info.StartLine,
                            start_column=fix_info.StartColumn,
                            end_line=fix_info.EndLine,
                            end_column=fix_info.EndColumn,
                            original_text=fix_info.OriginalText,
                            replacement_text=fix_info.ReplacementText,
                            fix_type=getattr(FixType, fix_info.FixType.upper()),
                            confidence=fix_info.Confidence
                        )
                        roslyn_changes.append(change)
                    
                    # Add any warnings
                    for warning in roslyn_result.Warnings:
                        result.warnings.append(warning)
                
                else:
                    result.warnings.append(f"Roslyn fixer error: {roslyn_result.Error}")
            
            except Exception as e:
                self.logger.error(f"Error using Roslyn fixer: {str(e)}")
                result.warnings.append(f"Failed to use Roslyn fixer: {str(e)}")
        
        # Apply fixes in sequence
        modified_code = code
        changes = []
        
        # 2. Apply Roslyn fixes if successful
        if roslyn_changes and roslyn_fixed_code != code:
            modified_code = roslyn_fixed_code
            changes.extend(roslyn_changes)
        
        # 3. Fix specific issues if provided
        if issues:
            issue_fixes = await self._fix_specific_issues(modified_code, issues, file_path)
            if issue_fixes:
                # Apply the changes
                for change in issue_fixes:
                    changes.append(change)
                modified_code = self.apply_changes(modified_code, issue_fixes)
        
        # 4. Apply regex-based fixes if enabled
        if self.use_regex_fixes:
            # Fix style issues
            if self.fix_style:
                style_fixes = self._fix_style_issues(modified_code)
                if style_fixes:
                    # Apply the changes
                    for change in style_fixes:
                        changes.append(change)
                    modified_code = self.apply_changes(modified_code, style_fixes)
            
            # Fix bug issues
            if self.fix_bugs:
                bug_fixes = self._fix_bug_issues(modified_code)
                if bug_fixes:
                    # Apply the changes
                    for change in bug_fixes:
                        changes.append(change)
                    modified_code = self.apply_changes(modified_code, bug_fixes)
        
        # 5. Auto-format the code if Roslyn formatter didn't run
        if self.autoformat and not self.roslyn_fixer:
            formatted_code, format_changes = await self._format_code(modified_code, file_path)
            if formatted_code != modified_code:
                # Record the formatting as a single change
                changes.extend(format_changes)
                modified_code = formatted_code
        
        # Update the result
        result.fixed_code = modified_code
        result.changes = changes
        result.success = modified_code != code or bool(changes)
        
        return result
    
    async def get_fix_suggestions(self, code: str, issue: Dict[str, Any], 
                                file_path: Optional[str] = None) -> List[FixChange]:
        """
        Get suggestions for fixing a specific issue.
        
        Args:
            code: The C# code containing the issue.
            issue: The issue to fix.
            file_path: Optional path to the file (for reference).
        
        Returns:
            List of FixChange objects with suggestions.
        """
        suggestions = []
        
        # Check if the issue is fixable
        if not issue.get('fixable', False):
            return suggestions
        
        rule_id = issue.get('rule_id', '')
        message = issue.get('message', '')
        line = issue.get('line', 0)
        column = issue.get('column', 0)
        
        # Try specific fixers based on rule_id or message
        if "CS0168" in rule_id or "is declared but never used" in message:
            # Unused local variable
            changes = self._fix_unused_variable(code, line, column, message)
            suggestions.extend(changes)
        
        elif "CS0219" in rule_id or "is assigned but its value is never used" in message:
            # Assigned but unused variable
            changes = self._fix_unused_assigned_variable(code, line, column, message)
            suggestions.extend(changes)
        
        elif "CS0649" in rule_id or "is never assigned to" in message:
            # Field is never assigned
            changes = self._fix_unassigned_field(code, line, column, message)
            suggestions.extend(changes)
        
        elif "IDE0003" in rule_id or "Name can be simplified" in message:
            # Name can be simplified
            changes = self._fix_name_simplification(code, line, column, message)
            suggestions.extend(changes)
        
        elif "IDE0051" in rule_id or "Private member is unused" in message:
            # Unused private member
            changes = self._fix_unused_member(code, line, column, message)
            suggestions.extend(changes)
        
        elif "IDE0060" in rule_id or "unused parameter" in message:
            # Unused parameter
            changes = self._fix_unused_parameter(code, line, column, message)
            suggestions.extend(changes)
        
        # If no specific fixer found, try LLM
        if not suggestions and self.llm:
            changes = await self._get_llm_suggestions(code, issue, file_path)
            suggestions.extend(changes)
        
        return suggestions
    
    async def _fix_specific_issues(self, code: str, issues: List[Dict[str, Any]], 
                                 file_path: Optional[str] = None) -> List[FixChange]:
        """
        Fix specific issues identified by the analyzer.
        
        Args:
            code: The C# code to fix.
            issues: List of issues to fix.
            file_path: Optional path to the file (for reference).
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Group issues by fixability to prioritize simple fixes first
        fixable_issues = []
        llm_issues = []
        
        for issue in issues:
            if issue.get('fixable', False):
                fix_type = issue.get('fix_type', '')
                if fix_type == 'llm-assisted':
                    llm_issues.append(issue)
                else:
                    fixable_issues.append(issue)
        
        # Process fixable issues first
        for issue in fixable_issues:
            # Get suggestions for fixing this issue
            suggestions = await self.get_fix_suggestions(code, issue, file_path)
            changes.extend(suggestions)
        
        # Then process LLM-assisted issues if LLM is available
        if self.llm and llm_issues:
            for issue in llm_issues:
                suggestions = await self.get_fix_suggestions(code, issue, file_path)
                changes.extend(suggestions)
        
        return changes
    
    def _fix_style_issues(self, code: str) -> List[FixChange]:
        """
        Fix common C# style issues using regex.
        
        Args:
            code: The C# code to fix.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Fix trailing whitespace
        changes.extend(self._fix_trailing_whitespace(code))
        
        # Fix missing braces in control statements
        changes.extend(self._fix_missing_braces(code))
        
        # Fix inconsistent naming (camelCase for local variables, PascalCase for methods, etc.)
        changes.extend(self._fix_inconsistent_naming(code))
        
        # Fix unnecessary using directives
        changes.extend(self._fix_unnecessary_usings(code))
        
        return changes
    
    def _fix_bug_issues(self, code: str) -> List[FixChange]:
        """
        Fix common C# bug issues using regex.
        
        Args:
            code: The C# code to fix.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Fix potential null reference exceptions
        changes.extend(self._fix_null_references(code))
        
        # Fix non-nullable variables that might be null
        changes.extend(self._fix_non_nullable_nulls(code))
        
        # Fix missing null checks in method parameters
        changes.extend(self._fix_missing_null_checks(code))
        
        # Fix potential integer division issues
        changes.extend(self._fix_integer_division(code))
        
        return changes
    
    async def _format_code(self, code: str, file_path: Optional[str] = None) -> Tuple[str, List[FixChange]]:
        """
        Format C# code using dotnet format.
        
        Args:
            code: The C# code to format.
            file_path: Optional path to the file (for reference).
        
        Returns:
            Tuple of (formatted_code, changes).
        """
        changes = []
        formatted_code = code
        
        try:
            # Write code to a temporary file
            with tempfile.NamedTemporaryFile(suffix='.cs', delete=False) as temp_file:
                temp_path = temp_file.name
                temp_file.write(code.encode('utf-8'))
            
            try:
                # Find dotnet command
                dotnet_cmd = "dotnet"
                if self.dotnet_path:
                    dotnet_cmd = os.path.join(self.dotnet_path, "dotnet")
                
                # Run dotnet format
                try:
                    # First check if dotnet format is available
                    subprocess.run([dotnet_cmd, "format", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
                    
                    # Run the format command
                    result = subprocess.run(
                        [dotnet_cmd, "format", "--include", temp_path, "--verify-no-changes", "--verbosity", "minimal"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        check=False
                    )
                    
                    # If the file was formatted, read it back
                    with open(temp_path, 'r', encoding='utf-8') as f:
                        new_code = f.read()
                    
                    if new_code != code:
                        formatted_code = new_code
                        
                        # Create a formatting change for the whole file
                        change = FixChange(
                            description="Format C# code",
                            start_line=1,
                            start_column=1,
                            end_line=len(code.splitlines()) + 1,
                            end_column=1,
                            original_text=code,
                            replacement_text=formatted_code,
                            fix_type=FixType.SIMPLE
                        )
                        changes.append(change)
                
                except (subprocess.SubprocessError, FileNotFoundError):
                    self.logger.warning("dotnet format command not available, using fallback formatting")
                    
                    # Apply simpler formatting (just fix indentation and whitespace)
                    formatted_code = self._format_code_fallback(code)
                    
                    if formatted_code != code:
                        # Create a formatting change for the whole file
                        change = FixChange(
                            description="Format C# code (basic formatting)",
                            start_line=1,
                            start_column=1,
                            end_line=len(code.splitlines()) + 1,
                            end_column=1,
                            original_text=code,
                            replacement_text=formatted_code,
                            fix_type=FixType.SIMPLE
                        )
                        changes.append(change)
            
            finally:
                # Clean up the temporary file
                os.unlink(temp_path)
        
        except Exception as e:
            self.logger.warning(f"Error formatting C# code: {str(e)}")
        
        return formatted_code, changes
    
    def _format_code_fallback(self, code: str) -> str:
        """
        Simple fallback formatting for C# code.
        
        Args:
            code: The C# code to format.
        
        Returns:
            The formatted code.
        """
        lines = code.splitlines()
        result = []
        indent_level = 0
        indent_size = 4
        
        for line in lines:
            # Adjust indentation based on braces
            stripped = line.strip()
            
            # Handle empty lines
            if not stripped:
                result.append('')
                continue
            
            # Check if line ends a block
            if stripped.startswith('}'):
                indent_level = max(0, indent_level - 1)
            
            # Add properly indented line
            result.append(' ' * (indent_level * indent_size) + stripped)
            
            # Check if line starts a new block
            if stripped.endswith('{'):
                indent_level += 1
        
        return '\n'.join(result)
    
    def _fix_trailing_whitespace(self, code: str) -> List[FixChange]:
        """
        Fix trailing whitespace in code.
        
        Args:
            code: The code to fix.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        lines = code.splitlines(True)  # Keep line endings
        
        for i, line in enumerate(lines):
            stripped = line.rstrip('\r\n')
            
            if stripped and stripped.rstrip() != stripped:
                # Line has trailing whitespace
                fixed_line = stripped.rstrip()
                if line.endswith('\r\n'):
                    fixed_line += '\r\n'
                elif line.endswith('\n'):
                    fixed_line += '\n'
                
                change = FixChange(
                    description="Remove trailing whitespace",
                    start_line=i + 1,
                    start_column=1,
                    end_line=i + 1,
                    end_column=len(line) + 1,
                    original_text=line,
                    replacement_text=fixed_line,
                    fix_type=FixType.SIMPLE
                )
                changes.append(change)
        
        return changes
    
    def _fix_missing_braces(self, code: str) -> List[FixChange]:
        """
        Fix missing braces in control statements (if, for, while, etc.).
        
        Args:
            code: The C# code to fix.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Regular expressions for control statements without braces
        patterns = [
            # if statement without braces
            (r'(if\s*\(.*?\))\s*([^{;].*?;)', r'\1 {\n\2\n}'),
            # for statement without braces
            (r'(for\s*\(.*?\))\s*([^{;].*?;)', r'\1 {\n\2\n}'),
            # while statement without braces
            (r'(while\s*\(.*?\))\s*([^{;].*?;)', r'\1 {\n\2\n}'),
            # foreach statement without braces
            (r'(foreach\s*\(.*?\))\s*([^{;].*?;)', r'\1 {\n\2\n}'),
        ]
        
        lines = code.splitlines()
        
        # Process each line
        for i, line in enumerate(lines):
            for pattern, replacement_template in patterns:
                match = re.search(pattern, line)
                if match:
                    control_stmt = match.group(1)
                    body_stmt = match.group(2)
                    
                    # Calculate indentation
                    indent_match = re.match(r'^(\s*)', line)
                    indent = indent_match.group(1) if indent_match else ""
                    body_indent = indent + "    "  # 4 spaces
                    
                    # Create replacement text with proper indentation
                    replacement = (f"{control_stmt} {{\n"
                                   f"{body_indent}{body_stmt}\n"
                                   f"{indent}}}")
                    
                    change = FixChange(
                        description=f"Add braces to {control_stmt.split('(')[0].strip()} statement",
                        start_line=i + 1,
                        start_column=match.start() + 1,
                        end_line=i + 1,
                        end_column=match.end() + 1,
                        original_text=match.group(0),
                        replacement_text=replacement,
                        fix_type=FixType.SIMPLE
                    )
                    changes.append(change)
        
        return changes
    
    def _fix_inconsistent_naming(self, code: str) -> List[FixChange]:
        """
        Fix inconsistent naming conventions in C# code.
        
        Args:
            code: The C# code to fix.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Fix local variables that don't use camelCase
        local_var_pattern = r'((?:var|int|string|bool|float|double|decimal|char|byte|short|long|object)\s+)([A-Z][a-zA-Z0-9]*)(\s*[=;])'
        lines = code.splitlines()
        
        for i, line in enumerate(lines):
            for match in re.finditer(local_var_pattern, line):
                var_type = match.group(1)
                var_name = match.group(2)
                suffix = match.group(3)
                
                # Convert to camelCase
                camel_case = var_name[0].lower() + var_name[1:]
                
                # Skip if already camelCase or it's a special case
                if var_name == camel_case or var_name.startswith('I') and len(var_name) > 1 and var_name[1].isupper():
                    continue
                
                change = FixChange(
                    description=f"Convert variable name to camelCase: {var_name} -> {camel_case}",
                    start_line=i + 1,
                    start_column=match.start(2) + 1,
                    end_line=i + 1,
                    end_column=match.end(2) + 1,
                    original_text=var_name,
                    replacement_text=camel_case,
                    fix_type=FixType.SIMPLE
                )
                changes.append(change)
        
        # Fix methods that don't use PascalCase
        method_pattern = r'((?:public|private|protected|internal|static)\s+(?:void|[a-zA-Z0-9<>[\]]+)\s+)([a-z][a-zA-Z0-9]*)(\s*\()'
        
        for i, line in enumerate(lines):
            for match in re.finditer(method_pattern, line):
                method_prefix = match.group(1)
                method_name = match.group(2)
                suffix = match.group(3)
                
                # Convert to PascalCase
                pascal_case = method_name[0].upper() + method_name[1:]
                
                # Skip if already PascalCase
                if method_name == pascal_case:
                    continue
                
                change = FixChange(
                    description=f"Convert method name to PascalCase: {method_name} -> {pascal_case}",
                    start_line=i + 1,
                    start_column=match.start(2) + 1,
                    end_line=i + 1,
                    end_column=match.end(2) + 1,
                    original_text=method_name,
                    replacement_text=pascal_case,
                    fix_type=FixType.SIMPLE
                )
                changes.append(change)
        
        return changes
    
    def _fix_unnecessary_usings(self, code: str) -> List[FixChange]:
        """
        Fix unnecessary using directives in C# code.
        
        Args:
            code: The C# code to fix.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # List of common unnecessary namespaces
        unnecessary = [
            "System.Collections",  # if System.Collections.Generic is also imported
            "System.Text",  # if only used for basic string operations
            "System.IO",  # if not using file operations
        ]
        
        lines = code.splitlines()
        
        # Find all using directives
        using_lines = []
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith("using ") and line.endswith(";"):
                using_lines.append((i, line))
        
        # Find duplicate or unnecessary usings
        seen_namespaces = set()
        
        for i, line in using_lines:
            # Extract namespace
            namespace = line[6:].strip().rstrip(';')
            
            # Check for duplicates
            if namespace in seen_namespaces:
                change = FixChange(
                    description=f"Remove duplicate using directive: {namespace}",
                    start_line=i + 1,
                    start_column=1,
                    end_line=i + 1,
                    end_column=len(lines[i]) + 1,
                    original_text=lines[i],
                    replacement_text="",  # Remove the line
                    fix_type=FixType.SIMPLE
                )
                changes.append(change)
                continue
            
            seen_namespaces.add(namespace)
            
            # Check for unnecessary namespaces
            for un in unnecessary:
                if namespace == un:
                    # Check if a more specific namespace is also included
                    has_specific = False
                    if namespace == "System.Collections":
                        has_specific = "System.Collections.Generic" in seen_namespaces
                    
                    if has_specific:
                        change = FixChange(
                            description=f"Remove unnecessary using directive: {namespace}",
                            start_line=i + 1,
                            start_column=1,
                            end_line=i + 1,
                            end_column=len(lines[i]) + 1,
                            original_text=lines[i],
                            replacement_text="",  # Remove the line
                            fix_type=FixType.SIMPLE
                        )
                        changes.append(change)
                        break
        
        return changes
    
    def _fix_null_references(self, code: str) -> List[FixChange]:
        """
        Fix potential null reference exceptions in C# code.
        
        Args:
            code: The C# code to fix.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Find potential null references (accessing properties or methods without null check)
        lines = code.splitlines()
        
        # Pattern for variable.Method() or variable.Property without null check
        ref_pattern = r'(\b[a-zA-Z][a-zA-Z0-9]*)(\.)[a-zA-Z][a-zA-Z0-9]*\b(?:\(|[^(.])'
        
        for i, line in enumerate(lines):
            # Skip lines with null checks
            if "null" in line or "?" in line:
                continue
            
            # Skip comment lines
            if line.strip().startswith("//") or line.strip().startswith("/*"):
                continue
            
            for match in re.finditer(ref_pattern, line):
                var_name = match.group(1)
                
                # Skip primitive types and common non-null variables
                if var_name in ["int", "string", "bool", "char", "double", "float",
                               "this", "base", "var", "Math", "Console", "System",
                               "StringBuilder", "List", "Dictionary"]:
                    continue
                
                # Check surrounding lines for null checks
                has_null_check = False
                start_check = max(0, i - 3)  # Check 3 lines before
                end_check = min(len(lines), i + 3)  # Check 3 lines after
                
                for j in range(start_check, end_check):
                    if j == i:
                        continue
                    
                    check_line = lines[j]
                    if f"{var_name} != null" in check_line or f"{var_name}?" in check_line:
                        has_null_check = True
                        break
                
                if not has_null_check:
                    # Suggest adding a null check
                    if "?." in line:
                        # Already using null conditional operator in the line
                        change = FixChange(
                            description=f"Use null conditional operator for '{var_name}'",
                            start_line=i + 1,
                            start_column=match.start(2) + 1,
                            end_line=i + 1,
                            end_column=match.end(2) + 1,
                            original_text=".",
                            replacement_text="?.",
                            fix_type=FixType.SIMPLE,
                            confidence=0.7
                        )
                        changes.append(change)
                    else:
                        # Add a null check before the line
                        indent_match = re.match(r'^(\s*)', line)
                        indent = indent_match.group(1) if indent_match else ""
                        
                        null_check = f"{indent}if ({var_name} != null)\n{indent}{{\n"
                        indented_line = f"{indent}    {line.strip()}\n"
                        closing_brace = f"{indent}}}\n"
                        
                        change = FixChange(
                            description=f"Add null check for '{var_name}'",
                            start_line=i + 1,
                            start_column=1,
                            end_line=i + 1,
                            end_column=len(line) + 1,
                            original_text=line,
                            replacement_text=null_check + indented_line + closing_brace,
                            fix_type=FixType.COMPLEX,
                            confidence=0.6
                        )
                        changes.append(change)
        
        return changes
    
    def _fix_non_nullable_nulls(self, code: str) -> List[FixChange]:
        """
        Fix non-nullable variables that might be null in C# code.
        
        Args:
            code: The C# code to fix.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Find assignments of null to non-nullable types
        lines = code.splitlines()
        
        # Pattern for reference type declarations without '?'
        type_pattern = r'(\b(?:string|object|[A-Z][a-zA-Z0-9<>[\]]+)\b)(\s+[a-zA-Z][a-zA-Z0-9]*)(\s*=\s*null\s*;)'
        
        for i, line in enumerate(lines):
            for match in re.finditer(type_pattern, line):
                type_name = match.group(1)
                var_decl = match.group(2)
                null_assign = match.group(3)
                
                # Skip if in C# 8 or higher nullable context
                # (assuming there's a '#nullable enable' directive)
                if '#nullable enable' in '\n'.join(lines[:i]):
                    continue
                
                # Suggest making the type nullable
                change = FixChange(
                    description=f"Make {type_name} nullable with '?' since it's assigned null",
                    start_line=i + 1,
                    start_column=match.end(1) + 1,
                    end_line=i + 1,
                    end_column=match.end(1) + 1,
                    original_text="",
                    replacement_text="?",
                    fix_type=FixType.SIMPLE
                )
                changes.append(change)
        
        return changes
    
    def _fix_missing_null_checks(self, code: str) -> List[FixChange]:
        """
        Fix missing null checks in method parameters.
        
        Args:
            code: The C# code to fix.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Find method parameters that should be null-checked
        lines = code.splitlines()
        
        # Pattern for method declarations with reference type parameters
        method_pattern = r'(public|private|protected|internal)\s+([a-zA-Z0-9<>[\]]+)\s+([a-zA-Z][a-zA-Z0-9]*)\s*\((.*?)\)'
        
        for i, line in enumerate(lines):
            match = re.search(method_pattern, line)
            if not match:
                continue
            
            access = match.group(1)
            return_type = match.group(2)
            method_name = match.group(3)
            params_str = match.group(4)
            
            # Extract parameters
            params = []
            for param in params_str.split(','):
                param = param.strip()
                if not param:
                    continue
                
                # Extract type and name
                parts = param.split()
                if len(parts) >= 2:
                    param_type = parts[0]
                    param_name = parts[1]
                    
                    # Check if it's a reference type that should be null-checked
                    if param_type in ["string", "object"] or (param_type[0].isupper() and param_type not in ["int", "bool", "long", "double", "float", "decimal"]):
                        params.append((param_type, param_name))
            
            # Check method body for null checks
            if not params:
                continue
            
            # Find the opening brace of the method
            method_body_start = i
            for j in range(i, min(i + 5, len(lines))):
                if '{' in lines[j]:
                    method_body_start = j
                    break
            
            # Check if there's a null check for each parameter
            method_body = '\n'.join(lines[method_body_start+1:method_body_start+10])  # Check first 10 lines of method
            
            for param_type, param_name in params:
                if f"if ({param_name} == null)" in method_body or f"if (null == {param_name})" in method_body or f"{param_name}?." in method_body:
                    continue
                
                # Add null check for the parameter
                indent = re.match(r'^(\s*)', lines[method_body_start+1]).group(1) if method_body_start+1 < len(lines) else "    "
                
                if "#nullable enable" in '\n'.join(lines[:i]):
                    # In nullable context, suggest adding ? to the parameter type
                    for idx, param in enumerate(params_str.split(',')):
                        if param_name in param:
                            # Make the parameter nullable
                            new_param = param.replace(param_type, f"{param_type}?")
                            new_params = params_str.split(',')
                            new_params[idx] = new_param
                            
                            change = FixChange(
                                description=f"Make parameter '{param_name}' nullable with '?'",
                                start_line=i + 1,
                                start_column=match.start(4) + 1,
                                end_line=i + 1,
                                end_column=match.end(4) + 1,
                                original_text=params_str,
                                replacement_text=','.join(new_params),
                                fix_type=FixType.SIMPLE
                            )
                            changes.append(change)
                            break
                else:
                    # Add a null check at the beginning of the method
                    null_check = f"{indent}if ({param_name} == null)\n{indent}{{\n{indent}    throw new ArgumentNullException(nameof({param_name}));\n{indent}}}\n\n"
                    
                    change = FixChange(
                        description=f"Add null check for parameter '{param_name}'",
                        start_line=method_body_start + 2,
                        start_column=1,
                        end_line=method_body_start + 2,
                        end_column=1,
                        original_text="",
                        replacement_text=null_check,
                        fix_type=FixType.SIMPLE
                    )
                    changes.append(change)
        
        return changes
    
    def _fix_integer_division(self, code: str) -> List[FixChange]:
        """
        Fix potential integer division issues in C# code.
        
        Args:
            code: The C# code to fix.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Find integer division that might lead to unexpected results
        lines = code.splitlines()
        
        # Pattern for integer division assigned to floating-point types
        div_pattern = r'((?:float|double|decimal)\s+[a-zA-Z][a-zA-Z0-9]*\s*=\s*)([a-zA-Z0-9]+\s*/\s*[a-zA-Z0-9]+)'
        
        for i, line in enumerate(lines):
            for match in re.finditer(div_pattern, line):
                float_assign = match.group(1)
                int_div = match.group(2)
                
                # Suggest explicit casting to float/double
                parts = int_div.split('/')
                if len(parts) == 2:
                    left = parts[0].strip()
                    right = parts[1].strip()
                    
                    change = FixChange(
                        description="Convert to floating-point division to avoid integer truncation",
                        start_line=i + 1,
                        start_column=match.start(2) + 1,
                        end_line=i + 1,
                        end_column=match.end(2) + 1,
                        original_text=int_div,
                        replacement_text=f"((double){left} / {right})",
                        fix_type=FixType.SIMPLE
                    )
                    changes.append(change)
        
        return changes
    
    def _fix_unused_variable(self, code: str, line: int, column: int, message: str) -> List[FixChange]:
        """
        Fix an unused variable issue.
        
        Args:
            code: The C# code.
            line: Line number of the issue.
            column: Column number of the issue.
            message: The error message.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Extract the variable name from the message
        var_match = re.search(r'\'([a-zA-Z0-9_]+)\'', message)
        if not var_match:
            return changes
        
        var_name = var_match.group(1)
        
        # Get the line of code
        lines = code.splitlines()
        if 0 < line <= len(lines):
            code_line = lines[line - 1]
            
            # Find the variable declaration
            var_match = re.search(fr'\b(\w+)\s+{re.escape(var_name)}\b', code_line)
            if var_match:
                # Two options: comment out the line or prefix with underscore
                comment_fix = FixChange(
                    description=f"Comment out unused variable '{var_name}'",
                    start_line=line,
                    start_column=1,
                    end_line=line,
                    end_column=len(code_line) + 1,
                    original_text=code_line,
                    replacement_text=f"// {code_line}  // Unused variable",
                    fix_type=FixType.SIMPLE,
                    confidence=0.8
                )
                changes.append(comment_fix)
                
                # Prefix with underscore
                if not var_name.startswith('_'):
                    # Find the variable name in the line
                    for match in re.finditer(fr'\b{re.escape(var_name)}\b', code_line):
                        # Check if this is the declaration (not part of the type)
                        if match.start() > var_match.end():
                            underscore_fix = FixChange(
                                description=f"Prefix unused variable '{var_name}' with underscore",
                                start_line=line,
                                start_column=match.start() + 1,
                                end_line=line,
                                end_column=match.end() + 1,
                                original_text=var_name,
                                replacement_text=f"_{var_name}",
                                fix_type=FixType.SIMPLE,
                                confidence=0.9
                            )
                            changes.append(underscore_fix)
                            break
        
        return changes
    
    def _fix_unused_assigned_variable(self, code: str, line: int, column: int, message: str) -> List[FixChange]:
        """
        Fix an unused assigned variable issue.
        
        Args:
            code: The C# code.
            line: Line number of the issue.
            column: Column number of the issue.
            message: The error message.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Extract the variable name from the message
        var_match = re.search(r'\'([a-zA-Z0-9_]+)\'', message)
        if not var_match:
            return changes
        
        var_name = var_match.group(1)
        
        # Get the line of code
        lines = code.splitlines()
        if 0 < line <= len(lines):
            code_line = lines[line - 1]
            
            # Find the variable assignment
            assignment_match = re.search(fr'\b{re.escape(var_name)}\s*=\s*([^;]+);', code_line)
            if assignment_match:
                # Remove the assignment but keep the expression for side effects
                expression = assignment_match.group(1).strip()
                
                # If the expression has potential side effects, keep it
                if '(' in expression or '.' in expression:
                    start_pos = assignment_match.start()
                    eq_pos = code_line.find('=', start_pos)
                    
                    if eq_pos > 0:
                        before = code_line[:start_pos]
                        after = code_line[eq_pos + 1:]
                        
                        change = FixChange(
                            description=f"Remove unused assignment to '{var_name}' but keep expression for side effects",
                            start_line=line,
                            start_column=1,
                            end_line=line,
                            end_column=len(code_line) + 1,
                            original_text=code_line,
                            replacement_text=f"{before}/* {var_name} = */{after}",
                            fix_type=FixType.SIMPLE
                        )
                        changes.append(change)
                else:
                    # Comment out the line if the expression has no side effects
                    change = FixChange(
                        description=f"Comment out unused assignment to '{var_name}'",
                        start_line=line,
                        start_column=1,
                        end_line=line,
                        end_column=len(code_line) + 1,
                        original_text=code_line,
                        replacement_text=f"// {code_line}  // Unused assignment",
                        fix_type=FixType.SIMPLE
                    )
                    changes.append(change)
        
        return changes
    
    def _fix_unassigned_field(self, code: str, line: int, column: int, message: str) -> List[FixChange]:
        """
        Fix an unassigned field issue.
        
        Args:
            code: The C# code.
            line: Line number of the issue.
            column: Column number of the issue.
            message: The error message.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Extract the field name from the message
        field_match = re.search(r'\'([a-zA-Z0-9_]+)\'', message)
        if not field_match:
            return changes
        
        field_name = field_match.group(1)
        
        # Get the line of code
        lines = code.splitlines()
        if 0 < line <= len(lines):
            code_line = lines[line - 1]
            
            # Find the field declaration
            field_match = re.search(fr'(private|protected|internal|public)\s+(\w+)\s+{re.escape(field_name)}\s*;', code_line)
            if field_match:
                field_type = field_match.group(2)
                
                # Determine default value based on type
                default_value = "null"
                if field_type in ["int", "long", "byte", "short"]:
                    default_value = "0"
                elif field_type in ["float", "double", "decimal"]:
                    default_value = "0.0"
                elif field_type == "bool":
                    default_value = "false"
                elif field_type == "char":
                    default_value = "' '"
                
                # Add assignment to default value
                semicolon_pos = code_line.rfind(';')
                if semicolon_pos > 0:
                    change = FixChange(
                        description=f"Initialize field '{field_name}' with default value",
                        start_line=line,
                        start_column=semicolon_pos + 1,
                        end_line=line,
                        end_column=semicolon_pos + 1,
                        original_text="",
                        replacement_text=f" = {default_value}",
                        fix_type=FixType.SIMPLE
                    )
                    changes.append(change)
        
        return changes
    
    def _fix_name_simplification(self, code: str, line: int, column: int, message: str) -> List[FixChange]:
        """
        Fix name simplification issue (e.g., use 'var' for obvious types).
        
        Args:
            code: The C# code.
            line: Line number of the issue.
            column: Column number of the issue.
            message: The error message.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Get the line of code
        lines = code.splitlines()
        if 0 < line <= len(lines):
            code_line = lines[line - 1]
            
            # Check for explicit type that could be 'var'
            type_match = re.search(r'(\w+)\s+(\w+)\s*=\s*new\s+\1', code_line)
            if type_match:
                explicit_type = type_match.group(1)
                var_name = type_match.group(2)
                
                change = FixChange(
                    description=f"Simplify declaration using 'var' for '{var_name}'",
                    start_line=line,
                    start_column=type_match.start(1) + 1,
                    end_line=line,
                    end_column=type_match.end(1) + 1,
                    original_text=explicit_type,
                    replacement_text="var",
                    fix_type=FixType.SIMPLE
                )
                changes.append(change)
        
        return changes
    
    def _fix_unused_member(self, code: str, line: int, column: int, message: str) -> List[FixChange]:
        """
        Fix unused private member issue.
        
        Args:
            code: The C# code.
            line: Line number of the issue.
            column: Column number of the issue.
            message: The error message.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Extract the member name from the message
        member_match = re.search(r'\'([a-zA-Z0-9_]+)\'', message)
        if not member_match:
            return changes
        
        member_name = member_match.group(1)
        
        # Get the line of code
        lines = code.splitlines()
        if 0 < line <= len(lines):
            code_line = lines[line - 1]
            
            # Check if it's a field or method
            if "(" in code_line:
                # It's a method, comment it out
                change = FixChange(
                    description=f"Comment out unused private method '{member_name}'",
                    start_line=line,
                    start_column=1,
                    end_line=line,
                    end_column=len(code_line) + 1,
                    original_text=code_line,
                    replacement_text=f"// {code_line}  // Unused method",
                    fix_type=FixType.SIMPLE
                )
                changes.append(change)
            else:
                # It's a field, try to find the declaration and comment it out
                change = FixChange(
                    description=f"Comment out unused private field '{member_name}'",
                    start_line=line,
                    start_column=1,
                    end_line=line,
                    end_column=len(code_line) + 1,
                    original_text=code_line,
                    replacement_text=f"// {code_line}  // Unused field",
                    fix_type=FixType.SIMPLE
                )
                changes.append(change)
        
        return changes
    
    def _fix_unused_parameter(self, code: str, line: int, column: int, message: str) -> List[FixChange]:
        """
        Fix unused parameter issue.
        
        Args:
            code: The C# code.
            line: Line number of the issue.
            column: Column number of the issue.
            message: The error message.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Extract the parameter name from the message
        param_match = re.search(r'\'([a-zA-Z0-9_]+)\'', message)
        if not param_match:
            return changes
        
        param_name = param_match.group(1)
        
        # Get the line of code
        lines = code.splitlines()
        if 0 < line <= len(lines):
            code_line = lines[line - 1]
            
            # Find the parameter in the method declaration
            param_match = re.search(fr'(\w+\s+{re.escape(param_name)})', code_line)
            if param_match:
                param_decl = param_match.group(1)
                
                # Prefix with underscore to acknowledge it's unused
                if not param_name.startswith('_'):
                    # Find the parameter name in the declaration
                    parts = param_decl.split()
                    if len(parts) >= 2:
                        old_param = parts[-1]
                        new_param = f"_{old_param}"
                        
                        change = FixChange(
                            description=f"Prefix unused parameter '{param_name}' with underscore",
                            start_line=line,
                            start_column=param_match.start() + param_decl.rfind(old_param) + 1,
                            end_line=line,
                            end_column=param_match.start() + param_decl.rfind(old_param) + len(old_param) + 1,
                            original_text=old_param,
                            replacement_text=new_param,
                            fix_type=FixType.SIMPLE
                        )
                        changes.append(change)
        
        return changes
    
    async def _get_llm_suggestions(self, code: str, issue: Dict[str, Any], 
                                file_path: Optional[str] = None) -> List[FixChange]:
        """
        Get suggestions for fixing an issue using LLM.
        
        Args:
            code: The C# code containing the issue.
            issue: The issue to fix.
            file_path: Optional path to the file (for reference).
        
        Returns:
            List of FixChange objects with suggestions.
        """
        changes = []
        
        if not self.llm:
            return changes
        
        try:
            # Extract issue details
            rule_id = issue.get('rule_id', '')
            message = issue.get('message', '')
            description = issue.get('description', '')
            line = issue.get('line', 0)
            
            # Extract the relevant code
            lines = code.splitlines()
            
            # Get context lines around the issue
            start_line = max(0, line - 5)
            end_line = min(len(lines), line + 5)
            
            context_code = '\n'.join(lines[start_line:end_line])
            
            # Construct the prompt for the LLM
            prompt = f"""I have a C# code issue to fix. Here's the issue:

- Rule ID: {rule_id}
- Message: {message}
- Description: {description}
- Line number: {line}

Here's the relevant code (line {line} is where the issue is):

```csharp
{context_code}
```

Please suggest a fix for this issue. Your response should include:
1. A brief explanation of the issue
2. The fixed code snippet
3. Explanation of the changes made

Return your response in JSON format:
```json
{{
  "explanation": "Brief explanation of the issue and fix",
  "original_code": "The problematic code snippet",
  "fixed_code": "The fixed code snippet"
}}
```
"""
            
            # Call the LLM to get a suggested fix
            suggestion = await self.llm.suggest_refactoring(code, "csharp", prompt)
            
            if suggestion.original_code and suggestion.refactored_code and suggestion.original_code != suggestion.refactored_code:
                # Create a fix change
                change = FixChange(
                    description=f"Fix issue: {message}",
                    start_line=line,
                    start_column=1,
                    end_line=line,
                    end_column=len(lines[line - 1]) + 1 if 0 < line <= len(lines) else 1,
                    original_text=suggestion.original_code,
                    replacement_text=suggestion.refactored_code,
                    fix_type=FixType.LLM,
                    confidence=suggestion.confidence
                )
                changes.append(change)
        
        except Exception as e:
            self.logger.warning(f"Error getting LLM suggestions: {str(e)}")
        
        return changes


if __name__ == "__main__":
    # Simple test for the C# fixer
    import asyncio
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    async def main():
        # Create the C# fixer
        fixer = CSharpFixer()
        
        # Test code with various issues
        test_code = """using System;
using System.Collections.Generic;
using System.Collections;  // Unnecessary
using System.Linq;
using System.Text;  // Unused

namespace CodeRefactorTest
{
    public class Program
    {
        private int UnusedField;
        
        public static void Main(string[] args)
        {
            // Unused variable
            string Greeting = "Hello, World!";
            
            // Uninitialized variable
            int count;
            
            // Missing braces in if statement
            if (args.Length > 0)
                Console.WriteLine("Arguments: " + args.Length);
            
            // Potential null reference
            string firstArg = args[0];
            Console.WriteLine(firstArg.Length);
            
            // Integer division assigned to double
            int a = 5;
            int b = 2;
            double result = a / b;  // Will be 2.0, not 2.5
            
            Console.WriteLine("Done");
        }
        
        private void UnusedMethod(string unusedParam)
        {
            // Method not used
            Console.WriteLine("Never called");
        }
    }
}
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