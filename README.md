
# Agentic POC

An Agent tailored to execute a few tools based on user input with ability to plan and orchestration several tools. This is a standalone application executed in local environment.

## Prerequisites

This project uses:
- [uv](https://docs.astral.sh/uv/) for Python package and environment management. Install it first:

```bash
brew install uv
```

#### Env setup
Make sure have `OPENAI_API_KEY` env var set.

Set up dev environment:
```
make dev-setup
```  
 

#### To run project:

```
cd agent-poc && make run
```



