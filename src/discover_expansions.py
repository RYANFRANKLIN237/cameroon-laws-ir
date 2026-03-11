import os
import json
import math
from collections import defaultdict
from tqdm import tqdm

INDEX_DIR = "index"
INDEX_PATH = os.path.join(INDEX_DIR, "inverted_index.json")
EXPANSION_OUTPUT = os.path.join(INDEX_DIR, "discovered_expansions.json")

def discover_expansions():
    if not os.path.exists(INDEX_PATH):
        print(f"Error: {INDEX_PATH} not found.")
        return

    print("Loading inverted index...")
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        inverted_index = json.load(f)

    all_units = set()
    for term in inverted_index:
        all_units.update(inverted_index[term].keys())
    
    total_docs = len(all_units)
    # Filter: Alpha only, length > 3, not too common, not too rare
    candidates = {t: set(p.keys()) for t, p in inverted_index.items() 
                  if t.isalpha() and len(t) > 3 and 1 < len(p) < (total_docs * 0.2)}

    unit_to_terms = defaultdict(list)
    for term, units in candidates.items():
        for unit in units:
            unit_to_terms[unit].append(term)

    expansion_dict = defaultdict(list)
    processed_pairs = set()
    
    for unit, unit_terms in tqdm(unit_to_terms.items(), desc="Calculating Jaccard Similarity"):
        unit_terms = sorted(list(set(unit_terms))) # Ensure unique terms per unit
        for i in range(len(unit_terms)):
            for j in range(i + 1, len(unit_terms)):
                t1, t2 = unit_terms[i], unit_terms[j]
                
                # Lexical ordering ensures we only ever evaluate (A, B), never (B, A)
                # This is the "Yin-Yang" killer
                pair = (t1, t2)
                if pair in processed_pairs:
                    continue
                
                intersection = len(candidates[t1].intersection(candidates[t2]))
                union = len(candidates[t1].union(candidates[t2]))
                similarity = intersection / union

                # Keep only significant links
                if similarity >= 0.3:
                    expansion_dict[t1].append({
                        "term": t2,
                        "sim": round(similarity, 3)
                    })
                
                processed_pairs.add(pair)

    # Sort the dictionary keys so your JSON is perfectly ordered for review
    sorted_expansion_dict = dict(sorted(expansion_dict.items()))

    with open(EXPANSION_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(sorted_expansion_dict, f, indent=2)

    print(f"\nSaved {len(sorted_expansion_dict)} non-redundant expansion keys to: {EXPANSION_OUTPUT}")

if __name__ == "__main__":
    discover_expansions()


# def discover_expansions():
#     if not os.path.exists(INDEX_PATH):
#         print(f"Error: {INDEX_PATH} not found.")
#         return

#     print("Loading inverted index...")
#     with open(INDEX_PATH, "r", encoding="utf-8") as f:
#         inverted_index = json.load(f)

#     all_units = set()
#     for term in inverted_index:
#         all_units.update(inverted_index[term].keys())
    
#     total_docs = len(all_units)
#     candidates = {t: set(p.keys()) for t, p in inverted_index.items() 
#                   if t.isalpha() and len(t) > 3 and 1 < len(p) < (total_docs * 0.2)}

#     unit_to_terms = defaultdict(list)
#     for term, units in candidates.items():
#         for unit in units:
#             unit_to_terms[unit].append(term)

#     # Use a set to track processed pairs to avoid Yin-Yang repetition
#     processed_pairs = set()
#     expansion_dict = defaultdict(list)
    
#     for unit, unit_terms in tqdm(unit_to_terms.items(), desc="Mining relationships"):
#         sorted_terms = sorted(unit_terms)
#         for i in range(len(sorted_terms)):
#             for j in range(i + 1, len(sorted_terms)):
#                 t1, t2 = sorted_terms[i], sorted_terms[j]
                
#                 if (t1, t2) in processed_pairs:
#                     continue
                
#                 intersection = len(candidates[t1].intersection(candidates[t2]))
#                 union = len(candidates[t1].union(candidates[t2]))
#                 similarity = intersection / union

#                 # 10x Threshold: Only keep strong relationships
#                 if similarity >= 0.4:
#                     # Logic: Map the rarer word to the more common word or vice versa
#                     # For expansion, we store both but in a flat list format
#                     expansion_dict[t1].append(t2)
#                     expansion_dict[t2].append(t1)
                
#                 processed_pairs.add((t1, t2))

#     with open(EXPANSION_OUTPUT, "w", encoding="utf-8") as f:
#         json.dump(expansion_dict, f, indent=2)

#     print(f"\nSaved {len(expansion_dict)} unique expansion keys to: {EXPANSION_OUTPUT}")

# if __name__ == "__main__":
#     discover_expansions()

# def discover_expansions():
#     if not os.path.exists(INDEX_PATH):
#         print(f"Error: {INDEX_PATH} not found. Build the index first.")
#         return

#     print("Loading inverted index...")
#     with open(INDEX_PATH, "r", encoding="utf-8") as f:
#         inverted_index = json.load(f)

#     # 1. FILTERING: Identify "Candidate Keywords"
#     # We want words that are specific (High IDF) but not typos (DF > 1)
#     all_units = set()
#     for term in inverted_index:
#         all_units.update(inverted_index[term].keys())
    
#     total_docs = len(all_units)
#     candidates = {}

#     for term, postings in inverted_index.items():
#         df = len(postings)
#         # 10x Filter: Ignore numbers, short words, and words appearing in > 20% of docs (noise)
#         if term.isalpha() and len(term) > 3 and 1 < df < (total_docs * 0.2):
#             candidates[term] = set(postings.keys())

#     print(f"Mining {len(candidates)} candidate keywords for relationships...")

#     # 2. CO-OCCURRENCE ANALYSIS
#     # We find terms that share the same legal units
#     related_map = defaultdict(list)
#     terms = list(candidates.keys())

#     # To be efficient, we map units to terms
#     unit_to_terms = defaultdict(list)
#     for term, units in candidates.items():
#         for unit in units:
#             unit_to_terms[unit].append(term)

#     # Calculate Jaccard Similarity for pairs found in the same unit
#     processed_pairs = set()
    
#     for unit, unit_terms in tqdm(unit_to_terms.items(), desc="Analyzing unit context"):
#         # Compare every term in this unit with every other term in this unit
#         for i in range(len(unit_terms)):
#             for j in range(i + 1, len(unit_terms)):
#                 t1, t2 = sorted([unit_terms[i], unit_terms[j]])
                
#                 if (t1, t2) in processed_pairs:
#                     continue
                
#                 # Jaccard = (Docs with both) / (Docs with either)
#                 intersection = len(candidates[t1].intersection(candidates[t2]))
#                 union = len(candidates[t1].union(candidates[t2]))
#                 similarity = intersection / union

#                 # Threshold: 0.3 means they appear together in 30% of their total context
#                 if similarity > 0.3:
#                     related_map[t1].append({"term": t2, "sim": round(similarity, 3)})
#                     related_map[t2].append({"term": t1, "sim": round(similarity, 3)})
                
#                 processed_pairs.add((t1, t2))

#     # 3. SAVE RESULTS
#     with open(EXPANSION_OUTPUT, "w", encoding="utf-8") as f:
#         json.dump(related_map, f, indent=2)

#     print(f"\nExpansion discovery complete.")
#     print(f"Discovered relationships for {len(related_map)} terms.")
#     print(f"Saved to: {EXPANSION_OUTPUT}")

# if __name__ == "__main__":
#     discover_expansions()