# app.py
from flask import Flask, request, jsonify
import uuid
import os
import json
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Optional imports - will be imported only if needed
boto3_optional_import_error = None
try:
    import boto3
except ImportError as e:
    boto3_optional_import_error = e

openai_optional_import_error = None
try:
    import openai
except ImportError as e:
    openai_optional_import_error = e

groq_optional_import_error = None
try:
    from groq import Groq
except ImportError as e:
    groq_optional_import_error = e

app = Flask(__name__)

# Configure AWS services - with graceful fallback if boto3 isn't installed
dynamodb = None
table = None
sns = None
sns_topic_arn = os.environ.get('SNS_TOPIC_ARN')

if boto3_optional_import_error is None:
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ.get('DYNAMODB_TABLE', 'SummarizationResults'))
        sns = boto3.client('sns')
    except Exception as e:
        print(f"Warning: AWS services not configured properly: {str(e)}")
        print("Continuing without AWS integration - results won't be stored in DynamoDB or published to SNS")

# LLM client selection based on environment variables
def get_llm_client():
    """
    Determine which LLM client to use based on environment variables.
    Prefers OpenAI if API key is available, otherwise falls back to Groq.
    """
    # Check if OpenAI is available and configured
    if openai_optional_import_error is None:
        openai_api_key = os.environ.get('OPENAI_API_KEY')
        if openai_api_key:
            try:
                openai.api_key = openai_api_key
                return "openai"
            except Exception as e:
                print(f"Warning: Failed to configure OpenAI client: {str(e)}")
    
    # Try Groq if OpenAI is not available
    if groq_optional_import_error is None:
        groq_api_key = os.environ.get('GROQ_API_KEY')
        if groq_api_key:
            return "groq"
    
    # Check what's missing
    if openai_optional_import_error is not None and groq_optional_import_error is not None:
        raise ValueError("Both OpenAI and Groq libraries are missing. Install at least one: 'pip install openai groq'")
    
    raise ValueError("Neither OpenAI nor Groq API keys found in environment. Set at least one in .env file")

# Try to configure the LLM provider, but don't fail immediately if not set up
llm_provider = None
try:
    llm_provider = get_llm_client()
except ValueError as e:
    print(f"Warning: {str(e)}")
    print("Service will start but summarization won't work until an LLM is configured")

@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({"status": "healthy", "llm_provider": llm_provider})

@app.route('/summarize', methods=['POST'])
def summarize():
    """
    Endpoint that receives CSV files, processes them through an LLM for summarization,
    stores the results in DynamoDB, and publishes an event to SNS.
    """
    # Check if a file was included in the request
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    
    # Verify the file has a filename and is a CSV
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if not file.filename.endswith('.csv'):
        return jsonify({"error": "File must be a CSV"}), 400
    
    try:
        # Parse the CSV with more robust error handling
        try:
            df = pd.read_csv(file, on_bad_lines='warn')
        except Exception as e:
            app.logger.error(f"CSV parsing error: {str(e)}")
            return jsonify({"error": f"Failed to parse CSV file: {str(e)}"}), 400
        
        # Generate a basic description of the CSV
        row_count = len(df)
        column_count = len(df.columns)
        columns = df.columns.tolist()
        
        # Sample data (first 5 rows) for the LLM
        sample_data = df.head(5).to_dict(orient='records')
        
        # Create prompt for the LLM
        prompt = f"""
        Analyze the following CSV data and provide a comprehensive summary as JSON. 
        The CSV has {row_count} rows and {column_count} columns: {columns}.
        
        Here's a sample of the first few rows:
        {json.dumps(sample_data, indent=2)}
        
        Please provide a summary that includes:
        1. Basic statistics for each column (data type, min/max values for numeric fields, most common values for categorical fields)
        2. Key insights or patterns in the data
        3. Any correlations or relationships between columns
        4. Any data quality issues observed
        
        Format your response as a JSON object with these sections.
        """
        
        # Process with the selected LLM with improved error handling
        summary = None
        
        try:
            if llm_provider == "openai":
                response = openai.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[
                        {"role": "system", "content": "You are a data analysis assistant. Provide summaries of CSV data in JSON format only."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                summary = json.loads(response.choices[0].message.content)
            else:  # Use Groq with Llama 3 70B
                client = Groq(api_key=os.environ.get('GROQ_API_KEY'))
                response = client.chat.completions.create(
                    model="llama3-70b-8192",
                    messages=[
                        {"role": "system", "content": "You are a data analysis assistant. Provide summaries of CSV data in JSON format only."},
                        {"role": "user", "content": prompt}
                    ]
                )
                
                # Extract JSON from response with improved parsing
                content = response.choices[0].message.content
                # Find JSON in the response (in case there's any markdown or extra text)
                try:
                    # First try to parse the entire content as JSON
                    summary = json.loads(content)
                except json.JSONDecodeError:
                    # If that fails, try to extract JSON from markdown code blocks or surrounding text
                    json_start = content.find('{')
                    json_end = content.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        try:
                            summary = json.loads(content[json_start:json_end])
                        except json.JSONDecodeError as e:
                            # If still fails, return the raw response with error
                            app.logger.error(f"JSON parsing error: {str(e)} in content: {content[json_start:json_end]}")
                            summary = {"error": "Could not parse LLM response as JSON", 
                                    "parsing_error": str(e),
                                    "summary_text": content}
                    else:
                        # Fallback if structured JSON not found
                        summary = {"error": "Could not find JSON in LLM response", "raw_response": content}
        except Exception as e:
            app.logger.error(f"LLM processing error: {str(e)}")
            return jsonify({"error": f"Failed to process with LLM: {str(e)}"}), 500
        
        # If no summary was generated, return an error
        if summary is None:
            return jsonify({"error": "Failed to generate summary from LLM"}), 500
        
        # Add metadata to the summary
        summary_id = str(uuid.uuid4())
        timestamp = pd.Timestamp.now().isoformat()
        
        result = {
            "summary_id": summary_id,
            "timestamp": timestamp,
            "filename": file.filename,
            "row_count": row_count,
            "column_count": column_count,
            "columns": columns,
            "llm_provider": llm_provider,
            "summary": summary
        }
        
        # Store in DynamoDB if available
        if table is not None:
            try:
                table.put_item(Item=result)
            except Exception as e:
                print(f"Warning: Failed to store result in DynamoDB: {str(e)}")
        
        # Publish to SNS if available
        if sns is not None and sns_topic_arn is not None:
            try:
                sns.publish(
                    TopicArn=sns_topic_arn,
                    Message=json.dumps({"event": "summary_created", "summary_id": summary_id}),
                    Subject="CSV Summary Created"
                )
            except Exception as e:
                print(f"Warning: Failed to publish to SNS: {str(e)}")
        
        return jsonify({
            "summary_id": summary_id,
            "timestamp": timestamp,
            "summary": summary
        })
        
    except Exception as e:
        app.logger.error(f"Error processing request: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)