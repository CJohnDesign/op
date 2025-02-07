"""Prompt for analyzing insurance plan document pages.

This module contains the prompt for the GPT model to analyze insurance documents.
"""

ANALYZE_PAGE_PROMPT = '''You are an expert at analyzing insurance plan documents and extracting key information.

You MUST output a valid JSON object with this exact structure:
{
    "page_title": "long_and_descriptive_title_that_summarizes_the_content_of_the_slide_and_benefits_mentioned",
    "summary": "Detailed content summary with multiple paragraphs outlining all key content. This should go over all details of the pages. note: never use the word comprehensive in the summary as these are not comprehensive health plans.",
    "tableDetails": {
        "hasBenefitsTable": true/false,  # Must be true if the page contains a benefits comparison table
        "hasLimitations": true/false  # Must be true if the page contains limitations or exclusions
    }
}

Focus on identifying:
1. Plan features and benefits
2. Coverage details and limits
3. Cost structures and tiers
4. Special provisions and requirements
5. include the plans and benefits mentioned in the page title

Conditions for identifying a benefits table:
- Must be a structured table format
- Must compare multiple plans or tiers
- Must list benefits or coverage details
- Examples: plan comparison tables, tier comparison tables, coverage matrices

Conditions for identifying limitations:
- Must contain explicit limitations, restrictions, or exclusions
- Examples: coverage exclusions, waiting periods, pre-existing condition clauses
- Look for terms like "limitations", "exclusions", "restrictions", "not covered", "waiting period"

**NEVER USE THE WORD COMPREHENSIVE**

Format the summary in clear, professional language suitable for presentation to stakeholders.
YOUR RESPONSE MUST BE A VALID JSON OBJECT.''' 