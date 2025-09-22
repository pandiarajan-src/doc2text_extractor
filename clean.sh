#!/bin/bash

# Clean script for doc2text_extractor
# Removes all files from output directories and clears SQLite database contents

set -e

echo "🧹 Starting cleanup process..."

# Remove all files from output directories
echo "📁 Cleaning output directories..."

if [ -d "outputs" ]; then
    echo "  - Removing contents of outputs/"
    rm -rf outputs/*
    echo "    ✓ outputs/ cleared"
else
    echo "  - outputs/ directory not found, skipping"
fi

if [ -d "test_outputs" ]; then
    echo "  - Removing contents of test_outputs/"
    rm -rf test_outputs/*
    echo "    ✓ test_outputs/ cleared"
else
    echo "  - test_outputs/ directory not found, skipping"
fi

if [ -d "test_outputs_cli" ]; then
    echo "  - Removing contents of test_outputs_cli/"
    rm -rf test_outputs_cli/*
    echo "    ✓ test_outputs_cli/ cleared"
else
    echo "  - test_outputs_cli/ directory not found, skipping"
fi

if [ -d "uploads" ]; then
    echo "  - Removing contents of uploads/"
    rm -rf uploads/*
    echo "    ✓ uploads/ cleared"
else
    echo "  - uploads/ directory not found, skipping"
fi

# Clear SQLite database contents
echo "🗄️  Clearing SQLite database..."

if [ -f "data/jobs.db" ]; then
    echo "  - Clearing jobs table in data/jobs.db"
    sqlite3 data/jobs.db "DELETE FROM jobs; VACUUM;"
    echo "    ✓ SQLite database cleared and vacuumed"
else
    echo "  - data/jobs.db not found, skipping database cleanup"
fi

# Clear log files if they exist
if [ -d "logs" ]; then
    echo "📋 Clearing log files..."
    rm -rf logs/*
    echo "    ✓ logs/ cleared"
fi

# Clear coverage reports if they exist
if [ -d "htmlcov" ]; then
    echo "📊 Clearing coverage reports..."
    rm -rf htmlcov/*
    echo "    ✓ htmlcov/ cleared"
fi

echo ""
echo "✅ Cleanup completed successfully!"
echo "   - All output directories cleared"
echo "   - SQLite database contents removed"
echo "   - Log files cleared"
echo "   - Coverage reports cleared"