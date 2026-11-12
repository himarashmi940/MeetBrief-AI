import streamlit as st
from dotenv import load_dotenv

from ai_analysis import BriefGenerationError, generate_meeting_brief
from pdf_generator import PDFGenerationError, create_pdf_report
from research import ResearchError, research_company


load_dotenv()

st.set_page_config(
    page_title="MeetBrief AI",
    page_icon="📋",
    layout="wide",
)

st.title("📋 MeetBrief AI")
st.subheader("Your Intelligent Meeting Preparation Assistant")
st.write(
    "Get AI-powered research, insights and discussion "
    "points before your important meetings."
)
st.divider()
st.header("Prepare Your Meeting")

with st.form("meeting_brief_form"):
    company = st.text_input(
        "Company or Person Name",
        placeholder="Example: Infosys, Google, or a person",
        max_chars=200,
    )
    meeting_date = st.date_input("Meeting Date")
    meeting_context = st.text_area(
        "Meeting Context",
        placeholder="Describe why you are attending this meeting "
                    "and what you want to discuss...",
        max_chars=1500,
    )
    submitted = st.form_submit_button(
        "Generate Meeting Brief",
        type="primary",
    )

if submitted:
    if not company.strip():
        st.warning("Please enter a company or person name.")
    elif not meeting_context.strip():
        st.warning("Please enter the meeting context.")
    else:
        request_key = (
            company.strip(),
            meeting_date.isoformat(),
            meeting_context.strip(),
        )
        previous_result = st.session_state.get("meeting_brief_result")

        if not previous_result or previous_result["request_key"] != request_key:
            try:
                with st.status("Preparing your meeting report...", expanded=True) as progress:
                    cached_research = st.session_state.get("meeting_brief_research")
                    if cached_research and cached_research["request_key"] == request_key:
                        progress.write("1. Using saved company research...")
                        research_data = cached_research["research_data"]
                    else:
                        progress.write("1. Researching company information...")
                        with st.spinner("Researching company information..."):
                            research_data = research_company(
                                company.strip(),
                                meeting_context.strip(),
                            )
                        st.session_state["meeting_brief_research"] = {
                            "request_key": request_key,
                            "research_data": research_data,
                        }

                    cached_briefing = st.session_state.get("meeting_brief_analysis")
                    if cached_briefing and cached_briefing["request_key"] == request_key:
                        progress.write("2. Using the saved Gemini analysis...")
                        briefing = cached_briefing["briefing"]
                    else:
                        progress.write("2. Analysing research with Gemini...")
                        with st.spinner("Analysing research with Gemini..."):
                            briefing = generate_meeting_brief(
                                company.strip(),
                                meeting_context.strip(),
                                research_data,
                            )
                        st.session_state["meeting_brief_analysis"] = {
                            "request_key": request_key,
                            "briefing": briefing,
                        }

                    progress.write("3. Preparing the meeting report...")
                    with st.spinner("Preparing the meeting report..."):
                        sources = research_data.get("results", []) or []
                        pdf_file = create_pdf_report(
                            company.strip(),
                            meeting_date,
                            briefing,
                            sources=sources,
                        )

                    st.session_state["meeting_brief_result"] = {
                        "request_key": request_key,
                        "briefing": briefing,
                        "research_data": research_data,
                        "pdf_file": pdf_file.getvalue(),
                    }
                    progress.update(
                        label="Your meeting report is ready.",
                        state="complete",
                    )
            except (ResearchError, BriefGenerationError, PDFGenerationError) as error:
                st.error(str(error))
        else:
            st.info("Showing the existing briefing; no additional API requests were made.")

result = st.session_state.get("meeting_brief_result")
current_key = (
    company.strip(),
    meeting_date.isoformat(),
    meeting_context.strip(),
)
if result and result["request_key"] == current_key:
    st.success("Your meeting briefing is ready!")
    st.divider()
    st.header("Your Meeting Brief")
    st.markdown(f"**Company / Person:** {company.strip()}")
    st.markdown(f"**Meeting Date:** {meeting_date}")
    st.markdown(result["briefing"])

    st.divider()
    st.subheader("Research Sources")
    sources = result["research_data"].get("results", []) or []
    valid_sources = [
        source for source in sources
        if isinstance(source, dict)
        and isinstance(source.get("url"), str)
        and source["url"].startswith(("http://", "https://"))
    ]
    if valid_sources:
        for index, source in enumerate(valid_sources, start=1):
            st.link_button(
                f"{index}. {source.get('title') or 'Research source'}",
                source["url"],
            )
    else:
        st.info("No source links were returned.")

    st.download_button(
        label="📄 Download Meeting Brief as PDF",
        data=result["pdf_file"],
        file_name="MeetBrief_Report.pdf",
        mime="application/pdf",
    )

st.divider()
st.caption("MeetBrief AI | Intelligent Meeting Preparation")
