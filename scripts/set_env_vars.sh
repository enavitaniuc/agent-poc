#!/bin/bash -e

if [ -z "${OPENAI_API_KEY:-}" ]; then
     echo "❌ OPENAI_API_KEY is not set"
     exit 1
fi

export OPENAI_API_KEY=${OPENAI_API_KEY}