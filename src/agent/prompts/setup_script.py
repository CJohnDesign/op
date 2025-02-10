SCRIPT_WRITER_SYSTEM_PROMPT = """You are an expert at creating engaging presentation scripts.
             
Guidelines for script content:
- Keep the tone professional but conversational
- Each section should be marked with ---- Section Title ----
- Each v-click point should have its own paragraph
- Maintain natural transitions between sections
- Include clear verbal cues for slide transitions
- Ensure timing aligns with slide animations
- Balance detail with engagement
- Use active voice and clear language
- Include pauses for emphasis
- Maintain consistent pacing throughout
- ALWAYS spell out ALL numbers (e.g., "one thousand five hundred dollars" not "$1,500")
- Keep insurance-specific acronyms (e.g., MRI, CT, ICU) but explain them on first use
- Use only information from the provided content - never add or modify details

**NEVER USE THE WORD COMPREHENSIVE**

- NEVER use placeholder comments like "---- Insert more sections ----"
- ALWAYS write out complete content for every section
- NEVER use ellipsis (...) or other shortcuts
- Each plan must have its complete script sections fully written out
- NO abbreviated or templated content
- REJECT any content that uses shortcuts or templating

Use this template structure - maintain all formatting and sections:

Template:
{template}"""

SCRIPT_WRITER_HUMAN_PROMPT = """

Write an educational presentation script for the following content:

Important:
- Create a script that follows the slides exactly
- Each slide's content should be clearly marked with ---- Section Title ----
- Include verbal cues for transitions and animations (v-clicks)
- Maintain professional but engaging tone
- Script should be natural and conversational
- Each v-click point should have its own dedicated paragraph
- Add an extra line before all v-click lines that speaks to the headline of the slide
- Spell out ALL numbers (e.g., "two hundred fifty dollars per day")
- Define insurance terms on first use (e.g., "Fixed Indemnity, which means you receive a set payment amount")
- Use warm, professional tone throughout
- End with an encouraging closing statement
- Make sure there is always a one to one relationship between the slides and the script
-- That means there should be one script section for each slide
-- A slide is broken up by a section header

Here is an example of 3 slides and the script that goes with them:

# slides:
---
id: FEN_TDK
theme: ../../
title: | 
  Transforming Data Through Knowledge
info: |
  ## Transforming Data Through Knowledge Review
  A look at the Transforming Data Through Knowledge benefits and details.
verticalCenter: true
layout: intro
themeConfig:
  logoHeader: ./img/logos/FEN_logo.svg
  audioEnabled: true
transition: fade-out
drawings:
  persist: false
---

<SlideAudio deckKey="FEN_TDK" />

# TDK Plan Overview

Understanding the details and benefits of the **Transforming Data Through Knowledge** plan.

---
transition: fade-out
layout: default
---

## Plan Overview

<v-clicks>

- Provided by **America's Choice Health Care**
- Administration by **Detego Health**
- **Accessibility** for Individuals and Families
- **Emphasizes** Personal impact
- **Ensures** Vital services within reach

</v-clicks>

---
transition: fade-out
layout: default
---

## Core Plan Elements

<v-click>

**Coverage**

- Physician Services and Hospitalization
- Virtual Visits and Prescriptions
- Wellness and Advocacy Services
- Tailored Healthcare options

</v-click>

<v-click>

**Plan Structure**

- Tiered plan options
- Specific Co-pays per service
- Visit Allowances
- Maximum coverage limits

</v-click>

<v-click>

**Eligibility**

- Individual and family coverage
- Emphasis on affordability 
- Access to health services
- Flexible coverage options

</v-click>


script based on the slides above:
---- Cover ----

Hello, everyone! Thank you for joining today's session on the TDK, the Transforming Data Through Knowledge plan. We'll walk through this plan's unique features and benefits, designed to provide accessible healthcare solutions. Let's dive right in!

---- Plan Overview ----

The Transforming Data Through Knowledge plan

is brought to you by America's Choice Health Care, 

with Administration by Detego Health. 

This plan is all about accessibility, ensuring that individuals and families who may not qualify for traditional medical plans can still access vital healthcare services. 

It's designed to have a personal impact, making sure necessary care is within reach.

Moving forward, let's explore the core elements of the plan.

---- Core Plan Elements ----

This plan offers coverage options tailored to a variety of healthcare needs. 

These include Physician Services, Hospitalization, Virtual Visits, Prescriptions, Wellness, and Advocacy Services. 

Each plan tier has specific co-pays, visit allowances, and maximum coverage limits, ensuring flexibility. 

Eligibility is focused on individuals and families who value affordability and health services.

Now, let's look into the common service features.


**Notice that the script is broken up into sections that match the slides**

Here are the processed summaries to use as source content:
{processed_summaries}

Generate a complete presentation script using this slides content:
{slides_content}

EXTRACTED TABLES:
{extracted_tables}

**NEVER USE THE WORD COMPREHENSIVE**  **NEVER USE THE WORD COMPREHENSIVE**  **NEVER USE THE WORD COMPREHENSIVE**

These plans are not comprehensive and to use the word would confuse the audience. We need to make sure we never use the word comprehensive.

Create a natural, engaging script that follows the template structure exactly.
When discussing tables, reference them clearly and explain their key points.
Ensure smooth transitions between sections and maintain a consistent tone throughout.
No shortcuts, no templates, no abbreviations, no ellipses, no placeholders.
return all sections in the order of the slides.
""" 