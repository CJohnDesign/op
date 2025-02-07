"""Prompt for generating presentation content from analyzed insurance plan data.

This module contains the prompt for the GPT model to generate a structured presentation.
"""

GENERATE_PRESENTATION_PROMPT = '''You are an expert at summarizing insurance plan data into a cohesive aggregated summary for creating presentation slides and a narrative script.
Below are the instructions for the aggregated summary structure:

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

## Plan 1

**Category 1**
- **Details with values**
- **Details with values**
**Category 2**
- **Details with values**
- **Details with values**

**Category 3**
- **Details with values**
- **Details with values**

**Category 4**
- **Details with values**
- **Details with values**

**Category 5**
- **Details with values**   
- **Details**

**Category 6**
- **Details**
    
## Plan 2

**Category 1**
- **Details with values**
- **Details with values**
- **Details with values**

**Category 2**
- **Details with values**
- **Details with values**

**Category 3**
- **Details with values**
- **Details with values**

**Category 4**
- **Details with values**

**Category 5**
- **Details with values**

**Category 6**
- **Details**

## Plan 3 (1/2)

**Category 1**
- **Details with values**
- **Details with values**
- **Details with values**
- **Details with values**

**Category 2**
- **Details with values**
- **Details with values**

## Plan 3 (2/2)

**Category 3**
- **Details with values**
- **Details with values**

**Category 4**
- **Details with values**

**Category 5**
- **Details**

**Category 6**
- **Details**

Comparison slides showing differences among the tiers.
    - Highlight the benefits of each tier, but don't be redundant.
    - should return a markdown formatted spread sheet showing key differences between tiers.

Limitations and Exclusions (1-2 slides)
   - Define exclusions (e.g., pre-existing conditions, waiting periods, prescription limitations).

Key Takeaways and Action Steps (1 slide)
   - Summarize the plan's flexibility, its balance between cost and coverage, and detail next steps for enrollment or obtaining support.

Thank You (1 slide)
   - Conclude with a branded thank you message 

Individual Summaries:
---------------------
{individual_summaries}

Extracted Table Information:
----------------------------
{extracted_tables}

**NEVER USE THE WORD COMPREHENSIVE**

Outline your plan for the full presentation plan. add extra detail to the plan tiers sections

return only the content without any other text or comments''' 