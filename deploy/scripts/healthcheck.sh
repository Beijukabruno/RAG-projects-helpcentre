#!/bin/sh
# Healthcheck script for chatbot API
curl --fail http://localhost:8000/health || exit 1
