#!/bin/bash

# Huawei Cloud API Documentation Scraper Deployment Script
# Download latest code via git clone and deploy locally

set -e  # Exit on error

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration variables
REPO_URL="https://github.com/Lance52259/huaweicloud-service-xmind-translate.git"
INSTALL_BASE_DIR="$HOME/.local"
INSTALL_DIR="$INSTALL_BASE_DIR/bin"
TOOL_DIR="$INSTALL_BASE_DIR/share/xmind-translate"
SCRIPT_NAME="xmind-translate"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Huawei Cloud API Documentation Scraper${NC}"
echo -e "${BLUE}  Local Deployment${NC}"
echo -e "${BLUE}========================================${NC}"

# Check required tools
echo -e "${YELLOW}Checking system environment...${NC}"

# Prioritize checking Python3.10 (as per user requirements)
PYTHON_CMD=""
PIP_CMD=""

if command -v python3.10 &> /dev/null; then
    PYTHON_CMD="python3.10"
    echo -e "${GREEN}✓ Python3.10: $(python3.10 --version)${NC}"
    # Check pip for python3.10
    if python3.10 -m pip --version &> /dev/null; then
        PIP_CMD="python3.10 -m pip"
        echo -e "${GREEN}✓ pip (python3.10): $(python3.10 -m pip --version)${NC}"
    elif command -v pip3.10 &> /dev/null; then
        PIP_CMD="pip3.10"
        echo -e "${GREEN}✓ pip3.10: $(pip3.10 --version)${NC}"
    else
        echo -e "${YELLOW}⚠ Warning: pip not found for python3.10, trying python3${NC}"
    fi
fi

# Fallback to python3 if python3.10 not found
if [ -z "$PYTHON_CMD" ]; then
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Error: python3.10 or python3 not found${NC}"
        echo "Please install Python 3.10 or higher (Python 3.10 recommended)"
        exit 1
    fi
    PYTHON_CMD="python3"
    echo -e "${YELLOW}⚠ Warning: python3.10 not found, using python3: $(python3 --version)${NC}"
    echo -e "${YELLOW}⚠ Recommendation: Install Python 3.10 for better compatibility${NC}"
    
    # Check pip for python3
    if ! command -v pip3 &> /dev/null; then
        echo -e "${YELLOW}⚠ Warning: pip3 not found, trying python3 -m pip${NC}"
        if ! python3 -m pip --version &> /dev/null; then
            echo -e "${RED}❌ Error: pip not found${NC}"
            echo "Please install pip"
            exit 1
        fi
        PIP_CMD="python3 -m pip"
    else
        PIP_CMD="pip3"
    fi
    echo -e "${GREEN}✓ pip: $($PIP_CMD --version)${NC}"
fi

# Check Git
if ! command -v git &> /dev/null; then
    echo -e "${RED}❌ Error: git not found${NC}"
    echo "Please install Git first"
    exit 1
fi
echo -e "${GREEN}✓ Git: $(git --version)${NC}"

# Create necessary directories
echo -e "${YELLOW}Creating directory structure...${NC}"
mkdir -p "$INSTALL_DIR"
mkdir -p "$(dirname "$TOOL_DIR")"

# Remove old version (if exists)
if [ -d "$TOOL_DIR" ]; then
    echo -e "${YELLOW}Found existing installation, updating...${NC}"
    rm -rf "$TOOL_DIR"
fi

# Clone repository
echo -e "${YELLOW}Cloning latest code...${NC}"
echo "Repository URL: $REPO_URL"
echo "Installation path: $TOOL_DIR"

if git clone "$REPO_URL" "$TOOL_DIR"; then
    echo -e "${GREEN}✓ Code download successful${NC}"
else
    echo -e "${RED}❌ Code download failed${NC}"
    exit 1
fi

# Verify Python script
echo -e "${YELLOW}Verifying tool...${NC}"
PYTHON_SCRIPT="$TOOL_DIR/src/cli.py"

if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo -e "${RED}❌ Python script not found: $PYTHON_SCRIPT${NC}"
    exit 1
fi

# Install Python dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
REQUIREMENTS_FILE="$TOOL_DIR/requirements.txt"

if [ ! -f "$REQUIREMENTS_FILE" ]; then
    echo -e "${RED}❌ Requirements file not found: $REQUIREMENTS_FILE${NC}"
    exit 1
fi

if $PIP_CMD install -r "$REQUIREMENTS_FILE" --quiet --user; then
    echo -e "${GREEN}✓ Dependencies installed successfully${NC}"
else
    echo -e "${YELLOW}⚠ Warning: Dependency installation may have issues, but continuing${NC}"
fi

# Test if script is executable
if $PYTHON_CMD "$PYTHON_SCRIPT" --help > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Tool verification successful${NC}"
else
    echo -e "${YELLOW}⚠ Warning: Tool verification returned non-zero exit code (this may be normal)${NC}"
fi

# Create executable wrapper script
echo -e "${YELLOW}Creating executable command...${NC}"
WRAPPER_SCRIPT="$INSTALL_DIR/$SCRIPT_NAME"

cat > "$WRAPPER_SCRIPT" << EOF
#!/bin/bash

# Huawei Cloud API Documentation Scraper Wrapper Script
# Auto-generated - $(date)

TOOL_SCRIPT="$TOOL_DIR/src/cli.py"

# Check if script exists
if [ ! -f "\$TOOL_SCRIPT" ]; then
    echo "Error: Huawei Cloud API Documentation Scraper script not found"
    echo "Script path: \$TOOL_SCRIPT"
    echo "Please re-run the deployment script"
    exit 1
fi

# Detect Python version (prioritize python3.10)
PYTHON_CMD=""
if command -v python3.10 &> /dev/null; then
    PYTHON_CMD="python3.10"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    echo "Error: python3.10 or python3 not found"
    echo "Please install Python 3.10 or higher"
    exit 1
fi

# Change to tool directory to ensure relative imports work
cd "$TOOL_DIR"

# Execute tool, passing all arguments
exec "\$PYTHON_CMD" "\$TOOL_SCRIPT" "\$@"
EOF

# Set execute permissions
chmod +x "$WRAPPER_SCRIPT"
echo -e "${GREEN}✓ Executable command created: $WRAPPER_SCRIPT${NC}"

# Check and configure PATH
echo -e "${YELLOW}Configuring environment variables...${NC}"
PATH_ALREADY_SET=false

# Check if current PATH contains install directory
if [[ ":$PATH:" == *":$INSTALL_DIR:"* ]]; then
    PATH_ALREADY_SET=true
    echo -e "${GREEN}✓ PATH already contains $INSTALL_DIR${NC}"
fi

# Determine shell configuration files to configure
SHELL_CONFIGS=()
if [ -n "$BASH_VERSION" ]; then
    # Bash shell - configure multiple files for compatibility
    [ -f "$HOME/.bashrc" ] && SHELL_CONFIGS+=("$HOME/.bashrc")
    [ -f "$HOME/.bash_profile" ] && SHELL_CONFIGS+=("$HOME/.bash_profile")
    # If none exist, create .bashrc
    if [ ${#SHELL_CONFIGS[@]} -eq 0 ]; then
        touch "$HOME/.bashrc"
        SHELL_CONFIGS+=("$HOME/.bashrc")
    fi
elif [ -n "$ZSH_VERSION" ]; then
    # Zsh shell
    [ -f "$HOME/.zshrc" ] && SHELL_CONFIGS+=("$HOME/.zshrc")
    if [ ${#SHELL_CONFIGS[@]} -eq 0 ]; then
        touch "$HOME/.zshrc"
        SHELL_CONFIGS+=("$HOME/.zshrc")
    fi
else
    # Other shells or unknown shell
    [ -f "$HOME/.profile" ] && SHELL_CONFIGS+=("$HOME/.profile")
    [ -f "$HOME/.bashrc" ] && SHELL_CONFIGS+=("$HOME/.bashrc")
    if [ ${#SHELL_CONFIGS[@]} -eq 0 ]; then
        touch "$HOME/.profile"
        SHELL_CONFIGS+=("$HOME/.profile")
    fi
fi

# Add PATH to each configuration file (if needed)
PATH_ADDED=false
for SHELL_CONFIG in "${SHELL_CONFIGS[@]}"; do
    # Check if configuration file already has PATH setting
    CONFIG_HAS_PATH=false
    if [ -f "$SHELL_CONFIG" ] && grep -q "$INSTALL_DIR" "$SHELL_CONFIG" 2>/dev/null; then
        CONFIG_HAS_PATH=true
    fi
    
    # Add PATH to configuration file (if needed)
    if [ "$CONFIG_HAS_PATH" = false ]; then
        echo -e "${YELLOW}Adding PATH to $SHELL_CONFIG${NC}"
        {
            echo ""
            echo "# Huawei Cloud API Documentation Scraper - $(date)"
            echo "export PATH=\"$INSTALL_DIR:\$PATH\""
        } >> "$SHELL_CONFIG"
        echo -e "${GREEN}✓ PATH added to $SHELL_CONFIG${NC}"
        PATH_ADDED=true
    else
        echo -e "${GREEN}✓ PATH configuration already exists in $SHELL_CONFIG${NC}"
    fi
done

# Temporarily set PATH (if configuration was added)
if [ "$PATH_ADDED" = true ]; then
    export PATH="$INSTALL_DIR:$PATH"
fi

# Final test
echo -e "${YELLOW}Performing final test...${NC}"
if "$WRAPPER_SCRIPT" --help > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Deployment successful!${NC}"
else
    echo -e "${YELLOW}⚠ Warning: Final test returned non-zero exit code (this may be normal)${NC}"
fi

# Display deployment information
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}🎉 Deployment completed!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}Installation Information:${NC}"
echo "  Tool directory: $TOOL_DIR"
echo "  Executable file: $WRAPPER_SCRIPT"
echo ""
echo -e "${YELLOW}Usage:${NC}"
echo "  xmind-translate                    # Scan all services"
echo "  xmind-translate --category ecs,obs # Scan specified services only"
echo "  xmind-translate --skip ecs,obs     # Scan all services but skip some"
echo "  xmind-translate --step 1           # Execute step 1 only (fetch product list)"
echo "  xmind-translate --step 2           # Execute step 2 only (fetch API categories)"
echo "  xmind-translate --step 3           # Execute step 3 only (generate Markdown)"
echo "  xmind-translate --search CodeArts  # Search products"
echo ""
echo -e "${YELLOW}Examples:${NC}"
echo "  xmind-translate --category ecs"
echo "  xmind-translate --category ecs,obs,rds --step 3"
echo "  xmind-translate --search CodeArts_Check"
echo ""
echo -e "${YELLOW}Environment Configuration:${NC}"
if [ "$PATH_ALREADY_SET" = true ]; then
    echo "  ✓ PATH already configured, commands ready to use"
else
    echo "  ⚠️  Please run the following commands to activate environment:"
    for SHELL_CONFIG in "${SHELL_CONFIGS[@]}"; do
        echo "     source $SHELL_CONFIG"
    done
    echo "  Or restart your terminal"
    echo ""
    echo "  Temporary use: xmind-translate command is available in current terminal"
fi

echo ""
echo -e "${YELLOW}Test Installation:${NC}"
if command -v xmind-translate &> /dev/null; then
    echo "  ✅ xmind-translate command available"
    echo ""
    echo -e "${YELLOW}Quick Test:${NC}"
    echo "  Run: xmind-translate --help"
else
    echo "  ⚠️  Please run the following commands to refresh environment:"
    for SHELL_CONFIG in "${SHELL_CONFIGS[@]}"; do
        echo "     source $SHELL_CONFIG"
    done
fi

echo ""
echo -e "${GREEN}Start using Huawei Cloud API Documentation Scraper!${NC}"

