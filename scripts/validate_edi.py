"""
Validate EDI file parsing (stretch goal).

This script tests basic EDI parsing functionality.
Currently a placeholder – would integrate edi-parser library.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agents.file_ingestor import FileIngestor

def validate_edi(filepath: str):
    """Validate EDI file structure (basic check)."""
    print(f"🔍 Validating EDI file: {filepath}")

    ingestor = FileIngestor()

    # Validate file exists and is EDI
    is_valid, error = ingestor.validate_file(filepath)
    if not is_valid:
        print(f"❌ {error}")
        return False

    print("✅ File format valid")

    # Read raw content
    with open(filepath, 'r') as f:
        content = f.read()

    # Basic EDI checks
    lines = content.strip().split('\n')
    print(f"   Lines: {len(lines)}")

    # Check for common EDI delimiters
    if '~' in content or '^' in content or ':' in content:
        print("✅ Contains EDI delimiters")
    else:
        print("⚠️  No standard EDI delimiters found – may not be EDI")

    print("\n⚠️  Note: Full EDI parsing not yet implemented (stretch goal)")
    print("   Would use: edi-parser library to convert to DataFrame")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_edi.py <edi_file>")
        sys.exit(1)

    filepath = sys.argv[1]
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        sys.exit(1)

    validate_edi(filepath)
