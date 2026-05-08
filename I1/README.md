# Zulip ML Features Assignment

This repository contains the implementation of two LLM-enabled features for Zulip: Message Recap and Topic Title Improver.

## Installation and Running

We assume the standard Zulip Vagrant development environment.

1.  **Start the environment:**
    ```bash
    vagrant up
    vagrant ssh
    ```


2.  **Install Dependencies:**
    This project uses `litellm`. Run the following to ensure it is installed in the Zulip environment:
    ```bash
    cd /srv/zulip
    ./tools/provision
    ```

3.  **Set up API Keys:**
    The features require an LLM API key (e.g., Groq, OpenAI). This is managed via the `LITELLM_API_KEY` environment variable.
    
    You can set this in your shell before running the server, or add it to `.bashrc`:
    ```bash
    export LITELLM_API_KEY="your-api-key-here"
    ```

4.  **Run the Server:**
    Start the development server with:
    ```bash
    cd /srv/zulip
    ./tools/run-dev
    ```
    The server will be accessible at `http://localhost:9991`.

## Features

### 1. Message Recap
Generates a concise summary of unread messages in a stream.
*   **Usage**: Navigate to a stream. Click the "Recap" button in the top header.
*   **Result**: A modal appears with a bulleted summary. Each point links to the original conversation.

### 2. Topic Title Improver
Detects when a conversation drifts and suggests a better title.
*   **Automated**: Send messages that drift from the current topic (e.g., talk about "coding" in a "Dating" topic). The system will **automatically rename** the topic and redirect all users to the new conversation thread.
*   **Manual**: Click the "Suggest Title" button (pencil icon) in the message view header to forcefully generate a suggestion.
