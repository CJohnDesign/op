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

GENERATED PRESENTATION CONTENT (MOST IMPORTANT - USE THIS AS YOUR PRIMARY SOURCE):
{presentation_content}

EXTRACTED TABLES:
{extracted_tables}

IMAGE USAGE GUIDELINES:
1. Brochure Page Images:
   - Available pages: {pages_list}
   - These are the actual brochure page images
   - Use these when referencing specific pages from the brochure
   - Example usage: ![Page 1](/img/pages/page1.jpg)
   - Always include descriptive alt text

2. Special Purpose Pages:
   - Pages with benefit tables: {pages_with_tables_list}
   - Pages with limitations: {pages_with_limitations_list}
   - Use benefit table pages for plan comparisons and tier details
   - Use limitation pages when discussing restrictions and exclusions
   - Match the appropriate page to the content being discussed

3. Logo Images:
   - Available logos: {logos_list}
   - These are company and product logos
   - Use these when mentioning company branding or products
   - Example usage: ![Company Logo](/img/logos/logo.svg)
   - Always include descriptive alt text

Key Image Rules:
- Brochure pages should ONLY be used when showing actual pages from the document
- Use benefit table pages specifically when showing plan comparisons
- Use limitation pages when discussing restrictions and exclusions
- Logos should ONLY be used when mentioning company branding or specific products
- Always use the exact paths provided in the lists above
- Every image must include descriptive alt text for accessibility
- Do not modify or alter the image paths in any way

Content Generation Rules:
- Use the generated presentation content as your primary source of information
- Maintain the exact structure and flow from the generated presentation
- Keep all benefit details, values, and limits exactly as specified
- Format the content to match the Slidev template structure
- Ensure all plan tiers are included with their complete details

Comparison Tables:
- these may look like they have a lot of v-clicks, but they don't
- only return the results of the comparison table in one continous paragraph

** RETURN THE SLIDES IN FULL, DONT SKIP ANY SECTIONS, ESPECIALLY THE PLAN TIERS SECTIONS **

Image Directory Information:
----------------------------------------
Image directories for pages with benefits tables: {pages_with_tables_list}
(Use these pages when showing benefit plan tier details)

Image directories for pages with limitations: {pages_with_limitations_list}
(Use these pages when showing exclusions, restrictions, or coverage limits)

Image directories for logos: {logos_list}

Here are the page summaries so you can get a better understanding of the content: 
{processed_summaries}
----------------------------------------

Final Instructions (VERY IMPORTANT):
----------------------------------------
{instructions}
----------------------------------------

Maintain all existing slides (intro, overview, thank you) and add the content slides in between.
Each content slide should use the appropriate layout and include v-clicks for progressive reveals.
""" 