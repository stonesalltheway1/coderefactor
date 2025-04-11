"""
Pytest fixtures for all test modules.
"""
import os
import sys
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add the parent directory to the path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture(scope="session")
def fixtures_dir():
    """Create and return a temporary fixtures directory for the test session."""
    temp_dir = tempfile.mkdtemp()
    try:
        # Create subdirectories for each language
        langs = ["python", "csharp", "web"]
        for lang in langs:
            lang_dir = Path(temp_dir) / lang
            lang_dir.mkdir(exist_ok=True)
        
        yield Path(temp_dir)
    finally:
        shutil.rmtree(temp_dir)


@pytest.fixture(scope="session")
def python_fixtures_dir(fixtures_dir):
    """Return the Python fixtures directory."""
    python_dir = fixtures_dir / "python"
    
    # Create a simple Python file for testing
    with open(python_dir / "simple.py", "w") as f:
        f.write("""
import os
import sys
import datetime  # Unused import

def add_numbers(a, b):
    \"\"\"Add two numbers and return the result.\"\"\"
    return a + b

def subtract_numbers(a, b):
    \"\"\"Subtract b from a and return the result.\"\"\"
    result = a - b  # This local variable is used
    return result

def multiply_numbers(a, b):
    \"\"\"Multiply two numbers and return the result.\"\"\"
    product = a * b  # Good: Variable is used
    return product

def divide_numbers(a, b):
    \"\"\"Divide a by b and return the result.\"\"\"
    # Issue: Missing check for division by zero
    return a / b
""")
    
    yield python_dir


@pytest.fixture(scope="session")
def csharp_fixtures_dir(fixtures_dir):
    """Return the C# fixtures directory."""
    csharp_dir = fixtures_dir / "csharp"
    
    # Create a simple C# file for testing
    with open(csharp_dir / "simple.cs", "w") as f:
        f.write("""using System;
using System.Collections.Generic;
using System.Linq;  // Unused namespace

namespace CodeRefactorTests
{
    /// <summary>
    /// A simple calculator class for testing the code analyzer and fixer.
    /// </summary>
    public class Calculator
    {
        // Unused field
        private int unusedField;

        /// <summary>
        /// Adds two numbers.
        /// </summary>
        /// <param name="a">First number</param>
        /// <param name="b">Second number</param>
        /// <returns>The sum of a and b</returns>
        public int Add(int a, int b)
        {
            return a + b;
        }

        /// <summary>
        /// Subtracts the second number from the first.
        /// </summary>
        /// <param name="a">First number</param>
        /// <param name="b">Second number</param>
        /// <returns>The result of a - b</returns>
        public int Subtract(int a, int b)
        {
            return a - b;
        }
    }
}""")
    
    yield csharp_dir


@pytest.fixture(scope="session")
def web_fixtures_dir(fixtures_dir):
    """Return the web fixtures directory."""
    web_dir = fixtures_dir / "web"
    
    # Create sample HTML, CSS, and JS files for testing
    with open(web_dir / "simple.html", "w") as f:
        f.write("""<html>
<head>
    <title>Test Page</title>
</head>
<body>
    <h1>Hello World!</h1>
    <img src=image.jpg alt=Image>
    <DIV class="container">
        <p>This is a paragraph
        <p>This is another paragraph</p>
    </DIV>
</body>
</html>""")
    
    with open(web_dir / "simple.css", "w") as f:
        f.write("""body {
    color: red;
    background-color: white
    font-size: 14px
}

h1 {
    color: blue;
    text-align: center
}

.container {
    width: 100%;
    padding: 20px;
    margin: 0
}""")
    
    with open(web_dir / "simple.js", "w") as f:
        f.write("""// Sample JavaScript with issues
function calculateTotal(items) {
    let total = 0;
    
    // Unused variable
    let count = items.length;
    
    for (let i = 0; i < items.length; i++) {
        total += items[i].price;
    }
    
    return total
}  // Missing semicolon

// Example usage
const products = [
    { name: 'Apple', price: 0.5 },
    { name: 'Orange', price: 0.7 },
    { name: 'Banana', price: 0.3 }
];

const total = calculateTotal(products);
console.log('Total:', total);
""")
    
    yield web_dir


@pytest.fixture
def sample_python_code():
    """Return a sample Python code with common issues for testing."""
    return """
import os
import sys
import datetime  # Unused import

def add_numbers(a, b):
    \"\"\"Add two numbers and return the result.\"\"\"
    return a + b

def subtract_numbers(a, b):
    \"\"\"Subtract b from a and return the result.\"\"\"
    result = a - b  # This local variable is used
    return result

def multiply_numbers(a, b):
    \"\"\"Multiply two numbers and return the result.\"\"\"
    product = a * b  # Good: Variable is used
    return product

def divide_numbers(a, b):
    \"\"\"Divide a by b and return the result.\"\"\"
    # Issue: Missing check for division by zero
    return a / b

class Calculator:
    \"\"\"A simple calculator class.\"\"\"
    
    def __init__(self, initial_value=0):
        \"\"\"Initialize the calculator with an optional initial value.\"\"\"
        self.value = initial_value
        self._unused_attr = None  # Unused attribute
    
    def add(self, x):
        \"\"\"Add x to the current value.\"\"\"
        self.value += x
        return self
    
    def subtract(self, x):
        \"\"\"Subtract x from the current value.\"\"\"
        self.value -= x
        return self
    
    def get_value(self):
        \"\"\"Return the current value.\"\"\"
        return self.value
    
    def reset(self):
        \"\"\"Reset the calculator to zero.\"\"\"
        old_value = self.value  # Unused variable
        self.value = 0
        return self

# Example usage
if __name__ == "__main__":
    x = 10
    y = 5
    
    # Calculate and print results
    print(f"Add: {add_numbers(x, y)}")
    print(f"Subtract: {subtract_numbers(x, y)}")
    print(f"Multiply: {multiply_numbers(x, y)}")
    
    try:
        print(f"Divide: {divide_numbers(x, y)}")
    except ZeroDivisionError:
        print("Cannot divide by zero")
    
    # Create and use calculator
    calc = Calculator(x)
    calc.add(y).subtract(3)
    print(f"Calculator: {calc.get_value()}")
"""


@pytest.fixture
def sample_csharp_code():
    """Return a sample C# code with common issues for testing."""
    return """using System;
using System.Collections.Generic;
using System.Linq;  // Unused namespace

namespace CodeRefactorTests
{
    /// <summary>
    /// A simple calculator class for testing the code analyzer and fixer.
    /// </summary>
    public class Calculator
    {
        // Unused field
        private int unusedField;

        /// <summary>
        /// Adds two numbers.
        /// </summary>
        /// <param name="a">First number</param>
        /// <param name="b">Second number</param>
        /// <returns>The sum of a and b</returns>
        public int Add(int a, int b)
        {
            return a + b;
        }

        /// <summary>
        /// Subtracts the second number from the first.
        /// </summary>
        /// <param name="a">First number</param>
        /// <param name="b">Second number</param>
        /// <returns>The result of a - b</returns>
        public int Subtract(int a, int b)
        {
            return a - b;
        }

        /// <summary>
        /// Multiplies two numbers.
        /// </summary>
        /// <param name="a">First number</param>
        /// <param name="b">Second number</param>
        /// <returns>The product of a and b</returns>
        public int Multiply(int a, int b)
        {
            return a * b;
        }

        /// <summary>
        /// Divides the first number by the second.
        /// </summary>
        /// <param name="a">First number</param>
        /// <param name="b">Second number</param>
        /// <returns>The result of a / b</returns>
        public double Divide(int a, int b)
        {
            // Missing null check
            return a / b;  // Potential division by zero
        }

        /// <summary>
        /// Calculates the average of a list of numbers.
        /// </summary>
        /// <param name="numbers">List of numbers</param>
        /// <returns>The average of the numbers</returns>
        public double Average(List<int> numbers)
        {
            // Issue: Potential null reference exception
            int sum = 0;
            foreach (int number in numbers)
            {
                sum += number;
            }
            
            return sum / numbers.Count;  // Potential division by zero
        }
    }

    /// <summary>
    /// Main program class.
    /// </summary>
    public class Program
    {
        /// <summary>
        /// Entry point of the application.
        /// </summary>
        /// <param name="args">Command line arguments</param>
        public static void Main(string[] args)
        {
            // Unused variable
            string Greeting = "Hello, World!";
            
            // Create a calculator
            Calculator calculator = new Calculator();
            
            // Perform calculations
            int a = 10;
            int b = 5;
            
            Console.WriteLine($"Add: {calculator.Add(a, b)}");
            Console.WriteLine($"Subtract: {calculator.Subtract(a, b)}");
            Console.WriteLine($"Multiply: {calculator.Multiply(a, b)}");
            
            // Issue: No try-catch for potential exception
            Console.WriteLine($"Divide: {calculator.Divide(a, b)}");
            
            // Create a list of numbers
            List<int> numbers = new List<int> { 1, 2, 3, 4, 5 };
            
            // Calculate and display the average
            double average = calculator.Average(numbers);
            Console.WriteLine($"Average: {average}");
            
            // Wait for user input before exiting
            Console.WriteLine("Press any key to exit...");
            Console.ReadKey();
        }
    }
}"""


@pytest.fixture
def sample_html_code():
    """Return a sample HTML code with common issues for testing."""
    return """<html>
<head>
    <title>Test Page</title>
</head>
<body>
    <h1>Hello World!</h1>
    <img src=image.jpg alt=Image>
    <DIV class="container">
        <p>This is a paragraph
        <p>This is another paragraph</p>
    </DIV>
    <span style="color: #1234ZZ">Invalid color</span>
</body>
</html>"""


@pytest.fixture
def sample_css_code():
    """Return a sample CSS code with common issues for testing."""
    return """body {
    color: red;
    background-color: white
    font-size: 14px
}

h1 {
    color: blue;
    text-align: center
}

.container {
    width: 100%;
    padding: 20px;
    margin: 0
}

#header {
    color: #1234ZZ;  /* Invalid color */
    background-color: redd;  /* Misspelled color */
}"""


@pytest.fixture
def sample_js_code():
    """Return a sample JavaScript code with common issues for testing."""
    return """// Sample JavaScript with issues
function calculateTotal(items) {
    let total = 0;
    
    // Unused variable
    let count = items.length;
    
    for (let i = 0; i < items.length; i++) {
        total += items[i].price;
    }
    
    return total
}  // Missing semicolon

// Potential null reference
function displayUser(user) {
    console.log(user.name);  // No null check
}

// Example usage
const products = [
    { name: 'Apple', price: 0.5 },
    { name: 'Orange', price: 0.7 },
    { name: 'Banana', price: 0.3 }
];

const total = calculateTotal(products);
console.log('Total:', total);

// Undefined variable
console.log(discount);  // Undefined
"""


@pytest.fixture
def complex_python_code():
    """Return a more complex Python code for testing."""
    return """
import os
import sys
import re
import json
import datetime
import math
import random
from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass


# Global variable
global_counter = 0


@dataclass
class UserData:
    \"\"\"Data class for user information.\"\"\"
    id: int
    name: str
    email: str
    active: bool = True
    created_at: Optional[datetime.datetime] = None
    metadata: Dict[str, Any] = None  # Issue: Should use field(default_factory=dict)


class DataProcessor:
    \"\"\"Class for processing data with various quality issues.\"\"\"
    
    def __init__(self, data_source: str, options: Optional[Dict[str, Any]] = None):
        \"\"\"Initialize the processor with a data source and options.\"\"\"
        self.data_source = data_source
        self.options = options or {}
        self.processed_items = 0
        self._cache = {}  # Private cache
        self._unUsed_variable = None  # Unused and badly named
    
    def process_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        \"\"\"Process a single data item.\"\"\"
        global global_counter
        
        # Increment counters
        self.processed_items += 1
        global_counter += 1
        
        # Issue: Unnecessarily complex code
        result = {}
        for key, value in item.items():
            if isinstance(value, str):
                # Issue: Uses strip() but doesn't check if needed
                result[key] = value.strip()
            elif isinstance(value, (int, float)):
                if value < 0:
                    # Issue: Magic number
                    result[key] = value * 1.1
                else:
                    result[key] = value
            elif isinstance(value, list):
                # Issue: Creates a new list unnecessarily
                new_list = []
                for subvalue in value:
                    new_list.append(subvalue)
                result[key] = new_list
            else:
                result[key] = value
        
        # Cache the result
        item_id = item.get('id')
        if item_id:
            self._cache[item_id] = result
        
        return result
"""


@pytest.fixture
def complex_csharp_code():
    """Return a more complex C# code for testing."""
    return """using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.IO;  // Unused namespace
using System.Diagnostics;  // Unused namespace

namespace CodeRefactorTests.Complex
{
    /// <summary>
    /// Data model for a user with quality issues.
    /// </summary>
    public class User
    {
        // Public fields (which should be properties)
        public int ID;
        public string Name;
        public string Email;
        
        // Unused private field
        private DateTime registrationDate;
        
        // Inconsistent naming convention (not camelCase)
        private bool IsActive;
        
        /// <summary>
        /// Default constructor.
        /// </summary>
        public User()
        {
            ID = 0;
            Name = string.Empty;
            Email = string.Empty;
            registrationDate = DateTime.Now;
            IsActive = true;
        }
        
        /// <summary>
        /// Constructor with parameters.
        /// </summary>
        public User(int id, string name, string email)
        {
            ID = id;
            Name = name;
            Email = email;
            registrationDate = DateTime.Now;
            IsActive = true;
        }
        
        /// <summary>
        /// Gets a display name for the user.
        /// </summary>
        public string GetDisplayName()
        {
            // Redundant check (null comparison for value type)
            if (ID == null)
            {
                return Name;
            }
            
            return $"{ID}: {Name}";
        }
        
        /// <summary>
        /// Validates the user email.
        /// </summary>
        public bool ValidateEmail()
        {
            // Overly simplified validation
            return Email.Contains("@");
        }
        
        /// <summary>
        /// Updates user status.
        /// </summary>
        /// <param name="active">New active status</param>
        public void SetStatus(bool active)
        {
            // Unused variable
            bool previousStatus = IsActive;
            
            IsActive = active;
        }
    }
}"""


@pytest.fixture
def python_analyzer():
    """Create a PythonAnalyzer instance for testing."""
    try:
        from coderefactor.analyzers.python_analyzer import PythonAnalyzer
        return PythonAnalyzer()
    except (ImportError, ModuleNotFoundError):
        pytest.skip("Python analyzer not available")


@pytest.fixture
def csharp_analyzer():
    """Create a CSharpAnalyzer instance for testing."""
    try:
        from coderefactor.analyzers.csharp_analyzer import CSharpAnalyzer
        return CSharpAnalyzer()
    except (ImportError, ModuleNotFoundError):
        return None  # Will be skipped in tests that require it


@pytest.fixture
def web_analyzer():
    """Create a WebTechAnalyzer instance for testing."""
    try:
        from coderefactor.analyzers.web_analyzer import WebTechAnalyzer
        return WebTechAnalyzer()
    except (ImportError, ModuleNotFoundError):
        pytest.skip("Web analyzer not available")


@pytest.fixture
def python_fixer():
    """Create a PythonFixer instance for testing."""
    try:
        from coderefactor.fixers.python_fixer import PythonFixer
        return PythonFixer()
    except (ImportError, ModuleNotFoundError):
        pytest.skip("Python fixer not available")


@pytest.fixture
def csharp_fixer():
    """Create a CSharpFixer instance for testing."""
    try:
        from coderefactor.fixers.csharp_fixer import CSharpFixer
        return CSharpFixer()
    except (ImportError, ModuleNotFoundError):
        return None  # Will be skipped in tests that require it


@pytest.fixture
def web_fixer():
    """Create a WebTechFixer instance for testing."""
    try:
        from coderefactor.fixers.web_fixer import WebTechFixer
        return WebTechFixer()
    except (ImportError, ModuleNotFoundError):
        pytest.skip("Web fixer not available")