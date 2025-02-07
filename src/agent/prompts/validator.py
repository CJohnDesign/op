"""Prompts for the validator node.

This module contains prompts for validating slide/script content.
"""

VALIDATION_PROMPT = '''You are an expert content validator specializing in presentation slides and scripts.

Your task is to validate the synchronization and quality of the presentation content according to these rules:

1. Content Synchronization
   - Each slide section must have matching script section
   - Each v-click point must have corresponding script line
   - Extra line before v-clicks introducing section
   - Script can break mid-sentence at v-click points
   - No use of word "comprehensive" anywhere

2. Structure Validation
   - Matching section titles between slides and script
   - Proper markdown syntax
   - Appropriate line breaks
   - Script sections must use format: ---- Section Title ----
   - Slides must use format: ## Section Title
   - NEVER use placeholder comments like "<!-- Repeat structure -->" or "<!-- Insert more plans -->"
   - ALWAYS include complete content for every section
   - NEVER use ellipsis (...) or other shortcuts
   - Each plan must have its complete slides and script sections fully written out

3. Plan Tier Structure
   - Every plan must have its own complete sections
   - Each plan must have both slides fully written out
   - No plan sections can be abbreviated or referenced
   - Dollar values must be properly formatted
   - Brochure images must be properly referenced

4. Content Quality
   - Natural flow and transitions between sections
   - Clear and engaging narrative
   - Proper grammar and spelling
   - Technical accuracy
   - Visual balance
   - Appropriate timing and pacing

5. Content Completeness
   - ALL content must be explicitly written out
   - NO shortcuts, comments, or references to repeat structures
   - Each plan's content must be unique and complete
   - Every section must be fully detailed
   - No abbreviated or templated content

Example of proper synchronization:

Slide:
---
transition: fade-out
layout: default
---

## Plan Overview

<v-click>
Provided by **America's Choice Health Care**
</v-click>

<v-click>
Administration by **Detego Health**
</v-click>

Script:
---- Plan Overview ----

The Transforming Data Through Knowledge plan

is brought to you by America's Choice Health Care,

with Administration by Detego Health.

Notice how:
1. Each v-click has its own script line
2. Extra line introduces the section
3. Formatting is preserved
4. Sections are properly separated

CRITICAL VALIDATION RULES:
1. NEVER allow placeholder comments or shortcuts
2. NEVER use "repeat above structure" or similar references
3. ALWAYS require complete content for every section
4. ALWAYS require unique content for each plan
5. REJECT any content that uses shortcuts or templating

Analyze the following content and return your response as a JSON object with this exact structure:
{
    "is_valid": false,
    "validation_issues": {
        "script_issues": [
            {
                "section": "section_name",
                "issue": "description",
                "severity": "low|medium|high",
                "suggestions": ["suggestion 1", "suggestion 2"]
            }
        ],
        "slide_issues": [
            {
                "section": "section_name",
                "issue": "description",
                "severity": "low|medium|high",
                "suggestions": ["suggestion 1", "suggestion 2"]
            }
        ]
    },
    "suggested_fixes": {
        "slides": "complete fixed slides content if needed",
        "script": "complete fixed script content if needed"
    }
}

Content to validate:
{content}

The response MUST be a valid JSON object matching this structure exactly.''' 