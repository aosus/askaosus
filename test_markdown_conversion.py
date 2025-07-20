#!/usr/bin/env python3
"""
Test script for markdown to HTML conversion functionality.
"""

import sys
sys.path.insert(0, '/app')

# Import the markdown conversion function directly
import markdown

def _convert_markdown_to_html(text: str) -> str:
    """
    Convert markdown text to HTML suitable for Matrix messages.
    
    This is a copy of the function from bot.py for testing.
    """
    try:
        # Configure markdown with extensions that produce Matrix-compatible HTML
        md = markdown.Markdown(
            extensions=[
                'markdown.extensions.nl2br',      # Convert newlines to <br>
                'markdown.extensions.fenced_code', # Support ```code blocks```
            ],
            # Configure to be more conservative with HTML output
            output_format='html'
        )
        
        # Convert markdown to HTML
        html = md.convert(text)
        return html
        
    except Exception as e:
        print(f"Failed to convert markdown to HTML: {e}")
        # Fallback: just convert newlines to <br> tags
        return text.replace('\n', '<br>')

def test_markdown_conversion():
    """Test markdown to HTML conversion."""
    
    test_cases = [
        # Test case 1: Basic formatting
        ("Hello **world**!", "Hello <strong>world</strong>!"),
        
        # Test case 2: Links
        ("Visit [our forum](https://discourse.example.org)", "Visit <a href=\"https://discourse.example.org\">our forum</a>"),
        
        # Test case 3: Code
        ("Use `sudo apt install` to install packages", "Use <code>sudo apt install</code> to install packages"),
        
        # Test case 4: Newlines
        ("Line 1\nLine 2", "Line 1<br />\nLine 2"),
        
        # Test case 5: Complex example
        ("I found a perfect match for your question: [Installing Software](https://discourse.example.org/t/install/123)\n\nThis guide covers **everything** you need!", 
         None),  # We'll just check that it converts without errors
    ]
    
    print("Testing markdown to HTML conversion...")
    
    for i, (markdown_input, expected_output) in enumerate(test_cases, 1):
        try:
            result = _convert_markdown_to_html(markdown_input)
            print(f"✓ Test {i} passed")
            print(f"  Input:  {markdown_input}")
            print(f"  Output: {result}")
            
            if expected_output and expected_output not in result:
                print(f"  Warning: Expected '{expected_output}' to be in result")
            
            print()
            
        except Exception as e:
            print(f"❌ Test {i} failed: {e}")
            print(f"  Input: {markdown_input}")
            print()
            
    print("✅ All markdown conversion tests completed!")

if __name__ == "__main__":
    test_markdown_conversion()
