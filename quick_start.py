# quick_start.py
"""
Quick setup script for CSV Summarization Microservice
This script sets up the minimal configuration needed to run the service
"""
import os
import sys
import subprocess
import platform

def check_python_version():
    """Check if Python version is at least 3.8"""
    required_version = (3, 8)
    current_version = sys.version_info
    
    if current_version < required_version:
        print(f"Error: Python {required_version[0]}.{required_version[1]} or higher is required")
        print(f"Current version: {current_version[0]}.{current_version[1]}")
        sys.exit(1)
    
    return True

def create_virtual_environment():
    """Create a virtual environment"""
    print("Creating virtual environment...")
    
    if os.path.exists("venv"):
        print("Virtual environment already exists, skipping creation.")
        return True
    
    try:
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        print("Virtual environment created successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error creating virtual environment: {e}")
        return False

def install_packages():
    """Install required packages"""
    print("Installing required packages...")
    
    # Determine the pip path based on the platform
    if platform.system() == "Windows":
        pip_path = os.path.join("venv", "Scripts", "pip")
    else:
        pip_path = os.path.join("venv", "bin", "pip")
    
    # Packages to install
    base_packages = ["flask", "pandas", "python-dotenv", "gunicorn"]
    
    # Ask which LLM providers to install
    print("\nWhich LLM provider(s) would you like to use?")
    print("1. OpenAI (GPT models)")
    print("2. Groq (Llama 3 70B)")
    print("3. Both")
    
    choice = input("Enter your choice (1-3): ").strip()
    
    llm_packages = []
    if choice in ["1", "3"]:
        llm_packages.append("openai")
    if choice in ["2", "3"]:
        llm_packages.append("groq")
    
    if not llm_packages:
        print("Error: You must select at least one LLM provider.")
        return False
    
    # Ask if AWS integration is needed
    aws_integration = input("\nDo you want AWS integration for DynamoDB and SNS? (y/n): ").lower().strip()
    if aws_integration == "y":
        base_packages.append("boto3")
    
    # Install packages
    packages = base_packages + llm_packages
    try:
        subprocess.run([pip_path, "install", "-U"] + packages, check=True)
        print("Packages installed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing packages: {e}")
        return False

def create_env_file():
    """Create a .env file with necessary configuration"""
    print("\nCreating .env file...")
    
    if os.path.exists(".env"):
        overwrite = input(".env file already exists. Overwrite? (y/n): ").lower().strip()
        if overwrite != "y":
            print("Skipping .env file creation.")
            return True
    
    env_content = [
        "# CSV Summarization Service Configuration",
        "",
        "# LLM API Keys (at least one is required)",
    ]
    
    openai_key = input("Enter your OpenAI API key (leave blank if not using): ").strip()
    if openai_key:
        env_content.append(f"OPENAI_API_KEY={openai_key}")
    
    groq_key = input("Enter your Groq API key (leave blank if not using): ").strip()
    if groq_key:
        env_content.append(f"GROQ_API_KEY={groq_key}")
    
    aws_integration = input("\nDo you want to configure AWS now? (y/n): ").lower().strip()
    if aws_integration == "y":
        env_content.extend([
            "",
            "# AWS Configuration",
            f"AWS_ACCESS_KEY_ID={input('AWS Access Key ID: ').strip()}",
            f"AWS_SECRET_ACCESS_KEY={input('AWS Secret Access Key: ').strip()}",
            f"AWS_REGION={input('AWS Region (default: us-east-1): ').strip() or 'us-east-1'}",
            f"DYNAMODB_TABLE={input('DynamoDB Table Name (default: SummarizationResults): ').strip() or 'SummarizationResults'}",
            f"SNS_TOPIC_ARN={input('SNS Topic ARN: ').strip()}"
        ])
    
    try:
        with open(".env", "w") as f:
            f.write("\n".join(env_content))
        print(".env file created successfully.")
        return True
    except Exception as e:
        print(f"Error creating .env file: {e}")
        return False

def create_run_script():
    """Create a run script based on the platform"""
    print("\nCreating run script...")
    
    if platform.system() == "Windows":
        script_name = "run.bat"
        script_content = "@echo off\r\necho Starting CSV Summarization Service...\r\n" \
                        "call venv\\Scripts\\activate\r\n" \
                        "python app.py"
    else:
        script_name = "run.sh"
        script_content = "#!/bin/bash\necho Starting CSV Summarization Service...\n" \
                        "source venv/bin/activate\n" \
                        "python app.py"
    
    try:
        with open(script_name, "w") as f:
            f.write(script_content)
        
        # Make executable on Unix-like systems
        if platform.system() != "Windows":
            os.chmod(script_name, 0o755)
        
        print(f"Run script created: {script_name}")
        return True
    except Exception as e:
        print(f"Error creating run script: {e}")
        return False

def main():
    """Main function"""
    print("=" * 60)
    print("CSV Summarization Microservice - Quick Setup")
    print("=" * 60)
    
    check_python_version()
    
    if not create_virtual_environment():
        sys.exit(1)
    
    if not install_packages():
        sys.exit(1)
    
    if not create_env_file():
        sys.exit(1)
    
    if not create_run_script():
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("Setup completed successfully!")
    print("=" * 60)
    
    if platform.system() == "Windows":
        print("\nTo run the service, execute: run.bat")
    else:
        print("\nTo run the service, execute: ./run.sh")
    
    print("\nThe service will be available at: http://localhost:5000")

if __name__ == "__main__":
    main()