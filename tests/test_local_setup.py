"""
Test suite to verify local development setup with uv works correctly.
"""
import subprocess
import sys
import shutil
from pathlib import Path


def test_uv_installed():
    """Verify that uv is installed and accessible."""
    result = subprocess.run(["uv", "--version"], capture_output=True, text=True)
    assert result.returncode == 0, "uv is not installed or not in PATH"
    assert "uv" in result.stdout, "uv version output not found"
    print(f"✓ uv installed: {result.stdout.strip()}")


def test_uv_sync():
    """Verify that uv sync creates virtual environment and installs dependencies."""
    result = subprocess.run(["uv", "sync"], capture_output=True, text=True, cwd=Path.cwd())
    assert result.returncode == 0, f"uv sync failed:\n{result.stderr}"
    
    # Also install git dependencies from requirements.txt
    result = subprocess.run(
        ["uv", "pip", "install", "-r", "requirements.txt"],
        capture_output=True,
        text=True,
        cwd=Path.cwd()
    )
    assert result.returncode == 0, f"Failed to install requirements.txt:\n{result.stderr}"
    assert Path(".venv").exists(), "Virtual environment not created"
    print("✓ uv sync completed successfully")


def test_venv_created():
    """Verify that .venv directory exists and contains Python."""
    venv_path = Path(".venv")
    assert venv_path.exists(), ".venv directory not found"
    
    # Check for Python executable in venv
    if sys.platform == "win32":
        python_exe = venv_path / "Scripts" / "python.exe"
    else:
        python_exe = venv_path / "bin" / "python"
    
    assert python_exe.exists(), f"Python executable not found in venv: {python_exe}"
    print(f"✓ Virtual environment exists at {venv_path}")


def test_dependencies_installed():
    """Verify that key dependencies are installed."""
    venv_path = Path(".venv")
    
    if sys.platform == "win32":
        python_exe = venv_path / "Scripts" / "python.exe"
    else:
        python_exe = venv_path / "bin" / "python"
    
    # Test importing key dependencies
    imports_to_test = [
        "fastapi",
        "uvicorn",
        "PIL",  # Pillow
        "httpx",
        "samsungtvws",  # samsung-tv-ws-api
    ]
    
    for module in imports_to_test:
        result = subprocess.run(
            [str(python_exe), "-c", f"import {module}"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Failed to import {module}:\n{result.stderr}"
    
    print(f"✓ All key dependencies installed: {', '.join(imports_to_test)}")


def test_app_importable():
    """Verify that the FastAPI app can be imported."""
    venv_path = Path(".venv")
    
    if sys.platform == "win32":
        python_exe = venv_path / "Scripts" / "python.exe"
    else:
        python_exe = venv_path / "bin" / "python"
    
    result = subprocess.run(
        [str(python_exe), "-c", "from src.main import app; print('FastAPI app imported successfully')"],
        capture_output=True,
        text=True,
        cwd=Path.cwd()
    )
    assert result.returncode == 0, f"Failed to import FastAPI app:\n{result.stderr}"
    print("✓ FastAPI app imports successfully")


def test_pyproject_toml_exists():
    """Verify that pyproject.toml exists and is properly formatted."""
    pyproject_path = Path("pyproject.toml")
    assert pyproject_path.exists(), "pyproject.toml not found"
    
    content = pyproject_path.read_text()
    assert "[project]" in content, "Missing [project] section in pyproject.toml"
    assert "name = " in content, "Missing name in pyproject.toml"
    assert "dependencies = " in content, "Missing dependencies in pyproject.toml"
    
    print("✓ pyproject.toml is properly formatted")


def test_requirements_txt_exists():
    """Verify that requirements.txt exists for git dependencies."""
    req_path = Path("requirements.txt")
    assert req_path.exists(), "requirements.txt not found"
    
    content = req_path.read_text()
    assert "fastapi" in content, "fastapi not in requirements.txt"
    assert "samsung-tv-ws-api" in content, "samsung-tv-ws-api not in requirements.txt"
    
    print("✓ requirements.txt contains expected dependencies")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Samsung Frame Art Gallery - Local Development Setup Tests")
    print("=" * 60 + "\n")
    
    tests = [
        ("uv Installation", test_uv_installed),
        ("uv sync Execution", test_uv_sync),
        ("Virtual Environment", test_venv_created),
        ("Dependencies Installation", test_dependencies_installed),
        ("FastAPI App Import", test_app_importable),
        ("pyproject.toml Validation", test_pyproject_toml_exists),
        ("requirements.txt Validation", test_requirements_txt_exists),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\nRunning: {test_name}...")
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test_name} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test_name} ERROR: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60 + "\n")
    
    sys.exit(0 if failed == 0 else 1)
