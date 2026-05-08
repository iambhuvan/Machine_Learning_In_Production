# Automation Tooling for Risk Analysis

This directory contains Python scripts to automate the identification of stakeholders and analysis of risks/requirements using an LLM (Groq via LiteLLM).

## Prerequisites
*   Python 3.8+
*   A Groq API Key

## Installation
1.  Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```
2.  Set your Groq API Key:
    *   Create a `.env` file in the root directory:
        ```
        LITELLM_API_KEY=gsk_...
        ```
    *   Or export it in your shell:
        ```bash
        export LITELLM_API_KEY="gsk_..."
        ```

## Usage

### Step 1: Identify Stakeholders
Run the identification script to generate a list of stakeholders.
```bash
python src/identify_stakeholders.py --output stakeholders_list.md
```
This will create `stakeholders_list.md`. You can review and edit this file manually if needed before proceeding.

### Step 2: Analyze Risks
Run the analysis script to generate values, losses, requirements, assumptions, and specifications for the stakeholders.
```bash
python src/analyze_risks.py --input stakeholders_list.md --output analysis_results.md
```
This will generate `analysis_results.md`.

## Files
*   `src/llm_client.py`: Wrapper for the LLM interaction (using `litellm`).
*   `src/identify_stakeholders.py`: Prompt logic for stakeholder discovery.
*   `src/analyze_risks.py`: Prompt logic for STPA-style analysis.
