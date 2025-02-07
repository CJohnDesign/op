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
- Maintain all frontmatter exactly as provided"""

SETUP_SLIDES_HUMAN_TEMPLATE = """
Use this exact template structure - maintain all formatting, frontmatter, and sections:

{template}

Generate a complete Slidev markdown presentation using this processed summary content:
{processed_summaries}

** DONT SKIP ANY SECTIONS, ESSPECIALLY THE PLAN TIERS SECTIONS **

Maintain all existing slides (intro, overview, thank you) and add the content slides in between.
Each content slide should use the appropriate layout and include v-clicks for progressive reveals.""" 