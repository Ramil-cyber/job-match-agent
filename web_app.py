import streamlit as st

MAX_INPUT_CHARACTERS = 15_000


st.set_page_config(
    page_title="Job Match Agent",
    page_icon="📄",
    layout="centered",
)

st.title("Job Match Agent")

st.write(
    "Paste a resume and job description to receive a structured, "
    "evidence-based comparison."
)

st.info(
    "Privacy reminder: Use fictional sample information while the "
    "application is still being developed."
)

with st.form("job_match_form"):
    resume_text = st.text_area(
        "Resume",
        height=250,
        max_chars=MAX_INPUT_CHARACTERS,
        placeholder="Paste the resume text here.",
    )

    job_description_text = st.text_area(
        "Job Description",
        height=250,
        max_chars=MAX_INPUT_CHARACTERS,
        placeholder="Paste the job description here.",
    )

    submitted = st.form_submit_button(
        "Analyze Match",
        type="primary",
        width="stretch",
    )

if submitted:
    if not resume_text.strip() or not job_description_text.strip():
        st.error("Please provide both a resume and a job description.")
    else:
        st.success(
            "Inputs received successfully. The AI connection will be added next."
        )
        st.caption(
            f"Resume: {len(resume_text):,} characters | "
            f"Job description: {len(job_description_text):,} characters"
        )
