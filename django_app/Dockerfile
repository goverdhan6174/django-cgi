# Dockerfile
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Django project into the container
COPY . /app

# Expose port 8000
EXPOSE 8000

# Command to run the application with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "nc_app.wsgi:application"]
