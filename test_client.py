# test_client.py
"""
Simple test client for the CSV Summarization Microservice.
This script allows uploading a CSV file and getting a summary without using curl.
"""
import requests
import sys
import json
import os

def summarize_csv(file_path, url="http://localhost:5000/summarize"):
    """
    Send a CSV file to the summarization service and print the result.
    
    Args:
        file_path (str): Path to the CSV file
        url (str): URL of the summarization endpoint
    """
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return
    
    if not file_path.lower().endswith('.csv'):
        print(f"Error: File must be a CSV: {file_path}")
        return
    
    print(f"Uploading {file_path} to {url}...")
    
    try:
        with open(file_path, 'rb') as file:
            files = {'file': (os.path.basename(file_path), file, 'text/csv')}
            response = requests.post(url, files=files)
        
        if response.status_code == 200:
            result = response.json()
            print("\nSummary successfully generated!")
            print(f"Summary ID: {result.get('summary_id', 'N/A')}")
            print(f"Timestamp: {result.get('timestamp', 'N/A')}")
            print("\nSummary Content:")
            print(json.dumps(result.get('summary', {}), indent=2))
        else:
            print(f"Error: Server returned status code {response.status_code}")
            print(response.text)
    
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the server. Is the service running?")
    except Exception as e:
        print(f"Error: {str(e)}")

def main():
    """Main function"""
    if len(sys.argv) != 2:
        print("Usage: python test_client.py <path_to_csv_file>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    summarize_csv(file_path)

if __name__ == "__main__":
    main()