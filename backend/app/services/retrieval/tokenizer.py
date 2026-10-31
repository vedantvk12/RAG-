import re

def tokenize(text: str) -> list[str]:
    """
    Conservative tokenization for BM25.
    Preserves meaningful technical terms like C++, C#, Node.js, GPT-4.
    Lowercases text but avoids aggressive stripping of embedded punctuation.
    """
    if not text or not isinstance(text, str):
        return []
    text = text.lower()
    
    # Strategy:
    # 1. We want to split on whitespace and generic sentence-ending punctuation 
    #    (like period at the end of a word, commas, quotes, brackets).
    # 2. But we want to preserve internal dots, pluses, dashes (e.g. node.js, c++, gpt-4).
    
    # Split on whitespace first
    raw_tokens = text.split()
    
    cleaned_tokens = []
    for token in raw_tokens:
        # Strip trailing punctuation that's likely not part of a tech term
        # (e.g., "node.js," -> "node.js", "end." -> "end")
        token = token.strip('.,:;!?"\'()[]{}')
        
        # If after stripping it's empty, skip
        if not token:
            continue
            
        cleaned_tokens.append(token)
        
    return cleaned_tokens
