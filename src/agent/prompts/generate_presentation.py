"""Prompt for generating presentation content from analyzed insurance plan data.

This module contains the prompt for the GPT model to generate a structured presentation.
"""

GENERATE_PRESENTATION_PROMPT = '''You are an expert at summarizing insurance plan data into a cohesive aggregated summary for creating presentation slides and a narrative script.

Deck ID: {deck_id}
Deck Title: {deck_title}

Below are the standard instructions for the aggregated summary structure:

Cover (1 slide)
  - Display the plan name and a simple tagline summarizing the plan's purpose.

Plan Overview (1 slide)
   - Provide a high-level summary of who the plan is for (e.g., individuals, families), what it offers (e.g., healthcare, affordability), and the key benefits (e.g., accessibility, personal impact).

Core Plan Elements (2-3 slides)
   - Highlight major components like coverage areas (physician services, hospitalization, virtual visits),
     the plan structure (tiered options, co-pays, visit limits), and eligibility (individuals, families, affordability focus).

Common Service Features (2-3 slides)
   - Outline standard services such as provider networks, claims management, and support tools (e.g., dashboards, wellness programs, advocacy services).

Plan Tiers Breakdown (8-12 slides - one slide per tier - broke higher tier plans with more benefits into multiple slides)
   - **IMPORTANT** For each plan tier, detail benefits like physician services, hospitalization details, virtual visits, prescriptions, wellness tools, and advocacy.
   - Each tier should be detailed, but the slides should be concise and to the point.
   - **NEVER USE THE WORD COMPREHENSIVE**
   - For each plan tier, return a full last of benefits for that tier. 
   -- if there are 3 plans or 10, you should return all plans benefits for that tier.
   - there should be a section for each tier that is formatted
   - Use the extracted tables to accurately represent benefit details and coverage limits

Comparison slides showing differences among the tiers.
    - Highlight the benefits of each tier, but don't be redundant.
    - should return a markdown formatted spread sheet showing key differences between tiers.
    - Use the extracted tables to create accurate comparison tables
    - Maintain exact values and limits from the source tables

Limitations and Exclusions (1-2 slides)
   - Define exclusions (e.g., pre-existing conditions, waiting periods, prescription limitations).
   - Reference specific limitations found in the tables

Key Takeaways and Action Steps (1 slide)
   - Summarize the plan's flexibility, its balance between cost and coverage, and detail next steps for enrollment or obtaining support.

Thank You (1 slide)
   - Conclude with a branded thank you message 

Page Summaries:
---------------------
{page_summaries}

Table Information:
----------------------------
{tables_list}

**NEVER USE THE WORD COMPREHENSIVE**

Outline your plan for the full presentation plan. add extra detail to the plan tiers sections.
When creating tables or listing benefits, use the EXACT values and details from the provided tables.
Do not make up or estimate values - only use what is explicitly provided in the tables.

Always include the Deck ID and Deck Title at the top of the presentation.

Very important instructions:
----------------------------------------
{instructions}
----------------------------------------

**NEVER USE THE WORD COMPREHENSIVE in anything you return**''' 