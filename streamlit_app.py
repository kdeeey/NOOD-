"""
NOOD - Public Speaking Coach

A Streamlit app for analyzing presentation videos with instant feedback.

Installation:
    pip install -r requirements.txt

Run locally:
    streamlit run streamlit_app.py

Dependencies:
    - combined_analyzer.py (main analysis engine)
    - Speech Analysis/speech_analyzer.py (ASR model)
"""

import streamlit as st
import tempfile
import json
import sys
from pathlib import Path

# ============================================================================
# Streamlit Config (MUST be first)
# ============================================================================

st.set_page_config(
    page_title="NOOD - Public Speaking Coach",
    page_icon="🎤",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Suppress warnings
import warnings
warnings.filterwarnings('ignore')


# ============================================================================
# Imports
# ============================================================================

# Add project modules to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "Speech Analysis"))

try:
    from combined_analyzer import SpeechAndBodyLanguageAnalyzer
except ImportError as e:
    st.error(f"❌ Import Error: {str(e)}")
    st.markdown("""
    **To fix:** Run `pip install -r requirements.txt`
    """)
    st.stop()


# ============================================================================
# Model Caching
# ============================================================================

@st.cache_resource(show_spinner=False)
def get_asr_model():
    """Load ASR model once and cache it."""
    try:
        from speech_analyzer import load_asr
        return load_asr()
    except Exception as e:
        st.error(f"Failed to load speech recognition model: {str(e)}")
        return None


# ============================================================================
# Helper Functions
# ============================================================================

def extract_transcript_from_video(video_path: str) -> str:
    """Extract transcript from video using cached ASR."""
    try:
        asr = get_asr_model()
        if asr is None:
            return None
        
        transcript = asr.transcribe_file(video_path)
        
        # Handle different return types
        if isinstance(transcript, (list, tuple)):
            transcript = transcript[0] if transcript else ""
        else:
            transcript = str(transcript)
        
        return transcript if transcript and transcript.strip() else None
    except Exception as e:
        st.error(f"Error extracting transcript: {str(e)}")
        return None


def run_analysis(transcript: str):
    """Run complete analysis on transcript."""
    try:
        analyzer = SpeechAndBodyLanguageAnalyzer(transcript=transcript)
        report = analyzer.run_analysis()
        return report, analyzer
    except Exception as e:
        st.error(f"Error during analysis: {str(e)}")
        return None, None


def format_score(score: float) -> str:
    """Format score for display."""
    if score >= 8:
        emoji = "🌟"
    elif score >= 6:
        emoji = "✨"
    elif score >= 4:
        emoji = "💪"
    else:
        emoji = "📈"
    return f"{emoji} {score:.1f}/10"


# ============================================================================
# Main UI
# ============================================================================

# Header (render once)
st.markdown("<h1 style='text-align: center;'>🎤 NOOD - Public Speaking Coach</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'><b>Upload your presentation video and get instant feedback</b></p>", unsafe_allow_html=True)
st.markdown("---")

# File uploader with unique key
uploaded_file = st.file_uploader(
    "Upload your presentation video",
    type=["mp4", "mov", "avi", "mkv", "flv", "wmv", "webm"],
    help="Supported formats: MP4, MOV, AVI, MKV, FLV, WMV, WebM",
    key="video_uploader_nood",
)


if uploaded_file is not None:
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
        tmp_file.write(uploaded_file.getbuffer())
        video_path = tmp_file.name
    
    # Show video
    st.markdown("### 📹 Your Video")
    st.video(uploaded_file)
    
    # Extract transcript
    st.markdown("---")
    st.markdown("### Processing...")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    status_text.text("🎙️ Loading speech recognition model...")
    progress_bar.progress(20)
    
    status_text.text("🎙️ Extracting transcript from video...")
    progress_bar.progress(50)
    
    transcript = extract_transcript_from_video(video_path)
    progress_bar.progress(100)
    status_text.empty()
    progress_bar.empty()
    
    if transcript:
        st.success("✓ Transcript extracted!")
        
        # Show transcript
        with st.expander("📄 View Full Transcript", expanded=False):
            st.text_area(
                "Transcript:",
                value=transcript,
                height=150,
                disabled=True,
                key="transcript_text",
            )
        
        # Run analysis
        st.markdown("---")
        st.markdown("### Analyzing...")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("🔍 Analyzing Grammar, Structure, Vocabulary, and Fluency...")
        progress_bar.progress(50)
        
        report, analyzer = run_analysis(transcript)
        
        progress_bar.progress(100)
        status_text.empty()
        progress_bar.empty()
        
        if report and analyzer:
            st.success("✓ Analysis complete!")
            st.markdown("---")
            
            # SECTION 1: Overall Score
            st.markdown("## 📊 Overall Confidence Score")
            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown(f"<h2 style='text-align: center; color: #2E86AB;'>{format_score(analyzer.overall_score)}</h2>", unsafe_allow_html=True)
            with col2:
                st.markdown(f"**Grade:** {analyzer.overall_grade}")
                st.markdown(f"**Proficiency:** {analyzer.overall_proficiency}")
            
            st.markdown("---")
            
            # SECTION 2: Speech
            st.markdown("## 🗣️ Speech Observations")
            if analyzer.speech_report and isinstance(analyzer.speech_report, dict):
                speech = analyzer.speech_report
                col1, col2, col3 = st.columns(3)
                with col1:
                    if "wpm" in speech:
                        st.metric("Speaking Rate", f"{speech['wpm'].get('raw', 0):.0f} WPM")
                with col2:
                    if "filler_rate" in speech:
                        st.metric("Filler Words", f"{speech['filler_rate'].get('raw', 0):.1f}%")
                with col3:
                    if "pause_ratio" in speech:
                        st.metric("Pause Ratio", f"{speech['pause_ratio'].get('raw', 0):.1f}%")
            else:
                st.info("No speech data available.")
            st.markdown("---")
            
            # SECTION 3: Language & Content
            st.markdown("## 📚 Language & Content Feedback")
            if analyzer.language_and_content_report:
                lac = analyzer.language_and_content_report
                
                # Scores
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Grammar", f"{lac.grammar_score:.1f}/10")
                with col2:
                    st.metric("Structure", f"{lac.sentence_structure_score:.1f}/10")
                with col3:
                    st.metric("Vocabulary", f"{lac.vocabulary_score:.1f}/10")
                with col4:
                    st.metric("Fluency", f"{lac.fluency_score:.1f}/10")
                
                # Grammar details
                st.markdown("### Grammar & Accuracy")
                if analyzer.grammar_report:
                    if analyzer.grammar_report.error_count == 0:
                        st.success("✓ No grammar errors!")
                    else:
                        st.warning(f"Found {analyzer.grammar_report.error_count} error(s)")
                        if analyzer.grammar_report.error_examples:
                            for example in analyzer.grammar_report.error_examples[:3]:
                                st.caption(f"→ \"{example['original']}\" should be \"{example['corrected']}\"")
                
                # Strengths & Improvements
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("### 💪 Strengths")
                    if lac.strengths:
                        for s in lac.strengths:
                            st.success(f"✓ {s}")
                    else:
                        st.info("Keep working on your skills!")
                
                with col2:
                    st.markdown("### 📈 Areas to Improve")
                    if lac.areas_for_improvement:
                        for a in lac.areas_for_improvement:
                            st.warning(f"• {a}")
                    else:
                        st.success("Great job!")
            
            st.markdown("---")
            
            # SECTION 4: Recommendations
            st.markdown("## 🎯 Top Recommended Actions")
            if analyzer.language_and_content_report and analyzer.language_and_content_report.top_recommendations:
                for i, rec in enumerate(analyzer.language_and_content_report.top_recommendations, 1):
                    st.markdown(f"**{i}. {rec}**")
            else:
                st.info("You're doing great!")
            
            st.markdown("---")
            
            # SECTION 5: Coach Message
            st.markdown("## 💬 Coach's Message")
            if analyzer.overall_score >= 8.0:
                st.success("**Excellent work!** You're well-prepared and confident. Focus on fine-tuning details.")
            elif analyzer.overall_score >= 6.0:
                st.info("**Good effort!** You have a solid foundation. Address the areas above for next time.")
            else:
                st.warning("**Keep practicing!** Each session helps you improve. You've got this! 💪")
            
            st.markdown("---")
            
            # Download report
            st.markdown("### 📥 Download Full Report")
            report_json = json.dumps(report, indent=2, ensure_ascii=False)
            st.download_button(
                label="📊 Download JSON Report",
                data=report_json,
                file_name="presentation_analysis_report.json",
                mime="application/json",
                key="download_report",
            )
    
    else:
        st.error("⚠️ Could not extract transcript.")
        st.markdown("**Make sure:** Video has clear audio, format is supported, audio quality is good")

st.markdown("---")
st.markdown("""
**⏱️ Processing Time:** 1-3 minutes (first run: 3-5 min for model download)

**📝 Note:** Optimized for presentations in English.
""")

st.markdown("""
---
<div style='text-align: center; color: gray; font-size: 0.8em;'>
Made with 💙 by NOOD - Your AI Public Speaking Coach
</div>
""", unsafe_allow_html=True)
