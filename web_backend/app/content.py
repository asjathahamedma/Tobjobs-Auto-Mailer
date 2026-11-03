from dataclasses import dataclass
import re


@dataclass(frozen=True)
class ApplicationContent:
    subject: str
    email: str
    cover_letter: str


def generate_application_content(
    *,
    job_title: str,
    company: str,
    applicant_name: str,
    profile_summary: str,
    matched_keywords: list[str],
    contact: dict[str, str],
) -> ApplicationContent:
    title = job_title.strip() or "the advertised position"
    company_name = company.strip() or "your organization"
    name = applicant_name.strip() or "Applicant"
    evidence = ", ".join(list(dict.fromkeys(
        keyword.strip() for keyword in matched_keywords if keyword.strip()
    ))[:4])
    summary = profile_summary.strip()
    generic_terms = {
        "a", "an", "and", "at", "for", "in", "of", "on", "or", "the", "to", "with",
        "engineer", "developer", "manager", "specialist", "analyst", "senior", "junior",
        "lead", "position", "role",
    }
    job_terms = {
        term
        for value in [job_title, *matched_keywords]
        for term in re.findall(r"[a-z0-9+#]+", value.casefold())
        if term not in generic_terms
    }
    summary_terms = set(re.findall(r"[a-z0-9+#]+", summary.casefold()))
    relevant_summary = summary if job_terms & summary_terms else ""

    email_paragraphs = [
        "Dear Hiring Team,",
        f"I am writing to apply for the {title} position advertised on TopJobs.lk.",
    ]
    if relevant_summary:
        email_paragraphs.append(
            f"My attached resume outlines my background relevant to this opportunity. "
            f"{relevant_summary.rstrip('.')}."
        )
    else:
        email_paragraphs.append("I have attached my resume for your consideration.")
    if evidence:
        email_paragraphs.append(
            f"The role's focus on {evidence} is relevant to the skills highlighted in my resume."
        )
    email_paragraphs.extend(
        ["Thank you for your time and consideration.", "Kind regards,", name]
    )
    for key in ("phone", "contact_email", "linkedin", "github", "portfolio"):
        value = contact.get(key, "").strip()
        if value:
            email_paragraphs.append(value)

    cover_paragraphs = [
        "Dear Hiring Manager,",
        f"I am writing to apply for the {title} position at {company_name}.",
    ]
    if relevant_summary:
        cover_paragraphs.append(
            f"My resume provides an overview of my background and skills. "
            f"{relevant_summary.rstrip('.')}."
        )
    else:
        cover_paragraphs.append(
            "I have attached my resume for your consideration and would welcome the opportunity "
            "to discuss my background in relation to this position."
        )
    if evidence:
        cover_paragraphs.append(
            f"The role's focus on {evidence} aligns with the skills highlighted in my resume."
        )
    cover_paragraphs.extend(
        [
            "Thank you for considering my application. I would be pleased to provide further "
            "information and discuss my suitability for the role.",
            "Yours sincerely,",
            name,
        ]
    )
    return ApplicationContent(
        subject=f"Application for {title} - {name}",
        email="\n\n".join(email_paragraphs),
        cover_letter="\n\n".join(cover_paragraphs),
    )
