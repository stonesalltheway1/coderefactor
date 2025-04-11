// CodeRefactor JavaScript Test File

// Missing "use strict" directive

// Unused variables
var unusedVariable = 42;
let anotherUnusedVariable = "test";

// Global variables (potential issue)
globalVar = "I am global"; // Missing var/let/const

// Function with issues
function calculateTotal(items) {
    // Unused variable
    let count = items.length;
    
    let total = 0;
    
    for (var i = 0; i < items.length; i++) {
        total += items[i].price
    } // Missing semicolon above
    
    return total
} // Missing semicolon

// Potential null reference
function displayUser(user) {
    // No null check before accessing property
    console.log(user.name);
    document.getElementById('user-name').textContent = user.name;
}

// Inconsistent quotes
var message1 = "Hello";
var message2 = 'World';

// Potentially problematic comparison
function checkValue(value) {
    if (value == null) { // Using == instead of ===
        return false;
    }
    
    if (value = true) { // Assignment in condition (should be ==)
        return true;
    }
    
    return false;
}

// Unreachable code
function processData(data) {
    return data.processed;
    
    // Code after return
    data.isProcessed = true;
}

// Duplicate function parameters
function addValues(a, b, a) { // Duplicate parameter name
    return a + b;
}

// Example usage
const products = [
    { name: 'Apple', price: 0.5 },
    { name: 'Orange', price: 0.7 },
    { name: 'Banana', price: 0.3 }
];

// Function call with potential issues
const total = calculateTotal(products);
console.log('Total:', total);

// Undefined variable usage
console.log(undefinedVar);

// Event listener with potential memory leak (not removed)
document.addEventListener('click', function() {
    console.log('Document clicked');
});

// Inefficient DOM queries
function updateElements() {
    // Same query repeated multiple times
    document.getElementById('element1').style.color = 'red';
    document.getElementById('element1').style.fontWeight = 'bold';
    document.getElementById('element1').textContent = 'Updated';
}

// Potential infinite loop
function potentialInfiniteLoop(array) {
    for (let i = 0; i < array.length; i++) {
        if (array[i] === 'special') {
            // Missing increment, could lead to infinite loop
            continue;
        }
        console.log(array[i]);
    }
}