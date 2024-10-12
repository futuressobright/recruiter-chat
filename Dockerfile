# Step 1: Build stage for compiling dependencies
FROM python:3.9-alpine AS builder

# Install build tools and libraries
RUN apk --no-cache add build-base g++ bash openblas-dev

# Set up working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Step 2: Production stage
FROM python:3.9-alpine

# Install runtime libraries only
RUN apk --no-cache add --virtual .runtime-deps bash openblas

# Copy necessary files from builder stage
COPY --from=builder /usr/local /usr/local
COPY --from=builder /app /app

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose the port
EXPOSE 8080

# Run the application
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8080", "app:app"]
