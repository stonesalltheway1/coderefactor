using System;
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
    
    /// <summary>
    /// Data processor class with various code quality issues.
    /// </summary>
    public class DataProcessor
    {
        // Inconsistent naming (should be camelCase)
        private List<User> UserList;
        
        // Not initialized in constructor
        private Dictionary<int, User> userCache;
        
        // Readonly field not marked as readonly
        private string connectionString;
        
        /// <summary>
        /// Default constructor.
        /// </summary>
        public DataProcessor()
        {
            UserList = new List<User>();
            connectionString = "Default";
            // Missing initialization for userCache
        }
        
        /// <summary>
        /// Constructor with connection string.
        /// </summary>
        /// <param name="connection">Database connection string</param>
        public DataProcessor(string connection)
        {
            UserList = new List<User>();
            connectionString = connection;
            // Still missing initialization for userCache
        }
        
        /// <summary>
        /// Adds a user to the list.
        /// </summary>
        /// <param name="user">User to add</param>
        public void AddUser(User user)
        {
            // Missing null check
            UserList.Add(user);
            
            // Potential null reference exception
            userCache.Add(user.ID, user);
        }
        
        /// <summary>
        /// Finds a user by ID.
        /// </summary>
        /// <param name="id">User ID</param>
        /// <returns>The found user or null</returns>
        public User FindUser(int id)
        {
            // Inefficient search (should use dictionary)
            foreach (User user in UserList)
            {
                if (user.ID == id)
                {
                    return user;
                }
            }
            
            return null;  // Should return default or use nullable reference type
        }
        
        /// <summary>
        /// Processes all users in the list.
        /// </summary>
        /// <returns>Number of processed users</returns>
        public int ProcessUsers()
        {
            // Unnecessarily complex loop
            int count = 0;
            for (int i = 0; i < UserList.Count; i++)
            {
                User user = UserList[i];
                
                // Empty if branch
                if (user != null)
                {
                    // Do nothing
                }
                
                // Missing else branch
                
                count++;
            }
            
            return count;
        }
        
        /// <summary>
        /// Gets active users.
        /// </summary>
        /// <returns>List of active users</returns>
        public List<User> GetActiveUsers()
        {
            // Missing implementation, unused field
            throw new NotImplementedException();
        }
        
        /// <summary>
        /// Analyzes user data.
        /// </summary>
        /// <returns>Analysis result string</returns>
        public string AnalyzeData()
        {
            // Magic numbers
            if (UserList.Count < 10)
            {
                return "Small dataset";
            }
            else if (UserList.Count < 100)
            {
                return "Medium dataset";
            }
            else
            {
                return "Large dataset";
            }
        }
    }
    
    /// <summary>
    /// Static utility class with issues.
    /// </summary>
    public static class DataUtility
    {
        /// <summary>
        /// Generates random users.
        /// </summary>
        /// <param name="count">Number of users to generate</param>
        /// <returns>List of randomly generated users</returns>
        public static List<User> GenerateRandomUsers(int count)
        {
            // Not using a seed for random (bad for testing)
            Random random = new Random();
            List<User> users = new List<User>();
            
            for (int i = 0; i < count; i++)
            {
                // Missing increment
                User user = new User(i, $"User{i}", $"user{i}@example.com");
                users.Add(user);
            }
            
            return users;
        }
        
        /// <summary>
        /// Calculates average ID in a list of users.
        /// </summary>
        /// <param name="users">List of users</param>
        /// <returns>Average ID value</returns>
        public static double CalculateAverageId(List<User> users)
        {
            // Missing null check
            // Potential arithmetic overflow
            int sum = 0;
            foreach (User user in users)
            {
                sum += user.ID;
            }
            
            // Potential division by zero
            return sum / users.Count;
        }
        
        /// <summary>
        /// Verifies all emails in a list of users.
        /// </summary>
        /// <param name="users">List of users to verify</param>
        /// <returns>Whether all emails are valid</returns>
        public static bool VerifyAllEmails(List<User> users)
        {
            // Manual iteration instead of using LINQ
            foreach (User user in users)
            {
                if (!user.ValidateEmail())
                {
                    return false;
                }
            }
            
            return true;
        }
    }
    
    /// <summary>
    /// Demo program with quality issues.
    /// </summary>
    public class Program
    {
        /// <summary>
        /// Main entry point.
        /// </summary>
        static void Main(string[] args)
        {
            // Unused variable
            string greeting = "Hello, Complex C# Example!";
            
            try
            {
                // Create a data processor
                DataProcessor processor = new DataProcessor("test-connection");
                
                // Generate random users
                List<User> users = DataUtility.GenerateRandomUsers(5);
                
                // Add users to processor
                foreach (User user in users)
                {
                    processor.AddUser(user);
                }
                
                // Process users
                int processedCount = processor.ProcessUsers();
                Console.WriteLine($"Processed {processedCount} users");
                
                // Calculate average ID
                double averageId = DataUtility.CalculateAverageId(users);
                Console.WriteLine($"Average ID: {averageId}");
                
                // Verify emails
                bool allEmailsValid = DataUtility.VerifyAllEmails(users);
                Console.WriteLine($"All emails valid: {allEmailsValid}");
                
                // Analyze data
                string analysisResult = processor.AnalyzeData();
                Console.WriteLine($"Analysis result: {analysisResult}");
            }
            catch (Exception ex)
            {
                // Empty catch block
            }
            finally
            {
                // Unreachable code (always runs)
                if (false)
                {
                    Console.WriteLine("This will never execute");
                }
            }
            
            // Wait for user input before exiting
            Console.WriteLine("Press any key to exit...");
            Console.ReadKey();
        }
    }
}