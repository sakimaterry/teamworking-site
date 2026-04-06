FROM python:3.11-slim
RUN pip install --no-cache-dir flask gunicorn
WORKDIR /app
COPY . .
EXPOSE 80
CMD ["gunicorn", "-b", "0.0.0.0:80", "-w", "2", "--access-logfile", "-", "server:app"]
