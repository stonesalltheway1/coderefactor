using System;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.Diagnostics;
using Microsoft.CodeAnalysis.MSBuild;
using Microsoft.Build.Locator;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Reflection;
using System.Net.Http;

namespace CodeRefactor.CSharp
{
    /// <summary>
    /// Severity levels for code issues
    /// </summary>
    public enum IssueSeverity
    {
        Info,
        Warning,
        Error,
        Critical
    }

    /// <summary>
    /// Categories of code issues
    /// </summary>
    public enum IssueCategory
    {
        Style,
        Performance,
        Security,
        Maintainability,
        Reliability,
        Usage,
        Design,
        Documentation,
        Complexity,
        CodeSmell,
        Error
    }

    /// <summary>
    /// Represents a code issue found by analysis
    /// </summary>
    public class AnalysisIssue
    {
        public string Id { get; set; } = Guid.NewGuid().ToString();
        public string FilePath { get; set; }
        public int Line { get; set; }
        public int Column { get; set; }
        public int? EndLine { get; set; }
        public int? EndColumn { get; set; }
        public string Message { get; set; }
        public string Description { get; set; }
        public IssueSeverity Severity { get; set; }
        public IssueCategory Category { get; set; }
        public string Source { get; set; } // Which analyzer found this issue
        public string RuleId { get; set; } // Original rule identifier
        public bool Fixable { get; set; }
        public string FixType { get; set; } // Simple, complex, llm-assisted, etc.
        public string CodeSnippet { get; set; }

        public override string ToString()
        {
            return $"[{Severity}] {FilePath}({Line},{Column}): {Message} [{RuleId}]";
        }
    }

    /// <summary>
    /// Result of code analysis on a file or project
    /// </summary>
    public class AnalysisResult
    {
        public string FilePath { get; set; }
        public List<AnalysisIssue> Issues { get; set; } = new List<AnalysisIssue>();
        public double ExecutionTime { get; set; }
        public string Error { get; set; }

        public override string ToString()
        {
            return $"Analysis of {FilePath}: {Issues.Count} issues found, execution time: {ExecutionTime}ms";
        }
    }

    /// <summary>
    /// Configuration options for C# code analysis
    /// </summary>
    public class CSharpAnalyzerConfig
    {
        public bool UseRoslynAnalyzers { get; set; } = true;
        public bool UseRoslynator { get; set; } = true;
        public bool UseSonarAnalyzer { get; set; } = false;
        public bool UseStyleCopAnalyzers { get; set; } = false;
        public HashSet<string> DisabledRules { get; set; } = new HashSet<string>();
        public Dictionary<string, string> RuleSeverities { get; set; } = new Dictionary<string, string>();
        public int MaxIssuesPerFile { get; set; } = 100;
        public bool IncludeHidden { get; set; } = false;
    }

    /// <summary>
    /// Main class for C# code analysis using Roslyn analyzers
    /// </summary>
    public class CSharpAnalyzer
    {
        private readonly CSharpAnalyzerConfig _config;
        private readonly ILogger _logger;
        private readonly List<DiagnosticAnalyzer> _analyzers = new List<DiagnosticAnalyzer>();
        private bool _isInitialized = false;

        public CSharpAnalyzer(CSharpAnalyzerConfig config = null, ILogger logger = null)
        {
            _config = config ?? new CSharpAnalyzerConfig();
            _logger = logger ?? new ConsoleLogger();
        }

        /// <summary>
        /// Initialize the analyzer with available diagnostics
        /// </summary>
        public void Initialize()
        {
            if (_isInitialized)
                return;

            try
            {
                // Register MSBuild instance
                if (!MSBuildLocator.IsRegistered)
                {
                    var instances = MSBuildLocator.QueryVisualStudioInstances().ToArray();
                    if (instances.Length > 0)
                    {
                        MSBuildLocator.RegisterInstance(instances.OrderByDescending(x => x.Version).First());
                    }
                    else
                    {
                        _logger.LogWarning("No Visual Studio instance found for MSBuild registration.");
                    }
                }

                // Load Roslyn built-in analyzers
                if (_config.UseRoslynAnalyzers)
                {
                    LoadBuiltInRoslynAnalyzers();
                }

                // Load Roslynator analyzers if available
                if (_config.UseRoslynator)
                {
                    LoadRoslynatorAnalyzers();
                }

                // Load SonarAnalyzer if available
                if (_config.UseSonarAnalyzer)
                {
                    LoadSonarAnalyzers();
                }

                // Load StyleCop Analyzers if available
                if (_config.UseStyleCopAnalyzers)
                {
                    LoadStyleCopAnalyzers();
                }

                _isInitialized = true;
                _logger.LogInfo($"CSharpAnalyzer initialized with {_analyzers.Count} analyzers.");
            }
            catch (Exception ex)
            {
                _logger.LogError($"Failed to initialize C# analyzer: {ex.Message}");
                _logger.LogDebug(ex.ToString());
            }
        }

        /// <summary>
        /// Analyze a single C# file
        /// </summary>
        public async Task<AnalysisResult> AnalyzeFileAsync(string filePath, CancellationToken cancellationToken = default)
        {
            if (!_isInitialized)
                Initialize();

            var result = new AnalysisResult { FilePath = filePath };
            var stopwatch = System.Diagnostics.Stopwatch.StartNew();

            try
            {
                if (!File.Exists(filePath))
                {
                    result.Error = $"File not found: {filePath}";
                    return result;
                }

                // Read the file content
                string code = await File.ReadAllTextAsync(filePath, cancellationToken);

                // Create syntax tree and compilation
                var tree = CSharpSyntaxTree.ParseText(code, path: filePath, cancellationToken: cancellationToken);
                var compilation = CSharpCompilation.Create(
                    Path.GetFileNameWithoutExtension(filePath),
                    new[] { tree },
                    GetBasicReferences(),
                    new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary));

                // Run analyzers
                var diagnostics = await RunAnalyzersAsync(compilation, cancellationToken);

                // Convert diagnostics to AnalysisIssue objects
                foreach (var diagnostic in diagnostics)
                {
                    if (result.Issues.Count >= _config.MaxIssuesPerFile)
                        break;

                    // Skip disabled rules
                    if (_config.DisabledRules.Contains(diagnostic.Id))
                        continue;

                    // Skip hidden diagnostics unless configured to include them
                    if (diagnostic.Severity == DiagnosticSeverity.Hidden && !_config.IncludeHidden)
                        continue;

                    try
                    {
                        var issue = ConvertDiagnosticToIssue(diagnostic, code);
                        result.Issues.Add(issue);
                    }
                    catch (Exception ex)
                    {
                        _logger.LogWarning($"Failed to convert diagnostic {diagnostic.Id}: {ex.Message}");
                    }
                }

                stopwatch.Stop();
                result.ExecutionTime = stopwatch.Elapsed.TotalMilliseconds;
                _logger.LogInfo($"Analysis completed for {filePath}. Found {result.Issues.Count} issues.");
            }
            catch (Exception ex)
            {
                stopwatch.Stop();
                result.ExecutionTime = stopwatch.Elapsed.TotalMilliseconds;
                result.Error = ex.Message;
                _logger.LogError($"Error analyzing {filePath}: {ex.Message}");
                _logger.LogDebug(ex.ToString());
            }

            return result;
        }

        /// <summary>
        /// Analyze a C# project file
        /// </summary>
        public async Task<Dictionary<string, AnalysisResult>> AnalyzeProjectAsync(string projectPath, CancellationToken cancellationToken = default)
        {
            if (!_isInitialized)
                Initialize();

            var results = new Dictionary<string, AnalysisResult>();

            try
            {
                _logger.LogInfo($"Analyzing project: {projectPath}");

                // Create MSBuild workspace
                using var workspace = MSBuildWorkspace.Create();
                
                // Register workspace failure handler
                workspace.WorkspaceFailed += (sender, args) =>
                {
                    _logger.LogWarning($"Workspace failure: {args.Diagnostic.Message}");
                };

                // Load the project
                var project = await workspace.OpenProjectAsync(projectPath, cancellationToken: cancellationToken);
                
                // Get compilation
                var compilation = await project.GetCompilationAsync(cancellationToken);
                
                if (compilation == null)
                {
                    _logger.LogError($"Failed to get compilation for project {projectPath}");
                    return results;
                }

                // Run analyzers
                var diagnostics = await RunAnalyzersAsync(compilation, cancellationToken);

                // Group diagnostics by file
                var diagnosticsByFile = diagnostics
                    .Where(d => d.Location.IsInSource)
                    .GroupBy(d => d.Location.GetLineSpan().Path);

                // Process each file
                foreach (var fileGroup in diagnosticsByFile)
                {
                    var filePath = fileGroup.Key;
                    var result = new AnalysisResult { FilePath = filePath };

                    try
                    {
                        // Get the source document
                        var document = project.Documents.FirstOrDefault(d => d.FilePath == filePath);
                        
                        if (document == null)
                        {
                            _logger.LogWarning($"Document not found for {filePath}");
                            continue;
                        }

                        // Get source code
                        var sourceText = await document.GetTextAsync(cancellationToken);
                        var code = sourceText.ToString();

                        // Convert diagnostics to issues
                        foreach (var diagnostic in fileGroup)
                        {
                            if (result.Issues.Count >= _config.MaxIssuesPerFile)
                                break;

                            // Skip disabled rules
                            if (_config.DisabledRules.Contains(diagnostic.Id))
                                continue;

                            // Skip hidden diagnostics unless configured to include them
                            if (diagnostic.Severity == DiagnosticSeverity.Hidden && !_config.IncludeHidden)
                                continue;

                            try
                            {
                                var issue = ConvertDiagnosticToIssue(diagnostic, code);
                                result.Issues.Add(issue);
                            }
                            catch (Exception ex)
                            {
                                _logger.LogWarning($"Failed to convert diagnostic {diagnostic.Id}: {ex.Message}");
                            }
                        }

                        results[filePath] = result;
                    }
                    catch (Exception ex)
                    {
                        result.Error = ex.Message;
                        results[filePath] = result;
                        _logger.LogWarning($"Error processing diagnostics for {filePath}: {ex.Message}");
                    }
                }

                _logger.LogInfo($"Analysis completed for project {projectPath}. Analyzed {results.Count} files.");
            }
            catch (Exception ex)
            {
                _logger.LogError($"Error analyzing project {projectPath}: {ex.Message}");
                _logger.LogDebug(ex.ToString());
            }

            return results;
        }

        /// <summary>
        /// Analyze all C# files in a directory
        /// </summary>
        public async Task<Dictionary<string, AnalysisResult>> AnalyzeDirectoryAsync(string directoryPath, string pattern = "*.cs", bool recursive = true, CancellationToken cancellationToken = default)
        {
            if (!_isInitialized)
                Initialize();

            var results = new Dictionary<string, AnalysisResult>();
            _logger.LogInfo($"Analyzing directory: {directoryPath}");

            try
            {
                // Find all C# files
                var searchOption = recursive ? SearchOption.AllDirectories : SearchOption.TopDirectoryOnly;
                var files = Directory.GetFiles(directoryPath, pattern, searchOption);

                // Analyze each file
                foreach (var file in files)
                {
                    if (cancellationToken.IsCancellationRequested)
                        break;

                    var result = await AnalyzeFileAsync(file, cancellationToken);
                    results[file] = result;
                }

                _logger.LogInfo($"Analysis completed for directory {directoryPath}. Analyzed {results.Count} files.");
            }
            catch (Exception ex)
            {
                _logger.LogError($"Error analyzing directory {directoryPath}: {ex.Message}");
                _logger.LogDebug(ex.ToString());
            }

            return results;
        }

        /// <summary>
        /// Get basic references needed for compilation
        /// </summary>
        private IEnumerable<MetadataReference> GetBasicReferences()
        {
            var references = new List<MetadataReference>();
            
            // Add basic .NET references
            var trustedAssembliesPaths = ((string)AppContext.GetData("TRUSTED_PLATFORM_ASSEMBLIES")).Split(Path.PathSeparator);
            var neededAssemblies = new[]
            {
                "mscorlib.dll",
                "System.dll",
                "System.Core.dll",
                "System.Runtime.dll",
                "netstandard.dll",
                "System.Collections.dll",
                "System.Linq.dll"
            };

            foreach (var path in trustedAssembliesPaths)
            {
                var fileName = Path.GetFileName(path);
                if (neededAssemblies.Contains(fileName, StringComparer.OrdinalIgnoreCase))
                {
                    try 
                    {
                        references.Add(MetadataReference.CreateFromFile(path));
                    }
                    catch (Exception ex)
                    {
                        _logger.LogDebug($"Failed to add reference {path}: {ex.Message}");
                    }
                }
            }

            return references;
        }

        /// <summary>
        /// Run all analyzers on a compilation
        /// </summary>
        private async Task<IEnumerable<Diagnostic>> RunAnalyzersAsync(Compilation compilation, CancellationToken cancellationToken)
        {
            if (_analyzers.Count == 0)
            {
                _logger.LogWarning("No analyzers available.");
                return Array.Empty<Diagnostic>();
            }

            var analyzersArray = _analyzers.ToImmutableArray();
            
            // Create analysis options
            var options = new AnalyzerOptions(ImmutableArray<AdditionalText>.Empty);
            
            // Run analyzers
            var compilationWithAnalyzers = compilation.WithAnalyzers(analyzersArray, options, cancellationToken);
            
            // Get all diagnostics
            var diagnostics = await compilationWithAnalyzers.GetAnalyzerDiagnosticsAsync(cancellationToken);
            
            return diagnostics;
        }

        /// <summary>
        /// Convert a Roslyn Diagnostic to our AnalysisIssue model
        /// </summary>
        private AnalysisIssue ConvertDiagnosticToIssue(Diagnostic diagnostic, string sourceCode)
        {
            // Get line and column info
            var lineSpan = diagnostic.Location.GetLineSpan();
            var startLinePosition = lineSpan.StartLinePosition;
            var endLinePosition = lineSpan.EndLinePosition;
            
            // Get code snippet
            string snippet = ExtractCodeSnippet(sourceCode, startLinePosition.Line, startLinePosition.Character, 
                endLinePosition.Line, endLinePosition.Character);

            // Map severity
            var severity = diagnostic.Severity switch
            {
                DiagnosticSeverity.Error => IssueSeverity.Error,
                DiagnosticSeverity.Warning => IssueSeverity.Warning,
                DiagnosticSeverity.Info => IssueSeverity.Info,
                DiagnosticSeverity.Hidden => IssueSeverity.Info,
                _ => IssueSeverity.Info
            };

            // Override severity if configured
            if (_config.RuleSeverities.TryGetValue(diagnostic.Id, out var configuredSeverity))
            {
                if (Enum.TryParse<IssueSeverity>(configuredSeverity, true, out var parsedSeverity))
                {
                    severity = parsedSeverity;
                }
            }

            // Determine category based on the diagnostic descriptor
            var category = DetermineCategory(diagnostic);

            // Determine if this diagnostic is fixable
            bool isFixable = diagnostic.Descriptor.CustomTags.Contains(WellKnownDiagnosticTags.Unnecessary) || 
                            diagnostic.Descriptor.CustomTags.Contains("Compiler") ||
                            diagnostic.Descriptor.CustomTags.Contains("CodeFix") ||
                            diagnostic.Descriptor.CustomTags.Contains("Fix");

            // Create analysis issue
            return new AnalysisIssue
            {
                FilePath = lineSpan.Path,
                Line = startLinePosition.Line + 1, // 1-based line numbers
                Column = startLinePosition.Character + 1, // 1-based column numbers
                EndLine = endLinePosition.Line + 1,
                EndColumn = endLinePosition.Character + 1,
                Message = diagnostic.GetMessage(),
                Description = diagnostic.Descriptor.Description.ToString(),
                Severity = severity,
                Category = category,
                Source = diagnostic.Descriptor.Category,
                RuleId = diagnostic.Id,
                Fixable = isFixable,
                FixType = isFixable ? "automated" : "manual",
                CodeSnippet = snippet
            };
        }

        /// <summary>
        /// Determine the category of an issue based on the diagnostic
        /// </summary>
        private IssueCategory DetermineCategory(Diagnostic diagnostic)
        {
            // First check if we can determine from the diagnostic category
            var category = diagnostic.Descriptor.Category.ToLowerInvariant() switch
            {
                "style" => IssueCategory.Style,
                "performance" => IssueCategory.Performance,
                "security" => IssueCategory.Security,
                "maintainability" => IssueCategory.Maintainability,
                "reliability" => IssueCategory.Reliability,
                "usage" => IssueCategory.Usage,
                "design" => IssueCategory.Design,
                "naming" => IssueCategory.Style,
                "documentation" => IssueCategory.Documentation,
                "compiler" => IssueCategory.Error,
                _ => IssueCategory.CodeSmell
            };

            // For some diagnostics, we can be more specific based on the diagnostic ID
            if (diagnostic.Id.StartsWith("CA"))
            {
                // Code Analysis diagnostics
                if (diagnostic.Id.StartsWith("CA1"))
                    return IssueCategory.Design;
                if (diagnostic.Id.StartsWith("CA2"))
                    return IssueCategory.Performance;
                if (diagnostic.Id.StartsWith("CA3"))
                    return IssueCategory.Security;
                if (diagnostic.Id.StartsWith("CA5"))
                    return IssueCategory.Security;
            }
            else if (diagnostic.Id.StartsWith("CS"))
            {
                // C# compiler diagnostics
                return IssueCategory.Error;
            }
            else if (diagnostic.Id.StartsWith("IDE"))
            {
                // IDE diagnostics
                return IssueCategory.Style;
            }
            else if (diagnostic.Id.StartsWith("SX"))
            {
                // StyleCop diagnostics
                if (diagnostic.Id.StartsWith("SA15"))
                    return IssueCategory.Documentation;
                if (diagnostic.Id.StartsWith("SA1"))
                    return IssueCategory.Style;
            }
            else if (diagnostic.Id.StartsWith("S"))
            {
                // SonarAnalyzer diagnostics
                if (diagnostic.Id == "S1067" || diagnostic.Id == "S1541")
                    return IssueCategory.Complexity;
                if (diagnostic.Id.StartsWith("S2"))
                    return IssueCategory.Security;
                if (diagnostic.Id.StartsWith("S3"))
                    return IssueCategory.Performance;
            }

            return category;
        }

        /// <summary>
        /// Extract a code snippet from source code based on line and column positions
        /// </summary>
        private string ExtractCodeSnippet(string sourceCode, int startLine, int startColumn, int endLine, int endColumn, int contextLines = 1)
        {
            try
            {
                if (string.IsNullOrEmpty(sourceCode))
                    return string.Empty;

                var lines = sourceCode.Split(new[] { "\r\n", "\n" }, StringSplitOptions.None);
                
                if (lines.Length == 0)
                    return string.Empty;

                // Adjust for context
                int snippetStartLine = Math.Max(0, startLine - contextLines);
                int snippetEndLine = Math.Min(lines.Length - 1, endLine + contextLines);

                // Build snippet
                var snippetBuilder = new StringBuilder();
                for (int i = snippetStartLine; i <= snippetEndLine; i++)
                {
                    snippetBuilder.AppendLine(lines[i]);
                }

                return snippetBuilder.ToString();
            }
            catch (Exception ex)
            {
                _logger.LogWarning($"Failed to extract code snippet: {ex.Message}");
                return string.Empty;
            }
        }

        /// <summary>
        /// Load built-in Roslyn analyzers
        /// </summary>
        private void LoadBuiltInRoslynAnalyzers()
        {
            try
            {
                // Add built-in Roslyn analyzers
                _logger.LogDebug("Loading built-in Roslyn analyzers");
                
                // Try to find Microsoft.CodeAnalysis.CSharp.dll
                var roslynAssemblyName = "Microsoft.CodeAnalysis.CSharp";
                var roslynAssembly = AppDomain.CurrentDomain.GetAssemblies()
                    .FirstOrDefault(a => a.GetName().Name.Equals(roslynAssemblyName));
                
                if (roslynAssembly == null)
                {
                    _logger.LogDebug($"Assembly {roslynAssemblyName} not found in current AppDomain");
                    return;
                }
                
                // Find all analyzer types in the assembly
                foreach (var type in roslynAssembly.GetTypes())
                {
                    if (typeof(DiagnosticAnalyzer).IsAssignableFrom(type) && !type.IsAbstract)
                    {
                        try
                        {
                            var analyzer = (DiagnosticAnalyzer)Activator.CreateInstance(type);
                            _analyzers.Add(analyzer);
                            _logger.LogDebug($"Added analyzer: {type.Name}");
                        }
                        catch (Exception ex)
                        {
                            _logger.LogDebug($"Failed to instantiate analyzer {type.Name}: {ex.Message}");
                        }
                    }
                }

                _logger.LogInfo($"Loaded {_analyzers.Count} built-in Roslyn analyzers");
            }
            catch (Exception ex)
            {
                _logger.LogWarning($"Failed to load built-in Roslyn analyzers: {ex.Message}");
            }
        }

        /// <summary>
        /// Load Roslynator analyzers if available
        /// </summary>
        private void LoadRoslynatorAnalyzers()
        {
            try
            {
                // Try to load Roslynator assembly
                var roslynatorAssemblyName = "Roslynator.CSharp.Analyzers";
                Assembly roslynatorAssembly = null;
                
                try
                {
                    // Try to find already loaded assembly
                    roslynatorAssembly = AppDomain.CurrentDomain.GetAssemblies()
                        .FirstOrDefault(a => a.GetName().Name.Equals(roslynatorAssemblyName));
                    
                    // If not found, try to load from file
                    if (roslynatorAssembly == null)
                    {
                        var binPath = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
                        var roslynatorPath = Path.Combine(binPath, $"{roslynatorAssemblyName}.dll");
                        
                        if (File.Exists(roslynatorPath))
                        {
                            roslynatorAssembly = Assembly.LoadFrom(roslynatorPath);
                        }
                    }
                }
                catch (Exception ex)
                {
                    _logger.LogDebug($"Failed to load Roslynator assembly: {ex.Message}");
                }
                
                if (roslynatorAssembly == null)
                {
                    _logger.LogDebug("Roslynator assembly not found");
                    return;
                }
                
                // Find all analyzer types in the assembly
                int count = 0;
                foreach (var type in roslynatorAssembly.GetTypes())
                {
                    if (typeof(DiagnosticAnalyzer).IsAssignableFrom(type) && !type.IsAbstract)
                    {
                        try
                        {
                            var analyzer = (DiagnosticAnalyzer)Activator.CreateInstance(type);
                            _analyzers.Add(analyzer);
                            count++;
                        }
                        catch (Exception ex)
                        {
                            _logger.LogDebug($"Failed to instantiate analyzer {type.Name}: {ex.Message}");
                        }
                    }
                }
                
                _logger.LogInfo($"Loaded {count} Roslynator analyzers");
            }
            catch (Exception ex)
            {
                _logger.LogWarning($"Failed to load Roslynator analyzers: {ex.Message}");
            }
        }

        /// <summary>
        /// Load SonarAnalyzer if available
        /// </summary>
        private void LoadSonarAnalyzers()
        {
            try
            {
                // Try to load SonarAnalyzer assembly
                var sonarAssemblyName = "SonarAnalyzer.CSharp";
                Assembly sonarAssembly = null;
                
                try
                {
                    // Try to find already loaded assembly
                    sonarAssembly = AppDomain.CurrentDomain.GetAssemblies()
                        .FirstOrDefault(a => a.GetName().Name.Equals(sonarAssemblyName));
                    
                    // If not found, try to load from file
                    if (sonarAssembly == null)
                    {
                        var binPath = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
                        var sonarPath = Path.Combine(binPath, $"{sonarAssemblyName}.dll");
                        
                        if (File.Exists(sonarPath))
                        {
                            sonarAssembly = Assembly.LoadFrom(sonarPath);
                        }
                    }
                }
                catch (Exception ex)
                {
                    _logger.LogDebug($"Failed to load SonarAnalyzer assembly: {ex.Message}");
                }
                
                if (sonarAssembly == null)
                {
                    _logger.LogDebug("SonarAnalyzer assembly not found");
                    return;
                }
                
                // Find all analyzer types in the assembly
                int count = 0;
                foreach (var type in sonarAssembly.GetTypes())
                {
                    if (typeof(DiagnosticAnalyzer).IsAssignableFrom(type) && !type.IsAbstract)
                    {
                        try
                        {
                            var analyzer = (DiagnosticAnalyzer)Activator.CreateInstance(type);
                            _analyzers.Add(analyzer);
                            count++;
                        }
                        catch (Exception ex)
                        {
                            _logger.LogDebug($"Failed to instantiate analyzer {type.Name}: {ex.Message}");
                        }
                    }
                }
                
                _logger.LogInfo($"Loaded {count} SonarAnalyzer analyzers");
            }
            catch (Exception ex)
            {
                _logger.LogWarning($"Failed to load SonarAnalyzer analyzers: {ex.Message}");
            }
        }

        /// <summary>
        /// Load StyleCop Analyzers if available
        /// </summary>
        private void LoadStyleCopAnalyzers()
        {
            try
            {
                // Try to load StyleCop.Analyzers assembly
                var styleCopAssemblyName = "StyleCop.Analyzers";
                Assembly styleCopAssembly = null;
                
                try
                {
                    // Try to find already loaded assembly
                    styleCopAssembly = AppDomain.CurrentDomain.GetAssemblies()
                        .FirstOrDefault(a => a.GetName().Name.Equals(styleCopAssemblyName));
                    
                    // If not found, try to load from file
                    if (styleCopAssembly == null)
                    {
                        var binPath = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
                        var styleCopPath = Path.Combine(binPath, $"{styleCopAssemblyName}.dll");
                        
                        if (File.Exists(styleCopPath))
                        {
                            styleCopAssembly = Assembly.LoadFrom(styleCopPath);
                        }
                    }
                }
                catch (Exception ex)
                {
                    _logger.LogDebug($"Failed to load StyleCop.Analyzers assembly: {ex.Message}");
                }
                
                if (styleCopAssembly == null)
                {
                    _logger.LogDebug("StyleCop.Analyzers assembly not found");
                    return;
                }
                
                // Find all analyzer types in the assembly
                int count = 0;
                foreach (var type in styleCopAssembly.GetTypes())
                {
                    if (typeof(DiagnosticAnalyzer).IsAssignableFrom(type) && !type.IsAbstract)
                    {
                        try
                        {
                            var analyzer = (DiagnosticAnalyzer)Activator.CreateInstance(type);
                            _analyzers.Add(analyzer);
                            count++;
                        }
                        catch (Exception ex)
                        {
                            _logger.LogDebug($"Failed to instantiate analyzer {type.Name}: {ex.Message}");
                        }
                    }
                }
                
                _logger.LogInfo($"Loaded {count} StyleCop.Analyzers analyzers");
            }
            catch (Exception ex)
            {
                _logger.LogWarning($"Failed to load StyleCop.Analyzers analyzers: {ex.Message}");
            }
        }
    }

    /// <summary>
    /// Interface for logging
    /// </summary>
    public interface ILogger
    {
        void LogInfo(string message);
        void LogWarning(string message);
        void LogError(string message);
        void LogDebug(string message);
    }

    /// <summary>
    /// Simple console logger implementation
    /// </summary>
    public class ConsoleLogger : ILogger
    {
        public void LogInfo(string message) => Console.WriteLine($"INFO: {message}");
        public void LogWarning(string message) => Console.WriteLine($"WARNING: {message}");
        public void LogError(string message) => Console.WriteLine($"ERROR: {message}");
        public void LogDebug(string message) => Console.WriteLine($"DEBUG: {message}");
    }
}