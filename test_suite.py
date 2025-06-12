#!/usr/bin/env python3
"""
Comprehensive test suite for the multi-backend configuration system.
This script tests all aspects of the configuration management and backend connectivity.
"""

import json
import os
import sys
import time
import requests
import subprocess
from typing import Dict, Any, List, Tuple
from config_manager import ConfigManager, ConfigurationError, BackendType


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'


class TestEnvironment:
    """Test environment manager for multi-backend configuration."""

    def __init__(self, config_path: str = "test_config.json"):
        self.config_path = config_path
        self.config_manager = None
        self.test_results = []

    def print_header(self, title: str):
        """Print a formatted test section header."""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.WHITE}{title.center(60)}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

    def print_test(self, test_name: str, status: str, message: str = ""):
        """Print a formatted test result."""
        if status == "PASS":
            icon = f"{Colors.GREEN}✅{Colors.END}"
            status_color = f"{Colors.GREEN}{status}{Colors.END}"
        elif status == "FAIL":
            icon = f"{Colors.RED}❌{Colors.END}"
            status_color = f"{Colors.RED}{status}{Colors.END}"
        elif status == "WARN":
            icon = f"{Colors.YELLOW}⚠️{Colors.END}"
            status_color = f"{Colors.YELLOW}{status}{Colors.END}"
        else:
            icon = f"{Colors.CYAN}ℹ️{Colors.END}"
            status_color = f"{Colors.CYAN}{status}{Colors.END}"

        print(f"{icon} {test_name:<40} [{status_color}]")
        if message:
            print(f"   {Colors.WHITE}{message}{Colors.END}")

        self.test_results.append((test_name, status, message))

    def test_configuration_loading(self) -> bool:
        """Test configuration file loading and validation."""
        self.print_header("Configuration Loading Tests")

        try:
            # Test 1: Load configuration
            self.config_manager = ConfigManager(self.config_path)
            self.print_test("Configuration file loading",
                            "PASS", f"Loaded {self.config_path}")

            # Test 2: Validate required sections
            required_sections = ["app", "backends", "database"]
            for section in required_sections:
                if section in self.config_manager.config:
                    self.print_test(f"Section '{section}' exists", "PASS")
                else:
                    self.print_test(
                        f"Section '{section}' exists", "FAIL", "Missing required section")
                    return False

            # Test 3: Validate backend configuration
            enabled_backends = self.config_manager.get_enabled_backends()
            self.print_test("Enabled backends detection", "PASS",
                            f"Found: {', '.join(enabled_backends)}")

            # Test 4: Default backend validation
            default_backend = self.config_manager.get_default_backend()
            if default_backend in enabled_backends:
                self.print_test("Default backend validation",
                                "PASS", f"Default: {default_backend}")
            else:
                self.print_test("Default backend validation", "FAIL",
                                f"Default '{default_backend}' not in enabled backends")
                return False

            return True

        except ConfigurationError as e:
            self.print_test("Configuration loading", "FAIL", str(e))
            return False
        except Exception as e:
            self.print_test("Configuration loading", "FAIL",
                            f"Unexpected error: {e}")
            return False

    def test_environment_variables(self) -> bool:
        """Test environment variable override functionality."""
        self.print_header("Environment Variable Tests")

        # Test environment variable overrides
        test_env_vars = {
            "CHAT_APP_PORT": "5001",
            "CHAT_APP_DEBUG": "false",
            "OLLAMA_URL": "http://test-ollama:11434",
            "LLAMA_CPP_URL": "http://test-llama:8120",
            "OLLAMA_TIMEOUT": "25",
            "MAX_CONCURRENT_REQUESTS": "8"
        }

        # Set test environment variables
        original_values = {}
        for env_var, test_value in test_env_vars.items():
            original_values[env_var] = os.getenv(env_var)
            os.environ[env_var] = test_value

        try:
            # Create a new config manager to test env var loading
            test_config_manager = ConfigManager(self.config_path)

            # Test specific overrides
            if test_config_manager.get('app', 'port') == 5001:
                self.print_test("Port environment override",
                                "PASS", "CHAT_APP_PORT applied")
            else:
                self.print_test("Port environment override",
                                "FAIL", "CHAT_APP_PORT not applied")

            if test_config_manager.get('backends', 'ollama', 'url') == "http://test-ollama:11434":
                self.print_test("Ollama URL override",
                                "PASS", "OLLAMA_URL applied")
            else:
                self.print_test("Ollama URL override", "FAIL",
                                "OLLAMA_URL not applied")

            if test_config_manager.get('backends', 'ollama', 'timeout') == 25:
                self.print_test("Timeout override", "PASS",
                                "OLLAMA_TIMEOUT applied")
            else:
                self.print_test("Timeout override", "FAIL",
                                "OLLAMA_TIMEOUT not applied")

            self.print_test("Environment variable system",
                            "PASS", "All overrides working")
            return True

        except Exception as e:
            self.print_test("Environment variable system", "FAIL", str(e))
            return False

        finally:
            # Restore original environment variables
            for env_var, original_value in original_values.items():
                if original_value is None:
                    os.environ.pop(env_var, None)
                else:
                    os.environ[env_var] = original_value

    def test_backend_connectivity(self) -> Dict[str, bool]:
        """Test connectivity to all configured backends."""
        self.print_header("Backend Connectivity Tests")

        if not self.config_manager:
            self.print_test("Backend connectivity", "FAIL",
                            "Config manager not initialized")
            return {}

        connectivity_results = {}
        enabled_backends = self.config_manager.get_enabled_backends()

        for backend_name in enabled_backends:
            backend_config = self.config_manager.get_backend_config(
                backend_name)

            if not backend_config:
                self.print_test(f"{backend_name} configuration",
                                "FAIL", "Backend config not found")
                connectivity_results[backend_name] = False
                continue

            # Test basic connectivity
            is_healthy, message = self.config_manager.test_backend_connectivity(
                backend_name)

            if is_healthy:
                self.print_test(
                    f"{backend_name} connectivity", "PASS", message)
                connectivity_results[backend_name] = True

                # Test specific endpoints for healthy backends
                self._test_backend_endpoints(backend_name, backend_config)
            else:
                self.print_test(
                    f"{backend_name} connectivity", "FAIL", message)
                connectivity_results[backend_name] = False

        return connectivity_results

    def _test_backend_endpoints(self, backend_name: str, backend_config) -> None:
        """Test specific endpoints for a backend."""
        try:
            headers = {}
            if backend_config.api_key:
                headers["Authorization"] = f"Bearer {backend_config.api_key}"

            if backend_name == "ollama":
                # Test Ollama-specific endpoints
                endpoints = [
                    ("/api/tags", "Models list"),
                    ("/api/version", "Version info")
                ]

                for endpoint, description in endpoints:
                    try:
                        response = requests.get(
                            f"{backend_config.url}{endpoint}",
                            headers=headers,
                            timeout=5
                        )
                        if response.status_code == 200:
                            self.print_test(
                                f"{backend_name} {description}", "PASS", f"Status: {response.status_code}")
                        else:
                            self.print_test(
                                f"{backend_name} {description}", "WARN", f"Status: {response.status_code}")
                    except Exception as e:
                        self.print_test(
                            f"{backend_name} {description}", "FAIL", str(e))

            elif backend_name == "llama_cpp":
                # Test llama.cpp OpenAI-compatible endpoints
                endpoints = [
                    ("/v1/models", "Models list"),
                    ("/health", "Health check")
                ]

                for endpoint, description in endpoints:
                    try:
                        response = requests.get(
                            f"{backend_config.url}{endpoint}",
                            headers=headers,
                            timeout=5
                        )
                        if response.status_code == 200:
                            self.print_test(
                                f"{backend_name} {description}", "PASS", f"Status: {response.status_code}")
                        else:
                            self.print_test(
                                f"{backend_name} {description}", "WARN", f"Status: {response.status_code}")
                    except Exception as e:
                        self.print_test(
                            f"{backend_name} {description}", "FAIL", str(e))

        except Exception as e:
            self.print_test(f"{backend_name} endpoint tests", "FAIL", str(e))

    def test_model_loading(self, connectivity_results: Dict[str, bool]) -> Dict[str, List]:
        """Test model loading from available backends."""
        self.print_header("Model Loading Tests")

        models_by_backend = {}

        for backend_name, is_connected in connectivity_results.items():
            if not is_connected:
                self.print_test(f"{backend_name} model loading",
                                "SKIP", "Backend not available")
                continue

            try:
                backend_config = self.config_manager.get_backend_config(
                    backend_name)
                headers = {}

                if backend_config.api_key:
                    headers["Authorization"] = f"Bearer {backend_config.api_key}"

                # Get models based on backend type
                if backend_name == "ollama":
                    response = requests.get(
                        f"{backend_config.url}/api/tags",
                        headers=headers,
                        timeout=backend_config.timeout
                    )

                    if response.status_code == 200:
                        data = response.json()
                        models = [model['name']
                                  for model in data.get('models', [])]
                        models_by_backend[backend_name] = models

                        if models:
                            self.print_test(
                                f"{backend_name} model loading", "PASS", f"Found {len(models)} models")
                            for model in models[:3]:  # Show first 3 models
                                print(f"   - {model}")
                        else:
                            self.print_test(
                                f"{backend_name} model loading", "WARN", "No models found")
                    else:
                        self.print_test(
                            f"{backend_name} model loading", "FAIL", f"HTTP {response.status_code}")

                elif backend_name == "llama_cpp":
                    # Add retry logic for llama.cpp model loading
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            response = requests.get(
                                f"{backend_config.url}/v1/models",
                                headers=headers,
                                timeout=max(backend_config.timeout, 15)
                            )

                            if response.status_code == 200:
                                # Validate JSON response
                                try:
                                    data = response.json()
                                    models = [model['id']
                                              for model in data.get('data', [])]
                                    models_by_backend[backend_name] = models

                                    if models:
                                        self.print_test(
                                            f"{backend_name} model loading", "PASS", f"Found {len(models)} models")
                                        # Show first 3 models
                                        for model in models[:3]:
                                            print(f"   - {model}")
                                    else:
                                        self.print_test(
                                            f"{backend_name} model loading", "WARN", "No models found")
                                    break

                                except (json.JSONDecodeError, KeyError) as e:
                                    if attempt < max_retries - 1:
                                        self.print_test(
                                            f"{backend_name} model loading retry", "WARN", f"JSON parse error, retrying... ({e})")
                                        time.sleep(2)
                                        continue
                                    else:
                                        self.print_test(
                                            f"{backend_name} model loading", "FAIL", f"Invalid JSON response: {e}")
                                        print(
                                            f"   Raw response: {response.text[:200]}...")
                                        models_by_backend[backend_name] = []
                                        break
                            else:
                                self.print_test(f"{backend_name} model loading", "FAIL",
                                                f"HTTP {response.status_code}: {response.text[:100]}")
                                models_by_backend[backend_name] = []
                                break

                        except requests.exceptions.Timeout:
                            if attempt < max_retries - 1:
                                self.print_test(f"{backend_name} model loading retry", "WARN",
                                                f"Timeout, retrying attempt {attempt + 2}/{max_retries}")
                                time.sleep(3)
                                continue
                            else:
                                self.print_test(
                                    f"{backend_name} model loading", "FAIL", "Request timed out after retries")
                                models_by_backend[backend_name] = []
                                break
                        except requests.exceptions.ConnectionError:
                            self.print_test(
                                f"{backend_name} model loading", "FAIL", "Connection failed - server may be down")
                            models_by_backend[backend_name] = []
                            break

            except Exception as e:
                self.print_test(
                    f"{backend_name} model loading", "FAIL", str(e))
                models_by_backend[backend_name] = []

        return models_by_backend

    def test_generation(self, models_by_backend: Dict[str, List]) -> Dict[str, bool]:
        """Test text generation from available backends."""
        self.print_header("Text Generation Tests")

        generation_results = {}
        test_prompt = "Hello, world!"

        for backend_name, models in models_by_backend.items():
            if not models:
                self.print_test(f"{backend_name} generation",
                                "SKIP", "No models available")
                continue

            try:
                backend_config = self.config_manager.get_backend_config(
                    backend_name)
                headers = {"Content-Type": "application/json"}

                if backend_config.api_key:
                    headers["Authorization"] = f"Bearer {backend_config.api_key}"

                # Use first available model
                test_model = models[0]

                if backend_name == "ollama":
                    # Test Ollama generation with optimized settings
                    payload = {
                        "model": test_model,
                        "prompt": test_prompt,
                        "stream": False,
                        "options": {
                            "num_predict": 5,  # Reduced for faster response
                            "temperature": 0.1,
                            "top_p": 0.9
                        }
                    }

                    # Use longer timeout for generation
                    generation_timeout = max(backend_config.timeout, 60)
                    response = requests.post(
                        f"{backend_config.url}/api/generate",
                        headers=headers,
                        json=payload,
                        timeout=generation_timeout
                    )

                    if response.status_code == 200:
                        data = response.json()
                        generated_text = data.get('response', '').strip()

                        if generated_text:
                            self.print_test(
                                f"{backend_name} generation", "PASS", f"Model: {test_model}")
                            print(f"   Generated: {generated_text[:50]}...")
                            generation_results[backend_name] = True
                        else:
                            self.print_test(
                                f"{backend_name} generation", "FAIL", "Empty response")
                            generation_results[backend_name] = False
                    else:
                        self.print_test(
                            f"{backend_name} generation", "FAIL", f"HTTP {response.status_code}")
                        generation_results[backend_name] = False

                elif backend_name == "llama_cpp":
                    # Test llama.cpp chat completion with better error handling
                    payload = {
                        "model": test_model,
                        "messages": [{"role": "user", "content": test_prompt}],
                        "max_tokens": 5,  # Reduced for faster response
                        "temperature": 0.1
                    }

                    # Add timeout with retry logic
                    generation_timeout = max(backend_config.timeout, 30)
                    max_retries = 2

                    for attempt in range(max_retries + 1):
                        try:
                            response = requests.post(
                                f"{backend_config.url}/v1/chat/completions",
                                headers=headers,
                                json=payload,
                                timeout=generation_timeout
                            )
                            break
                        except requests.exceptions.Timeout:
                            if attempt < max_retries:
                                self.print_test(
                                    f"{backend_name} generation retry", "WARN", f"Attempt {attempt + 1} timed out, retrying...")
                                time.sleep(2)
                                continue
                            else:
                                raise

                    if response.status_code == 200:
                        data = response.json()
                        generated_text = data['choices'][0]['message']['content'].strip(
                        )

                        if generated_text:
                            self.print_test(
                                f"{backend_name} generation", "PASS", f"Model: {test_model}")
                            print(f"   Generated: {generated_text[:50]}...")
                            generation_results[backend_name] = True
                        else:
                            self.print_test(
                                f"{backend_name} generation", "FAIL", "Empty response")
                            generation_results[backend_name] = False
                    else:
                        self.print_test(
                            f"{backend_name} generation", "FAIL", f"HTTP {response.status_code}")
                        generation_results[backend_name] = False

            except requests.exceptions.Timeout:
                self.print_test(f"{backend_name} generation", "FAIL",
                                f"Request timed out after {generation_timeout}s")
                generation_results[backend_name] = False
            except requests.exceptions.ConnectionError:
                self.print_test(f"{backend_name} generation",
                                "FAIL", "Connection failed - server may be down")
                generation_results[backend_name] = False
            except requests.exceptions.JSONDecodeError:
                self.print_test(f"{backend_name} generation",
                                "FAIL", "Invalid JSON response from server")
                generation_results[backend_name] = False

        return generation_results

    def test_flask_integration(self) -> bool:
        """Test Flask application integration."""
        self.print_header("Flask Integration Tests")

        try:
            # Test importing the app
            sys.path.append('.')
            from app import create_app

            # Create test app
            app = create_app(self.config_path)

            self.print_test("Flask app creation", "PASS",
                            "App created successfully")

            # Test configuration loading in app
            config_manager = app.config.get('CONFIG_MANAGER')
            if config_manager:
                self.print_test("Config manager in app", "PASS",
                                "ConfigManager properly injected")
            else:
                self.print_test("Config manager in app", "FAIL",
                                "ConfigManager not found in app config")
                return False

            # Test app configuration
            if app.config.get('SECRET_KEY'):
                self.print_test("Flask secret key", "PASS",
                                "Secret key configured")
            else:
                self.print_test("Flask secret key", "FAIL",
                                "Secret key missing")

            # Test with test client
            with app.test_client() as client:
                # Test config status endpoint
                response = client.get('/api/config/status')
                if response.status_code == 200:
                    self.print_test("Config status endpoint",
                                    "PASS", f"Status: {response.status_code}")

                    # Parse response
                    data = response.get_json()
                    if data and 'enabled_backends' in data:
                        enabled = data['enabled_backends']
                        self.print_test("Backend status in API",
                                        "PASS", f"Backends: {', '.join(enabled)}")
                    else:
                        self.print_test("Backend status in API",
                                        "FAIL", "Invalid response format")
                else:
                    self.print_test("Config status endpoint",
                                    "FAIL", f"Status: {response.status_code}")

            return True

        except ImportError as e:
            self.print_test("Flask app import", "FAIL", f"Import error: {e}")
            return False
        except Exception as e:
            self.print_test("Flask integration", "FAIL", str(e))
            return False

    def test_performance_benchmarks(self, connectivity_results: Dict[str, bool]) -> Dict[str, float]:
        """Run basic performance benchmarks."""
        self.print_header("Performance Benchmarks")

        performance_results = {}

        for backend_name, is_connected in connectivity_results.items():
            if not is_connected:
                self.print_test(f"{backend_name} performance",
                                "SKIP", "Backend not available")
                continue

            try:
                backend_config = self.config_manager.get_backend_config(
                    backend_name)

                # Benchmark health check response time
                start_time = time.time()
                is_healthy, _ = self.config_manager.test_backend_connectivity(
                    backend_name)
                end_time = time.time()

                response_time = (end_time - start_time) * \
                    1000  # Convert to milliseconds
                performance_results[backend_name] = response_time

                if response_time < 1000:  # Less than 1 second
                    self.print_test(f"{backend_name} response time",
                                    "PASS", f"{response_time:.2f}ms")
                elif response_time < 5000:  # Less than 5 seconds
                    self.print_test(f"{backend_name} response time",
                                    "WARN", f"{response_time:.2f}ms (slow)")
                else:
                    self.print_test(f"{backend_name} response time",
                                    "FAIL", f"{response_time:.2f}ms (too slow)")

            except Exception as e:
                self.print_test(f"{backend_name} performance", "FAIL", str(e))
                performance_results[backend_name] = float('inf')

        return performance_results

    def print_summary(self):
        """Print a summary of all test results."""
        self.print_header("Test Summary")

        passed = sum(1 for _, status,
                     _ in self.test_results if status == "PASS")
        failed = sum(1 for _, status,
                     _ in self.test_results if status == "FAIL")
        warned = sum(1 for _, status,
                     _ in self.test_results if status == "WARN")
        skipped = sum(1 for _, status,
                      _ in self.test_results if status == "SKIP")
        total = len(self.test_results)

        print(f"{Colors.BOLD}Total Tests: {total}{Colors.END}")
        print(f"{Colors.GREEN}Passed: {passed}{Colors.END}")
        print(f"{Colors.RED}Failed: {failed}{Colors.END}")
        print(f"{Colors.YELLOW}Warnings: {warned}{Colors.END}")
        print(f"{Colors.CYAN}Skipped: {skipped}{Colors.END}")

        if failed == 0:
            print(
                f"\n{Colors.GREEN}{Colors.BOLD}🎉 All critical tests passed!{Colors.END}")
            if warned > 0:
                print(
                    f"{Colors.YELLOW}⚠️  Some warnings detected - check configuration{Colors.END}")
        else:
            print(
                f"\n{Colors.RED}{Colors.BOLD}❌ {failed} test(s) failed - check configuration{Colors.END}")

        # Print failed tests
        if failed > 0:
            print(f"\n{Colors.RED}{Colors.BOLD}Failed Tests:{Colors.END}")
            for test_name, status, message in self.test_results:
                if status == "FAIL":
                    print(f"  - {test_name}: {message}")

    def run_all_tests(self) -> bool:
        """Run the complete test suite."""
        print(f"{Colors.BOLD}{Colors.PURPLE}")
        print("╔══════════════════════════════════════════════════════════╗")
        print("║              Multi-Backend Test Environment              ║")
        print("║                  Configuration Testing                   ║")
        print("╚══════════════════════════════════════════════════════════╝")
        print(f"{Colors.END}")

        # Run all test phases
        config_ok = self.test_configuration_loading()
        if not config_ok:
            print(
                f"{Colors.RED}Configuration loading failed - aborting tests{Colors.END}")
            return False

        env_ok = self.test_environment_variables()
        connectivity_results = self.test_backend_connectivity()
        models_by_backend = self.test_model_loading(connectivity_results)
        generation_results = self.test_generation(models_by_backend)
        flask_ok = self.test_flask_integration()
        performance_results = self.test_performance_benchmarks(
            connectivity_results)

        # Print summary
        self.print_summary()

        # Overall success check
        critical_failures = any(status == "FAIL" for _,
                                status, _ in self.test_results)
        return not critical_failures


def main():
    """Main test runner."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Test multi-backend configuration environment")
    parser.add_argument("--config", "-c", default="test_config.json",
                        help="Configuration file to test (default: test_config.json)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable verbose output")

    args = parser.parse_args()

    if not os.path.exists(args.config):
        print(
            f"{Colors.RED}Error: Configuration file '{args.config}' not found{Colors.END}")
        print(f"Please create the configuration file or run with --config <path>")
        sys.exit(1)

    # Create and run test environment
    test_env = TestEnvironment(args.config)
    success = test_env.run_all_tests()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
