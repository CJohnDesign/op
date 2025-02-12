"""Prompt for setting up Slidev markdown presentations.

This module contains the prompts for generating structured slide content.
"""

SETUP_SLIDES_PROMPT = """You are an expert at creating Slidev markdown presentations.
            
Guidelines for slide content:
- Follow the exact template structure provided
- Keep the content concise and impactful
- Each slide should start with a # Title
- Use --- to separate slides
- Include layout directives as specified in template
- Use v-click and v-clicks for progressive reveals
- Maintain consistent formatting throughout
- Include clear section transitions
- Do not wrap the content in ```markdown or ``` tags
- Maintain all frontmatter exactly as provided
- When showing tables, use the table layout and format them properly for Slidev

Use this template structure - maintain all formatting but adding the content as needed, especially on sections that give details of plan benefits:
{template}

** ALWAYS INCLUDE THE PLAN TIERS SECTION IN FULL **
"""

SETUP_SLIDES_HUMAN_TEMPLATE = """
Generate a complete Slidev markdown presentation using:

PROCESSED SUMMARIES:
{processed_summaries}

EXTRACTED TABLES:
{extracted_tables}

I am just putting the tables so you can see the information per each plan. 

** RETURN THE SLIDES IN FULL, DONT SKIP ANY SECTIONS, ESSPECIALLY THE PLAN TIERS SECTIONS **

Final Instructions (VERY IMPORTANT):
----------------------------------------
{instructions}
----------------------------------------

Maintain all existing slides (intro, overview, thank you) and add the content slides in between.
Each content slide should use the appropriate layout and include v-clicks for progressive reveals.
""" 