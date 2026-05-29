#!/usr/bin/env python3
"""
Performance optimization module for CareMate
Implements caching, parallel processing, and latency reduction
"""
import asyncio
import time
import hashlib
import json
import os
from typing import Dict, Optional, Tuple
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

class PerformanceOptimizer:
    """
    Handles caching and performance optimizations for CareMate
    """
    def __init__(self):
        self.response_cache = {}
        self.translation_cache = {}
        self.tts_cache = {}
        self.cache_dir = "cache"
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Load persistent caches
        self._load_caches()
    
    def _load_caches(self):
        """Load caches from disk"""
        try:
            cache_files = {
                'responses': 'response_cache.json',
                'translations': 'translation_cache.json',
                'tts': 'tts_cache.json'
            }
            
            for cache_name, filename in cache_files.items():
                filepath = os.path.join(self.cache_dir, filename)
                if os.path.exists(filepath):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                        if cache_name == 'responses':
                            self.response_cache = cache_data
                        elif cache_name == 'translations':
                            self.translation_cache = cache_data
                        elif cache_name == 'tts':
                            self.tts_cache = cache_data
                            
        except Exception as e:
            logger.warning(f"Cache loading error: {e}")
    
    def _save_caches(self):
        """Save caches to disk"""
        try:
            cache_data = {
                'response_cache.json': self.response_cache,
                'translation_cache.json': self.translation_cache,
                'tts_cache.json': self.tts_cache
            }
            
            for filename, data in cache_data.items():
                filepath = os.path.join(self.cache_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    
        except Exception as e:
            logger.warning(f"Cache saving error: {e}")
    
    def _get_cache_key(self, text: str, context: str = "") -> str:
        """Generate cache key from text and context"""
        combined = f"{text}|{context}".lower().strip()
        return hashlib.md5(combined.encode()).hexdigest()
    
    def get_cached_response(self, user_input: str, intent: str) -> Optional[str]:
        """Get cached AI response"""
        cache_key = self._get_cache_key(user_input, intent)
        return self.response_cache.get(cache_key)
    
    def cache_response(self, user_input: str, intent: str, response: str):
        """Cache AI response"""
        cache_key = self._get_cache_key(user_input, intent)
        self.response_cache[cache_key] = response
        
        # Limit cache size
        if len(self.response_cache) > 1000:
            # Remove oldest entries
            keys = list(self.response_cache.keys())
            for key in keys[:100]:
                del self.response_cache[key]
    
    def get_cached_translation(self, text: str, target_lang: str) -> Optional[str]:
        """Get cached translation"""
        cache_key = self._get_cache_key(text, target_lang)
        return self.translation_cache.get(cache_key)
    
    def cache_translation(self, text: str, target_lang: str, translation: str):
        """Cache translation"""
        cache_key = self._get_cache_key(text, target_lang)
        self.translation_cache[cache_key] = translation
        
        # Limit cache size
        if len(self.translation_cache) > 500:
            keys = list(self.translation_cache.keys())
            for key in keys[:50]:
                del self.translation_cache[key]
    
    def get_cached_tts(self, text: str, lang: str) -> Optional[str]:
        """Get cached TTS audio path"""
        cache_key = self._get_cache_key(text, lang)
        cached_path = self.tts_cache.get(cache_key)
        
        # Verify file still exists
        if cached_path and os.path.exists(cached_path):
            return cached_path
        elif cached_path:
            # Remove invalid cache entry
            del self.tts_cache[cache_key]
        
        return None
    
    def cache_tts(self, text: str, lang: str, audio_path: str):
        """Cache TTS audio path"""
        cache_key = self._get_cache_key(text, lang)
        self.tts_cache[cache_key] = audio_path
    
    def get_instant_response(self, user_input: str, intent: str) -> Optional[str]:
        """
        Get instant response ONLY for very clear, unambiguous requests.
        Avoid intercepting questions — let the ML model handle those.
        """
        user_lower = user_input.lower()
        
        # Only trigger on clear ACTION requests, not questions
        # Questions (why, what, how, do you, can you, is, are) go to the ML model
        question_starters = (
            "why", "what", "how", "do you", "can you", "is ", "are ",
            "does", "did", "will", "would", "could", "should", "tell me",
            "explain", "describe", "who", "when", "where"
        )
        if any(user_lower.startswith(q) for q in question_starters):
            return None  # Let ML model handle all questions
        
        # Ultra-fast responses ONLY for clear, unambiguous action requests
        instant_responses = {
            # Greetings (not questions)
            ("hello", "hi", "hey", "good morning", "good evening"):
                "Hello! I'm CareMate, your hospital assistant. How can I help you today?",
            
            # Clear emergency keywords
            ("emergency", "help me", "i can't breathe", "chest pain", "i am dying"):
                "I'm immediately alerting medical staff. Help is on the way!",
            
            # Clear comfort requests (not questions)
            ("i am bored", "i feel bored", "i'm bored", "feeling bored"):
                "I understand you're feeling bored. I'm here with you — is there anything I can help with?",
            
            # Clear basic needs (action requests, not questions)
            ("i need water", "give me water", "i want water", "can i have water"):
                "I'll request water for you right away.",
            
            ("i need food", "i am hungry", "i'm hungry", "i want food", "give me food"):
                "I'll notify the nutrition team about your meal request.",
            
            ("i need a nurse", "call the nurse", "send a nurse", "nurse please"):
                "I'm alerting a nurse to come to your room right away.",
            
            # Thank you
            ("thank you", "thanks", "thank u", "thank you so much"):
                "You're very welcome! I'm always here to help you.",
        }
        
        for keywords, response in instant_responses.items():
            if any(user_lower == keyword or user_lower.startswith(keyword) for keyword in keywords):
                logger.info(f"Instant response triggered for: {user_input}")
                return response
        
        return None
    
    def save_caches_async(self):
        """Save caches asynchronously"""
        try:
            self._save_caches()
        except Exception as e:
            logger.error(f"Async cache save error: {e}")

# Global optimizer instance
optimizer = PerformanceOptimizer()