#!/bin/bash
# scripts/build_frontend.sh

set -e

echo "🔄 Syncing version from pyproject.toml to package.json..."

# Extract version from pyproject.toml
PYTHON_VERSION=$(python -c "
import toml
with open('pyproject.toml', 'r') as f:
    config = toml.load(f)
print(config['tool']['poetry']['version'])
")

echo "📝 Python package version: $PYTHON_VERSION"

# Update package.json version
cd lyrics_transcriber/frontend

# Create a temporary CommonJS script to update package.json
cat > update_version.cjs << 'EOF'
const fs = require('fs');
const path = require('path');

const packageJsonPath = path.join(__dirname, 'package.json');
const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));

const newVersion = process.argv[2];
packageJson.version = newVersion;

fs.writeFileSync(packageJsonPath, JSON.stringify(packageJson, null, 2) + '\n');
console.log(`✅ Updated package.json version to ${newVersion}`);
EOF

# Run the version update script
node update_version.cjs "$PYTHON_VERSION"

# Clean up the temporary script
rm update_version.cjs

echo "🏗️  Building frontend..."
yarn install
yarn build

echo "✅ Frontend build complete!"
