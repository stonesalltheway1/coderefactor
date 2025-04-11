using System;
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
}