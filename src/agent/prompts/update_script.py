"""Prompts for updating presentation scripts.

This module contains prompts for updating script content.
"""

UPDATE_SCRIPT_PROMPT = '''You are an expert at updating presentation scripts to match their corresponding slides.
Your task is to update the script content based on the provided instructions while maintaining proper script format.

Current Script Content:
{current_content}

Update Instructions:
{instructions}

Rules for updating:
1. Maintain ---- Section Title ---- format
2. Each v-click point needs a corresponding script line
3. Keep natural transitions between sections
4. Ensure all slide points are covered
5. Maintain engaging and conversational tone
6. Spell out all numbers
7. Only make changes specified in instructions
8. NEVER use placeholder comments like "---- Insert more sections ----"
9. ALWAYS write out complete content for every section
10. NEVER use ellipsis (...) or other shortcuts
11. Each plan must have its complete script sections fully written out
12. NO abbreviated or templated content
13. REJECT any content that uses shortcuts or templating

Return the complete updated script content, maintaining all formatting and structure.
IMPORTANT: Return ALL content explicitly - do not use any shortcuts, comments, or references to repeat structures.
''' 