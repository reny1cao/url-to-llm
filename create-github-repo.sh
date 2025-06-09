#!/bin/bash

# GitHub repository creation script
# This script helps you create a new repository on GitHub and push the code

echo "GitHub Repository Setup for URL → LLM Pipeline"
echo "============================================="
echo ""
echo "This script will help you:"
echo "1. Create a new repository on GitHub"
echo "2. Push your local code to the repository"
echo ""
echo "Prerequisites:"
echo "- GitHub CLI (gh) installed and authenticated"
echo "- Or a GitHub personal access token"
echo ""

# Check if gh is installed
if command -v gh &> /dev/null; then
    echo "✓ GitHub CLI detected"
    echo ""
    
    read -p "Enter the repository name (default: url-to-llm): " REPO_NAME
    REPO_NAME=${REPO_NAME:-url-to-llm}
    
    read -p "Enter the organization/username (default: your-org): " ORG_NAME
    ORG_NAME=${ORG_NAME:-your-org}
    
    read -p "Make repository private? (y/N): " PRIVATE_REPO
    VISIBILITY="public"
    if [[ $PRIVATE_REPO =~ ^[Yy]$ ]]; then
        VISIBILITY="private"
    fi
    
    echo ""
    echo "Creating repository $ORG_NAME/$REPO_NAME..."
    
    # Create the repository
    gh repo create "$ORG_NAME/$REPO_NAME" \
        --description "Transform any website into AI-ready content with automated crawling and llm.txt manifest generation" \
        --$VISIBILITY \
        --source=. \
        --remote=origin \
        --push
    
    echo ""
    echo "✓ Repository created and code pushed!"
    echo ""
    echo "Repository URL: https://github.com/$ORG_NAME/$REPO_NAME"
    
else
    echo "GitHub CLI not found. Please install it or manually create the repository:"
    echo ""
    echo "Manual steps:"
    echo "1. Go to https://github.com/new"
    echo "2. Create a new repository named 'url-to-llm'"
    echo "3. Do NOT initialize with README, .gitignore, or license"
    echo "4. Run these commands:"
    echo ""
    echo "git remote add origin https://github.com/YOUR_USERNAME/url-to-llm.git"
    echo "git push -u origin main"
fi

echo ""
echo "Next steps:"
echo "1. Configure GitHub Secrets for CI/CD"
echo "2. Enable GitHub Actions in repository settings"
echo "3. Set up branch protection rules for 'main'"
echo "4. Configure Dependabot security updates"
echo ""
echo "Happy coding! 🚀"