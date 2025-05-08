"""
Metin parçalama işlemleri.
"""

import re
from typing import List, Dict, Any, Optional

def split_text(
    text: str, 
    chunk_size: int = 500, 
    chunk_overlap: int = 50,
    split_method: str = "token"
) -> List[str]:
    """
    Metni belirli boyutta parçalara ayırır.
    
    Args:
        text: Parçalanacak metin
        chunk_size: Parça boyutu (token/karakter)
        chunk_overlap: Parçalar arası örtüşme (token/karakter)
        split_method: Parçalama metodu (token, character, sentence, paragraph)
    
    Returns:
        List[str]: Metin parçaları
    """
    if not text:
        return []
    
    if split_method == "token":
        return split_by_tokens(text, chunk_size, chunk_overlap)
    elif split_method == "character":
        return split_by_characters(text, chunk_size, chunk_overlap)
    elif split_method == "sentence":
        return split_by_sentences(text, chunk_size, chunk_overlap)
    elif split_method == "paragraph":
        return split_by_paragraphs(text, chunk_size, chunk_overlap)
    else:
        # Varsayılan olarak token bazlı
        return split_by_tokens(text, chunk_size, chunk_overlap)

def split_by_characters(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    """
    Metni karakter bazında parçalara ayırır.
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        # Parça sonunu hesapla
        end = start + chunk_size
        
        # Son parça kontrolü
        if end >= len(text):
            chunks.append(text[start:])
            break
        
        # Kelime sınırında kes (boşluk ara)
        while end > start and text[end] != ' ':
            end -= 1
            
        # Boşluk bulunamadıysa, doğrudan kes
        if end == start:
            end = start + chunk_size
        
        # Parçayı ekle
        chunks.append(text[start:end])
        
        # Sonraki başlangıç noktasını hesapla
        start = end - chunk_overlap
        
        # Başlangıç negatif veya aynı olmamalı
        if start < 0:
            start = 0
        if start >= end:
            start = end
    
    return chunks

def split_by_tokens(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    """
    Metni yaklaşık token sayısına göre parçalara ayırır.
    Tam bir tokenizer kullanmak yerine kelime sayısına dayanır (4 kelime ~= 3 token).
    """
    # Kelimelere ayır
    words = text.split()
    
    if len(words) <= chunk_size:
        return [text]
        
    # Kelime/token oranı (yaklaşık)
    token_ratio = 0.75
    adjusted_chunk_size = int(chunk_size / token_ratio)
    adjusted_overlap = int(chunk_overlap / token_ratio)
    
    chunks = []
    start = 0
    
    while start < len(words):
        # Parça sonunu hesapla
        end = start + adjusted_chunk_size
        
        # Son parça kontrolü
        if end >= len(words):
            chunks.append(' '.join(words[start:]))
            break
        
        # Parçayı ekle
        chunks.append(' '.join(words[start:end]))
        
        # Sonraki başlangıç noktasını hesapla
        start = end - adjusted_overlap
        
        # Başlangıç negatif veya aynı olmamalı
        if start < 0:
            start = 0
        if start >= end:
            start = end
    
    return chunks

def split_by_sentences(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    """
    Metni cümle bazında parçalara ayırır.
    """
    # Cümlelere ayır
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    if len(sentences) == 1 or len(text) <= chunk_size:
        return [text]
    
    chunks = []
    current_chunk = []
    current_size = 0
    
    for sentence in sentences:
        sentence_size = len(sentence)
        
        # Cümle tek başına çok büyükse, kelime bazlı ayır
        if sentence_size > chunk_size:
            if current_chunk:
                chunks.append(' '.join(current_chunk))
                
                # Önceki chunk'ın son kısmını overlap olarak al
                overlap_words = []
                overlap_size = 0
                
                for word in reversed(current_chunk):
                    if overlap_size + len(word) + 1 > chunk_overlap:
                        break
                    overlap_words.insert(0, word)
                    overlap_size += len(word) + 1
                
                current_chunk = overlap_words
                current_size = overlap_size
            
            # Büyük cümleyi parçala
            sentence_chunks = split_by_tokens(sentence, chunk_size, chunk_overlap)
            
            # İlk parçayı mevcut chunk'a ekle
            if current_chunk:
                current_chunk.append(sentence_chunks[0])
                current_size += sentence_size
                chunks.append(' '.join(current_chunk))
                
                # Diğer parçaları doğrudan ekle
                chunks.extend(sentence_chunks[1:])
            else:
                chunks.extend(sentence_chunks)
            
            current_chunk = []
            current_size = 0
            continue
        
        # Normal durum: cümleyi mevcut chunk'a ekle
        if current_size + sentence_size + 1 > chunk_size and current_chunk:
            chunks.append(' '.join(current_chunk))
            
            # Örtüşme için son cümleleri sakla
            overlap_sentences = []
            overlap_size = 0
            
            for s in reversed(current_chunk):
                if overlap_size + len(s) + 1 > chunk_overlap:
                    break
                overlap_sentences.insert(0, s)
                overlap_size += len(s) + 1
            
            current_chunk = overlap_sentences
            current_size = overlap_size
        
        current_chunk.append(sentence)
        current_size += sentence_size + 1
    
    # Son chunk'ı ekle
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks

def split_by_paragraphs(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    """
    Metni paragraf bazında parçalara ayırır.
    """
    # Paragraflara ayır (boş satırlar)
    paragraphs = re.split(r'\n\s*\n', text)
    
    if len(paragraphs) == 1 or len(text) <= chunk_size:
        return [text]
    
    chunks = []
    current_chunk = []
    current_size = 0
    
    for paragraph in paragraphs:
        paragraph_size = len(paragraph)
        
        # Paragraf tek başına çok büyükse, cümle bazlı ayır
        if paragraph_size > chunk_size:
            if current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = []
                current_size = 0
            
            # Büyük paragrafı parçala
            paragraph_chunks = split_by_sentences(paragraph, chunk_size, chunk_overlap)
            chunks.extend(paragraph_chunks)
            continue
        
        # Normal durum: paragrafı mevcut chunk'a ekle
        if current_size + paragraph_size + 2 > chunk_size and current_chunk:
            chunks.append('\n\n'.join(current_chunk))
            
            # Örtüşme için son paragrafları sakla
            overlap_paragraphs = []
            overlap_size = 0
            
            for p in reversed(current_chunk):
                if overlap_size + len(p) + 2 > chunk_overlap:
                    break
                overlap_paragraphs.insert(0, p)
                overlap_size += len(p) + 2
            
            current_chunk = overlap_paragraphs
            current_size = overlap_size
        
        current_chunk.append(paragraph)
        current_size += paragraph_size + 2  # +2 for "\n\n"
    
    # Son chunk'ı ekle
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))
    
    return chunks