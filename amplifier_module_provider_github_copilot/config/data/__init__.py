"""Data package for YAML config files.

Contains SDK-correlated tabular data that changes when the SDK event schema changes:
  - errors.yaml  — error pattern mappings (SDK-correlated tabular data)
  - events.yaml  — event classification (SDK-correlated tabular data)

Access via importlib.resources:
    resources.files("amplifier_module_provider_github_copilot.config.data")
"""
