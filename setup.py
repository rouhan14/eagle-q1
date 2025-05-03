# setup.py
from setuptools import setup, find_packages

setup(
    name="csv-summarizer",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "flask==2.3.3",
        "boto3==1.28.38",
        "pandas==2.1.0",
        "openai==1.12.0",
        "groq==0.4.0",
        "python-dotenv==1.0.0",
        "gunicorn==21.2.0",
    ],
)

# run.sh
#!/bin/bash
# Simple script to run the application

# Create and activate virtual environment
# echo "Creating virtual environment..."
# python -m venv venv
# source venv/bin/activate

# # Install dependencies
# echo "Installing dependencies..."
# pip install -e .

# # Run the application
# echo "Starting the application..."
# python app.py