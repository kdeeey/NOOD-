"""
NOOD - Public Speaking Coach

A Streamlit app for analyzing presentation videos with instant feedback.

Installation:
    pip install streamlit

Run:
    streamlit run streamlit_app.py

Dependencies:
    - combined_analyzer.py (main analysis engine)
    - extract_transcript.py (transcript extraction)
    - Speech Analysis/speech_analyzer.py (ASR model)
"""

import streamlit as st
import tempfile
import json
import sys
from pathlib import Path

# Add project modules to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "Speech Analysis"))

from combined_analyzer import SpeechAndBodyLanguageAnalyzer
from speech_analyzer import load_asr


# ============================================================================
# Configuration
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
# Helper Functions
# ============================================================================

def extract_transcript_from_video(video_path: str) -> str:
    """Extract transcript from video/audio file using ASR."""
    try:
        asr = load_asr()
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


def run_analysis(transcript: str) -> dict:
    """Run complete analysis on transcript."""
    try:
        analyzer = SpeechAndBodyLanguageAnalyzer(transcript=transcript)
        report = analyzer.run_analysis()
        return report, analyzer
    except Exception as e:
        st.error(f"Error during analysis: {str(e)}")
        return None, None


def format_score(score: float, max_score: float = 10) -> str:
    """Format score for display."""
    if score >= 8:
        emoji = "🌟"
    elif score >= 6:
        emoji = "✨"
    elif score >= 4:
        emoji = "💪"
    else:
        emoji = "📈"
    return f"{emoji} {score:.1f}/{int(max_score)}"


def display_section_header(title: str):
    """Display a section header."""
    st.markdown(f"## {title}")


def display_section_subheader(title: str):
    """Display a subsection header."""
    st.markdown(f"### {title}")


# ============================================================================
# Main App Layout
# ============================================================================

# Header
st.title("🎤 NOOD - Public Speaking Coach")
st.markdown("**Upload your presentation video and get instant feedback**")
st.markdown("---")

# File uploader
uploaded_file = st.file_uploader(
    "Upload your presentation video",
    type=["mp4", "mov", "avi", "mkv", "flv", "wmv", "webm"],
    help="Supported formats: MP4, MOV, AVI, MKV, FLV, WMV, WebM",
)


if uploaded_file is not None:
    # Step 1: Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
        tmp_file.write(uploaded_file.getbuffer())
        video_path = tmp_file.name
    
    # Display uploaded video
    st.markdown("### 📹 Your Video")
    st.video(uploaded_file)
    
    # Step 2: Extract transcript
    st.markdown("---")
    with st.spinner("🎙️ Extracting transcript from video... (This may take 1-2 minutes)"):
        transcript = extract_transcript_from_video(video_path)
    
    if transcript:
        st.success("✓ Transcript extracted successfully!")
        
        # Show transcript preview
        with st.expander("View Full Transcript"):
            st.text_area(
                "Transcript:",
                value=transcript,
                height=150,
                disabled=True,
            )
        
        # Step 3: Run analysis
        st.markdown("---")
        with st.spinner("🔍 Analyzing your presentation... (This may take 2-3 minutes)"):
            report, analyzer = run_analysis(transcript)
        
        if report and analyzer:
            st.success("✓ Analysis complete!")
            st.markdown("---")
            
            # ================================================================
            # SECTION 1: Overall Confidence Score
            # ================================================================
            display_section_header("📊 Overall Confidence Score")
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown(f"<h2 style='text-align: center; color: #2E86AB;'>{format_score(analyzer.overall_score)}</h2>", unsafe_allow_html=True)
            with col2:
                st.markdown(f"**Grade:** {analyzer.overall_grade}")
                st.markdown(f"**Proficiency:** {analyzer.overall_proficiency}")
            
            st.markdown("---")
            
            # ================================================================
            # SECTION 2: Speech Observations
            # ================================================================
            display_section_header("🗣️ Speech Observations")
            
            if analyzer.speech_report and isinstance(analyzer.speech_report, dict):
                speech = analyzer.speech_report
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    if "wpm" in speech:
                        st.metric("Speaking Rate", f"{speech['wpm'].get('raw', 0):.0f} WPM")
                    if "overall" in speech:
                        st.metric("Overall Speech Score", f"{speech.get('grade', 'N/A')}")
                
                with col2:
                    if "filler_rate" in speech:
                        st.metric("Filler Words", f"{speech['filler_rate'].get('raw', 0):.1f}%")
                    if "pitch_variation" in speech:
                        st.metric("Pitch Variation", f"{speech['pitch_variation'].get('raw', 0):.1f} Hz")
                
                with col3:
                    if "energy_variation" in speech:
                        st.metric("Energy Variation", f"{speech['energy_variation'].get('raw', 0):.5f}")
                    if "pause_ratio" in speech:
                        st.metric("Pause Ratio", f"{speech['pause_ratio'].get('raw', 0):.1f}%")
                
                # Speech feedback
                if "wpm" in speech and "feedback" in speech["wpm"]:
                    st.info(f"💡 Speaking Rate: {speech['wpm']['feedback']}")
                if "filler_rate" in speech and "feedback" in speech["filler_rate"]:
                    st.info(f"💡 Filler Words: {speech['filler_rate']['feedback']}")
            else:
                st.info("Speech analysis data not available for this transcript.")
            
            st.markdown("---")
            
            # ================================================================
            # SECTION 3: Body Language Observations
            # ================================================================
            display_section_header("🧍 Body Language Observations")
            
            if analyzer.body_language_report and isinstance(analyzer.body_language_report, dict):
                body = analyzer.body_language_report
                st.info("Body language analysis requires video processing. Please ensure the video was analyzed with body language detection enabled.")
            else:
                st.info("📝 Body language analysis requires video frames. Since we're running transcript-only analysis, detailed body language metrics are not available. For full analysis, video must be processed frame-by-frame.")
            
            st.markdown("---")
            
            # ================================================================
            # SECTION 4: Language & Content Feedback
            # ================================================================
            display_section_header("📚 Language & Content Feedback")
            
            if analyzer.language_and_content_report:
                lac = analyzer.language_and_content_report
                
                # Overall language score
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric(
                        "Grammar",
                        f"{lac.grammar_score:.1f}/10",
                        delta=None
                    )
                    if analyzer.grammar_report:
                        st.caption(analyzer.grammar_report.feedback)
                
                with col2:
                    st.metric(
                        "Sentence Structure",
                        f"{lac.sentence_structure_score:.1f}/10",
                    )
                    if analyzer.sentence_structure_report:
                        st.caption(analyzer.sentence_structure_report.feedback)
                
                with col3:
                    st.metric(
                        "Vocabulary",
                        f"{lac.vocabulary_score:.1f}/10",
                    )
                    if analyzer.vocabulary_report:
                        st.caption(analyzer.vocabulary_report.feedback)
                
                with col4:
                    st.metric(
                        "Fluency",
                        f"{lac.fluency_score:.1f}/10",
                    )
                    if analyzer.fluency_report:
                        st.caption(analyzer.fluency_report.feedback)
                
                # Detailed observations
                display_section_subheader("Grammar & Accuracy")
                if analyzer.grammar_report:
                    if analyzer.grammar_report.error_count == 0:
                        st.success("✓ No grammar errors detected! Excellent accuracy.")
                    else:
                        st.warning(f"Found {analyzer.grammar_report.error_count} grammar error(s)")
                        if analyzer.grammar_report.error_examples:
                            for i, example in enumerate(analyzer.grammar_report.error_examples[:3], 1):
                                st.caption(f"{i}. \"{example['original']}\" → \"{example['corrected']}\"")
                
                display_section_subheader("Sentence Structure")
                if analyzer.sentence_structure_report:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Avg. Length", f"{analyzer.sentence_structure_report.avg_sentence_length:.1f} words")
                    with col2:
                        st.metric("Variety", analyzer.sentence_structure_report.variety_level.title())
                    with col3:
                        st.metric("Pattern", analyzer.sentence_structure_report.sentence_length_category.title())
                
                display_section_subheader("Vocabulary & Word Choice")
                if analyzer.vocabulary_report:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Level", analyzer.vocabulary_report.vocabulary_level.title())
                    with col2:
                        st.metric("Unique Words", analyzer.vocabulary_report.unique_words)
                    with col3:
                        st.metric("TTR", f"{analyzer.vocabulary_report.type_token_ratio:.3f}")
                
                display_section_subheader("Fluency & Flow")
                if analyzer.fluency_report:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Repetitions Detected", analyzer.fluency_report.repetition_count)
                    with col2:
                        st.metric("Fluency Level", analyzer.fluency_report.fluency_level.title())
                    
                    if analyzer.fluency_report.repetition_examples:
                        st.caption("Notable repetitions:")
                        for example in analyzer.fluency_report.repetition_examples[:3]:
                            st.caption(f"• '{example['word']}' repeated {example['count']} times")
                
                # Strengths and improvements
                st.markdown("---")
                col1, col2 = st.columns(2)
                
                with col1:
                    display_section_subheader("💪 Your Strengths")
                    if lac.strengths:
                        for strength in lac.strengths:
                            st.success(f"✓ {strength}")
                    else:
                        st.info("Keep working to build your strengths!")
                
                with col2:
                    display_section_subheader("📈 Areas to Improve")
                    if lac.areas_for_improvement:
                        for area in lac.areas_for_improvement:
                            st.warning(f"• {area}")
                    else:
                        st.success("Great work! You're doing well!")
            
            st.markdown("---")
            
            # ================================================================
            # SECTION 5: Actionable Tips
            # ================================================================
            display_section_header("🎯 Top Recommended Actions")
            
            if analyzer.language_and_content_report and analyzer.language_and_content_report.top_recommendations:
                for i, rec in enumerate(analyzer.language_and_content_report.top_recommendations, 1):
                    st.markdown(f"**{i}. {rec}**")
            else:
                st.info("You're doing great! Keep refining your presentation skills.")
            
            st.markdown("---")
            
            # ================================================================
            # SECTION 6: Coach's Note
            # ================================================================
            display_section_header("💬 Coach's Final Message")
            
            if analyzer.overall_score >= 8.0:
                st.success("""
                **Excellent work!** Your presentation demonstrates strong command of the material 
                and clear communication. You're well-prepared and confident. Focus on fine-tuning 
                the details for an even more polished delivery.
                """)
            elif analyzer.overall_score >= 6.0:
                st.info("""
                **Good effort!** You have a solid foundation. By addressing the areas highlighted above, 
                your next presentation will be significantly stronger. Focus on your recommended actions 
                for the most impact.
                """)
            else:
                st.warning("""
                **Keep practicing!** You have room to grow. Focus on the recommended actions in order 
                to build your presentation skills. Each practice session will help you improve. You've got this!
                """)
            
            st.markdown("---")
            
            # ================================================================
            # Download Report
            # ================================================================
            st.markdown("### 📥 Download Full Report")
            report_json = json.dumps(report, indent=2, ensure_ascii=False)
            st.download_button(
                label="Download JSON Report",
                data=report_json,
                file_name="presentation_analysis_report.json",
                mime="application/json",
            )
            
            st.markdown("---")
    
    else:
        st.error("⚠️ Could not extract transcript from video. Please ensure the video contains clear speech.")
        st.markdown("**Troubleshooting:**")
        st.markdown("- Ensure your video has clear audio")
        st.markdown("- Check that the video format is supported")
        st.markdown("- Try a different video file")

st.markdown("---")
st.markdown("""
**⏱️ Processing time:** 1-3 minutes depending on video length

**📝 Note:** This analysis uses AI models for speech recognition, grammar correction, and body language detection. 
Results are optimized for presentations in English.
""")


# ============================================================================
# Footer
# ============================================================================
st.markdown("""
---
<div style='text-align: center; color: gray; font-size: 0.8em;'>
Made with 💙 by NOOD - Your AI Public Speaking Coach
</div>
""", unsafe_allow_html=True)
