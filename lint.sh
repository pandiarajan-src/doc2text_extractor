#!/bin/bash

set -e

echo "🔍 Running linting checks for doc2text_extractor..."

# Check if uv is available
if ! command -v uv >/dev/null 2>&1; then
    echo "❌ uv not found. Please install it: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Sync dependencies
echo "📦 Syncing dependencies with uv..."
uv sync > /dev/null 2>&1 || {
    echo "❌ Failed to sync dependencies"
    exit 1
}

echo ""

# Run ruff for linting and formatting
echo "🚀 Running ruff linter..."
# Check for linting issues
if uv run ruff check .; then
    echo "✅ Ruff linting passed"
else
    echo "❌ Ruff linting failed"
    exit 1
fi

echo ""
echo "🎨 Running ruff formatter..."
if uv run ruff format . --check; then
    echo "✅ Ruff formatting check passed"
else
    echo "⚠️  Code formatting issues found. Run 'uv run ruff format .' to fix them."
    # Don't exit on formatting issues, just warn
fi

echo ""

# Run black for additional formatting check
echo "🎨 Running black formatter check..."
if uv run black --check .; then
    echo "✅ Black formatting check passed"
else
    echo "⚠️  Black formatting issues found. Run 'uv run black .' to fix them."
    # Don't exit on formatting issues, just warn
fi

echo ""

# Run mypy for type checking
echo "🔍 Running mypy type checker..."
if uv run mypy . --ignore-missing-imports --no-error-summary; then
    echo "✅ MyPy type checking passed"
else
    echo "⚠️  MyPy type checking found issues"
    # Don't exit on type checking issues, just warn for now
fi

echo ""
echo "🎉 Linting checks completed!"

# Summary
echo ""
echo "📋 Summary:"
echo "   - Code linting: ✅"
echo "   - Code formatting: Check output above"
echo "   - Type checking: Check output above"
echo ""
echo "💡 To fix formatting issues automatically:"
echo "   - Run: uv run ruff format ."
echo "   - Run: uv run black ."
echo "   - Or use: make format"
echo ""
echo "💡 To fix linting issues automatically:"
echo "   - Run: uv run ruff check . --fix"
echo "   - Or use: make format"