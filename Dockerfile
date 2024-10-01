FROM python:3.10-slim

WORKDIR /app

# Update pip
RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose port 5001
EXPOSE 5001

# Run the Flask app
CMD ["python", "app.py"]
