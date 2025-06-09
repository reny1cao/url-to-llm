#!/bin/bash

# Script to help push the URL to LLM project to GitHub

echo "GitHub Push Instructions for URL → LLM Pipeline"
echo "=============================================="
echo ""

# Check if git remote exists
if git remote get-url origin &>/dev/null; then
    echo "✓ Git remote 'origin' already configured"
    echo "  Current remote: $(git remote get-url origin)"
    echo ""
    read -p "Do you want to push to this remote? (Y/n): " PUSH_CONFIRM
    if [[ ! $PUSH_CONFIRM =~ ^[Nn]$ ]]; then
        echo "Pushing to GitHub..."
        git push -u origin main
        echo "✓ Code pushed successfully!"
    fi
else
    echo "No git remote configured. Please follow these steps:"
    echo ""
    echo "Option 1: Using GitHub CLI (recommended)"
    echo "----------------------------------------"
    echo "If you have GitHub CLI installed, run:"
    echo ""
    echo "gh repo create url-to-llm --public --source=. --remote=origin --push"
    echo ""
    echo "Option 2: Manual creation"
    echo "-------------------------"
    echo "1. Go to https://github.com/new"
    echo "2. Repository name: url-to-llm"
    echo "3. Description: Transform any website into AI-ready content with automated crawling and llm.txt manifest generation"
    echo "4. Choose Public or Private"
    echo "5. DO NOT initialize with README, .gitignore, or license"
    echo "6. Click 'Create repository'"
    echo ""
    echo "7. Then run these commands:"
    echo ""
    echo "# If using HTTPS:"
    echo "git remote add origin https://github.com/YOUR_USERNAME/url-to-llm.git"
    echo ""
    echo "# If using SSH:"
    echo "git remote add origin git@github.com:YOUR_USERNAME/url-to-llm.git"
    echo ""
    echo "# Push the code:"
    echo "git push -u origin main"
fi

echo ""
echo "After pushing, you should:"
echo "1. Visit your repository at https://github.com/YOUR_USERNAME/url-to-llm"
echo "2. Go to Settings > Actions > General and enable GitHub Actions"
echo "3. Go to Settings > Secrets and variables > Actions to add secrets"
echo "4. Check the Actions tab to see your CI/CD workflows"
echo ""

# Show current git status
echo "Current git status:"
echo "-------------------"
git status --short
echo ""
echo "Current branch: $(git branch --show-current)"
echo "Total commits: $(git rev-list --count HEAD)"