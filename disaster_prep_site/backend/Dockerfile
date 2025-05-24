# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the .env file. Make sure it's present during build or handled appropriately.
COPY .env .

# Copy the rest of the application code from your backend directory into the /app directory
COPY ./app ./app
COPY ./documents ./documents # Also copy documents folder if RAG needs it at runtime
COPY ./vectorstore_faiss ./vectorstore_faiss # Copy existing vector store if pre-built

# Make port 5001 available to the world outside this container
EXPOSE 5001

# Define environment variables (if not using .env or want to override)
# ENV GOOGLE_API_KEY your_api_key_here 

# Run main.py when the container launches
# The command in main.py is app.run(host='0.0.0.0', port=5001)
# If main.py is in app/main.py and app is a package:
CMD ["python", "-m", "app.main"]
