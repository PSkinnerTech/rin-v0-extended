#!/bin/bash
# Rin CLI - Setup Script

# Text colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Rin CLI Setup ===${NC}"
echo "This script will set up the Rin CLI environment."

# Check Python version
echo -e "\n${YELLOW}Checking Python version...${NC}"
python_version=$(python3 --version)
if [[ $? -ne 0 ]]; then
    echo -e "${RED}Error: Python 3 not found. Please install Python 3.9 or higher.${NC}"
    exit 1
fi
echo -e "${GREEN}Found $python_version${NC}"

# Create virtual environment
echo -e "\n${YELLOW}Creating virtual environment...${NC}"
if [ -d "venv" ]; then
    echo "Virtual environment already exists. Skipping creation."
else
    python3 -m venv venv
    if [[ $? -ne 0 ]]; then
        echo -e "${RED}Error: Failed to create virtual environment.${NC}"
        exit 1
    fi
    echo -e "${GREEN}Virtual environment created successfully.${NC}"
fi

# Activate virtual environment
echo -e "\n${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate
if [[ $? -ne 0 ]]; then
    echo -e "${RED}Error: Failed to activate virtual environment.${NC}"
    exit 1
fi
echo -e "${GREEN}Virtual environment activated.${NC}"

# Upgrade pip
echo -e "\n${YELLOW}Upgrading pip...${NC}"
pip install --upgrade pip
if [[ $? -ne 0 ]]; then
    echo -e "${RED}Warning: Failed to upgrade pip. Continuing anyway.${NC}"
fi

# Install package
echo -e "\n${YELLOW}Installing Rin CLI...${NC}"
pip install -e .
if [[ $? -ne 0 ]]; then
    echo -e "${RED}Error: Failed to install package.${NC}"
    exit 1
fi
echo -e "${GREEN}Rin CLI installed successfully.${NC}"

# Create .env file if it doesn't exist
echo -e "\n${YELLOW}Checking for .env file...${NC}"
if [ ! -f ".env" ]; then
    echo "Creating sample .env file..."
    cat > .env << EOF
OPENAI_API_KEY=your_openai_key_here
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/google-credentials.json
TTS_ENGINE=google
STT_ENGINE=whisper
LOG_LEVEL=INFO
LLM_MODEL=gpt-4
WHISPER_MODEL=base
EOF
    echo -e "${GREEN}Sample .env file created. Please edit it with your API keys.${NC}"
else
    echo -e "${GREEN}.env file already exists. Skipping creation.${NC}"
fi

# Check .env file
echo -e "\n${YELLOW}Checking .env file...${NC}"
if grep -q "your_openai_key_here" .env; then
    echo -e "${RED}Warning: You need to update the OPENAI_API_KEY in .env file.${NC}"
fi
if grep -q "/absolute/path/to/google-credentials.json" .env; then
    echo -e "${RED}Warning: You need to update the GOOGLE_APPLICATION_CREDENTIALS in .env file.${NC}"
fi

echo -e "\n${GREEN}Setup completed!${NC}"
echo -e "To activate the environment in the future, run: ${YELLOW}source venv/bin/activate${NC}"
echo -e "To test your setup, run: ${YELLOW}python test_setup.py${NC}"
echo -e "To use Rin CLI, run: ${YELLOW}rin ask \"Hello, Rin!\"${NC}" 