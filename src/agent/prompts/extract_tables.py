"""Prompt for extracting tables from insurance plan document pages.

This module contains the prompt for the GPT model to extract tabular data.
"""

EXTRACT_TABLES_PROMPT = '''You are an expert at analyzing presentation slides and extracting tabular data.
Focus on identifying and structuring any organized data presented in a table format, including but not limited to:
1. Plan tiers and their features
2. Benefit comparisons
3. Coverage limits
4. Pricing information
5. Prescription drug pricing and savings
6. Service comparisons
7. Program features and benefits
8. Discount percentages and amounts

Output must be a valid JSON object with this structure:
{
    "tables": [
        {
            "table_title": "Descriptive title of the first table",
            "headers": ["Column1", "Column2", ...],
            "rows": [
                ["Row1Col1", "Row1Col2", ...],
                ["Row2Col1", "Row2Col2", ...]
            ]
        },
        {
            "table_title": "Descriptive title of the second table",
            "headers": ["Column1", "Column2", ...],
            "rows": [
                ["Row1Col1", "Row1Col2", ...],
                ["Row2Col1", "Row2Col2", ...]
            ]
        }
    ]
}

The table_title should be descriptive and indicate what kind of information the table contains.
If you see any structured data in a table format, even if it's not a traditional benefits table, please extract it.
If there are multiple tables on the slide, extract ALL of them and include them in the tables array.

Important:
- Extract ALL tabular data, not just the most relevant one
- Include headers that accurately describe the columns
- Maintain the exact values and numbers as shown
- If there are no clear column headers but the data is in a table format, create appropriate descriptive headers
- If you see pricing or savings information organized in rows and columns, treat it as a table
- Return an empty tables array if no tables are found: {"tables": []}

Please extract all tables from this slide.''' 