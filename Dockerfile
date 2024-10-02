FROM python:3.10-slim

WORKDIR /app

# Update pip
RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose port 10000, for render.com
EXPOSE 10000

# Run the Flask app
CMD ["python", "app.py"]
