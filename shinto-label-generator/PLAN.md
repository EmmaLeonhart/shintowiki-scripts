# Expansion Plan: Detailed Entity Labeling Scope

This document defines the specific, literal requirements for the next phase of the Wikidata labeling pipeline.

## 1. Engishiki System (Q1342448)
- **Direct Links**: Label the **Engishiki** item itself and every entity it links to via any property.
- **Jinmyōchō (Q11064932)**:
    - Label the item itself.
    - Traverse all items linked via **has part(s)** (P527).
    - **Recursive Depth**: For every item found via P527, label it AND every entity that *those* items link to.

## 2. Institutional Hierarchies & Ranks
- **Japanese Court Rank (P14005)**: Every entity that is a valid value for this property must be labeled.
- **Modern Shrine Ranking (P13723)**: Every entity that is a valid value for this property must be labeled.

## 3. Deific Entities
- **Shinto Kami**: Label all Japanese Shinto deities.
- **Buddhist Deities**: Label all Japanese Buddhist deities.
- **Scope**: This is exhaustive for all entities identified as Japanese deities.

## 4. Shrine-Specific Context: Tsukiyomi Shrine (Q11516217)
- Using this as a literal requirement: Label every entity and property associated with **Tsukiyomi Shrine (Q11516217)**. This includes its dedicated deities, historical ranks, and any linked geographic or architectural items.

## 5. Execution Logic
- **Phonological Mapping**: Use the established multilang transliteration engines.
- **Recursive Discovery**: SPARQL queries will be designed to crawl P527 and subsequent links to ensure no "leaf" nodes in the Engishiki tree are missed.
- **Systematic Guesswork**: Where official translations are missing, apply the systematic romanization -> script conversion used in the shrine pipeline.
