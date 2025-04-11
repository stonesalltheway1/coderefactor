"""
A simple Python file for testing the code analyzer and fixer.
"""

import os
import sys
import datetime  # Unused import

def add_numbers(a, b):
    """Add two numbers and return the result."""
    return a + b

def subtract_numbers(a, b):
    """Subtract b from a and return the result."""
    result = a - b  # This local variable is used
    return result

def multiply_numbers(a, b):
    """Multiply two numbers and return the result."""
    product = a * b  # Good: Variable is used
    return product

def divide_numbers(a, b):
    """Divide a by b and return the result."""
    # Issue: Missing check for division by zero
    return a / b

class Calculator:
    """A simple calculator class."""
    
    def __init__(self, initial_value=0):
        """Initialize the calculator with an optional initial value."""
        self.value = initial_value
        self._unused_attr = None  # Unused attribute
    
    def add(self, x):
        """Add x to the current value."""
        self.value += x
        return self
    
    def subtract(self, x):
        """Subtract x from the current value."""
        self.value -= x
        return self
    
    def get_value(self):
        """Return the current value."""
        return self.value
    
    def reset(self):
        """Reset the calculator to zero."""
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