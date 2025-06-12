#!/usr/bin/env python3
"""
Simple test runner for backend abstraction layer.
This script ensures all imports work before running tests.
"""

import sys
import os
import subprocess

def check_imports():
    """Check if all backend modules can be imported."""
    print("🔍 Checking backend imports...")
    
    try:
        # Add current directory to Python path
        sys.path.insert(0, '.')
        
        # Test basic imports
        from backends.base import LLMBackend, BackendType, GenerationResponse
        from backends.models import ResponseNormalizer, ConfigValidator
        from backends.ollama import OllamaBackend
        from backends.llama_cpp import LlamaCppBackend
        from backends.manager import BackendManager
        
        print("✅ All backend imports successful!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure all backend files are created and contain the correct code.")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def check_dependencies():
    """Check if test dependencies are installed."""
    print("🔍 Checking test dependencies...")
    
    try:
        import pytest
        import aiohttp
        print("✅ Test dependencies available!")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Install with: pip install pytest pytest-asyncio pytest-mock aiohttp")
        return False

def run_tests():
    """Run the backend tests."""
    print("🧪 Running backend tests...")
    
    # Run pytest with specific configuration
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/test_backends.py",
        "-v",
        "--tb=short",
        "--disable-warnings"
    ]
    
    try:
        result = subprocess.run(cmd, check=False, capture_output=False)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False

def main():
    """Main test runner."""
    print("🚀 Backend Abstraction Layer Test Runner")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists("backends"):
        print("❌ backends/ directory not found.")
        print("Make sure you're running this from the chat-o-llama project root.")
        sys.exit(1)
    
    # Check virtual environment
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Warning: Virtual environment not detected.")
        print("It's recommended to activate your virtual environment first:")
        print("  source venv/bin/activate")
        print()
    
    # Run checks
    checks_passed = 0
    total_checks = 3
    
    if check_dependencies():
        checks_passed += 1
    
    if check_imports():
        checks_passed += 1
    
    if checks_passed < 2:
        print(f"❌ {total_checks - checks_passed} checks failed. Cannot run tests.")
        sys.exit(1)
    
    # Run tests
    print()
    if run_tests():
        checks_passed += 1
        print()
        print("🎉 All tests passed! Backend abstraction layer is working correctly.")
        print()
        print("Next steps:")
        print("- You can now proceed with Phase 2 (Database & Frontend Integration)")
        print("- The backend abstraction layer is ready for production use")
    else:
        print()
        print("❌ Some tests failed. Check the output above for details.")
        print()
        print("Common issues:")
        print("- Missing backend files (make sure all files from artifacts are created)")
        print("- Import path issues (make sure you're in the project root)")
        print("- Missing dependencies (run: pip install pytest pytest-asyncio pytest-mock aiohttp)")
        sys.exit(1)
    
    print(f"✅ {checks_passed}/{total_checks} checks passed!")

if __name__ == "__main__":
    main()
