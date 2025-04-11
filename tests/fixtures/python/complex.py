"""
A more complex Python file for testing the code analyzer and fixer.
Contains various code quality issues and edge cases.
"""

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
    """Data class for user information."""
    id: int
    name: str
    email: str
    active: bool = True
    created_at: Optional[datetime.datetime] = None
    metadata: Dict[str, Any] = None  # Issue: Should use field(default_factory=dict)


class DataProcessor:
    """Class for processing data with various quality issues."""
    
    def __init__(self, data_source: str, options: Optional[Dict[str, Any]] = None):
        """Initialize the processor with a data source and options."""
        self.data_source = data_source
        self.options = options or {}
        self.processed_items = 0
        self._cache = {}  # Private cache
        self._unUsed_variable = None  # Unused and badly named
    
    def process_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single data item."""
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
    
    def process_batch(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process a batch of items."""
        # Issue: Could use list comprehension
        results = []
        for item in items:
            processed = self.process_item(item)
            results.append(processed)
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics."""
        stats = {
            'processed_items': self.processed_items,
            'global_counter': global_counter,
            'cache_size': len(self._cache)
        }
        
        unused_var = 'This is unused'  # Unused variable
        
        return stats
    
    def clear_cache(self) -> None:
        """Clear the internal cache."""
        # Issue: Inefficient way to clear dict
        keys = list(self._cache.keys())
        for key in keys:
            del self._cache[key]
    
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Check if an email is valid."""
        # Issue: Regex is too simplistic
        pattern = r'[^@]+@[^@]+\.[^@]+'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def calculate_discount(price: float, discount_percent: float) -> float:
        """Calculate discounted price."""
        # Issue: Missing validation for negative values
        return price * (1 - discount_percent / 100)


def preprocess_data(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Preprocess data before main processing."""
    # Issue: Modifies input data
    for item in data:
        if 'name' in item:
            item['name'] = item['name'].title()
        
        if 'email' in item and not DataProcessor.is_valid_email(item['email']):
            # Issue: Silent failure
            item['email'] = None
    
    return data


def fetch_remote_data(url: str) -> Dict[str, Any]:
    """Fetch data from a remote source."""
    # Issue: No error handling
    import requests
    response = requests.get(url)
    return response.json()


def save_results(results: List[Dict[str, Any]], filename: str) -> bool:
    """Save processing results to a file."""
    try:
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        return True
    except IOError as e:
        # Issue: Catches exception but doesn't use it
        print("Error saving results")
        return False


def analyze_text(text: str) -> Dict[str, Any]:
    """Analyze text and return statistics."""
    # Issue: Inefficient algorithm
    words = text.split()
    word_count = len(words)
    
    # Count word frequencies
    word_freq = {}
    for word in words:
        word = word.lower().strip('.,!?;:()[]{}"\'-')
        if word:
            if word in word_freq:
                word_freq[word] += 1
            else:
                word_freq[word] = 1
    
    # Find most common words
    most_common = []
    max_freq = 0
    
    # Issue: Inefficient way to find max
    for word, freq in word_freq.items():
        if freq > max_freq:
            max_freq = freq
            most_common = [word]
        elif freq == max_freq:
            most_common.append(word)
    
    return {
        'word_count': word_count,
        'unique_words': len(word_freq),
        'most_common': most_common,
        'max_frequency': max_freq
    }


def generate_random_data(count: int) -> List[Dict[str, Any]]:
    """Generate random test data."""
    result = []
    
    for i in range(count):
        # Issue: Doesn't use a seed for reproducibility
        item = {
            'id': i + 1,
            'name': f"User {i + 1}",
            'email': f"user{i+1}@example.com",
            'age': random.randint(18, 80),
            'score': round(random.uniform(0, 100), 2),
            'active': random.choice([True, False]),
            'tags': random.sample(['tag1', 'tag2', 'tag3', 'tag4', 'tag5'], 
                                  k=random.randint(1, 3))
        }
        result.append(item)
    
    return result


# Testing code
if __name__ == "__main__":
    # Generate sample data
    data = generate_random_data(5)
    
    # Process the data
    processor = DataProcessor("sample")
    processed_data = processor.process_batch(data)
    
    # Print results
    for item in processed_data:
        print(f"Processed: {item}")
    
    # Example of poor error handling
    try:
        result = 10 / 0
    except:  # Issue: Bare except
        pass
    
    # Issue: Unreachable code
    if False:
        print("This will never execute")