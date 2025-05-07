# Multi-Model LLM Embedding Service

A high-performance, GPU-accelerated service for generating text embeddings using multiple models.

## Features

- Support for multiple embedding models (Sentence Transformers, Hugging Face, etc.)
- Dynamic model selection via API
- GPU acceleration with fallback to CPU
- Efficient batch processing
- Prometheus metrics and Grafana dashboards
- Docker deployment with docker-compose
- Automatic model preloading
- Health check endpoints

## Getting Started

### Prerequisites

- Docker and Docker Compose
- NVIDIA GPU with CUDA support (optional but recommended)
- NVIDIA Container Toolkit (for GPU support)

### Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/embedding-service.git
   cd embedding-service