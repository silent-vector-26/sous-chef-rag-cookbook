FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir python-dotenv openai azure-search-documents azure-identity streamlit azure-monitor-opentelemetry
COPY src ./src
COPY app ./app
COPY .streamlit ./.streamlit
COPY data ./data
ENV PYTHONPATH=/app/src
EXPOSE 8501
CMD ["streamlit", "run", "app/streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
