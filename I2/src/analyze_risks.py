import argparse
import os
import re
from llm_client import query_llm

SYSTEM_DESCRIPTION = """
We are designing a Dashcam system with a 'Child Safety' feature to locate missing children.
The system uses facial recognition on dashcam footage.
"""

# Prompt to extract just the names first
EXTRACT_NAMES_PROMPT = """
Below is a list of stakeholders in Markdown format.
Please extract ONLY the names of the stakeholders as a python list of strings.
Example output: ["Dashcam Owners", "Parents", "Police"]

List:
{stakeholders_content}
"""

# Deep analysis prompt per stakeholder
DEEP_ANALYSIS_PROMPT = """
{system_description}

Focus on the stakeholder: **{stakeholder_name}**

Your goal is to perform a deep STPA-style risk analysis for this specific stakeholder.
The assignment requires a high volume of rigorous requirements.

Please generate:
1. **5 to 10 distinct Losses** (Harms/Risks) relevant to this stakeholder's values.
2. For EACH Loss, define a corresponding **System Requirement (REQ)** to prevent it.
3. For EACH Requirement, provide **3 to 5 Environmental Assumptions (ASM)** AND **3 to 5 System Specifications (SPEC)**.

Format the output strictly as follows:

### {stakeholder_name}

#### Loss 1: [Name/Summary of Loss]
*   **Value at Risk**: [What value is threatened]
*   **Description**: [Detail of the loss]
*   **Requirement (REQ)**: [The requirement text]
    *   **ASM-1**: [Assumption 1]
    *   **ASM-2**: [Assumption 2]
    *   **ASM-3**: [Assumption 3]
    *   **SPEC-1**: [Specification 1]
    *   **SPEC-2**: [Specification 2]
    *   **SPEC-3**: [Specification 3]

... repeat for Loss 2, Loss 3, etc. (up to 10)

Ensure technical depth. Assumptions about the environment ("World") vs Specs about the system ("Machine").
"""

def extract_stakeholders(content):
    # Quick regex or LLM call to get the list. Let's use LLM to be safe/robust.
    response = query_llm(EXTRACT_NAMES_PROMPT.format(stakeholders_content=content), model="groq/llama-3.3-70b-versatile")
    # minimal cleanup to eval the list
    try:
        # Find the list part
        match = re.search(r'\[.*\]', response, re.DOTALL)
        if match:
            return eval(match.group(0))
    except:
        pass
    # Fallback: simple line parsing
    lines = content.split('\n')
    names = []
    for line in lines:
        if "*" in line:
            # * **Name**: Description
            parts = line.split("**")
            if len(parts) >= 2:
                names.append(parts[1])
    return names

def get_analyzed_stakeholders(output_file):
    if not os.path.exists(output_file):
        return []
    with open(output_file, 'r') as f:
        content = f.read()
    # Find headers like "### Stakeholder Name"
    # Note: Regex might need to be loose if spacing varies
    matches = re.findall(r'^### (.*?)$', content, re.MULTILINE)
    return [m.strip() for m in matches]

def main():
    parser = argparse.ArgumentParser(description="Analyze risks for stakeholders.")
    parser.add_argument("--input", default="stakeholders_list.md", help="Input file with stakeholders list")
    parser.add_argument("--output", default="analysis_results.md", help="Output file for analysis")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: Input file {args.input} not found.")
        return

    with open(args.input, "r") as f:
        stakeholders_content = f.read()

    print("Extracting stakeholder names...")
    stakeholders = extract_stakeholders(stakeholders_content)
    print(f"Found {len(stakeholders)} stakeholders: {stakeholders}")

    analyzed = get_analyzed_stakeholders(args.output)
    print(f"Already analyzed: {analyzed}")

    # If the file doesn't exist, create it with header.
    if not os.path.exists(args.output):
        with open(args.output, "w") as f:
            f.write("# Comprehensive Risk Analysis Report\n\n")

    for sh in stakeholders:
        if sh in analyzed:
            print(f"Skipping {sh} (already analyzed)...")
            continue
            
        print(f"Analyzing {sh}...")
        prompt = DEEP_ANALYSIS_PROMPT.format(
            system_description=SYSTEM_DESCRIPTION,
            stakeholder_name=sh
        )
        response = query_llm(prompt, model="groq/llama-3.3-70b-versatile")
        
        with open(args.output, "a") as f:
            f.write(response + "\n\n")
            f.flush() # Ensure write to disk

    print("Done. Report generated.")

if __name__ == "__main__":
    main()
