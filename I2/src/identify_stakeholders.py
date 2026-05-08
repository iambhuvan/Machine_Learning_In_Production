import argparse
from llm_client import query_llm

SYSTEM_DESCRIPTION = """
We are designing a Dashcam system that includes a 'Child Safety' feature.
The system connects to distributed dashcams to help locate missing children by identifying them in video feeds using an AI person recognition model.
The dashcams do not have direct internet access but communicate via USB/Bluetooth/Wifi.
The goal is to match dashcam footage against a database of missing children (similar to Amber alerts).
"""

PROMPT_TEMPLATE = """
{system_description}

Your task is to identify a comprehensive list of direct and indirect stakeholders for this system.
Think broadly about who affects the system and who is affected by it.
Consider:
1. Primary Users (Dashcam owners, Parents)
2. Indirect Users (Children, Pedestrians)
3. Operational Support (Law Enforcement, Non-profits)
4. Regulatory/Legal (Privacy advocates, Regulators)
5. Business (Competitors, Partners)

Please list at least 15 stakeholders. For each, provide a brief 1-sentence description of their interest or concern.
Format the output as a Markdown list.
"""

def main():
    parser = argparse.ArgumentParser(description="Identify stakeholders for the Dashcam system.")
    parser.add_argument("--output", default="stakeholders_list.md", help="Output file for the list")
    args = parser.parse_args()

    print("Querying LLM for stakeholders...")
    prompt = PROMPT_TEMPLATE.format(system_description=SYSTEM_DESCRIPTION)
    
    response = query_llm(prompt, model="groq/llama-3.3-70b-versatile") # Using Groq via LiteLLM
    
    print(f"Writing results to {args.output}...")
    with open(args.output, "w") as f:
        f.write("# Stakeholders List\n\n")
        f.write(response)
    
    print("Done.")

if __name__ == "__main__":
    main()
