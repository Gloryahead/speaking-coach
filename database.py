"""
database.py — Supabase functions for the speaking coach app.

Stores every practice session permanently so you can track
your improvement over time across all devices.
"""

import json
from datetime import datetime

import streamlit as st
from supabase import create_client, Client


def get_client() -> Client:
    """Creates a Supabase client from Streamlit secrets."""
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"],
    )


def save_session(analysis: dict, drill_type: str, feedback: str):
    """Saves a completed practice session to Supabase."""
    supabase = get_client()
    supabase.table("speaking_sessions").insert({
        "recorded_at":   datetime.now().isoformat(),
        "drill_type":    drill_type,
        "transcript":    analysis["transcript"],
        "word_count":    analysis["word_count"],
        "duration_secs": analysis["duration"],
        "wpm":           analysis["wpm"],
        "filler_count":  analysis["filler_total"],
        "filler_words":  json.dumps(analysis["fillers"]),
        "pause_count":   analysis["strategic_pauses"],
        "long_pauses":   analysis["long_pauses"],
        "overall_score": analysis["overall_score"],
        "feedback":      feedback,
    }).execute()


def get_recent_sessions(limit: int = 10) -> list[dict]:
    """Returns the most recent practice sessions, newest first."""
    supabase = get_client()
    result = supabase.table("speaking_sessions") \
        .select("*") \
        .order("recorded_at", desc=True) \
        .limit(limit) \
        .execute()
    return result.data or []


def get_all_sessions() -> list[dict]:
    """Returns all sessions for progress charts."""
    supabase = get_client()
    result = supabase.table("speaking_sessions") \
        .select("recorded_at, overall_score, wpm, filler_count, pause_count, drill_type") \
        .order("recorded_at") \
        .execute()
    return result.data or []
