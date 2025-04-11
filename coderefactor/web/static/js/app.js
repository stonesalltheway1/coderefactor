/**
 * CodeRefactor Web Interface
 * Main JavaScript application for the web interface
 */

// Global state
const state = {
    editor: null,
    monaco: null,
    currentLanguage: 'python',
    decorations: [],
    currentIssues: [],
    isAnalyzing: false,
    originalCode: null,
    refactoredCode: null,
    selectedIssueId: null,
    darkTheme: localStorage.getItem('darkTheme') === 'true'
};

// Default code samples for different languages
const DEFAULT_CODE_SAMPLES = {
    python: `def calculate_average(numbers):
    total = 0
    for n in numbers:
        total += n
    return total / len(numbers)

def process_data(data):
    # Process the data and return results
    results = []
    for item in data:
        if item > 10:
            results.append(item * 2)
        else:
            results.append(item)
    return results

# Example usage
data_list = [5, 10, 15, 20, 25]
avg = calculate_average(data_list)
print(f"Average: {avg}")
processed = process_data(data_list)
print(f"Processed data: {processed}")`,

    javascript: `// Function to calculate average
function calculateAverage(numbers) {
    let total = 0;
    for (let i = 0; i < numbers.length; i++) {
        total += numbers[i];
    }
    return total / numbers.length;
}

// Process data function
function processData(data) {
    // Process the data and return results
    const results = [];
    for (let i = 0; i < data.length; i++) {
        if (data[i] > 10) {
            results.push(data[i] * 2);
        } else {
            results.push(data[i]);
        }
    }
    return results;
}

// Example usage
const dataList = [5, 10, 15, 20, 25];
const avg = calculateAverage(dataList);
console.log("Average: " + avg);
const processed = processData(dataList);
console.log("Processed data: " + processed);`,

    typescript: `// Function to calculate average
function calculateAverage(numbers: number[]): number {
    let total = 0;
    for (let i = 0; i < numbers.length; i++) {
        total += numbers[i];
    }
    return total / numbers.length;
}

// Process data function
function processData(data: number[]): number[] {
    // Process the data and return results
    const results: number[] = [];
    for (let i = 0; i < data.length; i++) {
        if (data[i] > 10) {
            results.push(data[i] * 2);
        } else {
            results.push(data[i]);
        }
    }
    return results;
}

// Example usage
const dataList: number[] = [5, 10, 15, 20, 25];
const avg: number = calculateAverage(dataList);
console.log("Average: " + avg);
const processed: number[] = processData(dataList);
console.log("Processed data: " + processed);`,

    html: `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Simple Webpage</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            color: #333;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        header {
            background-color: #f4f4f4;
            padding: 20px;
            text-align: center;
        }
        .content {
            padding: 20px;
        }
        footer {
            text-align: center;
            margin-top: 20px;
            padding: 10px;
            background-color: #f4f4f4;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Welcome to My Website</h1>
            <p>A simple demonstration of HTML structure</p>
        </header>
        
        <div class="content">
            <h2>About This Page</h2>
            <p>This is a basic HTML template that demonstrates various HTML elements.</p>
            
            <h2>Features</h2>
            <ul>
                <li>Simple and clean design</li>
                <li>Responsive layout</li>
                <li>Basic styling with CSS</li>
            </ul>
            
            <h2>Contact Information</h2>
            <p>You can reach me at <a href="mailto:example@example.com">example@example.com</a></p>
        </div>
        
        <footer>
            <p>&copy; 2025 My Website. All rights reserved.</p>
        </footer>
    </div>
</body>
</html>`,

    css: `/* Main Styles */
body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    line-height: 1.6;
    margin: 0;
    padding: 0;
    background-color: #f4f4f4;
    color: #333;
}

.container {
    width: 80%;
    margin: auto;
    overflow: hidden;
}

/* Header Styles */
header {
    background: #50b3a2;
    color: white;
    padding: 20px 0;
    text-align: center;
}

header h1 {
    margin: 0;
    padding: 0;
}

/* Navigation Styles */
nav {
    background: #444;
    color: white;
}

nav ul {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
}

nav li {
    padding: 10px 20px;
}

nav a {
    color: white;
    text-decoration: none;
}

nav a:hover {
    color: #50b3a2;
}

/* Main Content */
.content {
    padding: 20px;
    background: white;
    margin: 20px 0;
    border-radius: 5px;
    box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
}

/* Footer */
footer {
    background: #444;
    color: white;
    text-align: center;
    padding: 10px;
    margin-top: 20px;
}

/* Media Queries */
@media (max-width: 700px) {
    .container {
        width: 95%;
    }
    
    nav ul {
        flex-direction: column;
    }
}`,

    csharp: `using System;
using System.Collections.Generic;
using System.Linq;

namespace CodeRefactorExample
{
    class Program
    {
        static void Main(string[] args)
        {
            // Example data
            List<int> dataList = new List<int> { 5, 10, 15, 20, 25 };
            
            // Calculate average
            double avg = CalculateAverage(dataList);
            Console.WriteLine($"Average: {avg}");
            
            // Process data
            List<int> processed = ProcessData(dataList);
            Console.WriteLine($"Processed data: {string.Join(", ", processed)}");
            
            Console.ReadLine();
        }
        
        static double CalculateAverage(List<int> numbers)
        {
            int total = 0;
            foreach (int n in numbers)
            {
                total += n;
            }
            return (double)total / numbers.Count;
        }
        
        static List<int> ProcessData(List<int> data)
        {
            // Process the data and return results
            List<int> results = new List<int>();
            foreach (int item in data)
            {
                if (item > 10)
                {
                    results.Add(item * 2);
                }
                else
                {
                    results.Add(item);
                }
            }
            return results;
        }
    }
}`
};

// Map of language names to Monaco language IDs
const LANGUAGE_MAP = {
    'python': 'python',
    'javascript': 'javascript',
    'typescript': 'typescript',
    'html': 'html',
    'css': 'css',
    'csharp': 'csharp'
};

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

/**
 * Initialize the application
 */
async function initializeApp() {
    // Set up theme
    if (state.darkTheme) {
        document.body.classList.add('dark-theme');
    }

    // Set up event listeners
    setupEventListeners();
    
    // Initialize Monaco Editor
    await initMonacoEditor();
    
    // Check if a file was uploaded via URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    const fileParam = urlParams.get('file');
    
    if (fileParam) {
        loadFileFromParam(fileParam);
    }
}

/**
 * Initialize Monaco Editor
 */
async function initMonacoEditor() {
    return new Promise((resolve) => {
        require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.52.0/min/vs' }});
        require(['vs/editor/editor.main'], function() {
            state.monaco = monaco;
            
            // Register themes
            registerEditorThemes();
            
            // Set the language from dropdown
            state.currentLanguage = document.getElementById('language-select').value;
            
            // Create the editor
            state.editor = monaco.editor.create(document.getElementById('editor'), {
                value: DEFAULT_CODE_SAMPLES[state.currentLanguage],
                language: LANGUAGE_MAP[state.currentLanguage],
                theme: state.darkTheme ? 'vs-dark' : 'vs',
                automaticLayout: true,
                minimap: { enabled: true },
                scrollBeyondLastLine: false,
                renderLineHighlight: 'all',
                contextmenu: true,
                lineNumbers: 'on',
                rulers: [80, 120],
                renderWhitespace: 'selection',
                fontFamily: 'Consolas, "Courier New", monospace',
                fontSize: 14
            });
            
            // Setup editor event listeners
            state.editor.onDidChangeModelContent(() => {
                // Clear decorations when code changes
                state.decorations = state.editor.deltaDecorations(state.decorations, []);
            });
            
            resolve();
        });
    });
}

/**
 * Register custom themes for Monaco Editor
 */
function registerEditorThemes() {
    // Define a dark theme
    monaco.editor.defineTheme('coderefactor-dark', {
        base: 'vs-dark',
        inherit: true,
        rules: [
            { token: 'comment', foreground: '6A9955', fontStyle: 'italic' },
            { token: 'keyword', foreground: '569CD6' },
            { token: 'string', foreground: 'CE9178' }
        ],
        colors: {
            'editor.background': '#1E1E2E',
            'editor.foreground': '#D4D4D4',
            'editorLineNumber.foreground': '#858585',
            'editorActiveLineNumber.foreground': '#C6C6C6'
        }
    });
}

/**
 * Set up all event listeners
 */
function setupEventListeners() {
    // Language selector change
    document.getElementById('language-select').addEventListener('change', (e) => {
        changeLanguage(e.target.value);
    });
    
    // Analyze button click
    document.getElementById('analyze-btn').addEventListener('click', () => {
        if (!state.isAnalyzing) {
            analyzeCode();
        }
    });
    
    // Explain button click
    document.getElementById('explain-btn').addEventListener('click', () => {
        if (!state.isAnalyzing) {
            explainCode();
        }
    });
    
    // Fix all button click
    document.getElementById('fix-all-btn').addEventListener('click', () => {
        if (!state.isAnalyzing && state.currentIssues.length > 0) {
            fixAllIssues();
        }
    });
    
    // Collapse results panel
    document.getElementById('collapse-results').addEventListener('click', toggleResultsPanel);
    
    // Modal close button
    document.querySelector('.close-modal').addEventListener('click', hideModal);
    
    // Modal dismiss button
    document.querySelector('.dismiss-btn').addEventListener('click', hideModal);
    
    // Modal apply button
    document.querySelector('.apply-btn').addEventListener('click', applyFix);
    
    // File upload
    const fileInput = document.getElementById('file-input');
    if (fileInput) {
        fileInput.addEventListener('change', handleFileUpload);
    }
    
    // Theme toggle
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }
    
    // Clicking outside modal closes it
    document.getElementById('fix-modal').addEventListener('click', (e) => {
        if (e.target === document.getElementById('fix-modal')) {
            hideModal();
        }
    });
    
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Ctrl+Enter or Cmd+Enter to analyze
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            if (!state.isAnalyzing) {
                analyzeCode();
            }
        }
        
        // Escape to close modal
        if (e.key === 'Escape') {
            hideModal();
        }
    });
}

/**
 * Change the language of the editor
 * @param {string} newLanguage - The new language to set
 */
function changeLanguage(newLanguage) {
    if (newLanguage === state.currentLanguage) return;
    
    state.currentLanguage = newLanguage;
    const monacoLang = LANGUAGE_MAP[newLanguage];
    
    // Set the language model
    monaco.editor.setModelLanguage(state.editor.getModel(), monacoLang);
    
    // Set default code sample if editor is empty
    if (state.editor.getValue().trim() === '') {
        state.editor.setValue(DEFAULT_CODE_SAMPLES[newLanguage]);
    }
    
    // Clear any existing issues
    clearIssues();
}

/**
 * Analyze the current code in the editor
 */
async function analyzeCode() {
    if (state.isAnalyzing) return;
    
    state.isAnalyzing = true;
    showLoading();
    clearIssues();
    hideExplanation();
    
    try {
        const code = state.editor.getValue();
        const language = state.currentLanguage;
        const useLLM = document.getElementById('use-llm-checkbox').checked;
        
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ code, language, use_llm: useLLM })
        });
        
        if (!response.ok) {
            throw new Error(`Error: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.error) {
            showError(data.error);
            return;
        }
        
        // Store current issues
        state.currentIssues = data.issues || [];
        
        // Show the issues
        displayIssues(state.currentIssues);
        
        // Add decorations to editor
        addIssueDecorations(state.currentIssues);
        
        // Show explanation if available
        if (data.explanation) {
            showExplanation(data.explanation);
        }
        
        // Show suggestions if available
        if (data.suggestions && data.suggestions.length > 0) {
            displaySuggestions(data.suggestions);
        }
    } catch (error) {
        console.error('Error analyzing code:', error);
        showError(`Error analyzing code: ${error.message}`);
    } finally {
        state.isAnalyzing = false;
        hideLoading();
    }
}

/**
 * Explain the current code in the editor
 */
async function explainCode() {
    if (state.isAnalyzing) return;
    
    state.isAnalyzing = true;
    showLoading();
    
    try {
        const code = state.editor.getValue();
        const language = state.currentLanguage;
        
        const response = await fetch('/api/explain', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ code, language })
        });
        
        if (!response.ok) {
            throw new Error(`Error: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.error) {
            showError(data.error);
            return;
        }
        
        // Show the explanation
        showExplanation(data.explanation);
    } catch (error) {
        console.error('Error explaining code:', error);
        showError(`Error explaining code: ${error.message}`);
    } finally {
        state.isAnalyzing = false;
        hideLoading();
    }
}

/**
 * Display issues in the results panel
 * @param {Array} issues - Array of issue objects
 */
function displayIssues(issues) {
    const issuesList = document.getElementById('issues-list');
    issuesList.innerHTML = '';
    
    if (issues.length === 0) {
        issuesList.innerHTML = `
            <div class="no-issues">
                <i class="fas fa-check-circle" style="font-size: 3rem; color: #2ecc71; margin-bottom: 15px;"></i>
                <p>No issues found! Good job!</p>
            </div>
        `;
        return;
    }
    
    // Group issues by severity
    const severityOrder = ['critical', 'error', 'warning', 'info'];
    const issuesBySeverity = {};
    
    severityOrder.forEach(severity => {
        issuesBySeverity[severity] = issues.filter(issue => 
            issue.severity.toLowerCase() === severity
        );
    });
    
    // Create issues header with counts
    const issuesHeader = document.createElement('div');
    issuesHeader.className = 'issues-header';
    
    const countsHtml = severityOrder
        .filter(severity => issuesBySeverity[severity].length > 0)
        .map(severity => `
            <span class="severity-${severity}" style="margin-right: 10px; font-size: 0.8rem;">
                ${severity}: ${issuesBySeverity[severity].length}
            </span>
        `)
        .join('');
    
    issuesHeader.innerHTML = `
        <div class="issues-count">
            ${issues.length} issue${issues.length !== 1 ? 's' : ''} found ${countsHtml}
        </div>
        <div class="issues-filters">
            <button class="filter-all active" data-filter="all">All</button>
            ${severityOrder.map(severity => `
                <button class="filter-${severity}" data-filter="${severity}"
                    ${issuesBySeverity[severity].length === 0 ? 'disabled' : ''}>
                    ${severity.charAt(0).toUpperCase() + severity.slice(1)}
                </button>
            `).join('')}
        </div>
    `;
    
    issuesList.appendChild(issuesHeader);
    
    // Add filter functionality
    issuesHeader.querySelectorAll('button[data-filter]').forEach(button => {
        button.addEventListener('click', (e) => {
            // Remove active class from all buttons
            issuesHeader.querySelectorAll('button[data-filter]').forEach(btn => {
                btn.classList.remove('active');
            });
            
            // Add active class to clicked button
            e.target.classList.add('active');
            
            // Filter issues
            const filter = e.target.dataset.filter;
            filterIssues(filter);
        });
    });
    
    // Create issues list
    const issuesListContainer = document.createElement('div');
    issuesListContainer.className = 'issues-list';
    issuesList.appendChild(issuesListContainer);
    
    // Process each issue
    issues.forEach(issue => {
        const severity = issue.severity.toLowerCase();
        const issueId = issue.id;
        
        const issueItem = document.createElement('div');
        issueItem.className = `issue-item issue-severity-${severity}`;
        issueItem.dataset.severity = severity;
        
        const issueHeader = document.createElement('div');
        issueHeader.className = 'issue-header';
        issueHeader.dataset.id = issueId;
        issueHeader.addEventListener('click', () => toggleIssueDetails(issueId));
        
        const title = issue.rule_id || `${issue.category} Issue`;
        
        issueHeader.innerHTML = `
            <div class="issue-title">
                <i class="fas fa-caret-right"></i>
                ${escapeHtml(title)}
            </div>
            <div class="issue-severity severity-${severity}">${severity}</div>
        `;
        
        const issueBody = document.createElement('div');
        issueBody.className = 'issue-body';
        issueBody.dataset.id = issueId;
        
        let codeSnippet = '';
        if (issue.code_snippet) {
            codeSnippet = `<div class="code-snippet">${escapeHtml(issue.code_snippet)}</div>`;
        }
        
        issueBody.innerHTML = `
            <div class="issue-location">Line ${issue.line}${issue.column ? `, Column ${issue.column}` : ''}</div>
            <div class="issue-message">${escapeHtml(issue.message)}</div>
            <div class="issue-description">${escapeHtml(issue.description || '')}</div>
            ${codeSnippet}
            <div class="issue-actions">
                <button class="goto-btn" data-line="${issue.line}" data-column="${issue.column || 0}">
                    <i class="fas fa-arrow-right"></i> Go to
                </button>
                ${issue.fixable ? `
                    <button class="fix-btn" data-issue-id="${issueId}">
                        <i class="fas fa-wrench"></i> Fix
                    </button>
                ` : ''}
            </div>
        `;
        
        issueItem.appendChild(issueHeader);
        issueItem.appendChild(issueBody);
        issuesListContainer.appendChild(issueItem);
    });
    
    // Add event listeners to buttons
    document.querySelectorAll('.goto-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent toggling when clicking the button
            const line = parseInt(btn.getAttribute('data-line'));
            const column = parseInt(btn.getAttribute('data-column'));
            goToLocation(line, column);
        });
    });
    
    document.querySelectorAll('.fix-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent toggling when clicking the button
            const issueId = btn.getAttribute('data-issue-id');
            getFixSuggestion(issueId);
        });
    });
}

/**
 * Toggle issue details visibility
 * @param {string} issueId - ID of the issue to toggle
 */
function toggleIssueDetails(issueId) {
    const header = document.querySelector(`.issue-header[data-id="${issueId}"]`);
    const body = document.querySelector(`.issue-body[data-id="${issueId}"]`);
    const icon = header.querySelector('i');
    
    body.classList.toggle('expanded');
    icon.classList.toggle('expanded');
}

/**
 * Filter issues by severity
 * @param {string} filter - Severity filter or 'all'
 */
function filterIssues(filter) {
    const issueItems = document.querySelectorAll('.issue-item');
    
    issueItems.forEach(item => {
        if (filter === 'all' || item.dataset.severity === filter) {
            item.style.display = '';
        } else {
            item.style.display = 'none';
        }
    });
}

/**
 * Toggle the results panel visibility
 */
function toggleResultsPanel() {
    const resultsPanel = document.querySelector('.results-panel');
    resultsPanel.classList.toggle('collapsed');
    
    const button = document.getElementById('collapse-results');
    const icon = button.querySelector('i');
    
    if (resultsPanel.classList.contains('collapsed')) {
        icon.className = 'fas fa-chevron-left';
        button.title = 'Expand Panel';
    } else {
        icon.className = 'fas fa-chevron-right';
        button.title = 'Collapse Panel';
    }
    
    // Resize editor
    setTimeout(() => state.editor.layout(), 300);
}

/**
 * Add decorations to the editor for issues
 * @param {Array} issues - Array of issue objects
 */
function addIssueDecorations(issues) {
    // Remove existing decorations
    state.decorations = state.editor.deltaDecorations(state.decorations, []);
    
    // Create new decorations
    const newDecorations = issues.map(issue => {
        const startLineNumber = issue.line;
        const startColumn = issue.column || 1;
        const endLineNumber = issue.end_line || issue.line;
        const endColumn = issue.end_column || 1000;
        
        const severity = issue.severity.toLowerCase();
        let className = 'issue-decoration';
        
        if (severity === 'critical' || severity === 'error') {
            className = 'error-decoration';
        } else if (severity === 'warning') {
            className = 'warning-decoration';
        } else {
            className = 'info-decoration';
        }
        
        return {
            range: new monaco.Range(startLineNumber, startColumn, endLineNumber, endColumn),
            options: {
                inlineClassName: className,
                hoverMessage: { value: issue.message || issue.description },
                className: `${className}-line`,
                glyphMarginClassName: `${severity}-glyph`
            }
        };
    });
    
    // Apply decorations
    state.decorations = state.editor.deltaDecorations([], newDecorations);
    
    // Add CSS for decorations if not already added
    if (!document.getElementById('decoration-styles')) {
        const style = document.createElement('style');
        style.id = 'decoration-styles';
        style.innerHTML = `
            .error-decoration { border-bottom: 2px wavy var(--error-color); }
            .warning-decoration { border-bottom: 2px wavy var(--warning-color); }
            .info-decoration { border-bottom: 2px dotted var(--info-color); }
            .error-decoration-line { background-color: rgba(231, 76, 60, 0.1); }
            .warning-decoration-line { background-color: rgba(243, 156, 18, 0.1); }
            .info-decoration-line { background-color: rgba(52, 152, 219, 0.1); }
            .critical-glyph, .error-glyph { 
                background: var(--error-color);
                border-radius: 50%;
                width: 8px !important;
                height: 8px !important;
                margin-left: 5px;
            }
            .warning-glyph { 
                background: var(--warning-color);
                border-radius: 50%;
                width: 8px !important;
                height: 8px !important;
                margin-left: 5px;
            }
            .info-glyph { 
                background: var(--info-color);
                border-radius: 50%;
                width: 8px !important;
                height: 8px !important;
                margin-left: 5px;
            }
        `;
        document.head.appendChild(style);
    }
}

/**
 * Get a fix suggestion for a specific issue
 * @param {string} issueId - ID of the issue to fix
 */
async function getFixSuggestion(issueId) {
    if (state.isAnalyzing) return;
    
    state.isAnalyzing = true;
    showLoading();
    
    try {
        const issue = state.currentIssues.find(i => i.id === issueId);
        if (!issue) {
            throw new Error('Issue not found');
        }
        
        state.selectedIssueId = issueId;
        const code = state.editor.getValue();
        const language = state.currentLanguage;
        const issueDescription = issue.description || issue.message;
        
        const response = await fetch('/api/fix', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                code, 
                language, 
                issue_id: issueId,
                issue_description: issueDescription
            })
        });
        
        if (!response.ok) {
            throw new Error(`Error: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.error) {
            showError(data.error);
            return;
        }
        
        // Show the fix modal
        showFixModal(data);
    } catch (error) {
        console.error('Error getting fix suggestion:', error);
        showError(`Error getting fix suggestion: ${error.message}`);
    } finally {
        state.isAnalyzing = false;
        hideLoading();
    }
}

/**
 * Show fix modal with suggestion
 * @param {Object} fixData - Fix suggestion data
 */
function showFixModal(fixData) {
    const modal = document.getElementById('fix-modal');
    const explanation = modal.querySelector('.explanation');
    const originalCodeContainer = document.getElementById('original-code');
    const refactoredCodeContainer = document.getElementById('refactored-code');
    
    // Set explanation
    explanation.textContent = fixData.explanation || 'No explanation provided';
    
    // Store code for apply action
    state.originalCode = fixData.original_code || '';
    state.refactoredCode = fixData.refactored_code || '';
    
    // Initialize original code editor if not already done
    if (!state.originalCodeEditor) {
        state.originalCodeEditor = monaco.editor.create(originalCodeContainer, {
            value: state.originalCode,
            language: LANGUAGE_MAP[state.currentLanguage],
            theme: state.darkTheme ? 'vs-dark' : 'vs',
            minimap: { enabled: false },
            readOnly: true,
            scrollBeyondLastLine: false,
            lineNumbers: 'on',
            renderWhitespace: 'selection',
            fontFamily: 'Consolas, "Courier New", monospace',
            fontSize: 14
        });
    } else {
        state.originalCodeEditor.setValue(state.originalCode);
        monaco.editor.setModelLanguage(state.originalCodeEditor.getModel(), LANGUAGE_MAP[state.currentLanguage]);
    }
    
    // Initialize refactored code editor if not already done
    if (!state.refactoredCodeEditor) {
        state.refactoredCodeEditor = monaco.editor.create(refactoredCodeContainer, {
            value: state.refactoredCode,
            language: LANGUAGE_MAP[state.currentLanguage],
            theme: state.darkTheme ? 'vs-dark' : 'vs',
            minimap: { enabled: false },
            readOnly: true,
            scrollBeyondLastLine: false,
            lineNumbers: 'on',
            renderWhitespace: 'selection',
            fontFamily: 'Consolas, "Courier New", monospace',
            fontSize: 14
        });
    } else {
        state.refactoredCodeEditor.setValue(state.refactoredCode);
        monaco.editor.setModelLanguage(state.refactoredCodeEditor.getModel(), LANGUAGE_MAP[state.currentLanguage]);
    }
    
    // Update themes if needed
    if (state.darkTheme) {
        state.originalCodeEditor.updateOptions({ theme: 'vs-dark' });
        state.refactoredCodeEditor.updateOptions({ theme: 'vs-dark' });
    } else {
        state.originalCodeEditor.updateOptions({ theme: 'vs' });
        state.refactoredCodeEditor.updateOptions({ theme: 'vs' });
    }
    
    // Show the modal
    modal.style.display = 'block';
    
    // Resize editors after display
    setTimeout(() => {
        state.originalCodeEditor.layout();
        state.refactoredCodeEditor.layout();
    }, 100);
}

/**
 * Hide the fix modal
 */
function hideModal() {
    document.getElementById('fix-modal').style.display = 'none';
}

/**
 * Apply the suggested fix
 */
function applyFix() {
    if (!state.refactoredCode) {
        showError('No fix data available');
        return;
    }
    
    // Apply the fix by replacing the entire code
    state.editor.setValue(state.refactoredCode);
    
    // Close the modal
    hideModal();
    
    // Clear the selected issue
    state.selectedIssueId = null;
    
    // Re-analyze the code
    analyzeCode();
}

/**
 * Fix all fixable issues
 */
function fixAllIssues() {
    const fixableIssues = state.currentIssues.filter(issue => issue.fixable);
    
    if (fixableIssues.length === 0) {
        showError('No fixable issues found');
        return;
    }
    
    // Get the first fixable issue
    getFixSuggestion(fixableIssues[0].id);
}

/**
 * Go to a specific location in the editor
 * @param {number} line - Line number
 * @param {number} column - Column number
 */
function goToLocation(line, column) {
    state.editor.revealPositionInCenter({ lineNumber: line, column: column });
    state.editor.setPosition({ lineNumber: line, column: column });
    state.editor.focus();
}

/**
 * Show explanation in the sidebar
 * @param {string} explanation - Explanation text
 */
function showExplanation(explanation) {
    const explanationContainer = document.getElementById('explanation-container');
    const explanationContent = document.getElementById('explanation-content');
    
    explanationContent.textContent = explanation;
    explanationContainer.classList.remove('hidden');
}

/**
 * Hide the explanation panel
 */
function hideExplanation() {
    document.getElementById('explanation-container').classList.add('hidden');
}

/**
 * Show loading overlay
 */
function showLoading() {
    document.getElementById('loading-overlay').style.display = 'flex';
}

/**
 * Hide loading overlay
 */
function hideLoading() {
    document.getElementById('loading-overlay').style.display = 'none';
}

/**
 * Show error message in the results panel
 * @param {string} message - Error message to display
 */
function showError(message) {
    const issuesList = document.getElementById('issues-list');
    issuesList.innerHTML = `
        <div class="error-message" style="padding: 20px; color: var(--error-color); background-color: rgba(231, 76, 60, 0.1); border-radius: 4px; margin-bottom: 15px;">
            <i class="fas fa-exclamation-triangle" style="margin-right: 10px;"></i>
            <p>${escapeHtml(message)}</p>
        </div>
    `;
}

/**
 * Handle file upload
 * @param {Event} event - File input change event
 */
function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    // Clear the file input value
    event.target.value = '';
    
    // Detect language from file extension
    const extension = file.name.split('.').pop().toLowerCase();
    const languageMap = {
        'py': 'python',
        'js': 'javascript',
        'jsx': 'javascript',
        'ts': 'typescript',
        'tsx': 'typescript',
        'html': 'html',
        'htm': 'html',
        'css': 'css',
        'scss': 'css',
        'less': 'css',
        'cs': 'csharp'
    };
    
    const language = languageMap[extension] || state.currentLanguage;
    
    // Set language in dropdown
    const languageSelect = document.getElementById('language-select');
    if (languageSelect.value !== language && languageMap[extension]) {
        languageSelect.value = language;
        changeLanguage(language);
    }
    
    // Read file
    const reader = new FileReader();
    reader.onload = function(e) {
        state.editor.setValue(e.target.result);
    };
    reader.readAsText(file);
}

/**
 * Load file from URL parameter
 * @param {string} fileParam - File path or URL
 */
async function loadFileFromParam(fileParam) {
    showLoading();
    
    try {
        // Check if it's a URL or a local path
        if (fileParam.startsWith('http')) {
            // Load from URL
            const response = await fetch(fileParam);
            if (!response.ok) {
                throw new Error(`Failed to load file: ${response.statusText}`);
            }
            
            const content = await response.text();
            
            // Detect language from URL extension
            const extension = fileParam.split('.').pop().toLowerCase();
            const languageMap = {
                'py': 'python',
                'js': 'javascript',
                'jsx': 'javascript',
                'ts': 'typescript',
                'tsx': 'typescript',
                'html': 'html',
                'htm': 'html',
                'css': 'css',
                'scss': 'css',
                'less': 'css',
                'cs': 'csharp'
            };
            
            const language = languageMap[extension] || state.currentLanguage;
            
            // Set language in dropdown
            const languageSelect = document.getElementById('language-select');
            if (languageSelect.value !== language && languageMap[extension]) {
                languageSelect.value = language;
                changeLanguage(language);
            }
            
            // Set content in editor
            state.editor.setValue(content);
        } else {
            // Local path - send to server to load
            const response = await fetch('/api/load-file', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ path: fileParam })
            });
            
            if (!response.ok) {
                throw new Error(`Failed to load file: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            // Set language in dropdown
            const languageSelect = document.getElementById('language-select');
            if (languageSelect.value !== data.language) {
                languageSelect.value = data.language;
                changeLanguage(data.language);
            }
            
            // Set content in editor
            state.editor.setValue(data.content);
        }
    } catch (error) {
        console.error('Error loading file:', error);
        showError(`Error loading file: ${error.message}`);
    } finally {
        hideLoading();
    }
}

/**
 * Toggle between light and dark themes
 */
function toggleTheme() {
    state.darkTheme = !state.darkTheme;
    
    // Save preference
    localStorage.setItem('darkTheme', state.darkTheme);
    
    // Apply to body
    document.body.classList.toggle('dark-theme', state.darkTheme);
    
    // Apply to editor
    state.editor.updateOptions({ 
        theme: state.darkTheme ? 'coderefactor-dark' : 'vs' 
    });
    
    // Apply to diff editors if they exist
    if (state.originalCodeEditor) {
        state.originalCodeEditor.updateOptions({ 
            theme: state.darkTheme ? 'coderefactor-dark' : 'vs' 
        });
    }
    
    if (state.refactoredCodeEditor) {
        state.refactoredCodeEditor.updateOptions({ 
            theme: state.darkTheme ? 'coderefactor-dark' : 'vs' 
        });
    }
}

/**
 * Display AI suggestions
 * @param {Array} suggestions - Array of suggestion objects
 */
function displaySuggestions(suggestions) {
    const container = document.createElement('div');
    container.className = 'suggestions-container';
    container.innerHTML = `
        <h4>AI Suggestions</h4>
        <div class="suggestions-list"></div>
    `;
    
    const suggestionsList = container.querySelector('.suggestions-list');
    
    suggestions.forEach(suggestion => {
        const suggestionItem = document.createElement('div');
        suggestionItem.className = 'suggestion-item';
        suggestionItem.innerHTML = `
            <div class="suggestion-title">${escapeHtml(suggestion.title || 'Improvement Suggestion')}</div>
            <div class="suggestion-description">${escapeHtml(suggestion.description || '')}</div>
            <button class="view-suggestion-btn">View Changes</button>
        `;
        
        suggestionsList.appendChild(suggestionItem);
        
        // Add event listener to view button
        suggestionItem.querySelector('.view-suggestion-btn').addEventListener('click', () => {
            showFixModal({
                original_code: suggestion.before || '',
                refactored_code: suggestion.after || '',
                explanation: suggestion.description || ''
            });
        });
    });
    
    // Add to DOM after issues list
    const issuesList = document.getElementById('issues-list');
    if (issuesList.nextSibling) {
        issuesList.parentNode.insertBefore(container, issuesList.nextSibling);
    } else {
        issuesList.parentNode.appendChild(container);
    }
}

/**
 * Clear all issues from UI and state
 */
function clearIssues() {
    // Clear issues list
    document.getElementById('issues-list').innerHTML = '';
    
    // Remove suggestions container if it exists
    const suggestionsContainer = document.querySelector('.suggestions-container');
    if (suggestionsContainer) {
        suggestionsContainer.remove();
    }
    
    // Remove decorations
    state.decorations = state.editor.deltaDecorations(state.decorations, []);
    
    // Reset current issues
    state.currentIssues = [];
}

/**
 * Helper function to escape HTML
 * @param {string} text - Text to escape
 * @returns {string} Escaped HTML
 */
function escapeHtml(text) {
    if (!text) return '';
    
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Helper function to provide debouncing functionality
 * @param {Function} func - Function to debounce
 * @param {number} wait - Debounce wait time in ms
 * @returns {Function} Debounced function
 */
function debounce(func, wait) {
    let timeout;
    return function(...args) {
        const context = this;
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(context, args), wait);
    };
}