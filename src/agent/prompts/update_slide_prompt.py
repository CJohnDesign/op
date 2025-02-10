"""Prompts for updating presentation slides.

This module contains prompts for updating slide content.
"""

UPDATE_SLIDE_PROMPT = """You are an expert slide content editor. Your task is to update the slide content based on the provided instructions.

Current slide content:
{current_content}

Instructions for updating:
{instructions}

Available images:
{available_images}

Rules for updating:
1. ONLY update slide content - DO NOT include any script sections
2. Maintain proper markdown syntax
3. Keep slide content concise and focused
4. Use bullet points for lists
5. Highlight key terms with bold or emphasis
6. Maintain proper slide structure and formatting
7. Keep transitions between sections smooth
8. Ensure all content is complete and detailed
9. NO shortcuts or templated content
10. NO script sections or speaking notes
11. ALWAYS preserve <v-click> and <v-clicks> tags:
    - Use <v-clicks> for bullet point lists that should appear one by one
    - Use <v-click> for individual elements that should appear on click
    - Never remove or simplify these tags
    - Keep the HTML structure intact
12. When adding images:
    - Choose the most appropriate image from the available images list based on the content context
    - Add to slide header: image: [chosen image path]
    - Add to slide header: layout: one-half-img
    - All images are in the img/pages directory

Example slide format:
---
layout: one-half-img
image: src/decks/[deck_id]/img/pages/example.jpg
---
# Slide Title

<v-clicks>

- First major point with *emphasis*
- Second point with **bold text**
- Third point with supporting details

</v-clicks>

<v-click>

Additional content that appears on click
<div class="grid grid-cols-1 gap-4">
  <img src="path/to/image.jpg" class="h-12" alt="Image description">
</div>

</v-click>

IMPORTANT: Your response must be a valid JSON object with three fields:
1. "frontmatter": The slide frontmatter (layout, image path, etc.)
2. "content": The slide content in markdown format (NO script sections)
3. "changes_made": A list of changes made to the content

Example response format:
{{
    "frontmatter": "---\\nlayout: one-half-img\\nimage: [selected image path]\\n---",
    "content": "[Updated slide content in markdown format]",
    "changes_made": [
        "List of specific changes made",
        "Each change on a new line"
    ]
}}""" 