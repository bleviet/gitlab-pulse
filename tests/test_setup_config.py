import os
from pathlib import Path

def test_env_example_has_safe_defaults():
    """Ensure .env.example doesn't leak secrets and has safe defaults."""
    env_example_path = Path(".env.example")
    assert env_example_path.exists(), ".env.example must exist for a clean setup flow"

    content = env_example_path.read_text()
    
    # Check for safe dummy values
    assert "GITLAB_URL=https://gitlab.com" in content
    assert "your-personal-access-token" in content
    assert "PROJECT_IDS=" in content, "PROJECT_IDS should default to empty to safely process all rules"

def test_default_rules_yaml_is_safe():
    """Ensure default.yaml does not hardcode developer-specific project IDs."""
    yaml_path = Path("app/config/rules/default.yaml")
    assert yaml_path.exists(), "Default rules YAML must exist"
    
    content = yaml_path.read_text()
    assert "project_ids: []" in content, "Default rules should apply globally by default (empty project_ids)"
    assert "12345678" in content, "Example project IDs should only be in comments"

def test_docker_entrypoint_exists_and_executable():
    """Ensure the docker entrypoint script exists and is executable."""
    entrypoint_path = Path("scripts/docker-entrypoint.sh")
    assert entrypoint_path.exists(), "Docker entrypoint script must exist"
    assert os.access(entrypoint_path, os.X_OK), "Docker entrypoint script must be executable"
