# Rin V0 Implementation Tips

This document contains practical tips and solutions for common issues you might encounter while implementing Rin V0 features, based on real implementation experiences.

## Regular Expression Best Practices

When implementing natural language processing features in Rin, especially for the list management, reminders, and other text parsing features, you'll use regular expressions extensively. Here are some best practices to avoid common errors:

### 1. Simplify Complex Patterns

Complex regex patterns with multiple nested capture groups, quote handling, and lookaheads/lookbehinds can lead to syntax errors and maintenance challenges.

**Instead of:**
```python
# Complex pattern with potential syntax errors
match = re.search(r"(?:list|called|named) ['\""]?([^'\""]*?)['\""]?(?: list)?(?:$| to | from )", query)
```

**Consider:**
```python
# Breaking down into multiple simpler patterns
def _extract_list_name(query):
    # Try multiple patterns one at a time
    match = re.search(r"list ([a-zA-Z0-9_\- ]+)(?: list)?", query)
    if match:
        return match.group(1).strip()
    
    match = re.search(r"called ([a-zA-Z0-9_\- ]+)", query)
    if match:
        return match.group(1).strip()
        
    match = re.search(r"named ([a-zA-Z0-9_\- ]+)", query)
    if match:
        return match.group(1).strip()
        
    return None
```

### 2. Prefer Explicit Character Classes

When matching text with variable content, prefer explicit character classes over negated patterns:

**Instead of:**
```python
# Negated character class can be error-prone when escaping
pattern = r"add ['\""]?([^'\""]*?)['\""]? to"
```

**Consider:**
```python
# More explicit about what characters are allowed
pattern = r"add ([a-zA-Z0-9_\- ]+) to"
```

### 3. Validate Parentheses Balance

Always ensure your regex patterns have properly balanced parentheses. Unbalanced parentheses can cause runtime errors that are difficult to debug.

**Tips:**
- Use a regex validator tool before implementing complex patterns
- Pay special attention to nested capture groups and non-capturing groups
- Visual inspection: count the opening `(` and closing `)` parentheses

### 4. Gradually Build Complex Patterns

When implementing a complex pattern, build it incrementally:

1. Start with a simple pattern targeting the core text
2. Test it with various inputs
3. Gradually add complexity and optional components
4. Test after each addition

## Testing and Debugging

### 1. Test Pattern Matching Separately

For complex natural language parsing, create simple test functions to validate your regex patterns before integrating them into your code:

```python
def test_pattern(pattern, test_cases):
    """Test a regex pattern against multiple test cases."""
    for input_text, expected_match in test_cases:
        match = re.search(pattern, input_text)
        result = match.group(1) if match else None
        print(f"Input: '{input_text}'")
        print(f"  Expected: '{expected_match}', Got: '{result}'")
        print(f"  {'✅ PASS' if result == expected_match else '❌ FAIL'}")

# Example usage
test_pattern(r"list ([a-zA-Z0-9_\- ]+)(?: list)?", [
    ("show my shopping list", "shopping"),
    ("create a grocery list", None),  # Should not match this pattern
    ("list todo items", "todo"),
])
```

### 2. Add Detailed Logging

To diagnose regex pattern issues in production, add detailed debugging logs:

```python
import logging
logger = logging.getLogger(__name__)

def _extract_list_name(query):
    patterns = [
        r"list ([a-zA-Z0-9_\- ]+)(?: list)?",
        r"called ([a-zA-Z0-9_\- ]+)",
        r"named ([a-zA-Z0-9_\- ]+)"
    ]
    
    logger.debug(f"Attempting to extract list name from: '{query}'")
    for i, pattern in enumerate(patterns):
        match = re.search(pattern, query)
        if match:
            result = match.group(1).strip()
            logger.debug(f"Pattern {i+1} matched: '{result}'")
            return result
    
    logger.debug("No patterns matched for list name extraction")
    return None
```

## SQLite and Async Operations

### 1. Database Connection Management

When using SQLite with aiosqlite, ensure proper connection management:

```python
async def add_item(self, list_name, item):
    """Add an item to a list"""
    await self._init_db()  # Always ensure the DB is initialized
    try:
        async with aiosqlite.connect(self.db_path) as db:  # Use context manager
            # Database operations...
            await db.commit()  # Don't forget to commit
        return True
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        return False  # Return meaningful value on error
```

### 2. Error Handling in Async Methods

For robust async operations, implement proper error handling:

```python
async def process_query(self, query, respond_with_voice=False):
    """Process a text query and return response"""
    try:
        # Process the query...
    except aiosqlite.Error as e:
        logger.error(f"Database error: {str(e)}", exc_info=True)
        return {"error": "Database error", "text": "I'm having trouble accessing my storage."}
    except asyncio.CancelledError:
        logger.warning("Query processing was cancelled")
        raise  # Re-raise cancellation
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}", exc_info=True)
        return {"error": str(e), "text": "I encountered an error while processing your request."}
```

## Cross-Platform Compatibility

### 1. Path Handling

Use `pathlib.Path` for cross-platform path handling:

```python
from pathlib import Path

# Instead of:
db_path = os.path.join(RIN_DIR, "rin.db")

# Use:
db_path = Path(RIN_DIR) / "rin.db"
```

### 2. Notification and Audio

Implement fallbacks for platform-specific features:

```python
async def _show_notification(self, title, message):
    """Show notification with fallbacks"""
    try:
        # Try platform-specific notification
        notification.notify(title=title, message=message)
    except Exception as e:
        logger.error(f"Notification error: {str(e)}")
        # Fallback to console
        print(f"\n[NOTIFICATION] {title}: {message}\n")
```

## Refactoring for Maintainability

### 1. Extract Complex Logic

When implementing features like list management or reminder handling, extract complex parsing logic into separate methods:

```python
# Instead of having all logic in handle_list_command:
async def handle_list_command(self, query):
    """Parse and handle list commands"""
    if self._is_create_list_command(query):
        return await self._create_list(query)
    elif self._is_show_lists_command(query):
        return await self._show_lists()
    elif self._is_show_list_command(query):
        return await self._show_list(query)
    # ...

def _is_create_list_command(self, query):
    """Check if query is a create list command"""
    return "create" in query.lower() and "list" in query.lower()

async def _create_list(self, query):
    """Handle creating a list"""
    list_name = self._extract_list_name(query)
    # ...
```

By following these best practices, you'll avoid common implementation pitfalls and create a more robust Rin V0 assistant.
